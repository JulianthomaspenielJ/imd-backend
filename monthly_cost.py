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

# -------------------------------
# Create Table if not exists
# -------------------------------
cursor.execute("""
CREATE TABLE IF NOT EXISTS monthly_cost (
    account_id VARCHAR(100),
    usage_month DATE,
    service_name VARCHAR(255),
    cost NUMERIC(10, 2),
    PRIMARY KEY (account_id, usage_month, service_name)
);
""")
conn.commit()

# -------------------------------
# Fetch AWS Credentials
# -------------------------------
cursor.execute("SELECT account_id, access_key, secret_key FROM master_user;")
accounts = cursor.fetchall()

# -------------------------------
# UPSERT Function
# -------------------------------
def upsert_monthly_cost(account_id, usage_month, service_name, cost):
    cursor.execute("""
        INSERT INTO monthly_cost (account_id, usage_month, service_name, cost)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (account_id, usage_month, service_name)
        DO UPDATE SET cost = EXCLUDED.cost;
    """, (account_id, usage_month, service_name, cost))

# -------------------------------
# Main Logic
# -------------------------------
for account_id, access_key, secret_key in accounts:
    print(f"🔄 Processing Account: {account_id}")

    ce = boto3.client(
        'ce',
        region_name='us-east-1',
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key
    )

    end_date = datetime.utcnow().date().replace(day=1)
    start_date = end_date - relativedelta(months=13)  # Last 14 full months

    current_date = start_date
    while current_date < end_date:
        next_month = (current_date + relativedelta(months=1)).replace(day=1)
        start_str = current_date.strftime('%Y-%m-%d')
        end_str = next_month.strftime('%Y-%m-%d')
        print(f"📅 Fetching: {start_str} to {end_str}")

        try:
            response = ce.get_cost_and_usage(
                TimePeriod={'Start': start_str, 'End': end_str},
                Granularity='MONTHLY',
                Metrics=['UnblendedCost'],
                GroupBy=[{'Type': 'DIMENSION', 'Key': 'SERVICE'}]
            )
        except Exception as e:
            print(f"❌ Error fetching data for {account_id}: {e}")
            break

        for result in response['ResultsByTime']:
            usage_month = result['TimePeriod']['Start']
            for group in result['Groups']:
                service_name = group['Keys'][0]
                cost_amount = float(group['Metrics']['UnblendedCost']['Amount'])
                if cost_amount > 0:
                    cost = round(cost_amount, 2)
                    upsert_monthly_cost(account_id, usage_month, service_name, cost)

        conn.commit()
        current_date = next_month

cursor.close()
conn.close()
print("✅ All monthly cost data upserted successfully.")
