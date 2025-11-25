import boto3
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime, timedelta

# ---------- DB CONFIG ----------
DB_CONFIG = {
    "host": "localhost",
    "dbname": "ims",
    "user": "postgres",
    "password": "Abcd@1234",  # change to your password
    "port": 5432
}

# ---------- SQL TABLE CREATION ----------
CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS Instancedeepdive (
    account_id VARCHAR(20) NOT NULL,
    region VARCHAR(30) NOT NULL,
    instance_id VARCHAR(50) NOT NULL,
    instance_name VARCHAR(255),
    instance_type VARCHAR(50),
    vcpu INT,
    ram NUMERIC,  -- in GiB
    volume_size NUMERIC,  -- EBS volume size in GiB (root volume)
    status VARCHAR(20),
    environment VARCHAR(50),
    period VARCHAR(10) NOT NULL,  -- 24h, 7d, 30d
    cpu_utilization NUMERIC,
    network_in NUMERIC,   -- in GB
    network_out NUMERIC,  -- in GB
    cost NUMERIC,
    updated_at TIMESTAMP DEFAULT NOW(),
    PRIMARY KEY (account_id, region, instance_id, period)
);
"""

UPSERT_SQL = """
INSERT INTO Instancedeepdive
(account_id, region, instance_id, instance_name, instance_type, vcpu, ram, volume_size,
 status, environment, period, cpu_utilization, network_in, network_out, cost, updated_at)
VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,NOW())
ON CONFLICT (account_id, region, instance_id, period)
DO UPDATE SET
    instance_name = EXCLUDED.instance_name,
    instance_type = EXCLUDED.instance_type,
    vcpu = EXCLUDED.vcpu,
    ram = EXCLUDED.ram,
    volume_size = EXCLUDED.volume_size,
    status = EXCLUDED.status,
    environment = EXCLUDED.environment,
    cpu_utilization = EXCLUDED.cpu_utilization,
    network_in = EXCLUDED.network_in,
    network_out = EXCLUDED.network_out,
    cost = EXCLUDED.cost,
    updated_at = NOW();
