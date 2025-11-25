import boto3
import psycopg2
from psycopg2.extras import execute_values
from datetime import datetime
from dateutil.relativedelta import relativedelta

# -------------------------------
# DB Config
# -------------------------------
DB_CONFIG = {
    "dbname": "ims",
    "user": "postgres",
    "password": "Abcd@1234",
    "host": "localhost",
    "port": "5432"
}

# -------------------------------
# Create service_status table if not exists
# -------------------------------
def create_service_status_table():
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS service_status (
            account_id VARCHAR(20),
            service_name TEXT,
            month DATE,
            status VARCHAR(20),
            start_month DATE,
            stop_month DATE,
            PRIMARY KEY (account_id, service_name, month)
        );
    """)
    conn.commit()
    cur.close()
    conn.close()
    print("[INFO] service_status table is ready.")

# -------------------------------
# Fetch AWS credentials from master_user table
# -------------------------------
def get_accounts_from_db():
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    cur.execute("SELECT account_id, access_key, secret_key FROM master_user;")
    accounts = cur.fetchall()
    cur.close()
    conn.close()
    return accounts

# -------------------------------
# Get first billing month for an account
# -------------------------------
def get_first_billing_month(client):
    now = datetime.utcnow().replace(day=1)
    start = now - relativedelta(months=13)  # Cost Explorer max is 14 months back
    first_seen = None

    while start <= now:
        end = start + relativedelta(months=1)
        response = client.get_cost_and_usage(
            TimePeriod={"Start": start.strftime("%Y-%m-%d"), "End": end.strftime("%Y-%m-%d")},
            Granularity="MONTHLY",
            Metrics=["UnblendedCost"],
            GroupBy=[{"Type": "DIMENSION", "Key": "SERVICE"}]
        )
        if any(float(i["Metrics"]["UnblendedCost"]["Amount"]) > 0 for i in response["ResultsByTime"][0]["Groups"]):
            first_seen = start
            break
        start += relativedelta(months=1)

    return first_seen

# -------------------------------
# Fetch service usage history (monthly)
# -------------------------------
def get_service_usage_history(client, start_date, end_date):
    service_usage = {}

    current = start_date
    while current <= end_date:
        next_month = current + relativedelta(months=1)

        response = client.get_cost_and_usage(
            TimePeriod={"Start": current.strftime("%Y-%m-%d"), "End": next_month.strftime("%Y-%m-%d")},
            Granularity="MONTHLY",
            Metrics=["UnblendedCost"],
            GroupBy=[{"Type": "DIMENSION", "Key": "SERVICE"}]
        )

        month_str = current.strftime("%Y-%m-%d")
        for group in response["ResultsByTime"][0]["Groups"]:
            service_name = group["Keys"][0]
            cost = float(group["Metrics"]["UnblendedCost"]["Amount"])
            if cost > 0:
                if service_name not in service_usage:
                    service_usage[service_name] = []
                service_usage[service_name].append(month_str)

        current += relativedelta(months=1)

    return service_usage

# -------------------------------
# Determine service start/stop status
# -------------------------------
def analyze_services(account_id, service_usage, all_months):
    results = []

    for service, months in service_usage.items():
        start_month = min(months)
        stop_month = max(months)

        for m in all_months:
            if m in months:
                # Service was running in this month
                status = "Running"
                if m == start_month:
                    status = "Newly Added"
                results.append((
                    account_id,
                    service,
                    datetime.strptime(m, "%Y-%m-%d").date(),
                    status,
                    datetime.strptime(start_month, "%Y-%m-%d").date(),
                    None  # stop_month is NULL for running services
                ))
            else:
                if m > stop_month:
                    # Service stopped after stop_month
                    results.append((
                        account_id,
                        service,
                        datetime.strptime(m, "%Y-%m-%d").date(),
                        "Stopped",
                        datetime.strptime(start_month, "%Y-%m-%d").date(),
                        datetime.strptime(stop_month, "%Y-%m-%d").date()
                    ))

    return results

# -------------------------------
# Upsert into service_status
# -------------------------------
def upsert_service_status(data):
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()

    query = """
        INSERT INTO service_status (account_id, service_name, month, status, start_month, stop_month)
        VALUES %s
        ON CONFLICT (account_id, service_name, month)
        DO UPDATE SET
            status = EXCLUDED.status,
            start_month = EXCLUDED.start_month,
            stop_month = EXCLUDED.stop_month;
    """
    execute_values(cur, query, data)
    conn.commit()
    cur.close()
    conn.close()

# -------------------------------
# Main script
# -------------------------------
def main():
    create_service_status_table()
    accounts = get_accounts_from_db()

    for account_id, access_key, secret_key in accounts:
        print(f"[INFO] Processing account: {account_id}")

        client = boto3.client(
            "ce",
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name="us-east-1"
        )

        first_month = get_first_billing_month(client)
        if not first_month:
            print(f"[WARN] No billing data found for {account_id}")
            continue

        now = datetime.utcnow().replace(day=1)
        service_usage = get_service_usage_history(client, first_month, now)

        all_months = [
            (first_month + relativedelta(months=i)).strftime("%Y-%m-%d")
            for i in range((now.year - first_month.year) * 12 + (now.month - first_month.month) + 1)
        ]

        results = analyze_services(account_id, service_usage, all_months)
        if results:
            upsert_service_status(results)
            print(f"[INFO] Inserted/Updated {len(results)} records for account {account_id}")

if __name__ == "__main__":
    main()
