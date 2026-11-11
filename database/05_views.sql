-- ==============================================================================
-- VoltTrack: Smart Meter Data Management System
-- File: 05_views.sql
-- Description: Analytical views for dashboards, reporting, and customer portals.
-- Target DBMS: MySQL 8.0
-- ==============================================================================

USE smartmeter;

DROP VIEW IF EXISTS v_customer_bill_summary;
DROP VIEW IF EXISTS v_area_consumption;
DROP VIEW IF EXISTS v_active_alerts;
DROP VIEW IF EXISTS v_overdue_bills;

-- View 1: Customer Invoice Summary with Settlement Balances
CREATE VIEW v_customer_bill_summary AS
SELECT 
    b.bill_id,
    c.customer_id,
    c.name AS customer_name,
    c.email,
    c.category,
    b.billing_period,
    b.units,
    b.amount,
    COALESCE(SUM(p.amount), 0) AS paid,
    ROUND(b.amount - COALESCE(SUM(p.amount), 0), 2) AS balance,
    b.due_date,
    b.status
FROM customer c
JOIN bill b ON b.customer_id = c.customer_id
LEFT JOIN payment p ON p.bill_id = b.bill_id
GROUP BY 
    b.bill_id, 
    c.customer_id, 
    c.name, 
    c.email,
    c.category,
    b.billing_period, 
    b.units, 
    b.amount, 
    b.due_date,
    b.status;

-- View 2: Monthly Energy Aggregation by Substation Area
CREATE VIEW v_area_consumption AS
SELECT 
    a.area_id,
    a.area_name,
    a.substation,
    a.city,
    DATE_FORMAT(r.reading_ts, '%Y-%m') AS ym,
    ROUND(SUM(r.units_consumed), 2) AS total_kwh,
    COUNT(DISTINCT m.meter_id) AS active_meters
FROM meter_reading r
JOIN meter m ON m.meter_id = r.meter_id
JOIN customer c ON c.customer_id = m.customer_id
JOIN area a ON a.area_id = c.area_id
GROUP BY a.area_id, a.area_name, a.substation, a.city, ym;

-- View 3: Unresolved Operational Alerts with Customer and Geolocation Context
CREATE VIEW v_active_alerts AS
SELECT 
    al.alert_id,
    al.meter_id,
    m.customer_id,
    c.name AS customer_name,
    c.phone AS customer_phone,
    a.area_name,
    m.location,
    al.type,
    al.message,
    al.raised_at,
    al.is_resolved
FROM alert al
JOIN meter m ON m.meter_id = al.meter_id
JOIN customer c ON c.customer_id = m.customer_id
JOIN area a ON a.area_id = c.area_id
WHERE al.is_resolved = FALSE;

-- View 4: Delinquent and Overdue Invoices with Aging Calculation
CREATE VIEW v_overdue_bills AS
SELECT 
    b.bill_id,
    c.customer_id,
    c.name AS customer_name,
    c.phone,
    a.area_name,
    b.billing_period,
    b.amount,
    COALESCE(SUM(p.amount), 0) AS paid,
    ROUND(b.amount - COALESCE(SUM(p.amount), 0), 2) AS balance,
    b.due_date,
    DATEDIFF(CURDATE(), b.due_date) AS days_late,
    b.status
FROM bill b
JOIN customer c ON c.customer_id = b.customer_id
JOIN area a ON a.area_id = c.area_id
LEFT JOIN payment p ON p.bill_id = b.bill_id
WHERE b.status IN ('UNPAID', 'PARTIAL', 'OVERDUE')
  AND b.due_date < CURDATE()
GROUP BY 
    b.bill_id, 
    c.customer_id, 
    c.name, 
    c.phone,
    a.area_name,
    b.billing_period, 
    b.amount, 
    b.due_date, 
    b.status;

