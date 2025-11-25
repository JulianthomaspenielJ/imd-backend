import boto3
import psycopg2
from datetime import datetime, timedelta
from botocore.exceptions import ClientError, NoCredentialsError, EndpointConnectionError

# -------------------------------
# Database Configuration
# -------------------------------
DB_CONFIG = {
    "dbname": "ims",
    "user": "postgres",
    "password": "Abcd@1234",
    "host": "localhost",
    "port": "5432"
}

# -------------------------------
# Tag Compliance Config
# -------------------------------
REQUIRED_TAGS = ["Name", "Environment", "Owner", "Project"]

# Update this list based on official AWS docs or your findings
NON_TAGGABLE_SERVICES = [
    "AWS Support (Business)",
    "AWS Support (Developer)",
    "AWS Support (Enterprise)",
    "Tax",
    "Amazon Route 53",
    "Data Transfer",
    "Savings Plans",
    "EC2 Instance Savings Plans",
    "AmazonCloudWatch",
    "AWS Cost Explorer",
    "AWS Key Management Service",
    "AWS Marketplace",
    "AWS Budgets",
    "Amazon Simple Email Service",
    "Amazon Simple Notification Service",
    "AWS Trusted Advisor",
    "AWS Organizations",
    "AWS CloudTrail",
    "Elastic Load Balancing",
    "AWS Identity and Access Management",
    "AWS Shield",
    "AWS Firewall Manager",
    "AWS Global Accelerator",
    "AWS Config",
    "AWS Systems Manager",
    "AWS CloudFormation",
    "Amazon Elastic Transcoder",
    "Amazon VPC",
    "Amazon SNS",
    "Amazon SQS",
    "AWS WAF",
    "Amazon Rekognition",
    "Amazon QuickSight",
    "AWS Service Catalog",
    "AWS Batch",
    "AWS Elastic Beanstalk",
    "AWS Step Functions",
    "AWS Glue",
    "AWS AppSync",
    "Amazon MQ",
    "AWS X-Ray",
    "AWS Lambda",
    "Amazon CloudFront",
    "AWS Transfer Family",
    "AWS CodeBuild",
    "AWS CodeDeploy",
    "AWS CodePipeline",
    "AWS CodeCommit",
    "AWS Snowball",
    "AWS DataSync",
    "Amazon Inspector",
    "AWS Secrets Manager",
    "Amazon ElastiCache",
    "Amazon Aurora Serverless",
    "Amazon EMR",
    "AWS Direct Connect",
    "Amazon ECR",
    "Amazon EKS",
    "AWS Cloud9",
    # add any other known non-taggable services you observe
]

