from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import psycopg2
from psycopg2.extras import RealDictCursor
from typing import List, Dict, Any

# -------------------------------
# DB CONFIG
# -------------------------------
DB_CONFIG = {
    "dbname": "ims",
    "user": "postgres",
    "password": "Abcd@1234",  # change to your password
    "host": "localhost",
    "port": 5432
}

# -------------------------------
# FastAPI Init
# -------------------------------
app = FastAPI(title="AWS EC2 AutoStart/Stop & Tag Compliance API")

# -------------------------------
# Utility: DB Query Helper
# -------------------------------
def query_db(query: str, params: tuple = ()) -> List[Dict[str, Any]]:
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute(query, params)
        rows = cur.fetchall()
        cur.close()
        conn.close()
        return rows
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# -------------------------------
# API Endpoint (Single)
# -------------------------------
@app.get("/aws-data")
def get_aws_data():
    # Fetch EC2 Auto Start/Stop Data
    ec2_data = query_db("SELECT * FROM ec2_auto_startstop;")

    # Fetch Tag Compliance Data
    tag_data = query_db("SELECT * FROM tag_compliance;")

    return {
        "ec2_auto_startstop": ec2_data,
        "tag_compliance": tag_data
    }
