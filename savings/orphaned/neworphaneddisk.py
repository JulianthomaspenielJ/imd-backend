import boto3
import psycopg2
from psycopg2.extras import DictCursor
from datetime import datetime

# ---------- DB CONFIG ----------
DB_CONFIG = {
    "host": "localhost",
    "dbname": "ims",
    "user": "postgres",
    "password": "Abcd@1234",
    "port": 5432
}

# ---------- DB CONNECTION ----------
def connect_db():
    return psycopg2.connect(**DB_CONFIG)

# ---------- FETCH ALL ACCOUNTS FROM DB ----------
def get_all_accounts():
    sql = """
    SELECT account_id, account_name, access_key, secret_key
    FROM cur_multiple_user;
    """
    with connect_db() as conn:
        with conn.cursor(cursor_factory=DictCursor) as cur:
            cur.execute(sql)
            return cur.fetchall()

# ---------- FETCH ORPHANED VOLUMES ----------
def get_orphaned_volumes(account, region):
    try:
        session = boto3.Session(
            aws_access_key_id=account["access_key"],
            aws_secret_access_key=account["secret_key"],
            region_name=region
        )
        ec2 = session.client("ec2")

        volumes = ec2.describe_volumes(
            Filters=[{"Name": "status", "Values": ["available"]}]
        )["Volumes"]

        orphaned = []
        for v in volumes:
            # Get volume name if exists
            name = None
            if "Tags" in v:
                for tag in v["Tags"]:
                    if tag["Key"].lower() == "name":
                        name = tag["Value"]

            orphaned.append({
                "volume_id": v["VolumeId"],
                "volume_size": v["Size"],
                "volume_type": v["VolumeType"],
                "volume_name": name,
                "region": region,
                "account_id": account["account_id"]
            })
        return orphaned

    except Exception as e:
        print(f"[ERROR] {account['account_id']} - {region}: {e}")
        return []

# ---------- FETCH COST FROM CUR TABLE ----------
def get_volume_cost_from_cur(volume_id):
    sql = """
    SELECT SUM(unblended_cost) AS cost
    FROM multiple_user_cur
    WHERE resource_id LIKE %s
      AND usage_date >= date_trunc('month', CURRENT_DATE)
      AND usage_date < date_trunc('month', CURRENT_DATE + interval '1 month');
    """
    with connect_db() as conn:
        with conn.cursor(cursor_factory=DictCursor) as cur:
            cur.execute(sql, (f"%{volume_id}%",))
            row = cur.fetchone()
            return float(row["cost"]) if row and row["cost"] else 0.0

# ---------- MAIN FUNCTION ----------
def main():
    print("🔎 Checking orphaned volumes across accounts & regions...")
    accounts = get_all_accounts()
    all_orphans = []

    for account in accounts:
        regions = boto3.session.Session().get_available_regions("ec2")
        for region in regions:
            orphaned = get_orphaned_volumes(account, region)
            for vol in orphaned:
                cost_savings = get_volume_cost_from_cur(vol["volume_id"])
                vol["cost_savings"] = cost_savings
                all_orphans.append(vol)

                print(f"[INFO] Orphaned Volume {vol['volume_id']} "
                      f"({vol['volume_size']}GB, {vol['volume_type']}) in {vol['region']} | "
                      f"Account {vol['account_id']} | Cost Savings: ${cost_savings:.2f}")

    # Save results into DB
    if all_orphans:
        with connect_db() as conn:
            with conn.cursor() as cur:
                for vol in all_orphans:
                    cur.execute("""
                        INSERT INTO orphaned_volumes_with_cost
                        (account_id, region, volume_id, volume_name, volume_type, volume_size, cost_savings, fetched_at, status)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (volume_id) DO UPDATE
                        SET cost_savings = EXCLUDED.cost_savings,
                            fetched_at = EXCLUDED.fetched_at,
                            volume_name = EXCLUDED.volume_name,
                            volume_type = EXCLUDED.volume_type,
                            volume_size = EXCLUDED.volume_size,
                            status = EXCLUDED.status;
                    """, (
                        vol["account_id"],
                        vol["region"],
                        vol["volume_id"],
                        vol["volume_name"],
                        vol["volume_type"],
                        vol["volume_size"],
                        vol["cost_savings"],
                        datetime.utcnow(),
                        "unassigned"   # default value for new/updated records
                    ))
            conn.commit()

    print("✅ Done. Orphaned volume report updated.")

# ---------- RUN ----------
if __name__ == "__main__":
    main()
