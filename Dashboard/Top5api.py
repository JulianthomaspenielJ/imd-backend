from fastapi import FastAPI, Query
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime, timedelta, date
from typing import Optional, Dict, Any, List

app = FastAPI()

# ---------- DB CONFIG ----------
DB_CONFIG = {
    "host": "localhost",
    "dbname": "ims",
    "user": "postgres",
    "password": "Abcd@1234",  # change accordingly
    "port": 5432
}


# ---------- Helper: DB connection ----------
def get_db_connection():
    return psycopg2.connect(**DB_CONFIG, cursor_factory=RealDictCursor)


# ---------- Helper: Get first & last day of current month ----------
def current_month_range():
    today = date.today()
    start = today.replace(day=1)
    if today.month == 12:
        end = today.replace(year=today.year + 1, month=1, day=1) - timedelta(days=1)
    else:
        end = today.replace(month=today.month + 1, day=1) - timedelta(days=1)
    return start, end


@app.get("/top5-costs")
def get_top5_costs(
    account_id: Optional[str] = Query(None, description="Filter by account ID"),
    start_date: Optional[str] = Query(None, description="Start date YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="End date YYYY-MM-DD"),
):
    """
    Get Top 5 costs:
    1. Default -> Current month (accounts, services, apps).
    2. If start_date & end_date provided -> Based on that range.
    3. If account_id + date range -> Top 5 apps, services for that account.
    4. If account_id only -> Top 5 apps, services for that account (current month).
    """
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # ---------- DATE RANGE ----------
        if start_date and end_date:
            start = datetime.strptime(start_date, "%Y-%m-%d").date()
            end = datetime.strptime(end_date, "%Y-%m-%d").date()
        else:
            start, end = current_month_range()

        results: Dict[str, List[Dict[str, Any]]] = {}

        # ---------- Query for Accounts ----------
        if not account_id:
            cur.execute(
                """
                SELECT account_id, SUM(unblended_cost) AS total_cost
                FROM multiple_user_cur
                WHERE usage_date BETWEEN %s AND %s
                GROUP BY account_id
                ORDER BY total_cost DESC
                LIMIT 5
                """,
                (start, end),
            )
            results["top_accounts"] = cur.fetchall()

        # ---------- Query for Services ----------
        if account_id:
            cur.execute(
                """
                SELECT service, SUM(unblended_cost) AS total_cost
                FROM multiple_user_cur
                WHERE usage_date BETWEEN %s AND %s
                AND account_id = %s
                GROUP BY service
                ORDER BY total_cost DESC
                LIMIT 5
                """,
                (start, end, account_id),
            )
        else:
            cur.execute(
                """
                SELECT service, SUM(unblended_cost) AS total_cost
                FROM multiple_user_cur
                WHERE usage_date BETWEEN %s AND %s
                GROUP BY service
                ORDER BY total_cost DESC
                LIMIT 5
                """,
                (start, end),
            )
        results["top_services"] = cur.fetchall()

        # ---------- Query for Apps (by `name` column) ----------
        if account_id:
            cur.execute(
                """
                SELECT name AS app, SUM(unblended_cost) AS total_cost
                FROM multiple_user_cur
                WHERE usage_date BETWEEN %s AND %s
                AND account_id = %s
                AND name IS NOT NULL AND name <> ''
                GROUP BY name
                ORDER BY total_cost DESC
                LIMIT 5
                """,
                (start, end, account_id),
            )
        else:
            cur.execute(
                """
                SELECT name AS app, SUM(unblended_cost) AS total_cost
                FROM multiple_user_cur
                WHERE usage_date BETWEEN %s AND %s
                AND name IS NOT NULL AND name <> ''
                GROUP BY name
                ORDER BY total_cost DESC
                LIMIT 5
                """,
                (start, end),
            )
        results["top_apps"] = cur.fetchall()

        cur.close()
        conn.close()

        return {
            "date_range": {"start": str(start), "end": str(end)},
            "filters": {"account_id": account_id},
            "results": results,
        }

    except Exception as e:
        return {"detail": f"Failed to fetch records: {str(e)}"}