# -------------------------------
# Ensure DB Table Exists
# -------------------------------
def ensure_table():
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS tag_compliance (
        account_id VARCHAR(100),
        check_date DATE,
        total_cost NUMERIC(12, 2),
        tagged_cost NUMERIC(12, 2),
        untagged_cost NUMERIC(12, 2),
        non_taggable_cost NUMERIC(12, 2),
        tagged_services TEXT,
        untagged_services TEXT,
        non_taggable_services TEXT,
        PRIMARY KEY (account_id, check_date)
    );
    """)
    conn.commit()
    cursor.close()
    conn.close()

# -------------------------------
# Fetch AWS Costs Grouped by Service & Tag
# -------------------------------
def fetch_costs_with_tags(ce_client, start_date, end_date, tag_key):
    return ce_client.get_cost_and_usage(
        TimePeriod={"Start": start_date, "End": end_date},
        Granularity="MONTHLY",
        Metrics=["UnblendedCost"],
        GroupBy=[
            {"Type": "DIMENSION", "Key": "SERVICE"},
            {"Type": "TAG", "Key": tag_key}
        ]
    )

# -------------------------------
# Get All AWS Regions
# -------------------------------
def get_all_regions(session):
    ec2 = session.client("ec2", region_name="us-east-1")
    return [r["RegionName"] for r in ec2.describe_regions(AllRegions=True)["Regions"]]

# -------------------------------
# Get Tagged/Untagged Resources Across Regions (ARN + Tags)
# -------------------------------
def get_resource_tags_all_regions(session):
    resources = []
    regions = get_all_regions(session)
    for region in regions:
        try:
            tagging = session.client("resourcegroupstaggingapi", region_name=region)
            paginator = tagging.get_paginator("get_resources")
            for page in paginator.paginate(ResourcesPerPage=100):
                for resource in page.get("ResourceTagMappingList", []):
                    arn = resource["ResourceARN"]
                    tags = {t["Key"]: t["Value"] for t in resource.get("Tags", [])}
                    resources.append({
                        "arn": arn,
                        "region": region,
                        "tags": tags
                    })
        except (ClientError, EndpointConnectionError) as e:
            print(f"⚠ Skipping region {region} for tag fetch: {e}")
            continue
    return resources

# -------------------------------
# Main Tag Compliance Function
# -------------------------------
def run_tag_compliance():
    ensure_table()

    today = datetime.utcnow().date()
    month_start = today.replace(day=1)
    month_end = (month_start + timedelta(days=32)).replace(day=1)

    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()

    cursor.execute("SELECT account_id, access_key, secret_key FROM master_user;")
    accounts = cursor.fetchall()

    for account_id, access_key, secret_key in accounts:
        print(f"\n🔍 Checking Tag Compliance for Account: {account_id}")

        total_cost = 0.0
        tagged_cost = 0.0
        untagged_cost = 0.0
        non_taggable_cost = 0.0

        tagged_services_detail = set()
        untagged_services_detail = set()
        non_taggable_services = set()

        try:
            session = boto3.Session(
                aws_access_key_id=access_key,
                aws_secret_access_key=secret_key
            )
            ce = session.client("ce", region_name="us-east-1")

            # Dictionary to track service costs by service and tags for deduplication
            service_costs = {}

            # Loop through each required tag key and collect cost info
            for tag_key in REQUIRED_TAGS:
                data = fetch_costs_with_tags(ce, str(month_start), str(month_end), tag_key)

                for result in data["ResultsByTime"]:
                    for group in result["Groups"]:
                        service_name = group["Keys"][0]
                        tag_value = group["Keys"][1]
                        cost = float(group["Metrics"]["UnblendedCost"]["Amount"])

                        # Track total cost once per service (we sum it later)
                        if service_name not in service_costs:
                            service_costs[service_name] = {
                                "cost": 0.0,
                                "tagged": True,
                                "missing_tags": set()
                            }
                        service_costs[service_name]["cost"] += cost

                        # Check if this service is non-taggable
                        if service_name in NON_TAGGABLE_SERVICES:
                            service_costs[service_name]["tagged"] = False  # Always non-taggable
                        else:
                            # If tag_value is "NoTagKey" then this tag is missing
                            if tag_value == "NoTagKey":
                                service_costs[service_name]["tagged"] = False
                                service_costs[service_name]["missing_tags"].add(tag_key)

            # After gathering costs for all tags, categorize each service properly
            for svc, info in service_costs.items():
                cost = info["cost"]
                total_cost += cost

                if svc in NON_TAGGABLE_SERVICES:
                    non_taggable_cost += cost
                    non_taggable_services.add(svc)
                elif info["tagged"]:
                    # Tagged service with all required tags present
                    # Add tag key-values for display - just generic since tag values are across keys
                    tagged_services_detail.add(f"{svc} (All Required Tags Present)")
                    tagged_cost += cost
                else:
                    # Untagged or missing some tags
                    missing = ", ".join(sorted(info["missing_tags"]))
                    untagged_services_detail.add(f"{svc} (Missing: {missing})")
                    untagged_cost += cost

            # Resource-level tag check (ARN + tags)
            resources = get_resource_tags_all_regions(session)
            for res in resources:
                tags_present = res["tags"]
                missing_tags = [t for t in REQUIRED_TAGS if t not in tags_present]

                # If resource belongs to a non-taggable service, ignore tagging for cost
                # But we don't have direct service name here; so only record untagged resources missing tags
                if missing_tags:
                    untagged_services_detail.add(
                        f"{res['arn']} (Missing: {', '.join(missing_tags)}; Region: {res['region']})"
                    )

        except (NoCredentialsError, ClientError) as e:
            print(f"❌ Account {account_id} failed AWS auth: {e}")
            tagged_services_detail = {"-"}
            untagged_services_detail = {"-"}
            non_taggable_services = {"-"}

        # -------------------------------
        # UPSERT into DB
        # -------------------------------
        cursor.execute("""
        INSERT INTO tag_compliance (
            account_id, check_date, total_cost, tagged_cost, untagged_cost, non_taggable_cost,
            tagged_services, untagged_services, non_taggable_services
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (account_id, check_date) DO UPDATE SET
            total_cost = EXCLUDED.total_cost,
            tagged_cost = EXCLUDED.tagged_cost,
            untagged_cost = EXCLUDED.untagged_cost,
            non_taggable_cost = EXCLUDED.non_taggable_cost,
            tagged_services = EXCLUDED.tagged_services,
            untagged_services = EXCLUDED.untagged_services,
            non_taggable_services = EXCLUDED.non_taggable_services;
        """, (
            account_id, month_start, round(total_cost, 2), round(tagged_cost, 2),
            round(untagged_cost, 2), round(non_taggable_cost, 2),
            ", ".join(sorted(tagged_services_detail)),
            ", ".join(sorted(untagged_services_detail)),
            ", ".join(sorted(non_taggable_services))
        ))

        conn.commit()

        # Console output
        print(f"📊 Total Cost: ${total_cost:.2f}")
        print(f"✅ Tagged Cost: ${tagged_cost:.2f}")
        print(f"⚠ Untagged Cost: ${untagged_cost:.2f}")
        print(f"📌 Non-Taggable Cost: ${non_taggable_cost:.2f}")
        print("✅ Tagged Services:", ", ".join(sorted(tagged_services_detail)))
        print("⚠ Untagged Services:", ", ".join(sorted(untagged_services_detail)))
        print("📌 Non-Taggable Services:", ", ".join(sorted(non_taggable_services)))

    cursor.close()
    conn.close()
    print("\n✅ Tag compliance check completed.")

# -------------------------------
# Run
# -------------------------------
if __name__ == "__main__":
    run_tag_compliance()
