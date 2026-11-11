"""
VoltTrack Smart Meter Simulator
Supports:
1. --bulk: Generates 100,000+ realistic hourly readings for 4 months with realistic diurnal curves.
2. --live: Continuously injects live meter readings every N seconds with anomaly probabilities
           (spikes for HIGH_USAGE, zero units for TAMPER, zero voltage for OUTAGE).
"""

import os
import sys
import time
import math
import random
import argparse
from datetime import datetime, timedelta
import pymysql

# Ensure project root is importable when run directly as a script
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from backend.config import Config


def get_connection():
    return pymysql.connect(
        host=Config.DB_HOST,
        port=Config.DB_PORT,
        user=Config.DB_USER,
        password=Config.DB_PASS,
        database=Config.DB_NAME,
        autocommit=False,
        charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor
    )


def simulate_hourly_usage(hour, meter_type, customer_category, month):
    """
    Simulates realistic kWh consumption based on time of day, customer category, and season.
    Peak hours: 18:00 - 22:00.
    """
    # Diurnal multiplier curve
    if 0 <= hour < 6:
        base_curve = 0.25 + 0.1 * math.sin(hour)
    elif 6 <= hour < 18:
        base_curve = 0.70 + 0.25 * math.sin((hour - 6) * math.pi / 12)
    elif 18 <= hour < 22:  # Peak window
        base_curve = 1.65 + 0.45 * math.sin((hour - 18) * math.pi / 4)
    else:  # 22 - 24
        base_curve = 0.55 + 0.15 * math.sin((hour - 22) * math.pi / 2)

    # Seasonal temperature factor (June/July/August hot summer vs September/October)
    season_factor = 1.25 if month in (5, 6, 7) else (1.10 if month in (8, 9) else 0.95)

    # Scale by customer category
    if customer_category == 'DOMESTIC':
        base_kwh = random.uniform(0.15, 0.45) * base_curve * season_factor
        voltage = round(random.uniform(224.0, 238.0), 1)
        pf = round(random.uniform(0.92, 0.98), 2)
    elif customer_category == 'COMMERCIAL':
        # Commercial has daytime + evening peak
        comm_curve = 2.0 if 9 <= hour <= 21 else 0.4
        base_kwh = random.uniform(1.2, 3.5) * comm_curve * season_factor
        voltage = round(random.uniform(228.0, 242.0), 1)
        pf = round(random.uniform(0.90, 0.96), 2)
    else:  # INDUSTRIAL
        # Industrial 24/7 steady load with shift patterns
        ind_curve = 1.3 if 8 <= hour <= 20 else 1.0
        base_kwh = random.uniform(8.0, 22.0) * ind_curve * season_factor
        voltage = round(random.uniform(400.0, 425.0) / 1.732, 1)  # Phase voltage
        pf = round(random.uniform(0.88, 0.95), 2)

    return round(max(0.01, base_kwh), 3), voltage, pf


