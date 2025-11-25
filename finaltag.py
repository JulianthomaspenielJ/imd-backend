import psycopg2
import boto3
from botocore.exceptions import ClientError
import json

# PostgreSQL DB config
DB_CONFIG = {
    "host": "localhost",
    "dbname": "ims",
    "user": "postgres",
    "password": "Abcd@1234",
    "port": "5432"
}

def get_accounts_from_db():
    """Fetch AWS accounts credentials from cur_multiple_user table"""
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    cur.execute("SELECT account_id, account_name, access_key, secret_key, bucket_name, prefix FROM cur_multiple_user")
    rows = cur.fetchall()
    cur.close()
    conn.close()

    accounts = []
    for row in rows:
        accounts.append({
            "account_id": row[0],
            "account_name": row[1],
            "access_key": row[2],
            "secret_key": row[3],
            "bucket_name": row[4],
            "prefix": row[5]
        })
    return accounts

def get_all_regions(session):
    """Fetch all available AWS regions"""
    try:
        ec2_client = session.client("ec2", region_name="us-east-1")  # EC2 is global in us-east-1
        regions = ec2_client.describe_regions(AllRegions=True)["Regions"]
        return [r["RegionName"] for r in regions if r["OptInStatus"] in ["opt-in-not-required", "opted-in"]]
    except Exception as e:
        print(f"Error fetching regions: {e}")
        return ["us-east-1"]  # fallback

def classify_tags(tags):
    """Classify resources as Fully Tagged, Partially Tagged, or Not Tagged"""
    if not tags or len(tags) == 0:
        return "Not Tagged"

    required_keys = ["Project", "Environment", "Name"]
    user_keys = ["User", "Owner"]

    has_user_key = any(k in tags for k in user_keys)

    missing = [k for k in required_keys if k not in tags]
    if not has_user_key:
        missing.append("User/Owner")

    if len(missing) == 0:
        return "Fully Tagged"
    else:
        return "Partially Tagged"

def fetch_tags_for_account(account):
    """Fetch tags for all resources in a given AWS account across all regions"""
    account_resources = []

    try:
        base_session = boto3.Session(
            aws_access_key_id=account["access_key"],
            aws_secret_access_key=account["secret_key"]
        )

        regions = get_all_regions(base_session)

        # -------- Loop through each region --------
        for region in regions:
            try:
                tagging_client = base_session.client("resourcegroupstaggingapi", region_name=region)

                paginator = tagging_client.get_paginator("get_resources")
                for page in paginator.paginate(ResourcesPerPage=100):
                    for resource in page.get("ResourceTagMappingList", []):
                        arn = resource.get("ResourceARN")
                        tags = {tag["Key"]: tag["Value"] for tag in resource.get("Tags", [])}
                        tag_type = classify_tags(tags)
                        account_resources.append({
                            "Account": account["account_name"],
                            "Region": region,
                            "Service": arn.split(":")[2] if ":" in arn else "Unknown",
                            "Resource": arn,
                            "Tags": tags,
                            "Type": tag_type
                        })
            except Exception as e:
                print(f"  ⚠️ Error in region {region} for account {account['account_name']}: {e}")

        # -------- Handle S3 Buckets (global) --------
        try:
            s3_client = base_session.client("s3")
            buckets = s3_client.list_buckets().get("Buckets", [])
            for bucket in buckets:
                bucket_name = bucket["Name"]
                try:
                    tag_set = s3_client.get_bucket_tagging(Bucket=bucket_name).get("TagSet", [])
                    tags = {tag["Key"]: tag["Value"] for tag in tag_set}
                except ClientError as e:
                    if e.response['Error']['Code'] == 'NoSuchTagSet':
                        tags = {}
                    else:
                        raise
                tag_type = classify_tags(tags)
                account_resources.append({
                    "Account": account["account_name"],
                    "Region": "global",
                    "Service": "s3",
                    "Resource": f"arn:aws:s3:::{bucket_name}",
                    "Tags": tags,
                    "Type": tag_type
                })
        except Exception as e:
            print(f"  ⚠️ Error fetching S3 buckets for account {account['account_name']}: {e}")

    except Exception as e:
        print(f"Error fetching tags for account {account['account_name']}: {e}")

    return account_resources

def create_tags_table():
    """Create tags table if not exists (with only required columns)"""
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS tags (
            id SERIAL PRIMARY KEY,
            account TEXT,
            region TEXT,
            service TEXT,
            resource TEXT,
            tags JSONB,
            type TEXT
        );
    """)
    conn.commit()
    cur.close()
    conn.close()

def clear_tags_table():
    """Truncate tags table before inserting fresh data"""
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    cur.execute("TRUNCATE TABLE tags;")
    conn.commit()
    cur.close()
    conn.close()

def insert_tags(resources):
    """Insert fetched tags into the tags table"""
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()

    for r in resources:
        cur.execute("""
            INSERT INTO tags (account, region, service, resource, tags, type)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (
            r['Account'],
            r['Region'],
            r['Service'],
            r['Resource'],
            json.dumps(r['Tags']),  # store tags as JSONB
            r['Type']
        ))

    conn.commit()
    cur.close()
    conn.close()

def main():
    # Prepare DB
    create_tags_table()
    clear_tags_table()

    accounts = get_accounts_from_db()
    all_data = []

    for account in accounts:
        print(f"\n🔹 Fetching resources for account: {account['account_name']} ({account['account_id']})")
        resources = fetch_tags_for_account(account)
        all_data.extend(resources)

    # Save results in DB
    insert_tags(all_data)

    # Print results (optional)
    for r in all_data:
        print("=" * 90)
        print(f"Account: {r['Account']}")
        print(f"Region: {r['Region']}")
        print(f"Service: {r['Service']}")
        print(f"Resource: {r['Resource']}")
        print(f"Tags: {r['Tags']}")
        print(f"Type: {r['Type']}")

if __name__ == "__main__":
    main()
