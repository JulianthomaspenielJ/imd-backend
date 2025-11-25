import boto3
import psycopg2
from psycopg2.extras import RealDictCursor, execute_values
from datetime import datetime
from collections import defaultdict

# ---------- DB CONFIG ----------
DB_CONFIG = {
    "host": "localhost",
    "dbname": "ims",
    "user": "postgres",
    "password": "Abcd@1234",  # change this to yours
    "port": 5432,
}

def connect_db():
    return psycopg2.connect(**DB_CONFIG)

# ---------- FETCH ORPHANED SNAPSHOTS ----------
def get_orphaned_snapshots(session, account_id, region):
    ec2 = session.client("ec2", region_name=region)
    orphaned = []
    try:
        snapshots = ec2.describe_snapshots(OwnerIds=[account_id])["Snapshots"]

        # All AMI snapshots
        amis = ec2.describe_images(Owners=[account_id])["Images"]
        ami_snapshot_ids = {bdm["Ebs"]["SnapshotId"]
                            for ami in amis
                            for bdm in ami.get("BlockDeviceMappings", [])
                            if "Ebs" in bdm}

        for snap in snapshots:
            snap_id = snap["SnapshotId"]

            # orphaned if not linked to an AMI and not linked to a volume
            if (snap_id not in ami_snapshot_ids) and ("VolumeId" not in snap):
                orphaned.append({
                    "snapshot_id": snap_id,
                    "description": snap.get("Description", ""),
                    "size": snap["VolumeSize"],
                    "start_time": snap["StartTime"].strftime("%Y-%m-%d"),
                    "name": next((tag["Value"] for tag in snap.get("Tags", []) if tag["Key"] == "Name"), None)
                })

    except Exception as e:
        print(f"Error fetching snapshots in {region} for {account_id}: {e}")
    return orphaned

# ---------- FETCH COSTINGS ----------
def get_snapshot_costs(snapshot_id, account_id):
    conn = connect_db()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        query = """
            SELECT usage_date, unblended_cost
            FROM multiple_user_cur
            WHERE resource_id LIKE %s
              AND account_id = %s
              AND service = 'Amazon Elastic Compute Cloud'
              AND usage_type ILIKE '%EBS:Snapshot%'
        """
        cur.execute(query, (f"%{snapshot_id}%", account_id))
        rows = cur.fetchall()

        monthwise = defaultdict(float)
        for row in rows:
            usage_date = row["usage_date"]
            month_name = usage_date.strftime("%B %Y")
            monthwise[month_name] += float(row["unblended_cost"])
        return dict(monthwise)
    finally:
        cur.close()
        conn.close()

# ---------- MAIN SCRIPT ----------
def main():
    conn = connect_db()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    # fetch accounts and credentials
    cur.execute("SELECT account_id, account_name, access_key, secret_key FROM cur_multiple_user")
    accounts = cur.fetchall()

    all_data = []

    for acc in accounts:
        account_id = acc["account_id"]
        account_name = acc["account_name"]
        access_key = acc["access_key"]
        secret_key = acc["secret_key"]

        print(f"\n🔍 Checking account {account_name} ({account_id})")

        # boto3 session
        session = boto3.session.Session(
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key
        )

        # get all available EC2 regions
        regions = session.get_available_regions("ec2")

        for region in regions:
            orphaned_snaps = get_orphaned_snapshots(session, account_id, region)
            for snap in orphaned_snaps:
                costs = get_snapshot_costs(snap["snapshot_id"], account_id)

                record = {
                    "account_id": account_id,
                    "account_name": account_name,
                    "region": region,
                    "snapshot_id": snap["snapshot_id"],
                    "snapshot_name": snap.get("name"),
                    "description": snap.get("description"),
                    "size": snap.get("size"),
                    "costs": costs
                }
                all_data.append(record)

    # store in table
    if all_data:
        insert_query = """
            INSERT INTO orphanedsnapshotswithcost
            (account_id, account_name, region, snapshot_id, snapshot_name, description, size, costs, created_at)
            VALUES %s
        """
        values = [
            (
                d["account_id"], d["account_name"], d["region"], d["snapshot_id"],
                d["snapshot_name"], d["description"], d["size"], str(d["costs"]),
                datetime.utcnow()
            )
            for d in all_data
        ]

        execute_values(cur, insert_query, values)
        conn.commit()
        print(f"\n✅ Inserted {len(all_data)} orphaned snapshots into DB.")
    else:
        print("\n⚠️ No orphaned snapshots found.")

    cur.close()
    conn.close()

if __name__ == "__main__":
    main()
