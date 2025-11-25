from fastapi import FastAPI
import psycopg2
from psycopg2.extras import RealDictCursor
from typing import List, Dict

# ---------- DB CONFIG ----------
DB_CONFIG = {
    "host": "localhost",
    "dbname": "ims",
    "user": "postgres",
    "password": "Abcd@1234",  # change to your db password
    "port": 5432
}

# ---------- FastAPI APP ----------
app = FastAPI(title="EC2 Auto Start/Stop API", version="1.0")

# ---------- DB CONNECTION ----------
def get_connection():
    return psycopg2.connect(**DB_CONFIG)

# ---------- FETCH ALL INSTANCES ----------
@app.get("/instances", response_model=List[Dict])
def get_all_instances():
    """
    Fetch all EC2 instances with AutoStart/AutoStop info
    from ec2_auto_startstop table.
    """
    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("SELECT * FROM ec2_auto_startstop ORDER BY account_id, region, instance_id")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows

# ---------- FILTER BY ACCOUNT ----------
@app.get("/instances/{account_id}", response_model=List[Dict])
def get_instances_by_account(account_id: str):
    """
    Fetch EC2 instances for a specific AWS Account ID
    """
    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute(
        "SELECT * FROM ec2_auto_startstop WHERE account_id = %s ORDER BY region, instance_id",
        (account_id,)
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows

# ---------- HEALTH CHECK ----------
@app.get("/")
def health_check():
    return {"status": "ok", "message": "EC2 Auto Start/Stop API running"}