"""

# ---------- FUNCTIONS ----------
def get_db_connection():
    return psycopg2.connect(**DB_CONFIG)

def fetch_accounts():
    """Fetch AWS credentials from cur_multiple_user table"""
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("SELECT account_id, access_key, secret_key FROM cur_multiple_user;")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows

def get_cost_and_env_from_cur(account_id, instance_id, days):
    """Fetch cost + environment from CUR table for given instance_id and last N days"""
    conn = get_db_connection()
    cur = conn.cursor()
    end_date = datetime.utcnow().date()
    start_date = end_date - timedelta(days=days)

    query = """
        SELECT COALESCE(SUM(unblended_cost),0), MAX(environment)
        FROM multiple_user_cur
        WHERE account_id = %s
          AND resource_id = %s
          AND usage_date BETWEEN %s AND %s;
    """
    cur.execute(query, (account_id, instance_id, start_date, end_date))
    row = cur.fetchone()
    total_cost = row[0] or 0.0
    environment = row[1] or "Unknown"

    cur.close()
    conn.close()
    return round(total_cost, 4), environment

def get_metrics_from_cw(cw, instance_id, days):
    """Fetch average CPU and sum of NetworkIn/Out for last N days"""
    end = datetime.utcnow()
    start = end - timedelta(days=days)

    cpu_avg, net_in_sum, net_out_sum = None, None, None

    try:
        # --- CPU ---
        cpu = cw.get_metric_statistics(
            Namespace="AWS/EC2",
            MetricName="CPUUtilization",
            Dimensions=[{"Name": "InstanceId", "Value": instance_id}],
            StartTime=start, EndTime=end,
            Period=3600 * 24,  # daily aggregation
            Statistics=["Average"]
        )
        if cpu["Datapoints"]:
            cpu_avg = sum(dp["Average"] for dp in cpu["Datapoints"]) / len(cpu["Datapoints"])

        # --- NetworkIn ---
        net_in = cw.get_metric_statistics(
            Namespace="AWS/EC2",
            MetricName="NetworkIn",
            Dimensions=[{"Name": "InstanceId", "Value": instance_id}],
            StartTime=start, EndTime=end,
            Period=3600 * 24,
            Statistics=["Sum"]
        )
        if net_in["Datapoints"]:
            net_in_sum = sum(dp["Sum"] for dp in net_in["Datapoints"]) / (1024 ** 3)  # bytes → GB

        # --- NetworkOut ---
        net_out = cw.get_metric_statistics(
            Namespace="AWS/EC2",
            MetricName="NetworkOut",
            Dimensions=[{"Name": "InstanceId", "Value": instance_id}],
            StartTime=start, EndTime=end,
            Period=3600 * 24,
            Statistics=["Sum"]
        )
        if net_out["Datapoints"]:
            net_out_sum = sum(dp["Sum"] for dp in net_out["Datapoints"]) / (1024 ** 3)  # bytes → GB

    except Exception as e:
        print(f"      [WARN] Metrics fetch failed for {instance_id}: {e}")

    return cpu_avg, net_in_sum, net_out_sum

def get_instance_metrics(session, account_id, region):
    """Fetch EC2 instance metrics + cost + environment + instance specs for a given region"""
    ec2 = session.client("ec2", region_name=region)
    cw = session.client("cloudwatch", region_name=region)

    data = []
    reservations = ec2.describe_instances()["Reservations"]

    for reservation in reservations:
        for instance in reservation["Instances"]:
            instance_id = instance["InstanceId"]

            # Instance name tag
            name = None
            for tag in instance.get("Tags", []):
                if tag["Key"] == "Name":
                    name = tag["Value"]

            # Instance state
            state = instance["State"]["Name"]

            # Instance type, vCPU, RAM
            instance_type = instance.get("InstanceType")
            vcpu = None
            ram_gb = None
            try:
                # describe instance types
                inst_type_desc = ec2.describe_instance_types(InstanceTypes=[instance_type])
                if inst_type_desc["InstanceTypes"]:
                    vcpu = inst_type_desc["InstanceTypes"][0]["VCpuInfo"]["DefaultVCpus"]
                    ram_gb = inst_type_desc["InstanceTypes"][0]["MemoryInfo"]["SizeInMiB"] / 1024  # MiB → GiB
            except Exception as e:
                print(f"      [WARN] Failed to fetch instance type details for {instance_id}: {e}")

            # Volume size (only root volume considered here)
            volume_size = None
            try:
                block_mappings = instance.get("BlockDeviceMappings", [])
                if block_mappings:
                    vol_id = block_mappings[0]["Ebs"]["VolumeId"]
                    vol_desc = ec2.describe_volumes(VolumeIds=[vol_id])
                    if vol_desc["Volumes"]:
                        volume_size = vol_desc["Volumes"][0]["Size"]  # in GiB
            except Exception as e:
                print(f"      [WARN] Failed to fetch volume size for {instance_id}: {e}")

            # Loop periods
            for period, days in [("24h", 1), ("7d", 7), ("30d", 30)]:
                cpu_avg, net_in, net_out = get_metrics_from_cw(cw, instance_id, days)
                cost, environment = get_cost_and_env_from_cur(account_id, instance_id, days)

                data.append((
                    account_id, region, instance_id, name, instance_type, vcpu, ram_gb, volume_size,
                    state, environment, period, cpu_avg, net_in, net_out, cost
                ))

    return data

def upsert_data(records):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(CREATE_TABLE_SQL)  # Ensure table exists
    for rec in records:
        cur.execute(UPSERT_SQL, rec)
    conn.commit()
    cur.close()
    conn.close()

# ---------- MAIN ----------
def main():
    accounts = fetch_accounts()
    for acc in accounts:
        account_id = acc["account_id"]
        print(f"[INFO] Processing account: {account_id}")

        session = boto3.session.Session(
            aws_access_key_id=acc["access_key"],
            aws_secret_access_key=acc["secret_key"]
        )

        # fetch all AWS regions dynamically
        ec2_global = session.client("ec2", region_name="us-east-1")
        regions = [r["RegionName"] for r in ec2_global.describe_regions()["Regions"]]

        for region in regions:
            print(f"   [INFO] Checking region: {region}")
            try:
                records = get_instance_metrics(session, account_id, region)
                if records:
                    upsert_data(records)
                    print(f"   [SUCCESS] Inserted/Updated {len(records)} rows for {account_id} in {region}")
                else:
                    print(f"   [INFO] No instances found in {region}")
            except Exception as e:
                print(f"   [ERROR] Failed in region {region}: {e}")

if __name__ == "__main__":
    main()
