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


@app.get("/monthly-cost-summary")
def get_monthly_cost_summary(
    account_id: Optional[str] = Query(None),
    usage_date: Optional[str] = Query(None)  # YYYY-MM-DD if provided
):
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # ---------- COST SUMMARY ----------
        now = datetime.now()
        current_month_label = now.strftime("%B %Y")  # e.g., "August 2025"
        prev_month = (now.replace(day=1) - timedelta(days=1))
        prev_month_label = prev_month.strftime("%B %Y")  # e.g., "July 2025"

        base_query = """
            SELECT COALESCE(SUM(cost), 0) AS total_cost
            FROM monthly_current_services
            WHERE month_label LIKE %s
        """

        if account_id:
            cur.execute(base_query + " AND account_id = %s", (f"%{current_month_label}%", account_id))
            current_month_cost = cur.fetchone()["total_cost"]

            cur.execute(base_query + " AND account_id = %s", (f"%{prev_month_label}%", account_id))
            prev_month_cost = cur.fetchone()["total_cost"]
        else:
            cur.execute(base_query, (f"%{current_month_label}%",))
            current_month_cost = cur.fetchone()["total_cost"]

            cur.execute(base_query, (f"%{prev_month_label}%",))
            prev_month_cost = cur.fetchone()["total_cost"]

        # --- Calculate % difference ---
        if prev_month_cost == 0:
            percent_change = None if current_month_cost == 0 else 100.0
        else:
            percent_change = ((current_month_cost - prev_month_cost) / prev_month_cost) * 100

        # ---------- FORECAST ----------
        if account_id:
            cur.execute("SELECT COALESCE(SUM(forecast_amount), 0) AS forecast_total FROM forecast_data WHERE account_id = %s", (account_id,))
            forecast_value = cur.fetchone()["forecast_total"]
        else:
            cur.execute("SELECT COALESCE(SUM(forecast_amount), 0) AS forecast_total FROM forecast_data")
            forecast_value = cur.fetchone()["forecast_total"]

        # ---------- SERVICE-WISE COST ----------
        service_costs = []
        if usage_date:
            # Case 1: Specific date -> from daily_cost
            service_query = """
                SELECT service_name, COALESCE(SUM(cost), 0) AS service_cost
                FROM daily_cost
                WHERE usage_date = %s
            """
            params = [usage_date]

            if account_id:
                service_query += " AND account_id = %s"
                params.append(account_id)

            service_query += " GROUP BY service_name ORDER BY service_name"
            cur.execute(service_query, tuple(params))
            service_costs = cur.fetchall()

        else:
            # Case 2: Default (current month) -> from monthly_current_services
            service_query = """
                SELECT service_name, COALESCE(SUM(cost), 0) AS service_cost
                FROM monthly_current_services
                WHERE month_label = %s
            """
            params = [current_month_label]

            if account_id:
                service_query += " AND account_id = %s"
                params.append(account_id)

            service_query += " GROUP BY service_name ORDER BY service_name"
            cur.execute(service_query, tuple(params))
            service_costs = cur.fetchall()

        # ---------- FINAL RESULT ----------
        result = {
            "account_id": account_id if account_id else "ALL",
            "current_month": current_month_label,
            "current_month_cost": round(current_month_cost, 2),
            "previous_month": prev_month_label,
            "previous_month_cost": round(prev_month_cost, 2),
            "percent_change": round(percent_change, 2) if percent_change is not None else "N/A",
            "status": "Increased" if percent_change and percent_change > 0 else "Decreased" if percent_change and percent_change < 0 else "No Change",
            "forecast_amount": round(forecast_value, 2),
            "service_wise_costs": [
                {"service_name": row["service_name"], "total_cost": round(row["service_cost"], 2)}
                for row in service_costs
            ]
        }

        cur.close()
        conn.close()
        return result

    except Exception as e:
        return {"detail": f"Failed to fetch records: {str(e)}"}
