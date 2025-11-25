import boto3
import psycopg2
from psycopg2.extras import RealDictCursor
from botocore.exceptions import ClientError

# ---------- DB CONFIG ----------
DB_CONFIG = {
    "host": "localhost",
    "dbname": "ims",
    "user": "postgres",
    "password": "Abcd@1234",  # change to your db password
    "port": 5432
}

# ---------- FETCH ACCOUNTS ----------
def get_accounts():
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("SELECT account_id, access_key, secret_key FROM cur_multiple_user")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows

# ---------- STORE RESULTS ----------
def store_results(records):
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()

    # Truncate table before inserting fresh data
    cur.execute("TRUNCATE TABLE ec2_auto_startstop")

    insert_query = """
        INSERT INTO ec2_auto_startstop 
        (account_id, region, instance_id, instance_type, auto_enabled, enabled_tag) 
        VALUES (%s, %s, %s, %s, %s, %s)
        ON CONFLICT (account_id, region, instance_id) 
        DO UPDATE SET 
            instance_type = EXCLUDED.instance_type,
            auto_enabled = EXCLUDED.auto_enabled,
            enabled_tag = EXCLUDED.enabled_tag;
    """

    cur.executemany(insert_query, records)
    conn.commit()
    cur.close()
    conn.close()

# ---------- CHECK EC2 INSTANCES ----------
def check_instances(account_id, access_key, secret_key):
    results = []
    try:
        # Fetch all AWS regions
        ec2_client = boto3.client(
            "ec2",
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name="us-east-1"
        )
        regions = [r["RegionName"] for r in ec2_client.describe_regions()["Regions"]]

        for region in regions:
            ec2 = boto3.client(
                "ec2",
                aws_access_key_id=access_key,
                aws_secret_access_key=secret_key,
                region_name=region
            )
            try:
                reservations = ec2.describe_instances()["Reservations"]
                for res in reservations:
                    for inst in res["Instances"]:
                        instance_id = inst["InstanceId"]
                        instance_type = inst["InstanceType"]

                        # Default values
                        auto_enabled = "NO"
                        enabled_tag = None

                        # Check tags
                        tags = inst.get("Tags", [])
                        for tag in tags:
                            key = tag["Key"].lower()
                            value = tag.get("Value", "").lower()

                            # Case 1: direct AutoStop/AutoStart tags
                            if key in ["autostop", "autostart"]:
                                auto_enabled = "YES"
                                enabled_tag = f"{tag['Key']}={tag['Value']}"

                            # Case 2: Service=AutoStart/AutoStop
                            elif key == "service" and value == "autostart/autostop":
                                auto_enabled = "YES"
                                enabled_tag = f"{tag['Key']}={tag['Value']}"

                        results.append((
                            account_id,
                            region,
                            instance_id,
                            instance_type,
                            auto_enabled,
                            enabled_tag
                        ))

            except ClientError as e:
                print(f"[ERROR] Failed in region {region} for account {account_id}: {e}")

    except ClientError as e:
        print(f"[ERROR] Could not describe regions for account {account_id}: {e}")

    return results

# ---------- MAIN ----------
def main():
    all_records = []
    accounts = get_accounts()

    for acc in accounts:
        account_id = acc["account_id"]
        access_key = acc["access_key"]
        secret_key = acc["secret_key"]

        print(f"[INFO] Processing account: {account_id}")
        records = check_instances(account_id, access_key, secret_key)
        all_records.extend(records)

    # Remove duplicates just in case
    unique_records = list({(r[0], r[1], r[2]): r for r in all_records}.values())

    store_results(unique_records)
    print(f"[SUCCESS] Inserted/Updated {len(unique_records)} records into ec2_auto_startstop")

if __name__ == "__main__":
    main()
