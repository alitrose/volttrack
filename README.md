# VoltTrack — Smart Meter Data Management & Grid Telemetry Web Application

> *"Real-time grid telemetry, progressive slab billing, and tamper defense — from meter pulse to paid invoice."*

**Deployment:** Localhost Stack (`http://localhost:5000` · MySQL 8.0 on Port `3306`)

**Architecture:** Full-Stack Python/MySQL (`HTML5 + Tailwind CSS + Chart.js` Frontend · `Python + Flask` REST API · `MySQL 8.0 InnoDB` Relational DBMS)

---

## 1. Project Overview

VoltTrack is a full-stack Smart Meter Data Management System (SMDMS) engineered to govern high-frequency IoT electricity telemetry, tiered slab billing, automated anomaly interception, and financial reconciliation. Built strictly in Third Normal Form (3NF/BCNF) on MySQL 8.0 InnoDB, it eliminates spreadsheet redundancies, enforces business rules natively at the database layer, and serves role-specific analytics portals over a stateless JWT REST API.

### Architectural & DBMS Scope
- **4-Role Access Control Model:** Dedicated web portals secured with JWT Bearer tokens (`ADMIN`, `CUSTOMER`, `TECHNICIAN`, `BILLING_OFFICER`) plus MySQL native RBAC roles (`r_admin`, `r_customer`, `r_technician`, `r_billing`).
- **Active Database Governance:** Business rules execute directly inside MySQL using `AFTER INSERT` / `BEFORE DELETE` triggers, cursor-driven stored procedures (`generate_all_bills`), deterministic functions (`calculate_slab_amount`), and `FOR UPDATE` + `SAVEPOINT` payment transactions (`process_payment`).
- **High-Volume Time-Series Telemetry:** Handles `100,000+` hourly meter readings using a composite B-Tree index `(meter_id, reading_ts)` and a monthly range-partitioned shadow table (`meter_reading_part`) alongside a CLI telemetry simulator (`--bulk` / `--live`).

---

## 2. Key Features

- **Real-Time Anomaly & Tamper Triggers (`trg_reading_alerts`):** Automatically classifies incoming readings and inserts alerts for grid outages (`0V`), meter bypass tampering (`0 kWh` with live voltage), high-usage surges (`> 5.0 kWh/hr`), and low-voltage brownouts (`< 180V`).
- **Progressive Slab Billing Engine:** Deterministic UDF `calculate_slab_amount` and cursor loop `generate_all_bills` compute multi-tier rates plus fixed charges across `DOMESTIC`, `COMMERCIAL`, and `INDUSTRIAL` tariffs idempotently.
- **ACID-Safe Payments & Overpayment Rollback (`process_payment`):** Locks target invoice rows via `SELECT ... FOR UPDATE`, establishes `SAVEPOINT before_pay`, rolls back on overpayment (`SQLSTATE 45000`), and auto-reconciles invoice status (`PARTIAL` / `PAID`) via `trg_payment_status`.
- **Immutable Financial Audit Trail:** `trg_tariff_audit` logs old/new slab changes into `audit_log`, while `trg_bill_no_delete` blocks deletions on bills with recorded payments.
- **Analytical Queries & Theft Detection:** Uses SQL Window Functions (`LAG()` to flag `>60%` monthly consumption drops, `ROW_NUMBER()` for 3-month consumption forecasting) and conditional `CASE` Peak (`18:00–21:59`) vs. Off-Peak Time-of-Use analytics.
- **Consumer Portal (`/customer`):** Interactive floating pill toolbar, 30-day Chart.js consumption trend, Time-of-Use donut chart, invoice payment modal, ReportLab PDF electricity bill downloads, and support grievance submission.
- **Admin, Billing & Technician Consoles (`/admin`, `/billing`, `/technician`):** Live KPI cards, top-10 consumers leaderboard, theft suspect monitoring, tariff editor with audit history, grievance/alert triage, and one-click `mysqldump` ACID snapshot backups.
- **Automated Background Jobs (`APScheduler`):** Schedules daily overdue invoice transitions (`00:05`) and monthly batch billing runs (`1st` of each month at `01:00`).

