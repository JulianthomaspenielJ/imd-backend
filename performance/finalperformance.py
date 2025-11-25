import boto3
import psycopg2
import pandas as pd
import datetime

DB_CONFIG = {
    "host": "localhost",
    "dbname": "ims",
    "user": "postgres",
    "password": "Abcd@1234",
    "port": 5432
}

def create_performance_table(cur):
    # Drop and create fresh table to guarantee truncation behavior
    cur.execute("DROP TABLE IF EXISTS performance_aws;")
    cur.execute("""
        CREATE TABLE performance_aws (
            id SERIAL PRIMARY KEY,
            account_id VARCHAR(32),
            account_name VARCHAR(64),
            region VARCHAR(32),
            instance_id VARCHAR(32),
            timestamp TIMESTAMP,
            cpu_utilization FLOAT,
            memory_utilization FLOAT,
            disk_utilization FLOAT,
            weekly_trend VARCHAR(32),
            weekly_sizing_recommendation VARCHAR(16),
            weekly_spike_detected BOOLEAN,
            monthly_trend VARCHAR(32),
            monthly_sizing_recommendation VARCHAR(16),
            monthly_spike_detected BOOLEAN
        );
    """)

def analyze_trend(df):
    # Returns trend, recommendation, spike detection for given cpu data frame
    spike = bool((df['cpu_utilization'] > 70).any())
    mean_cpu = float(df['cpu_utilization'].mean()) if pd.notnull(df['cpu_utilization'].mean()) else 0.0
    recommendation = 'upsize' if spike else ('downsize' if mean_cpu < 30 else 'keep')
    trend = 'spike' if spike else 'normal'
    return trend, recommendation, spike

def get_metrics(client, instance_id, start, end):
    metrics = {}
    for metric in ['CPUUtilization', 'DiskReadBytes', 'DiskWriteBytes']:
        response = client.get_metric_statistics(
            Namespace='AWS/EC2',
            MetricName=metric,
            Dimensions=[{'Name': 'InstanceId', 'Value': instance_id}],
            StartTime=start,
            EndTime=end,
            Period=3600,
            Statistics=['Average']
        )
        if response['Datapoints']:
            metrics[metric] = float(sorted(response['Datapoints'], key=lambda x: x['Timestamp'])[-1]['Average'])
        else:
            metrics[metric] = None

    mem_response = client.get_metric_statistics(
        Namespace='CWAgent',
        MetricName='mem_used_percent',
        Dimensions=[{'Name': 'InstanceId', 'Value': instance_id}],
        StartTime=start,
        EndTime=end,
        Period=3600,
        Statistics=['Average']
    )
    if mem_response['Datapoints']:
        metrics['MemoryUtilization'] = float(sorted(mem_response['Datapoints'], key=lambda x: x['Timestamp'])[-1]['Average'])
    else:
        metrics['MemoryUtilization'] = None

    return metrics

def main():
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    create_performance_table(cur)
    conn.commit()

    cur.execute("SELECT account_id, account_name, access_key, secret_key FROM cur_multiple_user;")
    accounts = cur.fetchall()

    regions = boto3.Session().get_available_regions('ec2')

    for account in accounts:
        account_id, account_name, ak, sk = account
        for region in regions:
            session = boto3.Session(
                aws_access_key_id=ak,
                aws_secret_access_key=sk,
                region_name=region
            )
            ec2 = session.client('ec2', region_name=region)
            cw = session.client('cloudwatch', region_name=region)
            try:
                reservations = ec2.describe_instances()['Reservations']
            except Exception:
                continue
            for res in reservations:
                for inst in res['Instances']:
                    instance_id = inst['InstanceId']

                    # Collect weekly and monthly metric data points
                    data_points = {}
                    for period_name, days in [('weekly', 7), ('monthly', 30)]:
                        start = datetime.datetime.utcnow() - datetime.timedelta(days=days)
                        end = datetime.datetime.utcnow()
                        metrics = get_metrics(cw, instance_id, start, end)
                        data_points[period_name] = {
                            'timestamp': end,
                            'cpu_utilization': float(metrics.get('CPUUtilization') or 0.0),
                            'memory_utilization': float(metrics.get('MemoryUtilization') or 0.0),
                            'disk_utilization': float((metrics.get('DiskReadBytes') or 0.0) + (metrics.get('DiskWriteBytes') or 0.0))
                        }

                    # Create DataFrames for trend analysis
                    weekly_df = pd.DataFrame([data_points['weekly']])
                    monthly_df = pd.DataFrame([data_points['monthly']])

                    weekly_trend, weekly_recommendation, weekly_spike = analyze_trend(weekly_df)
                    monthly_trend, monthly_recommendation, monthly_spike = analyze_trend(monthly_df)

                    # Insert combined record with both trends
                    cur.execute("""
                        INSERT INTO performance_aws (
                            account_id, account_name, region, instance_id, timestamp,
                            cpu_utilization, memory_utilization, disk_utilization,
                            weekly_trend, weekly_sizing_recommendation, weekly_spike_detected,
                            monthly_trend, monthly_sizing_recommendation, monthly_spike_detected
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, (
                        str(account_id),
                        str(account_name),
                        str(region),
                        str(instance_id),
                        data_points['monthly']['timestamp'],
                        data_points['monthly']['cpu_utilization'],
                        data_points['monthly']['memory_utilization'],
                        data_points['monthly']['disk_utilization'],
                        weekly_trend,
                        weekly_recommendation,
                        weekly_spike,
                        monthly_trend,
                        monthly_recommendation,
                        monthly_spike
                    ))
                    conn.commit()

    cur.close()
    conn.close()

if __name__ == "__main__":
    main()
