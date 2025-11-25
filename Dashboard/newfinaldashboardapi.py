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
    usage_date: Optional[str] = Query(None, description="Specific date YYYY-MM-DD"),
    start_date: Optional[str] = Query(None, description="Start date YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="End date YYYY-MM-DD"),
    period: Optional[str] = Query(None, description="Predefined period: 7d, 3m, 6m, 1y")
):
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        now = datetime.now()
        current_month_label = now.strftime("%B %Y")
        prev_month = (now.replace(day=1) - timedelta(days=1))
        prev_month_label = prev_month.strftime("%B %Y")

        # ---------- FUNCTION TO FETCH MONTHLY COST ----------
        def fetch_monthly_cost(label, acc_id=None):
            # Try from monthly_current_services
            base_query = "SELECT COALESCE(SUM(cost),0) AS total_cost FROM monthly_current_services WHERE month_label=%s"
            params = [label]
            if acc_id and acc_id != "ALL":
                base_query += " AND account_id=%s"
                params.append(acc_id)
            cur.execute(base_query, tuple(params))
            val = cur.fetchone()["total_cost"]

            # fallback from daily_cost if 0 or ALL
            if val == 0 or acc_id == "ALL" or acc_id is None:
                start_date = datetime.strptime(label, "%B %Y").replace(day=1).date()
                # last day of month
                if start_date.month == 12:
                    end_date = start_date.replace(year=start_date.year + 1, month=1, day=1) - timedelta(days=1)
                else:
                    end_date = start_date.replace(month=start_date.month + 1, day=1) - timedelta(days=1)

                daily_query = "SELECT COALESCE(SUM(cost),0) AS total_cost FROM daily_cost WHERE usage_date BETWEEN %s AND %s"
                dparams = [start_date, end_date]
                if acc_id and acc_id != "ALL":
                    daily_query += " AND account_id=%s"
                    dparams.append(acc_id)
                cur.execute(daily_query, tuple(dparams))
                val = cur.fetchone()["total_cost"]
            return val

        current_month_cost = fetch_monthly_cost(current_month_label, account_id)
        prev_month_cost = fetch_monthly_cost(prev_month_label, account_id)

        if prev_month_cost == 0:
            percent_change = None if current_month_cost == 0 else 100.0
        else:
            percent_change = ((current_month_cost - prev_month_cost) / prev_month_cost) * 100

        # ---------- FORECAST AMOUNT ----------
        if account_id and account_id != "ALL":
            cur.execute("SELECT COALESCE(SUM(forecast_amount),0) AS forecast_total FROM forecast_data WHERE account_id=%s", (account_id,))
            forecast_value = cur.fetchone()["forecast_total"]
        else:
            cur.execute("SELECT COALESCE(SUM(forecast_amount),0) AS forecast_total FROM forecast_data")
            forecast_value = cur.fetchone()["forecast_total"]

        # ---------- SERVICE WISE COSTS ----------
        def fetch_service_costs(label, acc_id=None, usage_date=None):
            if usage_date:
                query = "SELECT service_name, COALESCE(SUM(cost),0) AS service_cost FROM daily_cost WHERE usage_date=%s"
                params = [usage_date]
            else:
                query = "SELECT service_name, COALESCE(SUM(cost),0) AS service_cost FROM monthly_current_services WHERE month_label=%s"
                params = [label]

            if acc_id and acc_id != "ALL":
                query += " AND account_id=%s"
                params.append(acc_id)
            query += " GROUP BY service_name ORDER BY service_name"
            cur.execute(query, tuple(params))
            results = cur.fetchall()

            # fallback to daily_cost if empty
            if not results:
                if usage_date:
                    start = end = datetime.strptime(usage_date, "%Y-%m-%d").date()
                else:
                    start = datetime.strptime(label, "%B %Y").replace(day=1).date()
                    if start.month == 12:
                        end = start.replace(year=start.year + 1, month=1, day=1) - timedelta(days=1)
                    else:
                        end = start.replace(month=start.month + 1, day=1) - timedelta(days=1)
                dquery = "SELECT service_name, COALESCE(SUM(cost),0) AS service_cost FROM daily_cost WHERE usage_date BETWEEN %s AND %s"
                dparams = [start, end]
                if acc_id and acc_id != "ALL":
                    dquery += " AND account_id=%s"
                    dparams.append(acc_id)
                dquery += " GROUP BY service_name ORDER BY service_name"
                cur.execute(dquery, tuple(dparams))
                results = cur.fetchall()
            return results

        service_costs = fetch_service_costs(current_month_label, account_id)

        # ---------- DAILY SERVICE COSTS ----------
        today = datetime.now().date()
        if start_date and end_date:
            start = datetime.strptime(start_date, "%Y-%m-%d").date()
            end = datetime.strptime(end_date, "%Y-%m-%d").date()
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
                return {"detail":"Invalid period. Use one of: 7d,3m,6m,1y"}
        else:
            start, end = today - timedelta(days=300), today

        daily_query = "SELECT usage_date, service_name, COALESCE(SUM(cost),0) AS total_cost FROM daily_cost WHERE usage_date BETWEEN %s AND %s"
        params = [start, end]
        if account_id and account_id != "ALL":
            daily_query += " AND account_id=%s"
            params.append(account_id)
        daily_query += " GROUP BY usage_date, service_name ORDER BY usage_date, service_name"
        cur.execute(daily_query, tuple(params))
        daily_cost_records = cur.fetchall()

        # ---------- TOP 5 ----------
        top_results = {}
        top_where = "usage_date BETWEEN %s AND %s"
        top_params = [start, end]
        if account_id and account_id != "ALL":
            top_where += " AND account_id=%s"
            top_params.append(account_id)

        cur.execute(f"SELECT service AS name, COALESCE(SUM(unblended_cost),0) AS total_cost FROM multiple_user_cur WHERE {top_where} GROUP BY service ORDER BY total_cost DESC LIMIT 5", tuple(top_params))
        top_results["top_services"] = cur.fetchall()

        cur.execute(f"SELECT account_id, COALESCE(SUM(unblended_cost),0) AS total_cost FROM multiple_user_cur WHERE {top_where} GROUP BY account_id ORDER BY total_cost DESC LIMIT 5", tuple(top_params))
        top_results["top_accounts"] = cur.fetchall()

        cur.execute(f"SELECT COALESCE(name, service) AS app_name, COALESCE(SUM(unblended_cost),0) AS total_cost FROM multiple_user_cur WHERE {top_where} GROUP BY app_name ORDER BY total_cost DESC LIMIT 5", tuple(top_params))
        top_results["top_apps"] = cur.fetchall()

        # ---------- ALL ACCOUNT IDS ----------
        cur.execute("""
            SELECT DISTINCT account_id FROM monthly_current_services
            UNION
            SELECT DISTINCT account_id FROM daily_cost
            UNION
            SELECT DISTINCT account_id FROM forecast_data
            ORDER BY account_id
        """)
        all_accounts = [row["account_id"] for row in cur.fetchall()]
        all_accounts.insert(0,"ALL")

        # ---------- FINAL RESULT ----------
        result = {
            "account_id": account_id if account_id else "ALL",
            "all_account_ids": all_accounts,
            "date_range":{"start_date":str(start),"end_date":str(end)},
            "monthly_summary":{
                "current_month": current_month_label,
                "current_month_cost": round(current_month_cost,2),
                "previous_month": prev_month_label,
                "previous_month_cost": round(prev_month_cost,2),
                "percent_change": round(percent_change,2) if percent_change is not None else "N/A",
                "status":"Increased" if percent_change and percent_change>0 else "Decreased" if percent_change and percent_change<0 else "No Change",
                "forecast_amount": round(forecast_value,2),
                "service_wise_costs":[{"service_name":row["service_name"],"total_cost":round(row["service_cost"],2)} for row in service_costs]
            },
            "daily_service_costs":[{"usage_date":str(row["usage_date"]),"service_name":row["service_name"],"total_cost":round(row["total_cost"],2)} for row in daily_cost_records],
            "top_5": top_results
        }

        cur.close()
        conn.close()
        return result

    except Exception as e:
        return {"detail":f"Failed to fetch records: {str(e)}"}
