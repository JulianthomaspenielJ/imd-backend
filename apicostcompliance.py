from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import psycopg2
from psycopg2.extras import RealDictCursor
from typing import List, Optional
from datetime import date

# -------------------------------
# DB CONFIG
# -------------------------------
DB_CONFIG = {
    "dbname": "ims_db",
    "user": "postgres",
    "password": "*Postgres16",
    "host": "localhost",
    "port": 5432,
}

# -------------------------------
# DB HELPER
# -------------------------------
def get_db_connection():
    return psycopg2.connect(**DB_CONFIG)

# -------------------------------
# Pydantic Schema
# -------------------------------
class TagCompliance(BaseModel):
    account_id: str
    check_date: date
    total_cost: float
    tagged_cost: float
    untagged_cost: float
    non_taggable_cost: float
    tagged_services: Optional[str]
    untagged_services: Optional[str]
    non_taggable_services: Optional[str]

# -------------------------------
# FastAPI App
# -------------------------------
app = FastAPI(title="AWS Tag Compliance API")

# -------------------------------
# Fetch all records
# -------------------------------
@app.get("/compliance", response_model=List[TagCompliance])
def get_all_compliance():
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("SELECT * FROM tag_compliance ORDER BY check_date DESC;")
        rows = cur.fetchall()
        cur.close()
        conn.close()
        return rows
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# -------------------------------
# Fetch by account_id
# -------------------------------
@app.get("/compliance/{account_id}", response_model=List[TagCompliance])
def get_compliance_by_account(account_id: str):
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute(
            "SELECT * FROM tag_compliance WHERE account_id = %s ORDER BY check_date DESC;",
            (account_id,),
        )
        rows = cur.fetchall()
        cur.close()
        conn.close()

        if not rows:
            raise HTTPException(status_code=404, detail="No records found for this account")

        return rows
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# -------------------------------
# Insert / Update record
# -------------------------------
@app.post("/compliance", response_model=TagCompliance)
def add_or_update_compliance(record: TagCompliance):
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        query = """
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
        """

        cur.execute(
            query,
            (
                record.account_id,
                record.check_date,
                record.total_cost,
                record.tagged_cost,
                record.untagged_cost,
                record.non_taggable_cost,
                record.tagged_services,
                record.untagged_services,
                record.non_taggable_services,
            ),
        )

        conn.commit()
        cur.close()
        conn.close()
        return record
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