---

## 3. Portals & Demo Credentials

All demo accounts are pre-seeded in MySQL (`02_seed_data.sql`) with salted Werkzeug password hashes:

| Role | Username | Password | Portal Route | Key Capabilities |
| :--- | :--- | :--- | :--- | :--- |
| **System Administrator** | `admin` | `admin123` | `/admin` | Grid KPIs, top consumers, theft suspects, tariff editor with audit log, `mysqldump` backup |
| **Consumer** | `customer` | `Volt@123` | `/customer` | 30-day usage graph, Time-of-Use donut, pay invoices, download PDF bills, file complaints |
| **Field Technician** | `technician` | `Volt@123` | `/technician` | Resolve active tamper/outage alerts, inspect smart meters, update meter status, close tickets |
| **Billing Officer** | `billing` | `Volt@123` | `/billing` | Execute cursor batch billing, filter bills & overdue accounts, analyze substation revenue |

*(Individual consumer logins `customer1` through `customer60` are also seeded with password `Volt@123`).*

---

## 4. Technology Stack

- **Frontend:** HTML5, Tailwind CSS (CDN), Vanilla JavaScript (`Fetch API` + JWT storage), Chart.js (`4.x`), Noir & Crimson UI theme (`styles.css`)
- **Backend:** Python `3.11+`, Flask, Flask-JWT-Extended, Flask-CORS, PyMySQL, Werkzeug, APScheduler, ReportLab, `python-dotenv`
- **Database:** MySQL Community Server `8.0` (InnoDB engine, `utf8mb4_unicode_ci`, 13 normalized/partitioned tables, 4 views, 4 triggers, 3 stored procedures, 1 UDF, 4 RBAC roles)
- **Simulator & QA:** Python `argparse` telemetry generator (`simulator/meter_simulator.py`), `pytest`, standalone 17-case DBMS integrity suite, `EXPLAIN ANALYZE` index benchmark script

---

## 5. Architecture & Project Structure

```text
Browser (index.html, customer.html, admin.html, billing.html, technician.html)
   │
   │  HTTP / JSON + JWT Bearer Token (Fetch API -> /api/*)
   ▼
Flask REST API Server (backend/app.py · Port 5000)
   ├── Extensions: CORS + JWTManager + APScheduler (overdue & monthly batch jobs)
   ├── Blueprints: auth, customers, meters, readings, billing, payments,
   │               complaints, alerts, tariffs, analytics, admin
   ├── Services:   pdf_bill.py (ReportLab PDFs), db.py (PyMySQL DictCursor helpers)
   ▼
MySQL 8.0 InnoDB Database (smartmeter · Port 3306)
   ├── 13 Tables:  area, customer, employee, app_user, meter, meter_reading,
   │               tariff, bill, payment, complaint, alert, audit_log, meter_reading_part
   ├── 4 Views:    v_customer_bill_summary, v_area_consumption, v_active_alerts, v_overdue_bills
   ├── 4 Triggers: trg_reading_alerts, trg_payment_status, trg_tariff_audit, trg_bill_no_delete
   └── Routines:   calculate_slab_amount, generate_bill, generate_all_bills, process_payment
```

