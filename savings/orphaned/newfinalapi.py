from fastapi import FastAPI
import psycopg2
from psycopg2.extras import RealDictCursor

# ---------- DB CONFIG ----------
DB_CONFIG = {
    "host": "localhost",
    "dbname": "ims",
    "user": "postgres",
    "password": "Abcd@1234",   # change if needed
    "port": 5432
}

def connect_db():
    return psycopg2.connect(**DB_CONFIG)

# ---------- FASTAPI APP ----------
app = FastAPI(title="AWS Resource Optimization API")

@app.get("/resources")
def get_all_resources():
    """
    Fetch orphaned volumes, orphaned EIPs, orphaned snapshots,
    and underutilized EC2/EBS from DB in one response.
    """
    data = {
        "orphaned_volumes": [],
        "orphaned_eips": [],
        "orphaned_snapshots": [],
        "underutilized_ec2": [],
        "underutilized_ebs": []
    }

    conn = None
    try:
        conn = connect_db()
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # --- Orphaned Volumes ---
            cur.execute("""
                SELECT account_id, region, volume_id, volume_name,
                       volume_type, volume_size, cost_savings, fetched_at, status
                FROM orphaned_volumes_with_cost
                ORDER BY fetched_at DESC
            """)
            data["orphaned_volumes"] = cur.fetchall()

            # --- Orphaned EIPs ---
            cur.execute("""
                SELECT account_id, account_name, region, public_ip,
                       allocation_id, arn, months, cost
                FROM orphanedeip
                ORDER BY months DESC
            """)
            data["orphaned_eips"] = cur.fetchall()

            # --- Orphaned Snapshots ---
            cur.execute("""
                SELECT account_id, account_name, region, snapshot_id,
                       snapshot_name, description, size, costs, created_at
                FROM orphanedsnapshotswithcost
                ORDER BY created_at DESC
            """)
            data["orphaned_snapshots"] = cur.fetchall()

            # --- Underutilized EC2 ---
            cur.execute("""
                SELECT account_id, region, instance_id, instance_name,
                       instance_type, cost_savings, recommendations,
                       status, detected_at
                FROM underutilized_ec2
                ORDER BY detected_at DESC
            """)
            data["underutilized_ec2"] = cur.fetchall()

            # --- Underutilized EBS ---
            cur.execute("""
                SELECT account_id, region, volume_id, volume_name,
                       volume_type, volume_size, cost_savings, recommendations,
                       status, detected_at
                FROM underutilized_ebs
                ORDER BY detected_at DESC
            """)
            data["underutilized_ebs"] = cur.fetchall()

        return data

    except Exception as e:
        # Return full error message for debugging
        return {"error": str(e)}

    finally:
        if conn:
            conn.close()
