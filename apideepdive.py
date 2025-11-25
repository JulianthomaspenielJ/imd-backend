from fastapi import FastAPI, Query
from typing import Optional, List
import psycopg2
from psycopg2.extras import RealDictCursor

# ---------- DB CONFIG ----------
DB_CONFIG = {
    "host": "localhost",
    "dbname": "ims",
    "user": "postgres",
    "password": "Abcd@1234",  # change to your password
    "port": 5432
}

# ---------- FASTAPI ----------
app = FastAPI(title="EC2 Instance Deep Dive API",
              description="Fetch instance utilization, cost, and environment details from Instancedeepdive table",
              version="1.0.0")

# ---------- DB Connection ----------
def get_db_connection():
    return psycopg2.connect(**DB_CONFIG)

# ---------- ENDPOINT ----------
@app.get("/instances")
def get_instances(
    account_id: Optional[str] = Query(None, description="AWS account_id"),
    region: Optional[str] = Query(None, description="AWS region"),
    instance_id: Optional[str] = Query(None, description="EC2 Instance ID"),
    period: Optional[str] = Query(None, description="Metrics period (24h, 7d, 30d)")
):
    """
    Fetch instance details from Instancedeepdive table.
    You can filter by account_id, region, instance_id, and period.
    """
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    # --- Base query ---
    query = "SELECT * FROM Instancedeepdive WHERE 1=1"
    params = []

    # --- Add filters dynamically ---
    if account_id:
        query += " AND account_id = %s"
        params.append(account_id)

    if region:
        query += " AND region = %s"
        params.append(region)

    if instance_id:
        query += " AND instance_id = %s"
        params.append(instance_id)

    if period:
        query += " AND period = %s"
        params.append(period)

    query += " ORDER BY updated_at DESC"

    cur.execute(query, params)
    rows = cur.fetchall()
    cur.close()
    conn.close()

    return {"count": len(rows), "results": rows}