```text
volttrack/
├── .env.example                        # Environment variable template (copy to .env)
├── .gitignore
├── README.md
├── requirements.txt                    # Python dependencies
├── backend/
│   ├── app.py                          # Flask app factory, JWT handlers, static page routes
│   ├── auth.py                         # JWT login, /api/auth/me, role_required decorator
│   ├── config.py                       # Environment configuration loader
│   ├── db.py                           # PyMySQL connection, query, write & procedure helpers
│   ├── routes/
│   │   ├── admin.py                    # Audit logs, areas, mysqldump backup endpoint
│   │   ├── alerts.py                   # Alert feed & technician/admin resolution
│   │   ├── analytics.py                # KPIs, top consumers, theft suspects (LAG), revenue, forecast
│   │   ├── billing.py                  # Cursor batch billing, bills listing, PDF invoice export
│   │   ├── complaints.py               # Consumer grievance submission & technician triage
│   │   ├── customers.py                # Customer onboarding & strict isolation checks
│   │   ├── meters.py                   # Meter inventory, installation & status transitions
│   │   ├── payments.py                 # ACID payment settlement calling process_payment
│   │   ├── readings.py                 # IoT ingestion (X-API-KEY) & grouped chart series
│   │   └── tariffs.py                  # Tariff slab catalog & audited updates
│   └── services/
│       ├── pdf_bill.py                 # ReportLab electricity bill generator
│       └── scheduler.py                # APScheduler daily overdue & monthly billing cron jobs
├── database/
│   ├── 01_schema.sql                   # DDL, constraints, indexes & meter_reading_part partitions
│   ├── 02_seed_data.sql                # Areas, customers, employees, meters, tariffs, demo logins
│   ├── 03_functions_procedures.sql     # Slab UDF, cursor billing & SAVEPOINT payment procedures
│   ├── 04_triggers.sql                 # Reading alerts, payment sync, tariff audit & delete guard
│   ├── 05_views.sql                    # Dashboard & reporting SQL views
│   ├── 06_roles_privileges.sql         # MySQL 8.0 RBAC roles & least-privilege grants
│   ├── 07_analytics_queries.sql        # Reference analytical SQL queries
│   ├── 08_index_benchmark.sql          # EXPLAIN ANALYZE index vs full-scan benchmark
│   ├── apply_sql.py                    # Automated ordered SQL migration runner
│   ├── backup_restore.md               # mysqldump, PITR & concurrency locking guide
│   └── generate_seed_sql.py            # Seed data generator script
├── docs/
│   ├── dfd.md                          # Data Flow Diagrams (Context, Level-1, Billing)
│   ├── er_diagram.md                   # Entity-Relationship model & cardinality breakdown
│   ├── normalization.md                # UNF -> 1NF -> 2NF -> 3NF -> BCNF proof
│   └── test_cases.md                   # 17 DBMS verification test specifications
├── frontend/
│   ├── index.html                      # Welcome screen & portal sign-in
│   ├── customer.html                   # Consumer portal with floating pill toolbar
│   ├── admin.html                      # Administrator grid & audit console
│   ├── billing.html                    # Billing officer portal
│   ├── technician.html                 # Field technician portal
│   └── assets/
│       ├── css/styles.css              # Noir & crimson theme + capsule toolbar styles
│       ├── images/smart_meter_hero.jpg # Welcome screen artwork
│       └── js/                         # api.js, auth.js, charts.js
├── simulator/
│   └── meter_simulator.py              # Bulk history generator & live IoT anomaly feeder
└── tests/
    ├── run_tests.py                    # 6-suite standalone API & RBAC test runner
    ├── test_api.py                     # Pytest integration suite
    └── test_all_17_cases.py            # Full 17-case DBMS constraint, trigger & ACID suite
```

---

## 6. Getting Started (Local Development)

### Prerequisites
- **Python** `>= 3.11` and `pip`
- **MySQL Community Server 8.0** running locally on port `3306`

### Step 1: Clone the Repository
```bash
git clone https://github.com/alitrose/volttrack.git
cd volttrack
```

### Step 2: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 3: Configure Environment Variables
Copy the environment template and set your MySQL root/app password (never commit `.env` to Git):
```powershell
# Windows (PowerShell)
Copy-Item .env.example .env

# macOS / Linux
cp .env.example .env
```

#### Environment Variables Reference (`.env`)

