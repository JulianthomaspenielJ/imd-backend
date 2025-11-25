from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import psycopg2
from psycopg2.extras import RealDictCursor

# ---------- DB Config ----------
DB_CONFIG = {
    "host": "localhost",
    "dbname": "ims",
    "user": "postgres",
    "password": "Abcd@1234",
    "port": 5432
}

app = FastAPI()

# ---------- CORS Middleware ----------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Change to FE domain in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------- API: Get Monthly Costs + Service Breakdown ----------
@app.get("/monthly-current")
def get_monthly_current():
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor(cursor_factory=RealDictCursor)

    # Get total monthly costs
    cur.execute("""
        SELECT account_id, month_label, cost, last_updated
        FROM monthly_current
        ORDER BY last_updated DESC
    """)
    monthly_totals = cur.fetchall()

    # Get per-service costs
    cur.execute("""
        SELECT account_id, month_label, service_name, cost, last_updated
        FROM monthly_current_services
        ORDER BY last_updated DESC
    """)
    service_breakdowns = cur.fetchall()

    cur.close()
    conn.close()

    # Combine into dictionary
    data = []
    for total in monthly_totals:
        breakdown = [
            svc for svc in service_breakdowns
            if svc["account_id"] == total["account_id"] and svc["month_label"] == total["month_label"]
        ]
        data.append({
            "account_id": total["account_id"],
            "month_label": total["month_label"],
            "total_cost": total["cost"],
            "last_updated": total["last_updated"],
            "services": breakdown
        })

    return {"data": data}
