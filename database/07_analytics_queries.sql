-- ==============================================================================
-- VoltTrack: Smart Meter Data Management System
-- File: 07_analytics_queries.sql
-- Description: Advanced analytical queries demonstrating window functions,
--              ROLLUP, subqueries, CTEs, and Time-of-Use (ToU) analytics.
-- Target DBMS: MySQL 8.0
-- ==============================================================================

USE smartmeter;

-- Query 1: Monthly Consumption per Customer
SELECT 
    c.customer_id,
    c.name AS customer_name,
    DATE_FORMAT(r.reading_ts, '%Y-%m') AS month,
    ROUND(SUM(r.units_consumed), 2) AS kwh_consumed
FROM meter_reading r
JOIN meter m ON m.meter_id = r.meter_id
JOIN customer c ON c.customer_id = m.customer_id
GROUP BY c.customer_id, c.name, month
ORDER BY month DESC, kwh_consumed DESC;

-- Query 2: Top 10 Highest Energy Consumers
SELECT 
    c.customer_id,
    c.name AS customer_name,
    c.category,
    a.area_name,
    ROUND(SUM(r.units_consumed), 2) AS total_kwh
FROM meter_reading r
JOIN meter m ON m.meter_id = r.meter_id
JOIN customer c ON c.customer_id = m.customer_id
JOIN area a ON a.area_id = c.area_id
WHERE r.reading_ts >= DATE_SUB(CURDATE(), INTERVAL 60 DAY)
GROUP BY c.customer_id, c.name, c.category, a.area_name
ORDER BY total_kwh DESC
LIMIT 10;

-- Query 3: Delinquent & Overdue Receivables Aging Analysis
SELECT 
    c.customer_id,
    c.name AS customer_name,
    b.bill_id,
    b.billing_period,
    b.amount AS billed_amount,
    COALESCE(SUM(p.amount), 0) AS paid_amount,
    ROUND(b.amount - COALESCE(SUM(p.amount), 0), 2) AS balance_due,
    b.due_date,
    DATEDIFF(CURDATE(), b.due_date) AS days_overdue
FROM bill b
JOIN customer c ON c.customer_id = b.customer_id
LEFT JOIN payment p ON p.bill_id = b.bill_id
WHERE b.status IN ('UNPAID', 'PARTIAL', 'OVERDUE')
  AND b.due_date < CURDATE()
GROUP BY b.bill_id, c.customer_id, c.name, b.billing_period, b.amount, b.due_date
ORDER BY days_overdue DESC;

-- Query 4: Revenue Aggregation by Substation Area and Month (with ROLLUP)
SELECT 
    a.area_name,
    DATE_FORMAT(p.paid_at, '%Y-%m') AS month,
    ROUND(SUM(p.amount), 2) AS revenue
FROM payment p
JOIN bill b USING (bill_id)
JOIN customer c USING (customer_id)
JOIN area a USING (area_id)
GROUP BY a.area_name, month WITH ROLLUP;

-- Query 5: Above-Category-Average Outlier Analysis (Correlated Subquery + HAVING)
SELECT 
    c.category,
    c.customer_id,
    c.name AS customer_name,
    ROUND(SUM(b.units), 2) AS total_units_billed
FROM bill b
JOIN customer c ON c.customer_id = b.customer_id
GROUP BY c.category, c.customer_id, c.name
HAVING SUM(b.units) > (
    SELECT AVG(cat_sum.total_units)
    FROM (
        SELECT c2.category, c2.customer_id, SUM(b2.units) AS total_units
        FROM bill b2
        JOIN customer c2 ON c2.customer_id = b2.customer_id
        GROUP BY c2.category, c2.customer_id
    ) cat_sum
    WHERE cat_sum.category = c.category
)
ORDER BY c.category, total_units_billed DESC;

-- Query 6: Time-of-Use (ToU) Peak vs Off-Peak Distribution (Peak: 18:00 - 22:00)
SELECT 
    m.meter_id,
    c.name AS customer_name,
    ROUND(SUM(CASE WHEN HOUR(r.reading_ts) BETWEEN 18 AND 21 THEN r.units_consumed ELSE 0 END), 2) AS peak_kwh,
    ROUND(SUM(CASE WHEN HOUR(r.reading_ts) NOT BETWEEN 18 AND 21 THEN r.units_consumed ELSE 0 END), 2) AS offpeak_kwh,
    ROUND(SUM(r.units_consumed), 2) AS total_kwh,
    ROUND(100.0 * SUM(CASE WHEN HOUR(r.reading_ts) BETWEEN 18 AND 21 THEN r.units_consumed ELSE 0 END) / NULLIF(SUM(r.units_consumed), 0), 1) AS peak_percentage
FROM meter_reading r
JOIN meter m ON m.meter_id = r.meter_id
JOIN customer c ON c.customer_id = m.customer_id
GROUP BY m.meter_id, c.name
ORDER BY peak_percentage DESC;

-- Query 7: Electricity Theft / Bypass Suspects (Window Function LAG: >60% drop vs previous month)
WITH monthly_consumption AS (
    SELECT 
        m.meter_id,
        c.name AS customer_name,
        c.phone,
        DATE_FORMAT(r.reading_ts, '%Y-%m-01') AS ym,
        ROUND(SUM(r.units_consumed), 2) AS monthly_kwh
    FROM meter_reading r
    JOIN meter m ON m.meter_id = r.meter_id
    JOIN customer c ON c.customer_id = m.customer_id
    GROUP BY m.meter_id, c.name, c.phone, ym
),
consumption_delta AS (
    SELECT 
        meter_id,
        customer_name,
        phone,
        ym,
        monthly_kwh,
        LAG(monthly_kwh) OVER (PARTITION BY meter_id ORDER BY ym) AS prev_month_kwh
    FROM monthly_consumption
)
SELECT 
    meter_id,
    customer_name,
    phone,
    ym AS current_month,
    prev_month_kwh,
    monthly_kwh,
    ROUND(100.0 * (prev_month_kwh - monthly_kwh) / prev_month_kwh, 1) AS drop_percentage
FROM consumption_delta
WHERE prev_month_kwh > 50.0 
  AND monthly_kwh < (0.40 * prev_month_kwh)
ORDER BY drop_percentage DESC;

-- Query 8: Rolling 3-Month Moving Average Demand Forecast
WITH ranked_bills AS (
    SELECT 
        b.customer_id,
        c.name AS customer_name,
        b.billing_period,
        b.units,
        ROW_NUMBER() OVER (PARTITION BY b.customer_id ORDER BY b.billing_period DESC) AS rn
    FROM bill b
    JOIN customer c ON c.customer_id = b.customer_id
)
SELECT 
    customer_id,
    customer_name,
    ROUND(AVG(units), 2) AS forecast_next_month_kwh,
    COUNT(units) AS historical_months_counted
FROM ranked_bills
WHERE rn <= 3
GROUP BY customer_id, customer_name
ORDER BY forecast_next_month_kwh DESC;

