import boto3
import psycopg2
from psycopg2.extras import DictCursor
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

# ---------- DB CONFIG ----------
DB_CONFIG = {
    "host": "localhost",
    "dbname": "ims",
    "user": "postgres",
    "password": "Abcd@1234",  # change this
    "port": 5432
}


# ---------- CONNECT TO DB ----------
def connect_db():
    return psycopg2.connect(**DB_CONFIG)


# ---------- GET CREDENTIALS ----------
def get_credentials():
    """
    Fetch all account credentials from cur_multiple_user table
    """
    conn = connect_db()
    with conn.cursor(cursor_factory=DictCursor) as cur:
        cur.execute("SELECT account_id, account_name, access_key, secret_key FROM cur_multiple_user")
        rows = cur.fetchall()
    conn.close()
    return rows


# ---------- CREATE TARGET TABLE ----------
def create_table():
    conn = connect_db()
    with conn.cursor() as cur:
        cur.execute("DROP TABLE IF EXISTS orphanedeip")
        cur.execute(
            """
            CREATE TABLE orphanedeip (
                id SERIAL PRIMARY KEY,
                account_id VARCHAR(50),
                account_name VARCHAR(100),
                region VARCHAR(50),
                public_ip VARCHAR(50),
                allocation_id VARCHAR(100),
                arn TEXT,
                months VARCHAR(20),
                cost NUMERIC
            )
            """
        )
    conn.commit()
    conn.close()


# ---------- FETCH UNASSOCIATED EIPs ----------
def fetch_unassociated_eips(account_id, account_name, access_key, secret_key, region):
    """
    For a given account/region, return list of unassociated Elastic IPs along with ARN.
    """
    try:
        print(f"🔎 Scanning {account_name} ({account_id}) in {region}...")

        ec2 = boto3.client(
            "ec2",
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name=region,
        )
        response = ec2.describe_addresses()

        unassociated = []
        for addr in response.get("Addresses", []):
            if "InstanceId" not in addr and "NetworkInterfaceId" not in addr:
                allocation_id = addr.get("AllocationId")
                public_ip = addr.get("PublicIp")

                # Build ARN in the same format as CUR report
                # arn:aws:ec2:<region>:<account_id>:elastic-ip/<allocation_id>
                arn = f"arn:aws:ec2:{region}:{account_id}:elastic-ip/{allocation_id}"

                unassociated.append(
                    {
                        "account_id": account_id,
                        "account_name": account_name,
                        "region": region,
                        "public_ip": public_ip,
                        "allocation_id": allocation_id,
                        "arn": arn,
                    }
                )
        return unassociated

    except Exception as e:
        print(f"❌ Error in {account_name} ({account_id}) {region}: {e}")
        return []


# ---------- FETCH COSTS FROM CUR ----------
def fetch_eip_costs(arn, account_id):
    """
    Fetch month-by-month costs for a given Elastic IP ARN from multiple_user_cur
    """
    conn = connect_db()
    with conn.cursor(cursor_factory=DictCursor) as cur:
        cur.execute(
            """
            SELECT 
                TO_CHAR(DATE_TRUNC('month', usage_date), 'YYYY-MM') AS month,
                SUM(unblended_cost) AS total_cost
            FROM multiple_user_cur
            WHERE resource_id = %s
              AND account_id = %s
            GROUP BY DATE_TRUNC('month', usage_date)
            ORDER BY month
            """,
            (arn, account_id)
        )
        rows = cur.fetchall()
    conn.close()
    return rows


# ---------- SAVE RESULTS TO DB ----------
def save_to_db(eips):
    """
    Save unassociated EIP details along with costs month by month
    """
    if not eips:
        return

    conn = connect_db()
    with conn.cursor() as cur:
        for eip in eips:
            arn = eip["arn"]
            allocation_id = eip["allocation_id"]
            account_id = eip["account_id"]
            account_name = eip["account_name"]
            region = eip["region"]
            public_ip = eip["public_ip"]

            # Fetch CUR costs by ARN
            costs = fetch_eip_costs(arn, account_id)

            if costs:
                for row in costs:
                    cur.execute(
                        """
                        INSERT INTO orphanedeip
                        (account_id, account_name, region, public_ip, allocation_id, arn, months, cost)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        """,
                        (
                            account_id,
                            account_name,
                            region,
                            public_ip,
                            allocation_id,
                            arn,
                            row["month"],
                            row["total_cost"],
                        ),
                    )
            else:
                # If no cost history, still insert with cost = 0 for current month
                cur.execute(
                    """
                    INSERT INTO orphanedeip
                    (account_id, account_name, region, public_ip, allocation_id, arn, months, cost)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        account_id,
                        account_name,
                        region,
                        public_ip,
                        allocation_id,
                        arn,
                        datetime.now().strftime("%Y-%m"),
                        0,
                    ),
                )

    conn.commit()
    conn.close()


# ---------- MAIN ----------
def main():
    create_table()
    credentials = get_credentials()
    all_regions = boto3.session.Session().get_available_regions("ec2")

    tasks = []
    with ThreadPoolExecutor(max_workers=10) as executor:
        for cred in credentials:
            account_id, account_name, access_key, secret_key = cred
            for region in all_regions:
                tasks.append(
                    executor.submit(
                        fetch_unassociated_eips,
                        account_id,
                        account_name,
                        access_key,
                        secret_key,
                        region,
                    )
                )

        for future in as_completed(tasks):
            results = future.result()
            if results:
                save_to_db(results)


if __name__ == "__main__":
    main()
