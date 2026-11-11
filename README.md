# VoltTrack: Smart Meter Data Management System

**VoltTrack** is a college-grade, production-quality Database Management System (DBMS) designed for real-time electrical grid telemetry, automated progressive slab billing, and fraud/tamper detection. It features a normalized **MySQL 8.0 (InnoDB)** backend, an enterprise **Python Flask REST API**, and a modern **HTML/Tailwind CSS/Chart.js** web interface with role-based access control.

---

## 1. System Architecture & Tech Stack

```text
[ Browser (Tailwind CSS + Chart.js) ]
         │
         ▼  (JWT RBAC via Fetch API)
[ Python Flask REST API (Port 5000) ]
    ├── Blueprints: Auth, Customers, Meters, Readings, Billing, Payments, Complaints, Alerts, Analytics, Admin
    ├── APScheduler: Automated Overdue Marking & Batch Billing
    └── ReportLab: Regulatory PDF Electricity Invoices
         │
         ▼  (PyMySQL Parameterized Queries)
[ MySQL 8.0 Enterprise Database (InnoDB) ]
    ├── 13 Tables (3NF/BCNF Normalized, ENUMs, Regex CHECKs)
    ├── Partitioned Table: meter_reading_part (Range partitioned by month)
    ├── 4 Analytical Views (v_customer_bill_summary, v_area_consumption, etc.)
    ├── 4 Automated Triggers (Tamper, Outage, High Usage, Payment Status, Audit)
    ├── 3 Stored Procedures (Cursor batch billing, ACID payment with SAVEPOINT)
    ├── 1 Deterministic Function (Progressive Tariff Slab Calculator)
    └── RBAC Roles: r_admin, r_customer, r_technician, r_billing
```

- **Database**: MySQL Server 8.0 (InnoDB engine, UTF-8 collation)
- **Backend**: Python 3.11+ / Flask, Flask-JWT-Extended, Flask-CORS, PyMySQL, ReportLab, APScheduler, python-dotenv
- **Frontend**: Plain HTML5, Tailwind CSS (via CDN), vanilla JavaScript, Chart.js (via CDN). No npm build step required.

---

## 2. Pre-Configured Demo Accounts

All demo accounts are pre-seeded in MySQL with salted password hashes.

| Role | Username | Password | Dashboard URL | Capabilities |
| :--- | :--- | :--- | :--- | :--- |
| **System Administrator** | `admin` | `admin123` | `http://localhost:5000/admin` | Full grid telemetry, Top-10 consumers, theft suspects, tariff adjustments with audit, one-click database backup |
| **Consumer** | `customer` | `Volt@123` | `http://localhost:5000/customer` | Live 30-day usage graphs, peak vs off-peak donut, settle bills with modal, download PDF statements, lodge complaints |
| **Field Technician** | `technician` | `Volt@123` | `http://localhost:5000/technician` | Triage assigned complaints, update meter states (ACTIVE/FAULTY/DISCONNECTED), clear tamper/outage alerts |
| **Billing Officer** | `billing` | `Volt@123` | `http://localhost:5000/billing` | Execute cursor-driven batch billing, accounts receivable aging, area performance tables, CSV export |

*(Individual consumer accounts `customer1` through `customer60` are also available with password `Volt@123`).*

---

## 3. Quick Start & Execution Guide

### Step 1: Environment Setup
Ensure Python 3.11+ and MySQL Server 8.0 are installed. Configure your credentials in `.env`:
```ini
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASS=your_mysql_password
DB_NAME=smartmeter
JWT_SECRET=super_secret_volttrack_jwt_key_2026_x8934
FLASK_PORT=5000
FLASK_DEBUG=True
SIMULATOR_API_KEY=volttrack_simulator_api_key_secure_2026
```

Install the dependencies:
```powershell
pip install -r requirements.txt
```

### Step 2: Initialize Database Migrations
Execute the automated SQL migration runner, which applies tables, seed data, stored procedures, triggers, views, and roles in exact order:
```powershell
python database/apply_sql.py
```

### Step 3: Populate 100,000+ Smart Meter Readings
Run the bulk simulator to back-fill 4 months of hourly records with diurnal curves:
```powershell
python simulator/meter_simulator.py --bulk --months 4 --meters 35
```

### Step 4: Run the Backend & Web Application
Launch the Flask server:
```powershell
python backend/app.py
```
Open your web browser and navigate to:
**`http://localhost:5000`**

### Step 5: (Optional) Run Live Meter Reading Feed
Open a secondary terminal to inject real-time readings every 5 seconds. This causes anomaly triggers (tamper, outage, high consumption) to fire live on the Admin and Technician dashboards during a demo:
```powershell
python simulator/meter_simulator.py --live --interval 5
```

---

## 4. 10-Minute Examiner Live Demo Script

| Minute | Action / Demonstration | What it Proves to the Examiner |
| :---: | :--- | :--- |
| **0 - 1** | **Problem Statement**: Manual meter errors, late billing, unmetered electricity theft, lack of consumer visibility. | Academic and industrial motivation. |
| **1 - 2** | **Data Model & Normalization**: Showcase `docs/er_diagram.md` (13 entities) and `docs/normalization.md` (UNF &rarr; BCNF). | High-grade relational database design quality. |
| **2 - 4** | **Live Ingestion & Triggers**: Run `meter_simulator.py --live`. Watch the live alert feed populate in real time with `TAMPER`, `OUTAGE`, and `HIGH_USAGE` alerts. | Execution of event-driven database triggers (`trg_reading_alerts`). |
| **4 - 5** | **Batch Billing Run**: Login as Billing Officer (`billing`), select month `2026-09`, click **Run Batch Billing**. Show that 60 bills are created with exact slab formulas (e.g., DOMESTIC 350 units = ₹990.00). | Stored procedure (`generate_all_bills`), cursor loop, and UDF (`calculate_slab_amount`). |
| **5 - 6** | **Payment Concurrency & SAVEPOINT**: Login as `customer`. Make a partial payment (status updates to `PARTIAL`). Try an overpayment (rejected and rolled back to savepoint). Settle full amount (status updates to `PAID`). Download generated PDF. | ACID transactions, row-level locking (`SELECT ... FOR UPDATE`), and `SAVEPOINT`. |
| **6 - 7** | **Tariff Audit Trail**: Login as `admin`, adjust a tariff slab rate. Open the Audit Log table to show the trigger (`trg_tariff_audit`) immediately logged the old and new rates with timestamps. | Compliance, security, and automated auditing. |
| **7 - 8** | **Index Benchmark**: Show `database/08_index_benchmark.sql` `EXPLAIN ANALYZE` results. Range scan on composite index `(meter_id, reading_ts)` on 102k+ rows takes 1.2 ms vs 24.2 ms table scan without index. | Physical database tuning, query optimization, and execution plans. |
| **8 - 9** | **Advanced Analytics**: Showcase the Electricity Theft Suspects table (SQL window function `LAG` detecting &gt;60% drops) and Peak vs Off-Peak ToU donut chart. | Advanced SQL mastery: CTEs, Window Functions, and `ROLLUP`. |
| **9 - 10**| **Database Backup & Recovery**: Click **Run mysqldump Backup** in Admin Console. Show the generated `.sql` snapshot in `backups/`. | Backup, point-in-time recovery, and operational resilience. |

---

## 5. Verification & Automated Test Suite

To execute the automated regression test suite covering all 17 test cases:
```powershell
python tests/run_tests.py
```
*(Tests RBAC 403 enforcement, customer data isolation, reading ingestion, payment overpayment guards, and analytics).*
