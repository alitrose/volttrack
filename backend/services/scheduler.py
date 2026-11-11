import os
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
import pymysql
from backend.config import Config

scheduler = BackgroundScheduler()

def mark_overdue_bills():
    """
    Daily scheduled job: transitions overdue unpaid/partial bills to 'OVERDUE'.
    """
    try:
        conn = pymysql.connect(
            host=Config.DB_HOST,
            port=Config.DB_PORT,
            user=Config.DB_USER,
            password=Config.DB_PASS,
            database=Config.DB_NAME,
            charset="utf8mb4",
            autocommit=True
        )
        with conn.cursor() as cur:
            affected = cur.execute("""
                UPDATE bill
                SET status = 'OVERDUE'
                WHERE status IN ('UNPAID', 'PARTIAL')
                  AND due_date < CURDATE()
            """)
            print(f"[Scheduler] Daily overdue check completed. Marked {affected} bills as OVERDUE.")
        conn.close()
    except Exception as e:
        print(f"[Scheduler Error] Overdue marking failed: {e}")

def run_monthly_billing_batch():
    """
    Monthly scheduled job (1st of month): triggers cursor procedure generate_all_bills.
    """
    try:
        now = datetime.now()
        first_of_month = f"{now.year}-{now.month:02d}-01"
        conn = pymysql.connect(
            host=Config.DB_HOST,
            port=Config.DB_PORT,
            user=Config.DB_USER,
            password=Config.DB_PASS,
            database=Config.DB_NAME,
            charset="utf8mb4",
            autocommit=True
        )
        with conn.cursor() as cur:
            cur.callproc("generate_all_bills", (first_of_month,))
            print(f"[Scheduler] Monthly billing batch executed for {first_of_month}.")
        conn.close()
    except Exception as e:
        print(f"[Scheduler Error] Monthly billing failed: {e}")

def start_scheduler():
    if not scheduler.running:
        # Schedule daily overdue check at midnight
        scheduler.add_job(mark_overdue_bills, 'cron', hour=0, minute=5, id="daily_overdue_job", replace_existing=True)
        # Schedule monthly billing on the 1st of each month at 01:00
        scheduler.add_job(run_monthly_billing_batch, 'cron', day=1, hour=1, minute=0, id="monthly_billing_job", replace_existing=True)
        scheduler.start()
        print("[*] APScheduler background engine initialized.")
