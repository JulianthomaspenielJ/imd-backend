from fastapi import FastAPI, HTTPException
from psycopg2.extras import RealDictCursor
import psycopg2

# ---------- DB CONFIG ----------
DB_CONFIG = {
    "host": "localhost",
    "dbname": "ims",
    "user": "postgres",
    "password": "Abcd@1234",  # change to your password
    "port": 5432
}

# ---------- APP ----------
app = FastAPI(title="IMS API", version="1.0")

# ---------- DB CONNECTION ----------
def get_db_conn():
    try:
        conn = psycopg2.connect(**DB_CONFIG, cursor_factory=RealDictCursor)
        return conn
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database connection failed: {str(e)}")

# ---------- UTILITY ----------
def fetch_records(query: str, params: tuple = ()):
    conn = get_db_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(query, params)
            return cur.fetchall()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Query failed: {str(e)}")
    finally:
        conn.close()


# ---------- ENDPOINTS ----------
@app.get("/")
def root():
    return {"message": "IMS API is running"}


# 1. forecast_data
@app.get("/forecasts")
def get_forecasts():
    query = "SELECT * FROM forecast_data;"
    return fetch_records(query)


# 2. daily_cost
@app.get("/daily-cost")
def get_daily_cost():
    query = "SELECT * FROM daily_cost;"
    return fetch_records(query)


# 3. monthly_current_services
@app.get("/monthly-current")
def get_monthly_current_services():
    query = "SELECT * FROM monthly_current_services;"
    return fetch_records(query)


# 4. ec2_auto_startstop
@app.get("/ec2-auto")
def get_ec2_auto():
    query = "SELECT * FROM ec2_auto_startstop;"
    return fetch_records(query)


# 5. instancedeepdive
@app.get("/instance-deepdive")
def get_instance_deepdive():
    query = "SELECT * FROM instancedeepdive;"
    return fetch_records(query)


# 6. monthly_cost
@app.get("/monthly-cost")
def get_monthly_cost():
    query = "SELECT * FROM monthly_cost;"
    return fetch_records(query)


# 7. monthly_cost_conditions
@app.get("/monthly-cost-conditions")
def get_monthly_cost_conditions():
    query = "SELECT * FROM monthly_cost_conditions;"
    return fetch_records(query)


# 8. multiple_user_cur
@app.get("/records")
def get_multiple_user_cur():
    query = "SELECT * FROM multiple_user_cur;"
    return fetch_records(query)


# 9. service_status
@app.get("/service-status")
def get_service_status():
    query = "SELECT * FROM service_status;"
    return fetch_records(query)


# 10. tag_compliance
@app.get("/tag-compliance")
def get_tag_compliance():
    query = "SELECT * FROM tag_compliance;"
    return fetch_records(query)