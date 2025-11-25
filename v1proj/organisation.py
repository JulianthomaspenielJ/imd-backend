#!/usr/bin/env python3
"""
ims_org_cur_aggregator.py

- Reads DB connection info from .env
- Reads parent AWS credentials from organisation_account (is_parent = true)
- Uses Organizations to list linked accounts
- Reads CUR files from parent's S3 bucket/prefix
- Aggregates cost per account and per service
- Inserts into Postgres table 'db_costs'
- Prints summary: overall cost, parent cost breakdown, child costs & service breakdown
"""

import os
import io
import sys
from collections import defaultdict, OrderedDict
from decimal import Decimal
from dotenv import load_dotenv
import logging

import boto3
import pandas as pd
import psycopg2
from psycopg2.extras import execute_values

# ---------- Load env ----------
load_dotenv()

DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_PORT = int(os.getenv('DB_PORT', 5432))
DB_NAME = os.getenv('DB_NAME', 'ims')
DB_USER = os.getenv('DB_USER', 'postgres')
DB_PASSWORD = os.getenv('DB_PASSWORD', '')

AWS_DEFAULT_REGION = os.getenv('AWS_DEFAULT_REGION', 'us-east-1')
TMP_DIR = os.getenv('TMP_DIR', '/tmp/ims_cur')
os.makedirs(TMP_DIR, exist_ok=True)

# ---------- Logging ----------
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
log = logging.getLogger("ims_cur")

# ---------- DB helpers ----------
def get_db_conn():
    return psycopg2.connect(
        host=DB_HOST, port=DB_PORT, dbname=DB_NAME, user=DB_USER, password=DB_PASSWORD
    )

