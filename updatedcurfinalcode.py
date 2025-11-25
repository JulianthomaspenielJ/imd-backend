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
    cur.execute("SELECT account_id, access_key, secret_key FROM master_user")
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

# ------------------ Resolve Service Name ------------------
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
def process_cur(account_id, access_key, secret_key):
    session = boto3.Session(
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        region_name='us-east-1'
    )
    s3 = session.client('s3')
    bucket_name = 'newbucketforimsproject'
    prefix = 'ims_cost/'

    try:
        response = s3.list_objects_v2(Bucket=bucket_name, Prefix=prefix)
    except Exception as e:
        print(f"[ERROR] Unable to list objects in bucket: {e}")
        return []

    if 'Contents' not in response or not response['Contents']:
        print(f"[WARNING] No CUR files for account {account_id}")
        return []

    files = sorted(response['Contents'], key=lambda x: x['LastModified'], reverse=True)
    latest_file_key = files[0]['Key']
    obj = s3.get_object(Bucket=bucket_name, Key=latest_file_key)

    file_bytes = obj['Body'].read()
    bytestream = io.BytesIO(file_bytes)

    if latest_file_key.endswith(".gz"):
        file_obj = gzip.GzipFile(fileobj=bytestream, mode='rb')
    else:
        file_obj = bytestream

    reader = csv.DictReader(io.TextIOWrapper(file_obj, encoding='utf-8-sig'))

    cost_map = {}

    for row in reader:
        usage_date = (row.get("line_item_usage_start_date", "") or "")[:10]
        if not usage_date or not (start_date <= usage_date <= end_date):
            continue

        resource_id = row.get("line_item_resource_id", "") or ""
        unblended_cost = to_decimal(row.get("line_item_unblended_cost", "0"))

        tags = {}
        try:
            tags_raw = row.get("resource_tags", "")
            if tags_raw and tags_raw.strip():
                tags = json.loads(tags_raw.replace("'", '"'))
        except Exception:
            pass

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
        instance_type = row.get("product_instance_type", "") or ""   # <-- NEW FIELD

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
                "instance_type": instance_type   # <-- NEW FIELD
            }

    result = []
    for (acc, usage_date, resource_id, service), vals in sorted(cost_map.items(), key=lambda x: x[0][1]):
        amount = round2(vals["unblended_cost"])
        result.append((
            acc,
            usage_date,
            str(amount),
            resource_id,
            vals["region"],
            vals["usage_type"],
            service,
            vals["name"],
            vals["owner"],
            vals["environment"],
            vals["record_type"],
            vals["instance_type"]   # <-- NEW FIELD
        ))
    return result

# ------------------ Insert or Update to DB ------------------
def insert_to_db(rows):
    if not rows:
        return
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()

    # Force-create table with new column if not exists
    cur.execute("""
        CREATE TABLE IF NOT EXISTS v5_final_cost (
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
        INSERT INTO v5_final_cost (
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
        execute_values(cur, insert_query, rows)
        conn.commit()
    except Exception as e:
        print(f"[ERROR] Failed DB insert: {e}")
        conn.rollback()
    finally:
        cur.close()
        conn.close()

# ------------------ Summary Report ------------------
def summarize_service_costs():
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    cur.execute("""
        SELECT usage_date, service, ROUND(SUM(unblended_cost), 2) AS total_cost
        FROM v5_final_cost
        GROUP BY usage_date, service
        ORDER BY usage_date, service
    """)
    results = cur.fetchall()
    cur.close()
    conn.close()
    print("\n[SUMMARY] Daily total cost per service:")
    for usage_date, service, total_cost in results:
        print(f"{usage_date} | {service:<20} | ${total_cost}")

# ------------------ Main Logic ------------------
def main():
    accounts = get_accounts()
    for account_id, access_key, secret_key in accounts:
        print(f"[INFO] Processing account: {account_id}")
        rows = process_cur(account_id, access_key, secret_key)
        if rows:
            insert_to_db(rows)
            print(f"[SUCCESS] Inserted/Updated {len(rows)} records for {account_id}")
        else:
            print(f"[INFO] No data for account {account_id} in current date range")
    summarize_service_costs()

if __name__ == "__main__":
    main()