| Variable | Required | Default | Description |
| :--- | :--- | :--- | :--- |
| `DB_HOST` | Yes | `localhost` | MySQL server hostname |
| `DB_PORT` | Yes | `3306` | MySQL TCP port |
| `DB_USER` | Yes | `root` | MySQL database username |
| `DB_PASS` | Yes | *(empty)* | Your MySQL user password |
| `DB_NAME` | Yes | `smartmeter` | Target MySQL database schema |
| `JWT_SECRET` | Yes | `super_secret_...` | Secret key used to sign JWT access tokens |
| `FLASK_PORT` | No | `5000` | Flask HTTP listening port |
| `FLASK_DEBUG` | No | `True` | Enable Flask debug reloader (`True` / `False`) |
| `SIMULATOR_API_KEY` | Yes | `volttrack_simulator_...` | `X-API-KEY` header secret for `POST /api/readings` |
| `MYSQL_BIN_PATH` | Optional | `C:\Program Files\MySQL\MySQL Server 8.0\bin` | Directory containing `mysql.exe` and `mysqldump.exe` |

### Step 4: Initialize Database & Seed Telemetry
Apply `01_schema.sql` through `06_roles_privileges.sql` in strict dependency order, then generate 4 months of hourly smart meter readings (`100,000+` rows):
```bash
python database/apply_sql.py
python simulator/meter_simulator.py --bulk --months 4 --meters 15
```

