#!/usr/bin/env python3
"""
underutilized_cloudwatch_cur.py

Standalone script to:
- Read AWS credentials from cur_multiple_user
- Detect underutilized EC2 (low CPU) using CloudWatch
- Detect underutilized EBS (low I/O) using CloudWatch
- Fetch month-to-date costs for each resource from multiple_user_cur table
- TRUNCATE underutilized_ec2 and underutilized_ebs and insert fresh rows
- Optionally run as a FastAPI service with CORS (--serve)
"""

import os
import json
import sys
from datetime import datetime, timedelta
import boto3
import psycopg2
from psycopg2.extras import RealDictCursor, execute_values
import argparse
import math
import statistics

# Optional FastAPI - only used if --serve passed and fastapi is installed
try:
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware
    HAVE_FASTAPI = True
except Exception:
    HAVE_FASTAPI = False

# ---------------- DB CONFIG - change or use env vars ----------------
DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "dbname": os.getenv("DB_NAME", "ims"),
    "user": os.getenv("DB_USER", "postgres"),
    "password": os.getenv("DB_PASSWORD", "Abcd@1234"),
    "port": int(os.getenv("DB_PORT", "5432")),
}

# ---------------- Detection thresholds ----------------
EC2_CPU_THRESHOLD_PERCENT = 10.0      # average CPU < 10% => underutilized
EC2_EVAL_DAYS = 14                    # evaluate last 14 days

EBS_IOPS_THRESHOLD_PER_DAY = 1.0      # average ops/day < 1 => underutilized
EBS_EVAL_DAYS = 14

# ---------------- Utilities ----------------
def db_connect():
    conn_str = "host={host} dbname={dbname} user={user} password={password} port={port}".format(**DB_CONFIG)
    return psycopg2.connect(conn_str)

def month_start_and_today_dates():
    today = datetime.utcnow().date()
    month_start = today.replace(day=1)
    # return datetime objects for comparison with usage_date (assuming usage_date stored as date or timestamp)
    return datetime.combine(month_start, datetime.min.time()), datetime.combine(today, datetime.max.time())

def get_accounts():
    with db_connect() as conn, conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("SELECT account_id, account_name, access_key, secret_key FROM cur_multiple_user")
        return cur.fetchall()

def truncate_tables():
    with db_connect() as conn, conn.cursor() as cur:
        cur.execute("TRUNCATE underutilized_ec2 RESTART IDENTITY CASCADE")
        cur.execute("TRUNCATE underutilized_ebs RESTART IDENTITY CASCADE")
        conn.commit()

def sum_costs_month_to_date(account_id, resource_like_patterns, service_filters=None):
    """
    Sum unblended_cost from multiple_user_cur for given account_id and resource patterns
    resource_like_patterns: list of patterns for SQL LIKE comparisons (e.g. ['%i-0123%','%instance-name%'])
    service_filters: optional list of strings to match service (ILIKE any)
    """
    start_dt, end_dt = month_start_and_today_dates()
    query = """
        SELECT SUM(unblended_cost) as sum_cost
        FROM multiple_user_cur
        WHERE account_id = %s
          AND usage_date >= %s
          AND usage_date <= %s
    """
    params = [account_id, start_dt, end_dt]

    # resource_id match OR name match
    if resource_like_patterns:
        resource_clauses = []
        for pat in resource_like_patterns:
            resource_clauses.append("(resource_id ILIKE %s OR name ILIKE %s)")
            params.extend([pat, pat])
        query += " AND (" + " OR ".join(resource_clauses) + ")"

    if service_filters:
        svc_clauses = []
        for svc in service_filters:
            svc_clauses.append("service ILIKE %s")
            params.append(svc)
        query += " AND (" + " OR ".join(svc_clauses) + ")"

    with db_connect() as conn, conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(query, params)
        row = cur.fetchone()
        return float(row['sum_cost']) if row and row['sum_cost'] is not None else 0.0

# ---------------- CloudWatch helpers ----------------
def cw_client_for_keys(access_key, secret_key, region):
    return boto3.client("cloudwatch", region_name=region, aws_access_key_id=access_key, aws_secret_access_key=secret_key)

def ec2_client_for_keys(access_key, secret_key, region):
    return boto3.client("ec2", region_name=region, aws_access_key_id=access_key, aws_secret_access_key=secret_key)

def get_region_list(session):
    # session is boto3.Session
    return session.get_available_regions('ec2')

def get_instance_list(ec2_client):
    # returns list of instances: dicts with InstanceId, InstanceType, Tags, Placement (Region not here)
    instances = []
    paginator = ec2_client.get_paginator('describe_instances')
    for page in paginator.paginate():
        for r in page.get('Reservations', []):
            for i in r.get('Instances', []):
                instances.append(i)
    return instances

def get_volume_list(ec2_client):
    volumes = []
    paginator = ec2_client.get_paginator('describe_volumes')
    for page in paginator.paginate():
        volumes.extend(page.get('Volumes', []))
    return volumes

