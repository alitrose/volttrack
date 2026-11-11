# VoltTrack: Test Suite & Verification Matrix

This document records the 17 comprehensive test cases mandated by the **VoltTrack DBMS Specification**, covering integrity constraints, business triggers, stored procedures, cursor loops, transactional concurrency with SAVEPOINTs, RBAC security, and customer isolation.

---

## Test Cases Summary Table

| # | Test Objective | Test Input | Expected Behavior | Actual Execution Result | Status |
| :-: | :--- | :--- | :--- | :--- | :-: |
| **1** | Valid Customer Insert | Valid 10-digit Indian mobile starting with 9: `9876543210` | Row successfully inserted into `customer` table. | Insert executed; `customer_id` generated with no constraint errors. | **PASS** |
| **2** | Invalid Phone (CHECK Constraint) | Short / invalid mobile: `12345` | Database rejects insert with `chk_phone` violation. | `ERROR 3819 (HY000): Check constraint 'chk_phone' is violated.` | **PASS** |
| **3** | Duplicate Email (UNIQUE Constraint) | Existing customer email: `aarav.sharma@example.com` | Database rejects duplicate insert with error 1062. | `ERROR 1062 (23000): Duplicate entry for key 'customer.email'` | **PASS** |
| **4** | Negative Units (CHECK Constraint) | Ingestion reading with `units_consumed = -2.5` | Ingestion rejected with `chk_units` violation. | `ERROR 3819 (HY000): Check constraint 'chk_units' is violated.` | **PASS** |
| **5** | High Usage Trigger | Interval reading of `7.500 kWh` in 1 hour | Trigger `trg_reading_alerts` creates `HIGH_USAGE` alert in `alert` table. | Alert `#48` logged: `Unusual usage surge: 7.500 kWh in 1 hour` | **PASS** |
| **6** | Meter Tamper Trigger | `units_consumed = 0.000` with live voltage `230.0 V` | Trigger `trg_reading_alerts` flags potential meter bypass as `TAMPER`. | Alert `#47` logged: `Zero consumption with live voltage (230.00V) - possible meter bypass` | **PASS** |
| **7** | Grid Outage Trigger | Line voltage drops to `0.0 V` | Trigger `trg_reading_alerts` flags `OUTAGE`. | Alert `#46` logged: `Zero voltage detected at 2026-10-27` | **PASS** |
| **8** | Slab Tariff Calculation Function | `calculate_slab_amount('DOMESTIC', 350.00)` | Formula: $(100 \times 2.35) + (150 \times 4.70) + 50 = ₹990.00$ | Function returned exact value: `990.00` | **PASS** |
| **9** | Batch Billing Cursor Idempotency | `generate_all_bills('2026-09-01')` executed twice | Unique constraint `(customer_id, billing_period)` and `INSERT IGNORE` prevents duplicates. | Run 1: 60 bills created. Run 2: exactly 60 bills remain (0 duplicates created). | **PASS** |
| **10** | Partial Payment Processing | Customer pays `₹20.00` on a `₹301.45` bill | Trigger `trg_payment_status` sets bill status to `PARTIAL`. | Invoice status changed from `UNPAID` to `PARTIAL`; remaining balance `₹281.45`. | **PASS** |
| **11** | Full Payment Processing | Customer settles remaining `₹281.45` balance | Trigger `trg_payment_status` updates bill status to `PAID`. | Invoice status transitioned to `PAID`; balance becomes `₹0.00`. | **PASS** |
| **12** | Overpayment Guard (SAVEPOINT & Rollback) | Attempting to pay `₹1,000.00` when balance is `₹281.45` | Transaction rolls back to `SAVEPOINT before_pay` and signals SQLSTATE `45000`. | Rejected with: `(1644, 'Overpayment not allowed: payment exceeds remaining balance')` | **PASS** |
| **13** | Delete Paid Bill Integrity Guard | `DELETE FROM bill WHERE bill_id = 181;` (has payment) | Trigger `trg_bill_no_delete` aborts deletion. | Rejected with: `(1644, 'Integrity constraint violation: Cannot delete an invoice with recorded payments')` | **PASS** |
| **14** | Role-Based Access Control (MySQL Role) | `r_customer` attempts to run `UPDATE tariff` | MySQL engine rejects execution with access denied. | `ERROR 1142 (42000): UPDATE command denied to user for table 'tariff'` | **PASS** |
| **15** | REST API Role Guard (RBAC) | Customer token calls `GET /api/customers` (Admin only) | Decorator `@role_required('ADMIN')` aborts with HTTP 403 Forbidden. | Returned `403 Forbidden`: `user role 'CUSTOMER' lacks required permissions.` | **PASS** |
| **16** | Authentication Invalid Credentials | Login attempt with incorrect password | Auth service rejects with HTTP 401 Unauthorized; no JWT issued. | Returned `401 Unauthorized`: `Invalid username or password` | **PASS** |
| **17** | Customer Data Isolation | Customer 1 attempts `GET /api/customers/2` | Backend enforces ownership check and aborts with HTTP 403. | Returned `403 Forbidden`: `Access denied: cannot access another customer's record` | **PASS** |

---

## Automated Test Runner Output Log

```text
=== Running VoltTrack Automated Backend Tests ===
[1/6] Testing Authentication & Token Issuance...
      -> Passed: Auth and JWT generation verified.
[2/6] Testing RBAC (Customer cannot access Admin endpoints)...
      -> Passed: RBAC properly returned 403 Forbidden.
[3/6] Testing Customer Isolation (Cannot read other customer profile)...
      -> Passed: Server-side customer data isolation enforced.
[4/6] Testing Meter Readings Ingestion with X-API-KEY...
      -> Passed: Reading ingestion and anomaly trigger execution verified.
[5/6] Testing Batch Billing and Transactional Payment Processing...
      -> Passed: Overpayment rejected; partial payment updated status to PARTIAL.
[6/6] Testing Analytics, Reporting, and Audit Logs...
      -> Passed: Analytics, Top-10 consumers, and Audit logs returned accurately.

[+] ALL 6 CORE TEST SUITES PASSED WITH 100% SUCCESS!
```
