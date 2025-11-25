import boto3
import psycopg2
from psycopg2.extras import execute_values
from datetime import datetime
import logging

# ---------------- Logging Setup ----------------
logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")

# ---------------- DB Connection ----------------
def get_db_connection():
    return psycopg2.connect(
        dbname="ims",
        user="postgres",
        password="Abcd@1234",
        host="localhost",
        port="5432"
    )

# ---------------- Table Creation ----------------
def create_table():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS aws_ri_savings_plan (
            account_id VARCHAR(50),
            account_name VARCHAR(100),
            plan_type VARCHAR(50),
            region VARCHAR(50),
            arn TEXT,
            offering_type VARCHAR(100),
            instance_family VARCHAR(50),
            state VARCHAR(50),
            start_date TIMESTAMP,
            end_date TIMESTAMP,
            normalized_units VARCHAR(50),
            recurring_payment_amount NUMERIC,
            recurring_payment_frequency VARCHAR(50),
            utilization_percentage NUMERIC,
            PRIMARY KEY (account_id, arn)
        );
    """)
    conn.commit()
    cur.close()
    conn.close()
    logging.info("aws_ri_savings_plan table is ready.")

# ---------------- Fetch AWS Accounts ----------------
def fetch_accounts():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT account_id, account_name, access_key, secret_key FROM cur_multiple_user;")
    accounts = cur.fetchall()
    cur.close()
    conn.close()
    return accounts

# ---------------- Get All AWS Regions ----------------
def get_all_regions(session):
    try:
        ec2_client = session.client("ec2", region_name="us-east-1")
        regions = ec2_client.describe_regions(AllRegions=True)["Regions"]
        return [r["RegionName"] for r in regions]
    except Exception as e:
        logging.error(f"Failed to fetch regions: {e}")
        return ["us-east-1"]  # fallback

# ---------------- Fetch RI & SP ----------------
def fetch_ri_and_sp(account_id, account_name, access_key, secret_key):
    session = boto3.Session(
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key
    )

    regions = get_all_regions(session)
    results = []

    for region in regions:
        try:
            # ---------------- RI ----------------
            ec2_client = session.client("ec2", region_name=region)
            ri_response = ec2_client.describe_reserved_instances()
            for ri in ri_response.get("ReservedInstances", []):
                results.append((
                    account_id, account_name, "Reserved Instance", region,
                    ri.get("ReservedInstancesId"), ri.get("OfferingType"),
                    ri.get("InstanceType", "").split(".")[0] if ri.get("InstanceType") else None,
                    ri.get("State"), ri.get("Start"), ri.get("End"),
                    str(ri.get("InstanceCount")),
                    None, None, None
                ))

            # ---------------- Savings Plans ----------------
            sp_client = session.client("savingsplans", region_name=region)
            sp_response = sp_client.describe_savings_plans()
            for sp in sp_response.get("savingsPlans", []):
                results.append((
                    account_id, account_name, "Savings Plan", region,
                    sp.get("savingsPlanId"), sp.get("description"),
                    sp.get("productTypes", [None])[0],
                    sp.get("state"), sp.get("start"), sp.get("end"),
                    sp.get("commitment"), sp.get("recurringPaymentAmount"),
                    sp.get("recurringPaymentFrequency"),
                    None
                ))
        except Exception as e:
            logging.error(f"Failed for account {account_id} in region {region}: {e}")
            continue

    return results

# ---------------- UPSERT to DB ----------------
def upsert_records(records):
    if not records:
        return
    conn = get_db_connection()
    cur = conn.cursor()
    query = """
        INSERT INTO aws_ri_savings_plan (
            account_id, account_name, plan_type, region, arn,
            offering_type, instance_family, state, start_date, end_date,
            normalized_units, recurring_payment_amount,
            recurring_payment_frequency, utilization_percentage
        ) VALUES %s
        ON CONFLICT (account_id, arn) DO UPDATE SET
            account_name = EXCLUDED.account_name,
            plan_type = EXCLUDED.plan_type,
            region = EXCLUDED.region,
            offering_type = EXCLUDED.offering_type,
            instance_family = EXCLUDED.instance_family,
            state = EXCLUDED.state,
            start_date = EXCLUDED.start_date,
            end_date = EXCLUDED.end_date,
            normalized_units = EXCLUDED.normalized_units,
            recurring_payment_amount = EXCLUDED.recurring_payment_amount,
            recurring_payment_frequency = EXCLUDED.recurring_payment_frequency,
            utilization_percentage = EXCLUDED.utilization_percentage;
    """
    try:
        execute_values(cur, query, records)
        conn.commit()
    except Exception as e:
        logging.error(f"DB insert failed: {e}")
    finally:
        cur.close()
        conn.close()

# ---------------- Main ----------------
def main():
    create_table()
    accounts = fetch_accounts()
    for account_id, account_name, access_key, secret_key in accounts:
        logging.info(f"Processing account: {account_id} ({account_name})")
        try:
            records = fetch_ri_and_sp(account_id, account_name, access_key, secret_key)
            upsert_records(records)
            logging.info(f"Inserted/Updated {len(records)} records for {account_id}")
        except Exception as e:
            logging.error(f"Failed for account {account_id}: {e}")

if __name__ == "__main__":
    main()
