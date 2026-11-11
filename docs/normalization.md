# VoltTrack: Database Normalization Report & Data Dictionary

This document details the database normalization steps from **Unnormalized Form (UNF)** through **Boyce-Codd Normal Form (BCNF)**, specifies the data anomalies resolved, and provides the complete data dictionary.

---

## 1. Normalization Walkthrough (UNF to BCNF)

### 1.1 Unnormalized Form (UNF)
Consider a legacy spreadsheet or single flat file where all utility operations are logged together:

$$\text{UNF}(\underline{\text{CustID}}, \text{CustName}, \text{CustAddress}, \text{AreaName}, \text{Substation}, \text{City}, \text{Phone}, \text{Email}, \text{Category}, \{\text{MeterID}, \text{MeterType}, \text{InstallDate}\}, \{\text{ReadingTS}, \text{kWh}, \text{Voltage}\}, \{\text{BillMonth}, \text{BillAmt}, \text{DueDate}, \text{PaidAmt}, \text{PayMode}\}, \{\text{SlabFrom}, \text{SlabTo}, \text{Rate}\})$$

#### Anomalies Present in UNF:
- **Redundancy**: Repeating groups for multiple meters, readings, and monthly bills.
- **Insertion Anomaly**: Cannot record an area or tariff slab until a customer is added.
- **Update Anomaly**: If a customer's address changes, it must be updated in thousands of reading rows.
- **Deletion Anomaly**: Deleting a customer's bill history inadvertently erases meter technical specifications and area data.

---

### 1.2 First Normal Form (1NF)
**Rule**: Eliminate repeating groups; ensure all attributes are atomic; define a unique primary key.

- Flatten repeating groups into discrete entities:
  - `Customer` with single-valued atomic attributes.
  - `Meter` keyed by `meter_id`.
  - `Meter_Reading` keyed by `reading_id`.
  - `Bill` keyed by `bill_id`.
  - `Tariff` keyed by `tariff_id`.
- Phone numbers and addresses are stored as atomic fields with strict validation (`CHECK phone REGEXP '^[6-9][0-9]{9}$'`).

---

### 1.3 Second Normal Form (2NF)
**Rule**: Satisfy 1NF and ensure **no partial dependencies** on composite candidate keys. Every non-prime attribute must depend on the whole candidate key.

- In `meter_reading(reading_id, meter_id, reading_ts, units_consumed, voltage, power_factor)`:
  - `units_consumed`, `voltage`, and `power_factor` depend strictly on `reading_id` (or the candidate key `(meter_id, reading_ts)`).
- In `bill(bill_id, customer_id, billing_period, units, amount, due_date, status)`:
  - `due_date`, `units`, and `amount` depend strictly on the whole key `bill_id` (and the natural key `(customer_id, billing_period)`).
  - Customer contact details are separated into `customer`, eliminating any partial dependency.

---

### 1.4 Third Normal Form (3NF)
**Rule**: Satisfy 2NF and ensure **no transitive dependencies** ($X \rightarrow Y \rightarrow Z$). Non-prime attributes must depend only on candidate keys.

- **Area Isolation**:
  - In `customer`, `area_name`, `substation`, and `city` previously depended on `area_id`.
  - We extract `area(area_id PK, area_name UK, substation, city)`.
  - `customer.area_id` is a foreign key. Changes to a substation name require modifying exactly 1 row.
- **Tariff Isolation**:
  - Utility rates and fixed charges depend on `category` and slab thresholds, not on customer or bill IDs.
  - Slabs live in `tariff(tariff_id PK, category, slab_from, slab_to, rate_per_unit, fixed_charge)`.

---

### 1.5 Boyce-Codd Normal Form (BCNF)
**Rule**: Satisfy 3NF and for every functional dependency $X \rightarrow Y$, the determinant $X$ must be a **superkey**.

- In `tariff`:
  $$(\text{category}, \text{slab\_from}) \rightarrow \text{slab\_to}, \text{rate\_per\_unit}, \text{fixed\_charge}$$
  - The compound determinant `(category, slab_from)` is enforced as a candidate key via `UNIQUE KEY (category, slab_from)`.
  - Hence, every determinant in `tariff` is a candidate key.
- In `customer`:
  - `phone` is a candidate key (`UNIQUE`).
  - `email` is a candidate key (`UNIQUE`).
  - `customer_id` is the primary key.
  - Every determinant is a candidate key.

---

### 1.6 Justified Deliberate Denormalization (Snapshot Integrity)