def run_bulk_simulation(months=4, target_meters=15):
    """
    Generates 4 months of hourly records across target meters to exceed 100,000+ rows.
    Uses executemany inside chunked transactions for high throughput.
    """
    print(f"[*] Starting Bulk Simulation: {months} months across {target_meters} meters...")
    conn = get_connection()
    is_tty = sys.stdout.isatty()
    try:
        with conn.cursor() as cur:
            # Fetch target meters and customer category
            cur.execute("""
                SELECT m.meter_id, m.meter_type, c.category, c.customer_id
                FROM meter m
                JOIN customer c ON c.customer_id = m.customer_id
                ORDER BY m.meter_id
                LIMIT %s
            """, (target_meters,))
            meters = cur.fetchall()

            if not meters:
                print("[-] No meters found in database. Seed the database first.")
                return

            print(f"[*] Found {len(meters)} meters for back-fill.")

            # Calculate start date (4 months back from end of September 2026)
            end_date = datetime(2026, 9, 30, 23, 0, 0)
            start_date = datetime(2026, 6, 1, 0, 0, 0)  # June, July, August, September = 122 days
            total_hours = int((end_date - start_date).total_seconds() // 3600) + 1
            print(f"[*] Time horizon: {start_date} to {end_date} ({total_hours} hours per meter)")

            # Check existing count
            cur.execute("SELECT COUNT(*) AS total FROM meter_reading;")
            existing = cur.fetchone()['total']
            print(f"[*] Current meter_reading row count: {existing}")

            insert_sql = """
                INSERT INTO meter_reading (meter_id, reading_ts, units_consumed, voltage, power_factor)
                VALUES (%s, %s, %s, %s, %s)
            """

            # We want clean normal readings during bulk without flooding 100k alerts
            batch = []
            batch_size = 5000
            total_inserted = 0

            # Generate hourly intervals
            current_time = start_date
            hour_steps = []
            while current_time <= end_date:
                hour_steps.append(current_time)
                current_time += timedelta(hours=1)

            print(f"[*] Total reading points to generate: {len(meters) * len(hour_steps)} rows")

            # Ingest meter by meter
            for m in meters:
                mid = m['meter_id']
                mtype = m['meter_type']
                mcat = m['category']

                # Introduce one theft suspect pattern for meter 7 (usage drops by 70% in September)
                is_theft_suspect = (mid == 7)

                for ts in hour_steps:
                    kwh, volt, pf = simulate_hourly_usage(ts.hour, mtype, mcat, ts.month)

                    if is_theft_suspect and ts.month == 9:
                        kwh = round(kwh * 0.25, 3)  # Dramatic drop for analytics query 7

                    batch.append((mid, ts.strftime('%Y-%m-%d %H:%M:%S'), kwh, volt, pf))

                    if len(batch) >= batch_size:
                        cur.executemany(insert_sql, batch)
                        conn.commit()
                        total_inserted += len(batch)
                        batch.clear()
                        if is_tty:
                            print(f"    -> Inserted {total_inserted} records...", end='\r')
                        elif total_inserted % 25000 == 0:
                            print(f"    -> Inserted {total_inserted} records...")

            if batch:
                cur.executemany(insert_sql, batch)
                conn.commit()
                total_inserted += len(batch)
                batch.clear()

            print(f"\n[+] Bulk generation complete! Total inserted: {total_inserted} records.")

            # Mirror to partitioned table meter_reading_part for partitioning demo
            print("[*] Synchronizing partition table meter_reading_part...")
            cur.execute("INSERT IGNORE INTO meter_reading_part SELECT * FROM meter_reading;")
            conn.commit()
            print("[+] Partition table synced.")

            # Final count
            cur.execute("SELECT COUNT(*) AS total FROM meter_reading;")
            final_cnt = cur.fetchone()['total']
            print(f"[+] Verified meter_reading table row count: {final_cnt}")

    finally:
        conn.close()


def run_live_simulation(interval=5):
    """
    Runs in live continuous loop: every N seconds, inserts a reading for a random meter.
    Injects anomalies so triggers fire live during user demo.
    """
    print(f"[*] Starting Live Meter Reading Generator (Interval: {interval}s)...")
    print("    - 2.0% Probability: High Usage Spike (>5.0 kWh)")
    print("    - 1.0% Probability: Tamper Anomaly (0 kWh with live voltage)")
    print("    - 0.5% Probability: Grid Outage (0V)")
    print("    - 1.5% Probability: Brownout Voltage Sag (<180V)")
    print("[*] Press Ctrl+C to terminate live feed.\n")

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT meter_id, meter_type, customer_id FROM meter WHERE status = 'ACTIVE';")
            meters = cur.fetchall()

        if not meters:
            print("[-] No active meters found.")
            return

        while True:
            m = random.choice(meters)
            mid = m['meter_id']
            now = datetime.now()

            # Random roll for anomaly
            roll = random.random()
            if roll < 0.005:  # Outage
                units = 0.0
                volt = 0.0
                pf = 0.0
                anomaly = "[OUTAGE ALERT TRIGGERED]"
            elif roll < 0.015:  # Tamper (zero consumption, live voltage)
                units = 0.0
                volt = round(random.uniform(225.0, 235.0), 1)
                pf = 0.95
                anomaly = "[TAMPER ALERT TRIGGERED]"
            elif roll < 0.035:  # High usage spike
                units = round(random.uniform(5.5, 9.2), 3)
                volt = round(random.uniform(220.0, 235.0), 1)
                pf = 0.92
                anomaly = "[HIGH USAGE ALERT TRIGGERED]"
            elif roll < 0.050:  # Voltage sag
                units = round(random.uniform(0.5, 1.8), 3)
                volt = round(random.uniform(140.0, 175.0), 1)
                pf = 0.88
                anomaly = "[LOW VOLTAGE ALERT TRIGGERED]"
            else:  # Normal reading
                units, volt, pf = simulate_hourly_usage(now.hour, m['meter_type'], 'DOMESTIC', now.month)
                anomaly = "Normal"

            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO meter_reading (meter_id, reading_ts, units_consumed, voltage, power_factor)
                    VALUES (%s, %s, %s, %s, %s)
                """, (mid, now.strftime('%Y-%m-%d %H:%M:%S'), units, volt, pf))
                conn.commit()

            print(f"[{now.strftime('%H:%M:%S')}] Meter #{mid:02d} -> {units:.3f} kWh | {volt:.1f} V | PF {pf} | {anomaly}")
            time.sleep(interval)

    except KeyboardInterrupt:
        print("\n[*] Live simulator stopped by user.")
    finally:
        conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="VoltTrack Smart Meter Ingestion Simulator")
    parser.add_argument("--bulk", action="store_true", help="Back-fill 4 months of historical readings (100k+ rows)")
    parser.add_argument("--months", type=int, default=4, help="Months of historical data to generate (default: 4)")
    parser.add_argument("--meters", type=int, default=15, help="Number of meters to generate bulk data for (default: 15)")
    parser.add_argument("--live", action="store_true", help="Run continuous live reading stream")
    parser.add_argument("--interval", type=int, default=5, help="Seconds between live readings (default: 5)")

    args = parser.parse_args()

    if args.bulk:
        run_bulk_simulation(months=args.months, target_meters=args.meters)
    elif args.live:
        run_live_simulation(interval=args.interval)
    else:
        print("Usage: python meter_simulator.py --bulk [--months 4 --meters 15] OR python meter_simulator.py --live [--interval 5]")