def get_avg_cpu_for_instance(cw, instance_id, days=EC2_EVAL_DAYS):
    end = datetime.utcnow()
    start = end - timedelta(days=days)
    # Get daily averages: use Period = 86400 (1 day)
    try:
        resp = cw.get_metric_statistics(
            Namespace='AWS/EC2',
            MetricName='CPUUtilization',
            Dimensions=[{'Name':'InstanceId','Value':instance_id}],
            StartTime=start,
            EndTime=end,
            Period=86400,
            Statistics=['Average']
        )
        datapoints = resp.get('Datapoints', [])
        # datapoints may be unordered; compute average of daily averages
        if not datapoints:
            return None
        averages = [d['Average'] for d in datapoints if 'Average' in d]
        return float(sum(averages)/len(averages)) if averages else None
    except Exception:
        return None

def get_avg_iops_for_volume(cw, volume_id, days=EBS_EVAL_DAYS, region=None):
    """
    Return average (read_ops + write_ops) per day across the period.
    We'll query VolumeReadOps and VolumeWriteOps and sum their daily averages.
    """
    end = datetime.utcnow()
    start = end - timedelta(days=days)
    period = 86400
    total_daily = []
    try:
        read = cw.get_metric_statistics(
            Namespace='AWS/EBS',
            MetricName='VolumeReadOps',
            Dimensions=[{'Name':'VolumeId','Value':volume_id}],
            StartTime=start, EndTime=end, Period=period, Statistics=['Sum']
        ).get('Datapoints', [])
        write = cw.get_metric_statistics(
            Namespace='AWS/EBS',
            MetricName='VolumeWriteOps',
            Dimensions=[{'Name':'VolumeId','Value':volume_id}],
            StartTime=start, EndTime=end, Period=period, Statistics=['Sum']
        ).get('Datapoints', [])
        # Build mapping day->ops
        daily = {}
        for d in read:
            day = d['Timestamp'].date()
            daily.setdefault(day, 0.0)
            daily[day] += d.get('Sum', 0.0)
        for d in write:
            day = d['Timestamp'].date()
            daily.setdefault(day, 0.0)
            daily[day] += d.get('Sum', 0.0)
        if not daily:
            return None
        # average ops per day
        return float(sum(daily.values())/len(daily))
    except Exception:
        return None

# ---------------- Detection logic per account ----------------
def detect_underutilized_for_account(account):
    """
    account: dict with account_id, account_name, access_key, secret_key
    returns two lists: ec2_rows, ebs_rows and totals: ec2_total_cost, ebs_total_cost
    """
    acc_id = account['account_id']
    access_key = account['access_key']
    secret_key = account['secret_key']

    session = boto3.session.Session(aws_access_key_id=access_key, aws_secret_access_key=secret_key)
    regions = get_region_list(session)

    ec2_candidates = []
    ebs_candidates = []

    ec2_total_cost = 0.0
    ebs_total_cost = 0.0

    for region in regions:
        ec2c = ec2_client_for_keys(access_key, secret_key, region)
        cw = cw_client_for_keys(access_key, secret_key, region)

        # Instances
        try:
            instances = get_instance_list(ec2c)
        except Exception:
            instances = []

        for inst in instances:
            instance_id = inst.get('InstanceId')
            instance_type = inst.get('InstanceType')
            # get Name tag
            name = None
            for t in inst.get('Tags', []):
                if t.get('Key') == 'Name':
                    name = t.get('Value')
                    break

            # get avg CPU
            avg_cpu = get_avg_cpu_for_instance(cw, instance_id)
            # interpret None as no data; we'll skip those (can't judge)
            is_under = False
            reason = {}
            if avg_cpu is not None:
                reason['avg_cpu'] = round(avg_cpu,3)
                if avg_cpu < EC2_CPU_THRESHOLD_PERCENT:
                    is_under = True
            else:
                # If no CPU datapoints, skip marking
                reason['avg_cpu'] = None

            if is_under:
                # fetch month-to-date cost from CUR table
                # try matching by resource_id or name to get relevant cost rows
                patterns = [f"%{instance_id}%", f"%{instance_type}%", f"%{name}%" if name else None]
                patterns = [p for p in patterns if p]
                # Filter service to EC2-like entries
                service_filters = ['%EC2%', '%Elastic Compute Cloud%', '%Amazon Elastic Compute Cloud%']
                cost = sum_costs_month_to_date(acc_id, patterns, service_filters)
                ec2_total_cost += cost
                rec = {
                    "reason": "low_cpu",
                    "details": reason,
                    "suggestion": "Consider stop/delete or downsize instance"
                }
                ec2_candidates.append((
                    acc_id, region, instance_id, name, instance_type, float(round(cost,4)), json.dumps(rec), 'unassigned', datetime.utcnow()
                ))

        # Volumes
        try:
            volumes = get_volume_list(ec2c)
        except Exception:
            volumes = []

        for vol in volumes:
            vol_id = vol.get('VolumeId')
            vol_type = vol.get('VolumeType')
            vol_size = vol.get('Size')
            # find a "Name" tag if exists
            vname = None
            for t in vol.get('Tags', []):
                if t.get('Key') == 'Name':
                    vname = t.get('Value')
                    break

            avg_ops = get_avg_iops_for_volume(cw, vol_id)
            is_under_vol = False
            vreason = {}
            if avg_ops is not None:
                vreason['avg_ops_per_day'] = round(avg_ops,3)
                if avg_ops < EBS_IOPS_THRESHOLD_PER_DAY:
                    is_under_vol = True
            else:
                vreason['avg_ops_per_day'] = None

            # additionally if volume is unattached, mark as underutilized
            attachments = vol.get('Attachments', [])
            if not attachments:
                # unattached => likely orphaned/underutilized
                is_under_vol = True
                vreason['unattached'] = True

            if is_under_vol:
                patterns = [f"%{vol_id}%", f"%{vname}%" if vname else None]
                patterns = [p for p in patterns if p]
                service_filters = ['%EBS%', '%Elastic Block Store%', '%Amazon Elastic Block Store%', '%AmazonEC2%']
                cost = sum_costs_month_to_date(acc_id, patterns, service_filters)
                ebs_total_cost += cost
                rec = {
                    "reason": "low_io_or_unattached",
                    "details": vreason,
                    "suggestion": "Consider deleting or moving to lower-cost storage or snapshotting and deleting volume"
                }
                ebs_candidates.append((
                    acc_id, region, vol_id, vname, vol_type, vol_size, float(round(cost,4)), json.dumps(rec), 'unassigned', datetime.utcnow()
                ))

    return ec2_candidates, ebs_candidates, ec2_total_cost, ebs_total_cost

