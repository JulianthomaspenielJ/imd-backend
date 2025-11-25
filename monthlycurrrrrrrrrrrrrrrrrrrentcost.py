import psycopg2
from datetime import datetime, timedelta

# ---------- DB Config ----------
DB_CONFIG = {
    "host": "localhost",
    "dbname": "ims",
    "user": "postgres",
    "password": "Abcd@1234",
    "port": 5432
}

# ---------- Fetch Account IDs from DB ----------
def get_all_accounts():
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    cur.execute("SELECT DISTINCT account_id FROM multiple_user_cur;")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    if not rows:
        raise Exception("No AWS accounts found in multiple_user_cur table")
    return [r[0] for r in rows]

# ---------- Get Monthly Total & Per-Service Costs from CUR Table ----------
def get_monthly_costs_from_cur(account_id, start_date, end_date):
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()

    # --- Total cost for account in given range ---
    cur.execute("""
        SELECT COALESCE(SUM(unblended_cost), 0)
        FROM multiple_user_cur
        WHERE account_id = %s
          AND usage_date >= %s
          AND usage_date < %s;
    """, (account_id, start_date, end_date))
    total_cost = round(float(cur.fetchone()[0] or 0.0), 2)

    # --- Per-service cost breakdown ---
    cur.execute("""
        SELECT service, ROUND(SUM(unblended_cost), 2) as cost
        FROM multiple_user_cur
        WHERE account_id = %s
          AND usage_date >= %s
          AND usage_date < %s
        GROUP BY service;
    """, (account_id, start_date, end_date))
    service_costs = cur.fetchall()  # list of (service_name, cost)

    cur.close()
    conn.close()
    return total_cost, service_costs

# ---------- Store in monthly_current Table ----------
def store_cost(account_id, month_label, total_cost, service_costs):
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()

    # Main table for total cost
    cur.execute("""
        CREATE TABLE IF NOT EXISTS monthly_current_test (
            id SERIAL PRIMARY KEY,
            account_id TEXT,
            month_label TEXT,
            cost NUMERIC,
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (account_id, month_label)
        )
    """)

    # Breakdown table for per-service costs
    cur.execute("""
        CREATE TABLE IF NOT EXISTS monthly_current_services_test (
            id SERIAL PRIMARY KEY,
            account_id TEXT,
            month_label TEXT,
            service_name TEXT,
            cost NUMERIC,
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (account_id, month_label, service_name)
        )
    """)

    # Upsert total monthly cost
    cur.execute("""
        INSERT INTO monthly_current_test (account_id, month_label, cost)
        VALUES (%s, %s, %s)
        ON CONFLICT (account_id, month_label)
        DO UPDATE SET cost = EXCLUDED.cost, last_updated = CURRENT_TIMESTAMP
    """, (account_id, month_label, total_cost))

    # Upsert per-service costs
    for service_name, cost in service_costs:
        cur.execute("""
            INSERT INTO monthly_current_services_test (account_id, month_label, service_name, cost)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (account_id, month_label, service_name)
            DO UPDATE SET cost = EXCLUDED.cost, last_updated = CURRENT_TIMESTAMP
        """, (account_id, month_label, service_name, cost))

    conn.commit()
    cur.close()
    conn.close()

# ---------- Main Script ----------
if __name__ == "__main__":
    today = datetime.utcnow()
    first_of_month = today.replace(day=1)

    # Get all accounts from CUR table
    accounts = get_all_accounts()

    for account_id in accounts:
        # ---------- Last Month ----------
        last_month_end = first_of_month
        last_month_start = (first_of_month - timedelta(days=1)).replace(day=1)

        last_total, last_services = get_monthly_costs_from_cur(
            account_id,
            last_month_start.strftime("%Y-%m-%d"),
            last_month_end.strftime("%Y-%m-%d")
        )
        store_cost(account_id, last_month_start.strftime("%B %Y"), last_total, last_services)
        print(f"[{account_id}] Stored last month ({last_month_start.strftime('%B %Y')}): {last_total}")

        # ---------- Current Month till Today ----------
        current_total, current_services = get_monthly_costs_from_cur(
            account_id,
            first_of_month.strftime("%Y-%m-%d"),
            (today + timedelta(days=1)).strftime("%Y-%m-%d")  # include today
        )
        store_cost(account_id, first_of_month.strftime("%B %Y"), current_total, current_services)
        print(f"[{account_id}] Stored current month ({first_of_month.strftime('%B %Y')}) till {today.day}: {current_total}")
