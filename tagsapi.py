from fastapi import FastAPI
import psycopg2
from psycopg2.extras import RealDictCursor
import boto3

app = FastAPI()

# PostgreSQL connection config
DB_CONFIG = {
    "dbname": "ims",
    "user": "postgres",
    "password": "Abcd@1234",
    "host": "localhost",
    "port": 5432
}

# Required tags
REQUIRED_TAGS = {"Project", "Environment", "Name", "User", "Owner"}

def classify_tags(tags: dict):
    """Classify resources as Fully Tagged, Partially Tagged, or Not Tagged."""
    if not tags:
        return "Not Tagged"

    required_check = {"Project", "Environment", "Name"}
    user_or_owner = {"User", "Owner"}

    has_required = required_check.issubset(tags.keys())
    has_user_or_owner = any(k in tags for k in user_or_owner)

    if has_required and has_user_or_owner:
        return "Fully Tagged"
    elif any(k in tags for k in REQUIRED_TAGS):
        return "Partially Tagged"
    else:
        return "Not Tagged"

@app.get("/")
def root():
    return {"message": "AWS Tags API is running 🚀"}

@app.post("/fetch-tags")
def fetch_and_store_tags():
    """Fetch AWS tags across accounts/regions and insert into DB."""
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()

    # Drop & recreate the table
    cur.execute("""
        DROP TABLE IF EXISTS tags;
        CREATE TABLE tags (
            account TEXT,
            region TEXT,
            resource_arn TEXT,
            service TEXT,
            tags JSONB,
            type TEXT
        );
    """)
    conn.commit()

    # Example: one AWS account creds from DB (extend as needed)
    accounts = [
        {"account_name": "example", "aws_access_key": "your_access_key", "aws_secret_key": "your_secret_key"}
    ]

    for account in accounts:
        session = boto3.Session(
            aws_access_key_id=account["aws_access_key"],
            aws_secret_access_key=account["aws_secret_key"],
            region_name="us-east-1"  # default region for fetching regions
        )

        ec2_client = session.client("ec2")
        regions = [r["RegionName"] for r in ec2_client.describe_regions()["Regions"]]

        for region in regions:
            try:
                tagging_client = session.client("resourcegroupstaggingapi", region_name=region)

                paginator = tagging_client.get_paginator("get_resources")
                for page in paginator.paginate(ResourcesPerPage=50):
                    for resource in page.get("ResourceTagMappingList", []):
                        arn = resource["ResourceARN"]
                        service = arn.split(":")[2]
                        tags = {t["Key"]: t["Value"] for t in resource.get("Tags", [])}
                        tag_type = classify_tags(tags)

                        cur.execute("""
                            INSERT INTO tags (account, region, resource_arn, service, tags, type)
                            VALUES (%s, %s, %s, %s, %s, %s)
                        """, (account["account_name"], region, arn, service, tags, tag_type))
                        conn.commit()

            except Exception as e:
                print(f"Error in {account['account_name']} - {region}: {e}")

    cur.close()
    conn.close()

    return {"status": "success", "message": "Tags fetched and stored in DB."}

@app.get("/tags")
def get_tags():
    """Retrieve all tags from DB"""
    conn = psycopg2.connect(**DB_CONFIG, cursor_factory=RealDictCursor)
    cur = conn.cursor()
    cur.execute("SELECT * FROM tags")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows
