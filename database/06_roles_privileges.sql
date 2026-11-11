-- ==============================================================================
-- VoltTrack: Smart Meter Data Management System
-- File: 06_roles_privileges.sql
-- Description: MySQL 8.0 Role-Based Access Control (RBAC) and Least-Privilege Grants.
-- Target DBMS: MySQL 8.0
-- ==============================================================================

USE smartmeter;

-- Create Roles
CREATE ROLE IF NOT EXISTS r_admin;
CREATE ROLE IF NOT EXISTS r_customer;
CREATE ROLE IF NOT EXISTS r_technician;
CREATE ROLE IF NOT EXISTS r_billing;

-- 1. Administrator: Unrestricted operational governance
GRANT ALL PRIVILEGES ON smartmeter.* TO r_admin;

-- 2. Customer: Read own summarized billing, submit complaints, make payments
GRANT SELECT ON smartmeter.v_customer_bill_summary TO r_customer;
GRANT SELECT, INSERT ON smartmeter.complaint TO r_customer;
GRANT SELECT ON smartmeter.meter_reading TO r_customer;
GRANT EXECUTE ON PROCEDURE smartmeter.process_payment TO r_customer;

-- 3. Field Technician: Review alerts, update meter health, manage repair tickets
GRANT SELECT ON smartmeter.alert TO r_technician;
GRANT UPDATE (is_resolved) ON smartmeter.alert TO r_technician;
GRANT SELECT, UPDATE (status, assigned_to) ON smartmeter.complaint TO r_technician;
GRANT SELECT, UPDATE (status, location) ON smartmeter.meter TO r_technician;
GRANT SELECT ON smartmeter.v_active_alerts TO r_technician;

-- 4. Billing Officer: Generate monthly batches, manage invoices, reconcile payments
GRANT SELECT, INSERT, UPDATE ON smartmeter.bill TO r_billing;
GRANT SELECT, INSERT ON smartmeter.payment TO r_billing;
GRANT SELECT ON smartmeter.tariff TO r_billing;
GRANT SELECT ON smartmeter.v_customer_bill_summary TO r_billing;
GRANT SELECT ON smartmeter.v_overdue_bills TO r_billing;
GRANT SELECT ON smartmeter.v_area_consumption TO r_billing;
GRANT EXECUTE ON PROCEDURE smartmeter.generate_bill TO r_billing;
GRANT EXECUTE ON PROCEDURE smartmeter.generate_all_bills TO r_billing;
GRANT EXECUTE ON PROCEDURE smartmeter.process_payment TO r_billing;

-- 5. Demonstration of Privilege Revocation (Academic Demonstration Requirement)
REVOKE INSERT ON smartmeter.complaint FROM r_customer;
-- Re-grant required privilege for normal platform operations
GRANT INSERT ON smartmeter.complaint TO r_customer;

FLUSH PRIVILEGES;

