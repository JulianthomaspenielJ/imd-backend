from fastapi import FastAPI, Query
from typing import List, Optional
import psycopg2
from psycopg2.extras import RealDictCursor
from pydantic import BaseModel
from datetime import date

# ------------------ DB Config ------------------
DB_CONFIG = {
    "host": "localhost",
    "dbname": "ims",
    "user": "postgres",
    "password": "Abcd@1234"
}

# ------------------ FastAPI App ------------------
app = FastAPI(title="Multiple User CUR API", version="1.0")

# ------------------ Pydantic Model ------------------
class MultipleUserCur(BaseModel):
    account_id: str
    usage_date: date
    unblended_cost: float
    resource_id: str
    region: Optional[str]
    usage_type: Optional[str]
    service: str
    name: Optional[str]
    owner: Optional[str]
    environment: Optional[str]
    record_type: Optional[str]
    instance_type: Optional[str]

# ------------------ DB Connection Helper ------------------
def get_connection():
    return psycopg2.connect(**DB_CONFIG, cursor_factory=RealDictCursor)

# ------------------ API Endpoints ------------------

@app.get("/", tags=["Health"])
def root():
    return {"message": "Multiple User CUR API is running 🚀"}

@app.get("/records", response_model=List[MultipleUserCur], tags=["CUR Data"])
def get_records(
    account_id: Optional[str] = Query(None, description="Filter by account_id"),
    service: Optional[str] = Query(None, description="Filter by AWS service"),
    start_date: Optional[date] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="End date (YYYY-MM-DD)")
):
    """
    Fetch records from multiple_user_cur table with optional filters.
    """
    conn = get_connection()
    cur = conn.cursor()

    query = "SELECT * FROM multiple_user_cur WHERE 1=1"
    params = []

    if account_id:
        query += " AND account_id = %s"
        params.append(account_id)
    if service:
        query += " AND service = %s"
        params.append(service)
    if start_date:
        query += " AND usage_date >= %s"
        params.append(start_date)
    if end_date:
        query += " AND usage_date <= %s"
        params.append(end_date)

    query += " ORDER BY usage_date DESC"

    cur.execute(query, tuple(params))
    rows = cur.fetchall()

    cur.close()
    conn.close()

    return rows

@app.get("/services-summary", tags=["CUR Data"])
def get_service_summary(
    start_date: date,
    end_date: date,
    account_id: Optional[str] = None
):
    """
    Summarize total cost per service between date range.
    """
    conn = get_connection()
    cur = conn.cursor()

    query = """
        SELECT account_id, service, SUM(unblended_cost)::numeric(18,2) AS total_cost
        FROM multiple_user_cur
        WHERE usage_date BETWEEN %s AND %s
    """
    params = [start_date, end_date]

    if account_id:
        query += " AND account_id = %s"
        params.append(account_id)

    query += " GROUP BY account_id, service ORDER BY account_id, service"

    cur.execute(query, tuple(params))
    rows = cur.fetchall()

    cur.close()
    conn.close()

    return rows
