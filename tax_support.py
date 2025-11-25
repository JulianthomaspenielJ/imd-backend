import boto3
import psycopg2
from datetime import datetime
from dateutil.relativedelta import relativedelta

# -------------------------------
# PostgreSQL DB Connection
# -------------------------------
conn = psycopg2.connect(
    dbname='ims_db',
    user='postgres',
    password='*Postgres16',
    host='localhost',
    port='5432'
)
cursor = conn.cursor()

# Create table if not exists
cursor.execute("""
CREATE TABLE IF NOT EXISTS monthly_cost_conditions (
    account_id VARCHAR(100),
    usage_month DATE,
    condition_type VARCHAR(50), -- no_tax, no_tax_no_support, all_inclusive
    cost NUMERIC(12, 4),
    PRIMARY KEY (account_id, usage_month, condition_type)
);
""")
conn.commit()

# -------------------------------
# Fetch AWS Accounts
# -------------------------------
cursor.execute("SELECT account_id, access_key, secret_key FROM master_user;")
accounts = cursor.fetchall()

# -------------------------------
# UPSERT Function
# -------------------------------
def upsert_monthly_cost(account_id, usage_month, condition_type, cost):
    cursor.execute("""
        INSERT INTO monthly_cost_conditions (account_id, usage_month, condition_type, cost)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (account_id, usage_month, condition_type)
        DO UPDATE SET cost = EXCLUDED.cost;
    """, (account_id, usage_month, condition_type, cost))

# -------------------------------
# Fetch Cost Function
# -------------------------------
def fetch_monthly_cost(ce_client, start_str, end_str, exclude_services):
    # Build filter if exclusions exist
    if exclude_services:
        filter_obj = {
            "Not": {
                "Dimensions": {
                    "Key": "SERVICE",
                    "Values": exclude_services
                }
            }
        }
    else:
        filter_obj = None

    kwargs = {
        "TimePeriod": {"Start": start_str, "End": end_str},
        "Granularity": "MONTHLY",
        "Metrics": ["UnblendedCost"]
    }
    if filter_obj:
        kwargs["Filter"] = filter_obj

    response = ce_client.get_cost_and_usage(**kwargs)
    results = response["ResultsByTime"]

    # Single month expected in range
    total_cost = float(results[0]["Total"]["UnblendedCost"]["Amount"])
    return round(total_cost, 4)

# -------------------------------
# Main Logic
# -------------------------------
end_date = datetime.utcnow().date().replace(day=1)
start_date = end_date - relativedelta(months=13)  # last 14 months

for account_id, access_key, secret_key in accounts:
    print(f"🔄 Processing Account: {account_id}")

    ce = boto3.client(
        'ce',
        region_name='us-east-1',
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key
    )

    current_date = start_date
    while current_date < end_date:
        next_month = (current_date + relativedelta(months=1)).replace(day=1)
        start_str = current_date.strftime('%Y-%m-%d')
        end_str = next_month.strftime('%Y-%m-%d')
        usage_month = current_date

        # 1. Without Tax
        cost_no_tax = fetch_monthly_cost(ce, start_str, end_str, ["Tax"])
        upsert_monthly_cost(account_id, usage_month, "no_tax", cost_no_tax)

        # 2. Without Tax & Support Charge
        cost_no_tax_no_support = fetch_monthly_cost(ce, start_str, end_str, ["Tax", "AWS Support (Business)", "AWS Support (Enterprise)"])
        upsert_monthly_cost(account_id, usage_month, "no_tax_no_support", cost_no_tax_no_support)

        # 3. All inclusive
        cost_all_inclusive = fetch_monthly_cost(ce, start_str, end_str, [])
        upsert_monthly_cost(account_id, usage_month, "all_inclusive", cost_all_inclusive)

        conn.commit()
        current_date = next_month

cursor.close()
conn.close()
print("✅ All monthly cost data upserted successfully.")
