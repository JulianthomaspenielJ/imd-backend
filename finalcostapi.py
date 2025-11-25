from fastapi import FastAPI, Query
from typing import List, Optional, Union
from pydantic import BaseModel
import psycopg2
from datetime import datetime

app = FastAPI()

# -------------------------------
# Database Configuration
# -------------------------------
DB_CONFIG = {
    "dbname": "ims",
    "user": "postgres",
    "password": "Abcd@1234",
    "host": "localhost",
    "port": "5432"
}

# -------------------------------
# Models
# -------------------------------
class MonthlyCostCondition(BaseModel):
    account_id: str
    usage_month: str  # YYYY-MM-DD
    condition_type: str
    cost: float

class DailyCost(BaseModel):
    account_id: str
    usage_date: str  # YYYY-MM-DD
    service_name: str
    cost: float

class MonthlyCost(BaseModel):
    account_id: str
    usage_month: str  # YYYY-MM-DD
    service_name: str
    cost: float

class ForecastData(BaseModel):
    account_id: str
    month: str
    forecast_amount: float

# -------------------------------
# GET /forecasts  (From Code 1)
# -------------------------------
@app.get("/forecasts", response_model=List[ForecastData])
def get_forecasts():
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        cur.execute("SELECT account_id, month, forecast_amount FROM forecast_data;")
        rows = cur.fetchall()
        cur.close()
        conn.close()

        return [
            ForecastData(
                account_id=acc,
                month=mon,
                forecast_amount=float(amt)
            )
            for acc, mon, amt in rows
        ]
    except Exception as e:
        return {"error": str(e)}

# -------------------------------
# GET /monthly-cost-conditions
# -------------------------------
@app.get("/monthly-cost-conditions", response_model=Union[List[MonthlyCostCondition], dict])
def get_monthly_cost_conditions(
    condition_type: Optional[str] = Query(None, description="no_tax, no_tax_no_support, all_inclusive"),
    start_month: Optional[str] = Query(None, description="Start month YYYY-MM-DD"),
    end_month: Optional[str] = Query(None, description="End month YYYY-MM-DD")
):
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()

        query = "SELECT account_id, usage_month, condition_type, cost FROM monthly_cost_conditions"
        params = []
        conditions = []

        if condition_type:
            conditions.append("condition_type = %s")
            params.append(condition_type)
        if start_month and end_month:
            conditions.append("usage_month BETWEEN %s::date AND %s::date")
            params.extend([start_month, end_month])
        elif start_month:
            conditions.append("usage_month >= %s::date")
            params.append(start_month)
        elif end_month:
            conditions.append("usage_month <= %s::date")
            params.append(end_month)

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        query += " ORDER BY usage_month;"

        cursor.execute(query, tuple(params))
        rows = cursor.fetchall()
        cursor.close()
        conn.close()

        if not rows:
            return {"message": "No data found for given filters"}

        return [
            MonthlyCostCondition(
                account_id=row[0],
                usage_month=str(row[1]),
                condition_type=row[2],
                cost=float(row[3])
            )
            for row in rows
        ]
    except Exception as e:
        return {"error": str(e)}

# -------------------------------
# GET /daily-cost (with optional date filter)
# -------------------------------
@app.get("/daily-cost", response_model=List[DailyCost])
def get_daily_cost(
    start_date: Optional[str] = Query(None, description="Start date in YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="End date in YYYY-MM-DD")
):
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()

        query = "SELECT account_id, usage_date, service_name, cost FROM daily_cost"
        params = []

        # Parse dates safely
        if start_date:
            try:
                start_date_obj = datetime.strptime(start_date, "%Y-%m-%d").date()
            except ValueError:
                return {"error": "Invalid start_date format, use YYYY-MM-DD"}
        else:
            start_date_obj = None

        if end_date:
            try:
                end_date_obj = datetime.strptime(end_date, "%Y-%m-%d").date()
            except ValueError:
                return {"error": "Invalid end_date format, use YYYY-MM-DD"}
        else:
            end_date_obj = None

        # Build WHERE clause dynamically
        if start_date_obj and end_date_obj:
            query += " WHERE usage_date BETWEEN %s AND %s"
            params.extend([start_date_obj, end_date_obj])
        elif start_date_obj:
            query += " WHERE usage_date >= %s"
            params.append(start_date_obj)
        elif end_date_obj:
            query += " WHERE usage_date <= %s"
            params.append(end_date_obj)

        query += " ORDER BY usage_date;"

        cursor.execute(query, tuple(params))
        rows = cursor.fetchall()
        cursor.close()
        conn.close()

        return [
            DailyCost(
                account_id=row[0],
                usage_date=str(row[1]),
                service_name=row[2],
                cost=float(row[3])
            )
            for row in rows
        ]
    except Exception as e:
        return {"error": str(e)}

# -------------------------------
# GET /monthly-cost
# -------------------------------
@app.get("/monthly-cost", response_model=List[MonthlyCost])
def get_monthly_cost():
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        cursor.execute("SELECT account_id, usage_month, service_name, cost FROM monthly_cost ORDER BY usage_month;")
        rows = cursor.fetchall()
        cursor.close()
        conn.close()

        return [
            MonthlyCost(
                account_id=row[0],
                usage_month=str(row[1]),
                service_name=row[2],
                cost=float(row[3])
            )
            for row in rows
        ]
    except Exception as e:
        return {"error": str(e)}
