import boto3
import psycopg2
from datetime import datetime
import calendar

# ---------- DB Config ----------
DB_CONFIG = {
    "host": "localhost",
    "dbname": "ims",
    "user": "postgres",
    "password": "Abcd@1234",
    "port": "5432"
}

# ---------- Create Table if Not Exists ----------
def create_forecast_table():
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS forecast_data (
            account_id VARCHAR(20),
            month VARCHAR(7),
            forecast_amount NUMERIC(12, 2)
        );
    """)
    conn.commit()
    cur.close()
    conn.close()
    print("[INFO] forecast_data table ready.")

# ---------- Get AWS Credentials from DB ----------
def get_accounts_from_db():
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()

    cur.execute("SELECT account_id, access_key, secret_key FROM cur_multiple_user;")
    accounts = cur.fetchall()

    cur.close()
    conn.close()
    return accounts

# ---------- Fetch Forecast from AWS ----------
def get_forecast(access_key, secret_key):
    client = boto3.client(
        "ce",
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        region_name="us-east-1"
    )

    today = datetime.utcnow().strftime('%Y-%m-%d')
    year = datetime.utcnow().year
    month_num = datetime.utcnow().month
    last_day = calendar.monthrange(year, month_num)[1]
    end_of_month = datetime(year, month_num, last_day).strftime('%Y-%m-%d')

    response = client.get_cost_forecast(
        TimePeriod={
            'Start': today,          # start from today
            'End': end_of_month      # until last day of month
        },
        Metric="UNBLENDED_COST",
        Granularity="MONTHLY"
    )

    forecast_amount = round(float(response["Total"]["Amount"]), 2)  # round to 2 decimals
    return forecast_amount, datetime.utcnow().strftime("%Y-%m")

# ---------- Store Forecast in DB ----------
def store_forecasts(all_forecasts):
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()

    # Truncate table once before inserting all accounts
    cur.execute("TRUNCATE TABLE forecast_data;")

    # Insert all accounts' forecasts
    cur.executemany(
        "INSERT INTO forecast_data (account_id, month, forecast_amount) VALUES (%s, %s, %s)",
        all_forecasts
    )

    conn.commit()
    cur.close()
    conn.close()
    print(f"[INFO] Stored forecasts for {len(all_forecasts)} accounts.")

# ---------- Main ----------
if __name__ == "__main__":
    create_forecast_table()

    accounts = get_accounts_from_db()
    if not accounts:
        print("[ERROR] No accounts found in master_user_test table.")
        exit()

    all_forecasts = []
    for account_id, access_key, secret_key in accounts:
        forecast_amount, month = get_forecast(access_key, secret_key)
        all_forecasts.append((account_id, month, forecast_amount))
        print(f"[INFO] Fetched forecast for {account_id}: {forecast_amount} for {month}")

    store_forecasts(all_forecasts)