# ---------------- Main flow ----------------
def run_once():
    accounts = get_accounts()
    if not accounts:
        print("No accounts found in cur_multiple_user.")
        return

    print("Truncating existing underutilized tables...")
    truncate_tables()

    grand_ec2 = 0.0
    grand_ebs = 0.0
    total_ec2_rows = 0
    total_ebs_rows = 0

    for acc in accounts:
        print(f"\nProcessing account {acc.get('account_id')} ({acc.get('account_name')})")
        try:
            ec2_rows, ebs_rows, ec2_cost, ebs_cost = detect_underutilized_for_account(acc)
            # insert rows
            if ec2_rows:
                with db_connect() as conn, conn.cursor() as cur:
                    sql = """
                        INSERT INTO underutilized_ec2
                        (account_id, region, instance_id, instance_name, instance_type, cost_savings, recommendations, status, detected_at)
                        VALUES %s
                    """
                    execute_values(cur, sql, ec2_rows)
                    conn.commit()
            if ebs_rows:
                with db_connect() as conn, conn.cursor() as cur:
                    sql = """
                        INSERT INTO underutilized_ebs
                        (account_id, region, volume_id, volume_name, volume_type, volume_size, cost_savings, recommendations, status, detected_at)
                        VALUES %s
                    """
                    execute_values(cur, sql, ebs_rows)
                    conn.commit()

            print(f"  EC2 items added: {len(ec2_rows)}  | EC2 month-to-date cost (sum): ${ec2_cost:,.2f}")
            print(f"  EBS items added: {len(ebs_rows)}  | EBS month-to-date cost (sum): ${ebs_cost:,.2f}")

            total_ec2_rows += len(ec2_rows)
            total_ebs_rows += len(ebs_rows)
            grand_ec2 += ec2_cost
            grand_ebs += ebs_cost

        except Exception as e:
            print(f"  Error processing account {acc.get('account_id')}: {e}")

    print("\n=== SUMMARY ===")
    print(f"Total EC2 rows inserted: {total_ec2_rows}")
    print(f"Total EBS rows inserted: {total_ebs_rows}")
    print(f"Total EC2 potential savings (month-to-date): ${grand_ec2:,.2f}")
    print(f"Total EBS potential savings (month-to-date): ${grand_ebs:,.2f}")
    print(f"Combined potential savings (month-to-date): ${grand_ec2 + grand_ebs:,.2f}")

# ---------------- Optional FastAPI serve mode (CORS) ----------------
def create_app_for_serving():
    if not HAVE_FASTAPI:
        raise RuntimeError("FastAPI not installed. Install fastapi and uvicorn if you want serve mode.")
    app = FastAPI()
    app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
    @app.get("/run-scan")
    def run_scan_endpoint():
        try:
            run_once()
            return {"status":"ok", "message":"scan completed"}
        except Exception as e:
            return {"status":"error", "message": str(e)}
    @app.get("/health")
    def health():
        return {"status":"alive"}
    return app

# ---------------- CLI ----------------
def main():
    p = argparse.ArgumentParser()
    p.add_argument("--serve", action="store_true", help="Start as HTTP service (requires FastAPI & uvicorn)")
    p.add_argument("--port", type=int, default=8000, help="Port for serve mode")
    args = p.parse_args()

    if args.serve:
        if not HAVE_FASTAPI:
            print("FastAPI not installed. Install with: pip3 install fastapi uvicorn")
            sys.exit(1)
        app = create_app_for_serving()
        import uvicorn
        uvicorn.run(app, host="0.0.0.0", port=args.port)
    else:
        run_once()

if __name__ == "__main__":
    main()
