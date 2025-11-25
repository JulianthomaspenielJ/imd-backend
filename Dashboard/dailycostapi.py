from fastapi import FastAPI, Query
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime, timedelta
from typing import Optional

app = FastAPI()

# ---------- DB CONFIG ----------
DB_CONFIG = {
    "host": "localhost",
    "dbname": "ims",
    "user": "postgres",
    "password": "Abcd@1234",  # change to your password
    "port": 5432
}


# ---------- Helper: Get DB Connection ----------
def get_db_connection():
    return psycopg2.connect(**DB_CONFIG, cursor_factory=RealDictCursor)


@app.get("/service-wise-daily-costs")
def get_service_wise_daily_costs(
    account_id: Optional[str] = Query(None, description="Filter by account ID"),
    start_date: Optional[str] = Query(None, description="Start date YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="End date YYYY-MM-DD"),
    period: Optional[str] = Query(
        None, description="Predefined period: 7d, 3m, 6m, 1y"
    )
):
    """
    Fetch service-wise daily costs from `daily_cost`:
    1. Default -> last 7 days (all accounts or filtered by account_id).
    2. Custom -> start_date & end_date.
    3. Predefined -> 7d, 3m, 6m, 1y.
    """
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # ---------- DATE RANGE LOGIC ----------
        today = datetime.now().date()

        if start_date and end_date:
            # Custom date range
            start = datetime.strptime(start_date, "%Y-%m-%d").date()
            end = datetime.strptime(end_date, "%Y-%m-%d").date()
        elif period:
            if period == "7d":
                start = today - timedelta(days=7)
                end = today
            elif period == "3m":
                start = today - timedelta(days=90)
                end = today
            elif period == "6m":
                start = today - timedelta(days=180)
                end = today
            elif period == "1y":
                start = today - timedelta(days=365)
                end = today
            else:
                return {"detail": "Invalid period. Use one of: 7d, 3m, 6m, 1y"}
        else:
            # Default last 7 days
            start = today - timedelta(days=7)
            end = today

        # ---------- QUERY ----------
        query = """
            SELECT usage_date, service_name, COALESCE(SUM(cost),0) AS total_cost
            FROM daily_cost
            WHERE usage_date BETWEEN %s AND %s
        """
        params = [start, end]

        if account_id:
            query += " AND account_id = %s"
            params.append(account_id)

        query += " GROUP BY usage_date, service_name ORDER BY usage_date, service_name"

        cur.execute(query, tuple(params))
        records = cur.fetchall()

        cur.close()
        conn.close()

        return [
            {
                "usage_date": str(row["usage_date"]),
                "service_name": row["service_name"],
                "total_cost": round(row["total_cost"], 2),
            }
            for row in records
        ]

    except Exception as e:
        return {"detail": f"Failed to fetch records: {str(e)}"}
