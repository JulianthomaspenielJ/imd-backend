from fastapi import FastAPI, Query
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime, timedelta
from typing import Optional

app = FastAPI()

DB_CONFIG = {
    "host": "localhost",
    "dbname": "ims",
    "user": "postgres",
    "password": "Abcd@1234",  # Change for production
    "port": 5432
}

def get_db_connection():
    return psycopg2.connect(**DB_CONFIG, cursor_factory=RealDictCursor)

@app.get("/cost-summary")
def get_cost_summary(
    account_id: Optional[str] = Query(None, description="Filter by account ID"),
    usage_date: Optional[str] = Query(None, description="Specific date YYYY-MM-DD"),
    start_date: Optional[str] = Query(None, description="Start date YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="End date YYYY-MM-DD"),
    period: Optional[str] = Query(None, description="Predefined period: 7d, 3m, 6m, 1y")
):
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # Determine date range
        today = datetime.now().date()

        if usage_date:
            start = end = datetime.strptime(usage_date, "%Y-%m-%d").date()
        elif period:
            if period == "7d":
                start, end = today - timedelta(days=7), today
            elif period == "3m":
                start, end = today - timedelta(days=90), today
            elif period == "6m":
                start, end = today - timedelta(days=180), today
            elif period == "1y":
                start, end = today - timedelta(days=365), today
            else:
                return {"detail": "Invalid period. Use one of: 7d, 3m, 6m, 1y"}
        elif start_date and end_date:
            start = datetime.strptime(start_date, "%Y-%m-%d").date()
            end = datetime.strptime(end_date, "%Y-%m-%d").date()
        else:
            # Default to current month
            now = datetime.now()
            start = now.replace(day=1).date()
            end = now.date()

        current_month_label = datetime.now().strftime("%B %Y")
        prev_month = (datetime.now().replace(day=1) - timedelta(days=1))
        prev_month_label = prev_month.strftime("%B %Y")

        # ---------- MONTHLY COST SUMMARY ----------
        def get_sum(table, column, where_clauses: list, params: list):
            sql = f"SELECT COALESCE(SUM({column}), 0) AS total FROM {table} WHERE {' AND '.join(where_clauses)}"
            cur.execute(sql, tuple(params))
            return cur.fetchone()["total"]

        # Current month cost
        where_current = ["month_label LIKE %s"]
        params_current = [f"%{current_month_label}%"]
        if account_id:
            where_current.append("account_id = %s")
            params_current.append(account_id)
        current_month_cost = get_sum("monthly_current_services", "cost", where_current, params_current)

        # Previous month cost
        where_prev = ["month_label LIKE %s"]
        params_prev = [f"%{prev_month_label}%"]
        if account_id:
            where_prev.append("account_id = %s")
            params_prev.append(account_id)
        prev_month_cost = get_sum("monthly_current_services", "cost", where_prev, params_prev)

        if prev_month_cost == 0:
            percent_change = None if current_month_cost == 0 else 100.0
        else:
            percent_change = ((current_month_cost - prev_month_cost) / prev_month_cost) * 100
        status = "Increased" if percent_change and percent_change > 0 else "Decreased" if percent_change and percent_change < 0 else "No Change"

        # Forecast cost
        where_forecast = ["1=1"]
        params_forecast = []
        if account_id:
            where_forecast.append("account_id = %s")
            params_forecast.append(account_id)
        forecast_value = get_sum("forecast_data", "forecast_amount", where_forecast, params_forecast)

        # ---------- SERVICE & CLOUD SPEND BREAKDOWN ----------
        svc_clause = ["month_label LIKE %s"]
        svc_params = [f"%{current_month_label}%"]
        if account_id:
            svc_clause.append("account_id = %s")
            svc_params.append(account_id)
        cur.execute(
            f"SELECT service_name, COALESCE(SUM(cost), 0) AS total_cost FROM monthly_current_services WHERE {' AND '.join(svc_clause)} GROUP BY service_name ORDER BY total_cost DESC",
            tuple(svc_params)
        )
        service_breakdown = cur.fetchall()

        # ---------- DAILY COSTS ----------
        daily_sql = "SELECT usage_date, service_name, COALESCE(SUM(cost),0) AS total_cost FROM daily_cost WHERE usage_date BETWEEN %s AND %s"
        daily_params = [start, end]
        if account_id:
            daily_sql += " AND account_id = %s"
            daily_params.append(account_id)
        daily_sql += " GROUP BY usage_date, service_name ORDER BY usage_date, service_name"
        cur.execute(daily_sql, tuple(daily_params))
        daily_costs = cur.fetchall()

        # ---------- TOP 5 QUERIES ----------
        acc_filter_str = "AND account_id = %s" if account_id else ""
        acc_filter_params = (account_id,) if account_id else ()

        # Top services
        cur.execute(
            f"""SELECT service AS name, COALESCE(SUM(unblended_cost),0) AS total_cost
                FROM multiple_user_cur
                WHERE usage_date BETWEEN %s AND %s {acc_filter_str}
                GROUP BY service ORDER BY total_cost DESC LIMIT 5""",
            (start, end) + acc_filter_params
        )
        top_services = cur.fetchall()

        # Top apps
        cur.execute(
            f"""SELECT COALESCE(name, service) AS app_name, COALESCE(SUM(unblended_cost),0) AS total_cost
                FROM multiple_user_cur
                WHERE usage_date BETWEEN %s AND %s {acc_filter_str}
                GROUP BY app_name ORDER BY total_cost DESC LIMIT 5""",
            (start, end) + acc_filter_params
        )
        top_apps = cur.fetchall()

        # Top accounts (not filtered by acc id)
        cur.execute(
            """SELECT account_id, COALESCE(SUM(unblended_cost),0) AS total_cost
               FROM multiple_user_cur
               WHERE usage_date BETWEEN %s AND %s
               GROUP BY account_id ORDER BY total_cost DESC LIMIT 5""",
            (start, end)
        )
        top_accounts = cur.fetchall()

        result = {
            "account_id": account_id or "ALL",
            "period_start": str(start),
            "period_end": str(end),
            "monthly_summary": {
                "current_month": current_month_label,
                "current_month_cost": round(current_month_cost, 2),
                "previous_month": prev_month_label,
                "previous_month_cost": round(prev_month_cost, 2),
                "percent_change": round(percent_change, 2) if percent_change is not None else "N/A",
                "status": status,
                "forecast_amount": round(forecast_value, 2),
                "service_wise_costs": [
                    {"service_name": row["service_name"], "total_cost": round(row["total_cost"], 2)}
                    for row in service_breakdown
                ]
            },
            "daily_service_costs": [
                {"usage_date": str(row["usage_date"]), "service_name": row["service_name"], "total_cost": round(row["total_cost"], 2)}
                for row in daily_costs
            ],
            "top_5": {
                "top_services": top_services,
                "top_apps": top_apps,
                "top_accounts": top_accounts
            }
        }
        cur.close()
        conn.close()
        return result

    except Exception as e:
        return {"detail": f"Failed to fetch records: {str(e)}"}
