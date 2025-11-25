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


@app.get("/cost-summary")
def get_cost_summary(
    account_id: Optional[str] = Query(None, description="Filter by account ID"),
    usage_date: Optional[str] = Query(None, description="Specific date YYYY-MM-DD for service-wise costs"),
    start_date: Optional[str] = Query(None, description="Start date YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="End date YYYY-MM-DD"),
    period: Optional[str] = Query(None, description="Predefined period: 7d, 3m, 6m, 1y")
):
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # ---------- MONTHLY COST SUMMARY ----------
        now = datetime.now()
        current_month_label = now.strftime("%B %Y")
        prev_month = (now.replace(day=1) - timedelta(days=1))
        prev_month_label = prev_month.strftime("%B %Y")

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

        if prev_month_cost == 0:
            percent_change = None if current_month_cost == 0 else 100.0
        else:
            percent_change = ((current_month_cost - prev_month_cost) / prev_month_cost) * 100

        if account_id:
            cur.execute("SELECT COALESCE(SUM(forecast_amount), 0) AS forecast_total FROM forecast_data WHERE account_id = %s", (account_id,))
            forecast_value = cur.fetchone()["forecast_total"]
        else:
            cur.execute("SELECT COALESCE(SUM(forecast_amount), 0) AS forecast_total FROM forecast_data")
            forecast_value = cur.fetchone()["forecast_total"]

        # ---------- SERVICE-WISE COSTS (Monthly or Daily) ----------
        service_costs = []
        if usage_date:
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

        # ---------- SERVICE-WISE DAILY COSTS (code 2 logic) ----------
        today = datetime.now().date()
        if start_date and end_date:
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
            start = today - timedelta(days=7)
            end = today

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
        daily_cost_records = cur.fetchall()

        # ---------- FINAL RESULT ----------
        result = {
            "account_id": account_id if account_id else "ALL",
            "monthly_summary": {
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
            },
            "daily_service_costs": [
                {
                    "usage_date": str(row["usage_date"]),
                    "service_name": row["service_name"],
                    "total_cost": round(row["total_cost"], 2),
                }
                for row in daily_cost_records
            ]
        }

        cur.close()
        conn.close()
        return result

    except Exception as e:
        return {"detail": f"Failed to fetch records: {str(e)}"}
