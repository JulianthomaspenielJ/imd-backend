import boto3
import psycopg2
import gzip
import csv
import io
import json
from datetime import datetime, timedelta
from psycopg2.extras import execute_values
from decimal import Decimal, ROUND_HALF_UP, InvalidOperation

# ------------------ DB Config ------------------
DB_CONFIG = {
    "host": "localhost",
    "dbname": "ims",
    "user": "postgres",
    "password": "Abcd@1234"
}

# ------------------ Date Range ------------------
start_date = datetime.utcnow().replace(day=1).strftime('%Y-%m-%d')
end_date = (datetime.utcnow() - timedelta(days=1)).strftime('%Y-%m-%d')

# ------------------ Helpers ------------------
def to_decimal(val):
    """Safe Decimal converter that handles '', None, and non-numeric cases."""
    if val is None:
        return Decimal('0')
    s = str(val).strip()
    if not s:
        return Decimal('0')
    try:
        return Decimal(s)
    except InvalidOperation:
        try:
            return Decimal(str(float(s)))
        except Exception:
            return Decimal('0')

def round2(d: Decimal) -> Decimal:
    """Round HALF UP to 2 decimal places (e.g. 0.9999 -> 1.00)."""
    return d.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

# ------------------ Fetch AWS Accounts ------------------
def get_accounts():
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    # fetch account_name as well so we can show account-friendly name in summary
    cur.execute("SELECT account_id, account_name, access_key, secret_key, bucket_name, prefix FROM cur_multiple_user")
    accounts = cur.fetchall()
    cur.close()
    conn.close()
    return accounts

# ------------------ Normalize Region ------------------
def normalize_region(row):
    return (
        row.get("product_region") or
        row.get("product_location") or
        row.get("availability_zone") or
        row.get("line_item_availability_zone") or
        "Any"
    )

# ------------------ Resolve Service ------------------
def resolve_service(row):
    base_service = (row.get("line_item_product_code") or "").strip()
    operation = (row.get("line_item_operation") or "").strip()
    if base_service == "AmazonEC2":
        if "RunInstances" in operation:
            return "AmazonEC2"
        else:
            return "AmazonEC2-Other"
    return base_service

# ------------------ Process CUR File ------------------
def process_cur(account_id, access_key, secret_key, bucket_name, prefix):
    session = boto3.Session(
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        region_name='us-east-1'
    )
    s3 = session.client('s3')

    try:
        response = s3.list_objects_v2(Bucket=bucket_name, Prefix=prefix)
    except Exception as e:
        print(f"[ERROR] Unable to list objects in bucket {bucket_name} for {account_id}: {e}")
        return []

    if 'Contents' not in response or not response['Contents']:
        print(f"[WARNING] No CUR files for account {account_id}")
        return []

    files = sorted(response['Contents'], key=lambda x: x['LastModified'], reverse=True)
    latest_file_key = files[0]['Key']
    try:
        obj = s3.get_object(Bucket=bucket_name, Key=latest_file_key)
    except Exception as e:
        print(f"[ERROR] Unable to get object {latest_file_key} from {bucket_name} for {account_id}: {e}")
        return []

    file_bytes = obj['Body'].read()
    bytestream = io.BytesIO(file_bytes)

    if latest_file_key.endswith(".gz"):
        file_obj = gzip.GzipFile(fileobj=bytestream, mode='rb')
    else:
        file_obj = bytestream

    reader = csv.DictReader(io.TextIOWrapper(file_obj, encoding='utf-8-sig'))

    cost_map = {}

    for row in reader:
        # usage date normalized to YYYY-MM-DD
        usage_date = (row.get("line_item_usage_start_date", "") or "")[:10]
        if not usage_date or not (start_date <= usage_date <= end_date):
            continue

        resource_id = row.get("line_item_resource_id", "") or ""
        unblended_cost = to_decimal(row.get("line_item_unblended_cost", "0"))

        # parse resource tags safely
        tags = {}
        try:
            tags_raw = row.get("resource_tags", "")
            if tags_raw and tags_raw.strip():
                # CUR sometimes stores tags as a python-style dict string; convert safely
                tags = json.loads(tags_raw.replace("'", '"'))
        except Exception:
            tags = {}

        name = (
            row.get("resource_tags_user_Name", "") or
            row.get("resource_tags_user_name", "") or
            tags.get("user_name", "")
        )
        owner = (
            row.get("resource_tags_user_Owner", "") or
            row.get("resource_tags_user_owner", "") or
            tags.get("user_owner", "")
        )
        environment = (
            row.get("resource_tags_user_Environment", "") or
            row.get("resource_tags_user_environment", "") or
            tags.get("user_environment", "")
        )

        service = resolve_service(row)
        region = normalize_region(row)
        usage_type = row.get("line_item_usage_type", "") or ""
        record_type = row.get("line_item_line_item_type", "") or ""
        instance_type = row.get("product_instance_type", "") or ""

        key = (account_id, usage_date, resource_id, service)
        entry = cost_map.get(key)
        if entry:
            entry["unblended_cost"] += unblended_cost
        else:
            cost_map[key] = {
                "unblended_cost": unblended_cost,
                "region": region,
                "usage_type": usage_type,
                "service": service,
                "name": name,
                "owner": owner,
                "environment": environment,
                "record_type": record_type,
                "instance_type": instance_type
            }

    result = []
    # sort by usage_date then resource etc
    for (acc, usage_date, resource_id, service), vals in sorted(cost_map.items(), key=lambda x: x[0][1]):
        amount = round2(vals["unblended_cost"])
        # store Decimal (numeric) directly, not string
        result.append((
            acc,
            usage_date,
            amount,
            resource_id,
            vals["region"],
            vals["usage_type"],
            service,
            vals["name"],
            vals["owner"],
            vals["environment"],
            vals["record_type"],
            vals["instance_type"]
        ))
    return result

