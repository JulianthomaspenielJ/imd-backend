from fastapi import FastAPI, Query
import psycopg2
from psycopg2.extras import RealDictCursor
from typing import Optional

# ---------- DB CONFIG ----------
DB_CONFIG = {
    "host": "localhost",
    "dbname": "ims",
    "user": "postgres",
    "password": "Abcd@1234",   # change if needed
    "port": 5432
}

# ---------- DB Connection ----------
def get_db_connection():
    return psycopg2.connect(**DB_CONFIG, cursor_factory=RealDictCursor)

app = FastAPI(title="AWS Performance API", version="1.0")

# ---------- API Endpoints ----------

@app.get("/performance")
def get_performance(
    account_id: Optional[str] = Query(None, description="Filter by account_id"),
    region: Optional[str] = Query(None, description="Filter by region"),
    instance_id: Optional[str] = Query(None, description="Filter by instance_id"),
    limit: int = Query(50, description="Number of rows to fetch")
):
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        query = "SELECT * FROM performance_aws WHERE 1=1"
        params = []

        if account_id:
            query += " AND account_id = %s"
            params.append(account_id)
        if region:
            query += " AND region = %s"
            params.append(region)
        if instance_id:
            query += " AND instance_id = %s"
            params.append(instance_id)

        query += " ORDER BY timestamp DESC LIMIT %s"
        params.append(limit)

        cur.execute(query, tuple(params))
        results = cur.fetchall()

        cur.close()
        conn.close()
        return {"data": results}

    except Exception as e:
        return {"error": str(e)}
