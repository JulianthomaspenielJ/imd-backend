from fastapi import FastAPI, Query
from typing import Optional, List
import psycopg2
from psycopg2.extras import RealDictCursor

app = FastAPI()

DB_CONFIG = {
    "dbname": "ims",
    "user": "postgres",
    "password": "Abcd@1234",
    "host": "localhost",
    "port": "5432"
}

# -------------------------------
# DB Connection Helper
# -------------------------------
def get_db_connection():
    return psycopg2.connect(**DB_CONFIG, cursor_factory=RealDictCursor)

# -------------------------------
# API Endpoint to Fetch Service Status
# -------------------------------
@app.get("/service-status")
def get_service_status(
    account_id: Optional[str] = Query(None, description="AWS Account ID"),
    month: Optional[str] = Query(None, description="Month in YYYY-MM format"),
    status: Optional[str] = Query(None, description="Service status: Running, Stopped, Newly Added")
):
    query = "SELECT account_id, service_name, month, status, start_month, stop_month FROM service_status WHERE 1=1"
    params = []

    if account_id:
        query += " AND account_id = %s"
        params.append(account_id)
    if month:
        query += " AND TO_CHAR(month, 'YYYY-MM') = %s"
        params.append(month)
    if status:
        query += " AND status = %s"
        params.append(status)

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(query, tuple(params))
    rows = cur.fetchall()
    cur.close()
    conn.close()

    return {"count": len(rows), "data": rows}
