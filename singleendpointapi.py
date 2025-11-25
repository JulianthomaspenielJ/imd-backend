from fastapi import FastAPI, HTTPException
from psycopg2.extras import RealDictCursor
import psycopg2
import os
import uuid
import json
from typing import List, Optional
from pydantic import BaseModel, EmailStr, Field, validator
from psycopg2.extras import Json

# ---------- DB CONFIG ----------
DB_CONFIG = {
    "host": "localhost",
    "dbname": "ims_db",
    "user": "postgres",
    "password": "*Postgres16",  # change to your password
    "port": 5432
}

# ---------- APP ----------
app = FastAPI(title="IMS API", version="1.0")


# ---------- DB CONNECTION ----------
def get_db_conn():
    try:
        conn = psycopg2.connect(**DB_CONFIG, cursor_factory=RealDictCursor)
        return conn
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database connection failed: {str(e)}")

# ---------- UTILITY ----------
def fetch_records(query: str, params: tuple = ()):
    conn = get_db_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(query, params)
            return cur.fetchall()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Query failed: {str(e)}")
    finally:
        conn.close()


# ---------- SINGLE ENDPOINT ----------
@app.get("/all-data")
def get_all_data():
    try:
        return {
            "forecast_data": fetch_records("SELECT * FROM forecast_data;"),
            "daily_cost": fetch_records("SELECT * FROM daily_cost;"),
            "monthly_current_services": fetch_records("SELECT * FROM monthly_current_services;"),
            "ec2_auto_startstop": fetch_records("SELECT * FROM ec2_auto_startstop;"),
            "instancedeepdive": fetch_records("SELECT * FROM instancedeepdive;"),
            "monthly_cost": fetch_records("SELECT * FROM monthly_cost;"),
            "monthly_cost_conditions": fetch_records("SELECT * FROM monthly_cost_conditions;"),
            "multiple_user_cur": fetch_records("SELECT * FROM multiple_user_cur;"),
            "service_status": fetch_records("SELECT * FROM service_status;"),
            "tag_compliance": fetch_records("SELECT * FROM tag_compliance;")
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch all records: {str(e)}")



if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
