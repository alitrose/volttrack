-- ==============================================================================
-- VoltTrack: Smart Meter Data Management System
-- File: 03_functions_procedures.sql
-- Description: Stored procedures, user-defined functions, cursors, and transactions.
-- Target DBMS: MySQL 8.0
-- ==============================================================================

USE smartmeter;

DROP FUNCTION IF EXISTS calculate_slab_amount;
DROP PROCEDURE IF EXISTS generate_bill;
DROP PROCEDURE IF EXISTS generate_all_bills;
DROP PROCEDURE IF EXISTS process_payment;

DELIMITER $$

-- 1. Deterministic Slab Calculation Function
CREATE FUNCTION calculate_slab_amount(p_category VARCHAR(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci, p_units DECIMAL(10,2))
RETURNS DECIMAL(12,2)
DETERMINISTIC
READS SQL DATA
BEGIN
    DECLARE v_energy DECIMAL(12,2) DEFAULT 0;
    DECLARE v_fixed DECIMAL(12,2) DEFAULT 0;

    -- Calculate consumption charge across all progressive slabs
    SELECT COALESCE(SUM((LEAST(p_units, slab_to) - slab_from) * rate_per_unit), 0)
    INTO v_energy
    FROM tariff
    WHERE category = p_category AND p_units > slab_from;

    -- Retrieve applicable fixed connection charge
    SELECT COALESCE(MAX(fixed_charge), 0)
    INTO v_fixed
    FROM tariff
    WHERE category = p_category;

    RETURN ROUND(v_energy + v_fixed, 2);
END$$

-- 2. Single Customer Bill Generation Procedure
CREATE PROCEDURE generate_bill(IN p_customer_id INT, IN p_month DATE)
BEGIN
    DECLARE v_units DECIMAL(10,2) DEFAULT 0;
    DECLARE v_cat VARCHAR(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
    DECLARE v_bill_amount DECIMAL(12,2) DEFAULT 0;

    -- Fetch customer tariff category
    SELECT category INTO v_cat FROM customer WHERE customer_id = p_customer_id;

    -- Aggregate monthly meter readings across all meters owned by customer
    SELECT COALESCE(SUM(r.units_consumed), 0)
    INTO v_units
    FROM meter_reading r
    JOIN meter m ON m.meter_id = r.meter_id
    WHERE m.customer_id = p_customer_id
      AND r.reading_ts >= p_month
      AND r.reading_ts < DATE_ADD(p_month, INTERVAL 1 MONTH);

    -- Calculate amount using slab function
    SET v_bill_amount = calculate_slab_amount(v_cat, v_units);

    -- Insert into bill if not already generated (idempotent via unique constraint)
    INSERT IGNORE INTO bill (customer_id, billing_period, units, amount, due_date, status)
    VALUES (
        p_customer_id,
        p_month,
        v_units,
        v_bill_amount,
        DATE_ADD(LAST_DAY(p_month), INTERVAL 15 DAY),
        'UNPAID'
    );
END$$

-- 3. Batch Bill Generation Using Cursor
CREATE PROCEDURE generate_all_bills(IN p_month DATE)
BEGIN
    DECLARE done INT DEFAULT 0;
    DECLARE v_cid INT;

    -- Cursor to iterate over all active customers
    DECLARE cur CURSOR FOR SELECT customer_id FROM customer;
    DECLARE CONTINUE HANDLER FOR NOT FOUND SET done = 1;

    OPEN cur;
    bill_loop: LOOP
        FETCH cur INTO v_cid;
        IF done = 1 THEN
            LEAVE bill_loop;
        END IF;
        CALL generate_bill(v_cid, p_month);
    END LOOP;
    CLOSE cur;
END$$

-- 4. ACID Transactional Payment Processing with Row Locking and SAVEPOINT
CREATE PROCEDURE process_payment(
    IN p_bill_id INT,
    IN p_amount DECIMAL(12,2),
    IN p_mode VARCHAR(12),
    IN p_ref VARCHAR(40)
)
BEGIN
    DECLARE v_due DECIMAL(12,2);
    DECLARE v_total DECIMAL(12,2);
    DECLARE v_paid DECIMAL(12,2);

    -- Rollback on any SQL exception
    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        ROLLBACK;
        RESIGNAL;
    END;

    START TRANSACTION;

    -- Lock bill row to prevent concurrent race condition payments
    SELECT amount INTO v_total FROM bill WHERE bill_id = p_bill_id FOR UPDATE;

    SELECT COALESCE(SUM(amount), 0) INTO v_paid FROM payment WHERE bill_id = p_bill_id;
    SET v_due = v_total - v_paid;

    SAVEPOINT before_pay;

    -- Reject payment exceeding outstanding balance
    IF p_amount > v_due THEN
        ROLLBACK TO SAVEPOINT before_pay;
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Overpayment not allowed: payment exceeds remaining balance';
    END IF;

    -- Insert valid payment; trg_payment_status updates bill status
    INSERT INTO payment (bill_id, amount, mode, transaction_ref)
    VALUES (p_bill_id, p_amount, p_mode, p_ref);

    COMMIT;
END$$

DELIMITER ;