In `bill`:
- Attributes `units` (DECIMAL 10,2) and `amount` (DECIMAL 12,2) are intentionally stored as **immutable snapshots**.
- **Justification**:
  1. Utility tariffs change over time. If older bills recomputed their amount dynamically from the live `tariff` table, historical tax invoices would change retroactively, violating legal accounting regulations.
  2. Performance: Generating accounts receivable and balance reports avoids running heavy multi-slab integration calculations across hundreds of thousands of historical meter readings.

---

## 2. Complete Data Dictionary

| Table | Column | Data Type | Nullable | Key / Constraint | Description |
| :--- | :--- | :--- | :---: | :--- | :--- |
| **area** | `area_id` | INT | NO | PRIMARY KEY, AUTO_INCREMENT | Unique substation area ID |
| | `area_name` | VARCHAR(60) | NO | UNIQUE | Sector name (e.g., Indiranagar) |
| | `substation` | VARCHAR(80) | NO | - | High-voltage grid substation identifier |
| | `city` | VARCHAR(60) | NO | - | Municipal city (e.g., Bengaluru) |
| **customer** | `customer_id` | INT | NO | PRIMARY KEY, AUTO_INCREMENT | Unique customer identifier |
| | `name` | VARCHAR(80) | NO | - | Full consumer name |
| | `address` | VARCHAR(200) | NO | - | Service delivery street address |
| | `area_id` | INT | NO | FOREIGN KEY &rarr; `area.area_id` | Substation area assignment |
| | `phone` | CHAR(10) | NO | UNIQUE, CHECK `^[6-9][0-9]{9}$` | 10-digit Indian mobile number |
| | `email` | VARCHAR(100) | NO | UNIQUE | Consumer electronic mail address |
| | `category` | ENUM | NO | DEFAULT 'DOMESTIC' | DOMESTIC, COMMERCIAL, INDUSTRIAL |
| | `created_at` | TIMESTAMP | NO | DEFAULT CURRENT_TIMESTAMP | Registration timestamp |
| **employee** | `emp_id` | INT | NO | PRIMARY KEY, AUTO_INCREMENT | Unique employee identifier |
| | `name` | VARCHAR(80) | NO | - | Staff member name |
| | `role` | ENUM | NO | - | ADMIN, TECHNICIAN, METER_READER, BILLING_OFFICER |
| | `area_id` | INT | YES | FOREIGN KEY &rarr; `area.area_id` | Assigned jurisdiction |
| | `phone` | CHAR(10) | YES | UNIQUE | Contact mobile number |
| **app_user** | `user_id` | INT | NO | PRIMARY KEY, AUTO_INCREMENT | Authentication identity |
| | `username` | VARCHAR(50) | NO | UNIQUE | Login username |
| | `password_hash`| VARCHAR(255) | NO | - | Salted Werkzeug scrypt/pbkdf2 hash |
| | `role` | ENUM | NO | - | ADMIN, CUSTOMER, TECHNICIAN, BILLING_OFFICER |
| | `customer_id` | INT | YES | FOREIGN KEY &rarr; `customer.customer_id` | Linked consumer account |
| | `emp_id` | INT | YES | FOREIGN KEY &rarr; `employee.emp_id` | Linked staff account |
| | `is_active` | BOOLEAN | NO | DEFAULT TRUE | Account state |
| **meter** | `meter_id` | INT | NO | PRIMARY KEY, AUTO_INCREMENT | Physical smart meter hardware ID |
| | `customer_id` | INT | NO | FOREIGN KEY &rarr; `customer.customer_id` | Registered owner |
| | `meter_type` | ENUM | NO | DEFAULT 'SINGLE_PHASE' | SINGLE_PHASE, THREE_PHASE |
| | `install_date`| DATE | NO | - | Commissioning date |
| | `status` | ENUM | NO | DEFAULT 'ACTIVE' | ACTIVE, FAULTY, DISCONNECTED |
| | `location` | VARCHAR(120) | YES | - | Physical meter cabinet position |
| **meter_reading**| `reading_id` | BIGINT | NO | PRIMARY KEY, AUTO_INCREMENT | Unique time-series record ID |
| | `meter_id` | INT | NO | FOREIGN KEY &rarr; `meter.meter_id` | Smart meter source |
| | `reading_ts` | DATETIME | NO | INDEX `idx_reading_meter_ts` | Timestamp of hourly recording |
| | `units_consumed`| DECIMAL(8,3)| NO | CHECK `units_consumed >= 0` | Energy consumed in interval (kWh) |
| | `voltage` | DECIMAL(6,2)| NO | - | Line root-mean-square voltage (V) |
| | `power_factor`| DECIMAL(3,2)| NO | CHECK `power_factor BETWEEN 0 AND 1`| Phase power factor |
| **tariff** | `tariff_id` | INT | NO | PRIMARY KEY, AUTO_INCREMENT | Tariff rule ID |
| | `category` | ENUM | NO | - | DOMESTIC, COMMERCIAL, INDUSTRIAL |
| | `slab_from` | DECIMAL(10,2)| NO | UNIQUE with `category` | Lower boundary of consumption slab |
| | `slab_to` | DECIMAL(10,2)| NO | CHECK `slab_to > slab_from` | Upper boundary of consumption slab |
| | `rate_per_unit`| DECIMAL(6,2)| NO | CHECK `rate_per_unit >= 0` | Cost per kWh in this tier (₹) |
| | `fixed_charge`| DECIMAL(8,2)| NO | DEFAULT 0 | Fixed connection surcharge (₹) |
| **bill** | `bill_id` | INT | NO | PRIMARY KEY, AUTO_INCREMENT | Invoice serial number |
| | `customer_id` | INT | NO | FOREIGN KEY &rarr; `customer.customer_id` | Billed consumer |
| | `billing_period`| DATE | NO | UNIQUE with `customer_id` | Billing month (1st of month) |
| | `units` | DECIMAL(10,2)| NO | - | Total kWh billed in month |
| | `amount` | DECIMAL(12,2)| NO | - | Total payable invoice amount (₹) |
| | `due_date` | DATE | NO | - | Payment cutoff date (month end + 15d)|
| | `status` | ENUM | NO | DEFAULT 'UNPAID' | UNPAID, PARTIAL, PAID, OVERDUE |
| **payment** | `payment_id` | INT | NO | PRIMARY KEY, AUTO_INCREMENT | Transaction receipt ID |
| | `bill_id` | INT | NO | FOREIGN KEY &rarr; `bill.bill_id` | Paid invoice reference |
| | `amount` | DECIMAL(12,2)| NO | CHECK `amount > 0` | Paid amount (₹) |
| | `mode` | ENUM | NO | - | UPI, CARD, NETBANKING, CASH |
| | `paid_at` | TIMESTAMP | NO | DEFAULT CURRENT_TIMESTAMP | Transaction timestamp |
| | `transaction_ref`| VARCHAR(40)| NO | UNIQUE | Gateway authorization reference |
| **complaint** | `complaint_id`| INT | NO | PRIMARY KEY, AUTO_INCREMENT | Ticket number |
| | `customer_id` | INT | NO | FOREIGN KEY &rarr; `customer.customer_id` | Lodging customer |
| | `type` | ENUM | NO | - | BILLING, METER_FAULT, OUTAGE, OTHER |
| | `description` | VARCHAR(300)| NO | - | Incident description |
| | `status` | ENUM | NO | DEFAULT 'OPEN' | OPEN, ASSIGNED, RESOLVED |
| | `assigned_to` | INT | YES | FOREIGN KEY &rarr; `employee.emp_id` | Assigned field technician |
| | `created_at` | TIMESTAMP | NO | DEFAULT CURRENT_TIMESTAMP | Lodging timestamp |
| **alert** | `alert_id` | INT | NO | PRIMARY KEY, AUTO_INCREMENT | Trigger alert ID |
| | `meter_id` | INT | NO | FOREIGN KEY &rarr; `meter.meter_id` | Originating meter |
| | `type` | ENUM | NO | - | HIGH_USAGE, TAMPER, OUTAGE, LOW_VOLTAGE |
| | `message` | VARCHAR(200)| NO | - | Automated alert message from trigger|
| | `raised_at` | TIMESTAMP | NO | DEFAULT CURRENT_TIMESTAMP | Event timestamp |
| | `is_resolved` | BOOLEAN | NO | DEFAULT FALSE | Clearance status |
| **audit_log** | `log_id` | BIGINT | NO | PRIMARY KEY, AUTO_INCREMENT | Audit sequence ID |
| | `table_name` | VARCHAR(40) | NO | - | Target table modified |
| | `record_id` | VARCHAR(40) | NO | - | Primary key value modified |
| | `action` | VARCHAR(10) | NO | - | UPDATE, DELETE, INSERT |
| | `old_value` | TEXT | YES | - | Pre-modification state |
| | `new_value` | TEXT | YES | - | Post-modification state |
| | `changed_by` | VARCHAR(80) | NO | - | Database or application user |
| | `changed_at` | TIMESTAMP | NO | DEFAULT CURRENT_TIMESTAMP | Audit timestamp |