### Step 5: Run the Application Locally
Start the Flask REST API & web frontend:
```bash
python backend/app.py
```
Open **[http://localhost:5000](http://localhost:5000)** in your browser, click **Click to Continue**, and sign in with any demo role.

*(Optional)* Open a second terminal to stream live smart meter readings and anomaly triggers every 5 seconds:
```bash
python simulator/meter_simulator.py --live --interval 5
```

---

## 7. Automated Testing & Verification

Ensure MySQL is running and migrations/seed data have been applied, then execute any of the verification suites:

```bash
# 1. Full 17-case DBMS verification (CHECKs, triggers, UDF, cursor, SAVEPOINT rollback, RBAC, isolation)
python tests/test_all_17_cases.py

# 2. Standalone 6-suite backend & workflow verifier
python tests/run_tests.py

# 3. Pytest API integration test suite
pytest tests/test_api.py -v
```

### Query Optimization Benchmark
Run `database/08_index_benchmark.sql` in MySQL Workbench to compare range scan performance on `100,000+` rows:
- **With composite index (`idx_reading_meter_ts`):** `range` scan examining `~744` rows in `~1.36 ms`.
- **Without index (`reading_benchmark`):** `ALL` full table scan examining `100,000+` rows (`~45 ms`).

---

## 8. API Endpoints Reference

| Method | Endpoint | Auth / Role | Description |
| :--- | :--- | :--- | :--- |
| `POST` | `/api/auth/login` | Public | Authenticate credentials and issue JWT Bearer token |
| `GET` | `/api/auth/me` | JWT | Return authenticated user claims and role metadata |
| `GET` | `/api/customers` | `ADMIN`, `BILLING_OFFICER` | List/filter customers (`?search=`, `?category=`, `?area_id=`) |
| `POST` | `/api/customers` | `ADMIN` | Create customer and auto-provision login (`customer<id>`) |
| `GET` | `/api/customers/:id` | JWT (isolated) | Get customer profile, meters & recent bills (blocks other customers with `403`) |
| `GET` | `/api/meters` | JWT (scoped) | List meters (customer sees own meters; staff can filter `?status=`, `?area_id=`) |
| `GET` | `/api/meters/:id` | JWT (isolated) | Retrieve smart meter metadata and consumer assignment |
| `POST` | `/api/meters` | `ADMIN`, `TECHNICIAN` | Register and commission a smart meter |
| `PATCH` | `/api/meters/:id/status` | `ADMIN`, `TECHNICIAN` | Transition meter status (`ACTIVE`, `FAULTY`, `DISCONNECTED`) |
| `POST` | `/api/readings` | `X-API-KEY` header | Ingest reading pulse and return trigger-generated alerts if fired |
| `GET` | `/api/readings/meter/:id` | JWT (isolated) | Time-series consumption (`?group=hour\|day\|month`, `?from=`, `?to=`) |
| `POST` | `/api/billing/generate` | `ADMIN`, `BILLING_OFFICER` | Execute cursor procedure `generate_all_bills` for target `month` |
| `GET` | `/api/bills` | `ADMIN`, `BILLING_OFFICER` | Query `v_customer_bill_summary` (`?status=`, `?area_id=`, `?month=`, `?search=`) |
| `GET` | `/api/me/bills` | `CUSTOMER` | Retrieve signed-in consumer's invoice ledger |
| `GET` | `/api/bills/:id/pdf` | JWT (isolated) | Generate & download official ReportLab PDF electricity invoice |
| `POST` | `/api/payments` | JWT (isolated) | Execute `process_payment` ACID procedure with overpayment guard |
| `GET` | `/api/payments` | JWT (scoped) | List payment transaction history |
| `GET` | `/api/complaints` | JWT (scoped) | List consumer support tickets / technician queue |
| `POST` | `/api/complaints` | JWT | Submit grievance (`BILLING`, `METER_FAULT`, `OUTAGE`, `OTHER`) |
| `PATCH` | `/api/complaints/:id` | `ADMIN`, `TECHNICIAN` | Assign technician or update status (`OPEN`, `ASSIGNED`, `RESOLVED`) |
| `GET` | `/api/alerts` | JWT (scoped) | Fetch anomaly alerts (`?resolved=true\|false`, `?type=`) |
| `PATCH` | `/api/alerts/:id/resolve` | `ADMIN`, `TECHNICIAN` | Mark active grid alert as resolved |
| `GET` | `/api/tariffs` | Public / JWT | List progressive tariff slabs ordered by category and tier |
| `PUT` | `/api/tariffs/:id` | `ADMIN` | Update slab rate/fixed charge and return `trg_tariff_audit` entry |
| `GET` | `/api/analytics/kpis` | JWT | Summary counts, total billed, collected, and outstanding balance |
| `GET` | `/api/analytics/top-consumers` | `ADMIN`, `BILLING_OFFICER` | Top 10 energy consumers over the last 60 days |
| `GET` | `/api/analytics/peak-offpeak` | JWT | Time-of-Use energy split (Peak `18:00–21:59` vs Off-Peak) |
| `GET` | `/api/analytics/theft-suspects` | `ADMIN`, `TECHNICIAN` | `LAG()` window query detecting `>60%` monthly consumption drops |
| `GET` | `/api/analytics/outages` | JWT | Recent zero-voltage outage alerts |
| `GET` | `/api/analytics/revenue` | `ADMIN`, `BILLING_OFFICER` | Monthly revenue trend & substation area revenue breakdown |
| `GET` | `/api/analytics/forecast` | `ADMIN`, `BILLING_OFFICER` | `ROW_NUMBER()` trailing 3-period rolling consumption forecast |
| `GET` | `/api/areas` | Public / JWT | List distribution areas and substations |
| `GET` | `/api/audit` | `ADMIN` | Inspect `audit_log` entries (`?table=`, `?limit=`) |
| `POST` | `/api/admin/backup` | `ADMIN` | Run non-blocking `mysqldump --single-transaction` snapshot to `backups/` |

---

## 9. Documentation & Viva Artifacts

- [Entity-Relationship Diagram & Cardinalities](docs/er_diagram.md)
- [Normalization Proof (UNF to BCNF)](docs/normalization.md)
- [Data Flow Diagrams (Level 0, 1 & Billing)](docs/dfd.md)
- [17 DBMS Test Case Specifications](docs/test_cases.md)
- [Backup, PITR Recovery & Concurrency Locking Guide](database/backup_restore.md)