# ------------------ Insert or Update ------------------
def insert_to_db(rows):
    if not rows:
        return
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()

    # create table if not exists (keeping your column layout)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS multiple_user_cur(
            account_id     VARCHAR NOT NULL,
            usage_date     DATE NOT NULL,
            unblended_cost NUMERIC(18,2),
            resource_id    TEXT NOT NULL,
            region         TEXT,
            usage_type     TEXT,
            service        TEXT NOT NULL,
            name           TEXT,
            owner          TEXT,
            environment    TEXT,
            record_type    TEXT,
            instance_type  TEXT,
            PRIMARY KEY (account_id, usage_date, resource_id, service)
        )
    """)

    insert_query = """
        INSERT INTO multiple_user_cur(
            account_id, usage_date, unblended_cost, resource_id,
            region, usage_type, service, name, owner, environment, record_type, instance_type
        ) VALUES %s
        ON CONFLICT (account_id, usage_date, resource_id, service)
        DO UPDATE SET
            unblended_cost = EXCLUDED.unblended_cost,
            region         = EXCLUDED.region,
            usage_type     = EXCLUDED.usage_type,
            name           = EXCLUDED.name,
            owner          = EXCLUDED.owner,
            environment    = EXCLUDED.environment,
            record_type    = EXCLUDED.record_type,
            instance_type  = EXCLUDED.instance_type
    """

    try:
        # execute_values handles Decimal correctly for NUMERIC columns
        execute_values(cur, insert_query, rows)
        conn.commit()
    except Exception as e:
        print(f"[ERROR] Failed DB insert: {e}")
        conn.rollback()
    finally:
        cur.close()
        conn.close()

# ------------------ Summary Report (account-wise) ------------------
def summarize_service_costs_account_wise():
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    # join to cur_multiple_user to get account_name, and group by account_id, usage_date, service
    query = """
        SELECT
            m.account_id,
            COALESCE(u.account_name, '') AS account_name,
            m.usage_date,
            m.service,
            ROUND(SUM(m.unblended_cost)::numeric, 2) AS total_cost
        FROM multiple_user_cur m
        LEFT JOIN cur_multiple_user u ON m.account_id = u.account_id
        WHERE m.usage_date BETWEEN %s AND %s
        GROUP BY m.account_id, u.account_name, m.usage_date, m.service
        ORDER BY m.account_id, m.usage_date, m.service
    """
    cur.execute(query, (start_date, end_date))
    results = cur.fetchall()
    cur.close()
    conn.close()

    if not results:
        print("\n[SUMMARY] No records found in multiple_user_cur for the date range.")
        return

    # Print grouped by account
    print("\n[SUMMARY] Daily total cost per service (account-wise):")
    current_acc = None
    for account_id, account_name, usage_date, service, total_cost in results:
        if account_id != current_acc:
            # new account header
            print("\n------------------------------------------------------------")
            print(f"Account: {account_id}  {f'({account_name})' if account_name else ''}")
            print("------------------------------------------------------------")
            current_acc = account_id
        print(f"{usage_date} | {service:<20} | ${total_cost}")

# ------------------ Main ------------------
def main():
    accounts = get_accounts()
    for account in accounts:
        # now account tuple includes account_name
        account_id, account_name, access_key, secret_key, bucket_name, prefix = account
        print(f"[INFO] Processing account: {account_id} {f'({account_name})' if account_name else ''}")
        rows = process_cur(account_id, access_key, secret_key, bucket_name, prefix)
        if rows:
            insert_to_db(rows)
            print(f"[SUCCESS] Inserted/Updated {len(rows)} records for {account_id}")
        else:
            print(f"[INFO] No data for account {account_id} in current date range")
    # print account-wise summary
    summarize_service_costs_account_wise()

if __name__ == "__main__":
    main()