def ensure_tables(conn):
    cur = conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS organisation_account (
        account_id BIGINT PRIMARY KEY,
        account_name VARCHAR(200),
        access_key VARCHAR(100),
        secret_key VARCHAR(200),
        bucket_name VARCHAR(200),
        prefix VARCHAR(500),
        is_parent BOOLEAN DEFAULT FALSE
    );
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS db_costs (
        id SERIAL PRIMARY KEY,
        account_id BIGINT,
        account_name VARCHAR(200),
        service VARCHAR(200),
        billing_period_start DATE,
        billing_period_end DATE,
        total_cost NUMERIC(18,4),
        usage_quantity NUMERIC(18,4),
        currency VARCHAR(20),
        inserted_at TIMESTAMP DEFAULT NOW()
    );
    """)
    conn.commit()
    cur.close()

# ---------- CUR reading helpers ----------
def read_s3_to_df(s3_client, bucket, key):
    """Download object and parse to pandas DataFrame. Supports csv, csv.gz, parquet."""
    obj = s3_client.get_object(Bucket=bucket, Key=key)
    data = obj['Body'].read()
    keyl = key.lower()
    if keyl.endswith('.parquet'):
        return pd.read_parquet(io.BytesIO(data))
    if keyl.endswith('.csv') or keyl.endswith('.csv.gz'):
        if keyl.endswith('.csv.gz'):
            return pd.read_csv(io.BytesIO(data), compression='gzip', low_memory=False)
        else:
            return pd.read_csv(io.BytesIO(data), low_memory=False)
    raise ValueError("Unsupported file type: " + key)

def detect_cols(df):
    """Detect columns used for account id, service, cost, usage, currency, billing period."""
    cols = set([c.lower() for c in df.columns])
    mapping = {}
    for c in ['line_item_usage_account_id','payer_account_id','account_id','billing_account_id']:
        if c in cols:
            mapping['acct'] = c
            break
    for c in ['line_item_product_code','product_product_name','product_name','product','service']:
        if c in cols:
            mapping['service'] = c
            break
    for c in ['line_item_unblended_cost','unblended_cost','line_item_blended_cost','blended_cost','cost']:
        if c in cols:
            mapping['cost'] = c
            break
    for c in ['line_item_usage_amount','usage_amount','usage_quantity','usagequantity']:
        if c in cols:
            mapping['usage'] = c
            break
    for c in ['line_item_currency_code','currency_code','currency']:
        if c in cols:
            mapping['currency'] = c
            break
    for c in ['bill_billing_period_start_date','billing_period_start','bill_billing_period_start']:
        if c in cols:
            mapping['start'] = c
            break
    for c in ['bill_billing_period_end_date','billing_period_end','bill_billing_period_end']:
        if c in cols:
            mapping['end'] = c
            break
    return mapping

def safe_decimal(v):
    try:
        if pd.isna(v):
            return Decimal('0.0')
        return Decimal(str(v))
    except Exception:
        s = str(v).replace(',','').strip()
        try:
            return Decimal(s)
        except Exception:
            return Decimal('0.0')

# ---------- Main ----------
def main():
    log.info("IMS Org CUR Aggregator starting")

    # DB connect
    conn = get_db_conn()
    ensure_tables(conn)
    cur = conn.cursor()

    # Read parent row
    cur.execute("""
        SELECT account_id, account_name, access_key, secret_key, bucket_name, prefix
        FROM organisation_account WHERE is_parent = true LIMIT 1
    """)
    parent_row = cur.fetchone()
    if not parent_row:
        log.error("No parent found in organisation_account (set is_parent = true for parent). Exiting.")
        conn.close()
        sys.exit(1)

    parent_account_id, parent_account_name, parent_ak, parent_sk, bucket_name, prefix = parent_row
    log.info(f"Using parent: id={parent_account_id} name={parent_account_name} bucket={bucket_name} prefix={prefix}")

    # Create boto3 session using parent keys
    session = boto3.Session(
        aws_access_key_id=parent_ak,
        aws_secret_access_key=parent_sk,
        region_name=AWS_DEFAULT_REGION
    )
    org_client = session.client('organizations')
    s3_client = session.client('s3')

    # 1) Discover child accounts via Organizations
    child_accounts = []
    try:
        paginator = org_client.get_paginator('list_accounts')
        for page in paginator.paginate():
            for a in page.get('Accounts', []):
                child_accounts.append({
                    'Id': a['Id'],
                    'Name': a.get('Name',''),
                    'Email': a.get('Email',''),
                    'Status': a.get('Status','')
                })
        log.info(f"Found {len(child_accounts)} accounts in Organization (including management account).")
    except Exception as e:
        log.warning("Could not call Organizations.list_accounts (permissions issue?). Will rely on CUR account IDs. Exception: %s", e)

    # 2) Scan CUR files in S3 prefix and aggregate
    paginator = s3_client.get_paginator('list_objects_v2')
    pageit = paginator.paginate(Bucket=bucket_name, Prefix=prefix)
    overall_service_totals = defaultdict(Decimal)
    per_account = OrderedDict()
    grand_total = Decimal('0.0')

    files_processed = 0
    for page in pageit:
        for obj in page.get('Contents', []):
            key = obj['Key']
            if key.endswith('/') or key.endswith('.manifest'):
                continue
            if not (key.lower().endswith('.csv') or key.lower().endswith('.csv.gz') or key.lower().endswith('.parquet')):
                continue
            files_processed += 1
            log.info(f"Processing s3://{bucket_name}/{key}")
            try:
                df = read_s3_to_df(s3_client, bucket_name, key)
            except Exception as e:
                log.exception("Failed to read S3 object %s: %s", key, e)
                continue

            if df.empty:
                log.info("File empty, skipping.")
                continue

            df.columns = [c.lower() for c in df.columns]
            mapping = detect_cols(df)
            if 'cost' not in mapping or 'service' not in mapping:
                log.warning("Cannot find cost or service column in file %s. Skipping.", key)
                continue

            acct_col = mapping.get('acct')
            svc_col = mapping['service']
            cost_col = mapping['cost']
            usage_col = mapping.get('usage')
            currency_col = mapping.get('currency')
            start_col = mapping.get('start')
            end_col = mapping.get('end')

            # --- Case 1: CUR has account column ---
            if acct_col and acct_col in df.columns:
                group_cols = [acct_col, svc_col]
                grouped = df.groupby(group_cols)[cost_col].sum().reset_index()
                usage_grp = None
                if usage_col and usage_col in df.columns:
                    usage_grp = df.groupby(group_cols)[usage_col].sum().reset_index().set_index([acct_col, svc_col])

                for _, row in grouped.iterrows():
                    acct_id = str(row[acct_col])
                    svc = row[svc_col] if pd.notna(row[svc_col]) else 'Unknown'
                    cost = safe_decimal(row[cost_col])

                    usage = None
                    if usage_grp is not None:
                        try:
                            usage_val = usage_grp.loc[(acct_id, svc)][usage_col]
                            usage = safe_decimal(usage_val)
                        except Exception:
                            usage = None

                    acct_name = None
                    if child_accounts:
                        for a in child_accounts:
                            if a['Id'] == acct_id:
                                acct_name = a['Name'] or acct_name
                                break
                    if not acct_name:
                        acct_name = f"Account-{acct_id}"

                    if acct_id not in per_account:
                        per_account[acct_id] = {'account_name': acct_name, 'total': Decimal('0.0'), 'services': defaultdict(Decimal)}
                    per_account[acct_id]['services'][svc] += cost
                    per_account[acct_id]['total'] += cost
                    overall_service_totals[svc] += cost
                    grand_total += cost

                # Insert aggregated rows
                insert_rows = []
                bstart = bend = None
                try:
                    if start_col and start_col in df.columns:
                        v = df[start_col].dropna().astype(str).iloc[0]
                        bstart = pd.to_datetime(v).date()
                    if end_col and end_col in df.columns:
                        v = df[end_col].dropna().astype(str).iloc[0]
                        bend = pd.to_datetime(v).date()
                except Exception:
                    bstart = bend = None

                file_grouped = df.groupby([acct_col, svc_col])[cost_col].sum().reset_index()
                for _, r in file_grouped.iterrows():
                    acct_id = str(r[acct_col])
                    svc = r[svc_col] if pd.notna(r[svc_col]) else 'Unknown'
                    cost = safe_decimal(r[cost_col])
                    insert_rows.append((int(acct_id), f"Account-{acct_id}", svc, bstart, bend, float(cost), None, None))

                if insert_rows:
                    try:
                        cur2 = conn.cursor()
                        sql = """
                        INSERT INTO db_costs (account_id, account_name, service, billing_period_start, billing_period_end, total_cost, usage_quantity, currency)
                        VALUES %s
                        """
                        execute_values(cur2, sql, insert_rows, page_size=100)
                        conn.commit()
                        cur2.close()
                    except Exception as e:
                        conn.rollback()
                        log.exception("Failed inserting aggregated rows: %s", e)

            # --- Case 2: No account column ---
            else:
                total_cost = safe_decimal(df[cost_col].sum())
                svc_grouped = df.groupby(svc_col)[cost_col].sum().reset_index()
                acct_id = str(parent_account_id)
                acct_name = parent_account_name
                if acct_id not in per_account:
                    per_account[acct_id] = {'account_name': acct_name, 'total': Decimal('0.0'), 'services': defaultdict(Decimal)}
                for _, r in svc_grouped.iterrows():
                    svc = r[svc_col] if pd.notna(r[svc_col]) else 'Unknown'
                    cost = safe_decimal(r[cost_col])
                    per_account[acct_id]['services'][svc] += cost
                    per_account[acct_id]['total'] += cost
                    overall_service_totals[svc] += cost
                    grand_total += cost

                insert_rows = []
                for _, r in svc_grouped.iterrows():
                    svc = r[svc_col] if pd.notna(r[svc_col]) else 'Unknown'
                    cost = safe_decimal(r[cost_col])
                    insert_rows.append((int(parent_account_id), acct_name, svc, None, None, float(cost), None, None))
                if insert_rows:
                    try:
                        cur2 = conn.cursor()
                        sql = """
                        INSERT INTO db_costs (account_id, account_name, service, billing_period_start, billing_period_end, total_cost, usage_quantity, currency)
                        VALUES %s
                        """
                        execute_values(cur2, sql, insert_rows, page_size=100)
                        conn.commit()
                        cur2.close()
                    except Exception as e:
                        conn.rollback()
                        log.exception("Failed inserting aggregated rows (no acct col): %s", e)

    if files_processed == 0:
        log.warning("No CUR files processed under the given prefix. Check prefix and S3 permissions.")

    # ---------- Print summary ----------
    print("\n" + "="*80)
    print(f"Overall Cost = ${grand_total:.2f}")
    print("="*80 + "\n")

    parent_id_str = str(parent_account_id)
    if parent_id_str in per_account:
        p = per_account[parent_id_str]
        print(f"Parent Account (id={parent_id_str}, name={parent_account_name}) = ${p['total']:.2f}")
        for svc, cost in sorted(p['services'].items(), key=lambda kv: -kv[1]):
            print(f"   {svc}: ${cost:.2f}")
        print("")

    for acct_id, info in per_account.items():
        if acct_id == parent_id_str:
            continue
        print(f"Child Account (id={acct_id}, name={info['account_name']}) = ${info['total']:.2f}")
        for svc, cost in sorted(info['services'].items(), key=lambda kv: -kv[1]):
            print(f"   {svc}: ${cost:.2f}")
        print("")

    if child_accounts:
        seen = set(per_account.keys())
        for a in child_accounts:
            aid = a['Id']
            if aid not in seen:
                print(f"Child Account (id={aid}, name={a.get('Name','')}) = $0.00 (no usage rows found in CUR)")

    print("\nOverall service breakdown:")
    for svc, cost in sorted(overall_service_totals.items(), key=lambda kv: -kv[1]):
        print(f"   {svc}: ${cost:.2f}")

    print("\nDone. Aggregated rows were inserted into 'db_costs'.\n")
    conn.close()

if __name__ == '__main__':
    main()
