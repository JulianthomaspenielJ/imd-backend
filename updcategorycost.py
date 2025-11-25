import psycopg2
from psycopg2.extras import RealDictCursor
from collections import defaultdict

# ---------- DB CONFIG ----------
DB_CONFIG = {
    "host": "localhost",
    "dbname": "ims",
    "user": "postgres",
    "password": "Abcd@1234",  # change to your password
    "port": 5432
}

# ---------- CATEGORY MAP (normalized to DB short service names) ----------
CATEGORY_MAP = {
    # ---------------- Compute ----------------
    "Compute": [
        "AmazonEC2", "AmazonEC2-Other", "AWSElasticBeanstalk", "AWSLambda", "ElasticMapReduce",
        "AWSFargate", "AWSBatch", "AWSOutposts", "AmazonLightsail",
        "AmazonECS", "AmazonEKS", "VMwareCloudOnAWS", "AWSWavelength"
    ],

    # ---------------- Database ----------------
    "Database": [
        "AmazonRDS", "AmazonAurora", "AmazonDynamoDB", "AmazonRedshift",
        "AmazonElastiCache", "AmazonDocumentDB", "AmazonNeptune", "AmazonQLDB",
        "AmazonTimestream", "AmazonSimpleDB", "AWSDatabaseMigrationService"
    ],

    # ---------------- AI/ML ----------------
    "AI/ML": [
        "AmazonSageMaker", "AWSComprehend", "AmazonRekognition", "AmazonTranslate",
        "AmazonPolly", "AmazonLex", "AmazonTranscribe", "AmazonTextract",
        "AmazonForecast", "AmazonPersonalize", "AWSDeepLens", "AWSInferentia",
        "AWSPanorama", "AWSHealthLake"
    ],

    # ---------------- Storage ----------------
    "Storage": [
        "AmazonS3", "AmazonEBS", "AmazonEFS", "AmazonFSx",
        "AmazonGlacier", "AmazonS3GlacierDeepArchive", "AmazonS3Outposts",
        "AWSBackup", "AWSStorageGateway"
    ],

    # ---------------- Data Transfer ----------------
    "Data Transfer": [
        "AWSDataTransfer"  # explicit billing line item
    ],

    # ---------------- Networking ----------------
    "Networking": [
        "AmazonVPC", "AmazonRoute53", "AWSDirectConnect", "AWSTransitGateway",
        "AWSGlobalAccelerator", "AmazonCloudFront", "AWSPrivateLink",
        "AWSAppMesh", "AmazonAPIGateway", "ElasticLoadBalancing"
    ],

    # ---------------- Migration / Transfer ----------------
    "Migration / Transfer": [
        "AWSDataSync", "AWSSnowball", "AWSSnowmobile"
    ],

    # ---------------- Analytics / Streaming ----------------
    "Analytics / Streaming": [
        "AmazonKinesis", "AmazonAthena", "AWSGlue", "AmazonEMR"
    ],

    # ---------------- Security / Monitoring ----------------
    "Security / Monitoring": [
        "awskms", "AWSCloudTrail", "AmazonCloudWatch", "AWSConfig", "AWSWAF",
        "AWS Key Management Service", "AWSKMS", "AWS Identity and Access Management (IAM)",
        "Amazon GuardDuty", "AWS WAF", "AWS Shield", "AWS Security Hub",
        "Amazon Macie", "AWS Secrets Manager"
    ],

    # ---------------- Developer Tools ----------------
    "Developer Tools": [
        "AWSCodeCommit", "AWSCodeBuild", "AWSCodeDeploy", "AWSCodePipeline"
    ],

    # ---------------- Business Applications ----------------
    "Business Applications": [
        "AmazonQuickSight"
    ],

    # ---------------- Management & Governance ----------------
    "Management & Governance": [
        "AWSCostExplorer", "AWSSystemsManager"
    ],

    # ---------------- Application Integration ----------------
    "Application Integration": [
        "AWSQueueService", "AWSEvents"  # SQS + EventBridge
    ],

    # ---------------- Others (catch-all) ----------------
    "Others": []  # unmapped services will fall here
}


# ---------- MAIN FUNCTION ----------
def fetch_category_costs():
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor(cursor_factory=RealDictCursor)

    # Fetch aggregated costs by account + service
    cur.execute("""
        SELECT account_id, service, SUM(unblended_cost) as total_cost
        FROM multiple_user_cur
        GROUP BY account_id, service
        ORDER BY account_id, total_cost DESC;
    """)
    rows = cur.fetchall()
    conn.close()

    # Structure: { account_id -> { category -> {total, services[]} } }
    account_category_data = defaultdict(lambda: defaultdict(lambda: {"total": 0, "services": []}))

    for row in rows:
        account_id = row["account_id"]
        service = row["service"]
        cost = float(row["total_cost"])
        found = False

        # Match service to category
        for category, services in CATEGORY_MAP.items():
            if service in services:
                account_category_data[account_id][category]["total"] += cost
                account_category_data[account_id][category]["services"].append(
                    {"service": service, "cost": cost}
                )
                found = True
                break

        # If no match → Others
        if not found:
            account_category_data[account_id]["Others"]["total"] += cost
            account_category_data[account_id]["Others"]["services"].append(
                {"service": service, "cost": cost}
            )

    # Keep only Top 5 services per category
    for acc_id, categories in account_category_data.items():
        for cat in categories:
            categories[cat]["services"] = sorted(
                categories[cat]["services"],
                key=lambda x: x["cost"],
                reverse=True
            )[:5]

    return account_category_data


# ---------- RUN SCRIPT ----------
if __name__ == "__main__":
    data = fetch_category_costs()
    for account_id, categories in data.items():
        print(f"\n===== Account {account_id} =====")
        for category, info in categories.items():
            print(f"{category} - Total: ${info['total']:.2f}")
            for s in info["services"]:
                print(f"   {s['service']} - ${s['cost']:.2f}")
