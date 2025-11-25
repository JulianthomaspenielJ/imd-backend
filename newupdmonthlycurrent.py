import boto3
import psycopg2
from datetime import datetime, timedelta

# ---------- DB Config ----------
DB_CONFIG = {
    "host": "localhost",
    "dbname": "ims",
    "user": "postgres",
    "password": "Abcd@1234",
    "port": 5432
}

# ---------- Fetch AWS Credentials for ALL Accounts ----------
def get_all_aws_credentials():
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    cur.execute("""
        SELECT access_key, secret_key, account_id
        FROM cur_multiple_user;
    """)
    rows = cur.fetchall()
    cur.close()
    conn.close()
    if not rows:
        raise Exception("No AWS credentials found in cur_multiple_user table")
    return rows  # list of tuples: (access_key, secret_key, account_id)

# ---------- Get Monthly Total & Per-Service Costs from AWS ----------
def get_monthly_costs(access_key, secret_key, start_date, end_date):
    client = boto3.client(
        "ce",
        region_name="us-east-1",
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key
    )

    response = client.get_cost_and_usage(
        TimePeriod={"Start": start_date, "End": end_date},
        Granularity="MONTHLY",
        Metrics=["UnblendedCost"],
        GroupBy=[{"Type": "DIMENSION", "Key": "SERVICE"}]
    )

    total_amount = 0.0
    service_costs = []

    for group in response["ResultsByTime"][0]["Groups"]:
        service_name = group["Keys"][0]
        amount = round(float(group["Metrics"]["UnblendedCost"]["Amount"]), 2)
        total_amount += amount
        service_costs.append((service_name, amount))

    return round(total_amount, 2), service_costs

# ---------- Store in monthly_current Table ----------
def store_cost(account_id, month_label, total_cost, service_costs):
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()

    # Main table for total cost
    cur.execute("""
        CREATE TABLE IF NOT EXISTS monthly_current (
            id SERIAL PRIMARY KEY,
            account_id TEXT,
            month_label TEXT,
            cost NUMERIC,
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (account_id, month_label)
        )
    """)

    # Breakdown table for per-service costs
    cur.execute("""
        CREATE TABLE IF NOT EXISTS monthly_current_services (
            id SERIAL PRIMARY KEY,
            account_id TEXT,
            month_label TEXT,
            service_name TEXT,
            cost NUMERIC,
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (account_id, month_label, service_name)
        )
    """)

    # Upsert total monthly cost
    cur.execute("""
        INSERT INTO monthly_current (account_id, month_label, cost)
        VALUES (%s, %s, %s)
        ON CONFLICT (account_id, month_label)
        DO UPDATE SET cost = EXCLUDED.cost, last_updated = CURRENT_TIMESTAMP
    """, (account_id, month_label, total_cost))

    # Upsert per-service costs
    for service_name, cost in service_costs:
        cur.execute("""
            INSERT INTO monthly_current_services (account_id, month_label, service_name, cost)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (account_id, month_label, service_name)
            DO UPDATE SET cost = EXCLUDED.cost, last_updated = CURRENT_TIMESTAMP
        """, (account_id, month_label, service_name, cost))

    conn.commit()
    cur.close()
    conn.close()

# ---------- Main Script ----------
if __name__ == "__main__":
    today = datetime.utcnow()
    first_of_month = today.replace(day=1)

    # Get AWS credentials for all accounts
    accounts = get_all_aws_credentials()

    for access_key, secret_key, account_id in accounts:
        # ---------- Last Month ----------
        last_month_end = first_of_month
        last_month_start = (first_of_month - timedelta(days=1)).replace(day=1)
        last_total, last_services = get_monthly_costs(
            access_key, secret_key,
            last_month_start.strftime("%Y-%m-%d"),
            last_month_end.strftime("%Y-%m-%d")
        )
        store_cost(account_id, last_month_start.strftime("%B %Y"), last_total, last_services)
        print(f"[{account_id}] Stored last month ({last_month_start.strftime('%B %Y')}): {last_total}")

        # ---------- Current Month till Today ----------
        current_total, current_services = get_monthly_costs(
            access_key, secret_key,
            first_of_month.strftime("%Y-%m-%d"),
            today.strftime("%Y-%m-%d")
        )
        store_cost(account_id, first_of_month.strftime("%B %Y"), current_total, current_services)
        print(f"[{account_id}] Stored current month ({first_of_month.strftime('%B %Y')}) till {today.day}: {current_total}")
