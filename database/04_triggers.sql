-- ==============================================================================
-- VoltTrack: Smart Meter Data Management System
-- File: 04_triggers.sql
-- Description: Business rules, tamper/outage alerting, payment triggers, audit log.
-- Target DBMS: MySQL 8.0
-- ==============================================================================

USE smartmeter;

DROP TRIGGER IF EXISTS trg_reading_alerts;
DROP TRIGGER IF EXISTS trg_payment_status;
DROP TRIGGER IF EXISTS trg_tariff_audit;
DROP TRIGGER IF EXISTS trg_bill_no_delete;

DELIMITER $$

-- Trigger 1: Real-time anomaly and tamper detection on every incoming reading
CREATE TRIGGER trg_reading_alerts
AFTER INSERT ON meter_reading
FOR EACH ROW
BEGIN
    -- Outage detection: line voltage has dropped to zero
    IF NEW.voltage = 0 THEN
        INSERT INTO alert (meter_id, type, message)
        VALUES (NEW.meter_id, 'OUTAGE', CONCAT('Zero voltage detected at ', NEW.reading_ts));
    -- Tamper detection: voltage is live but zero energy consumed in the interval
    ELSEIF NEW.units_consumed = 0 THEN
        INSERT INTO alert (meter_id, type, message)
        VALUES (NEW.meter_id, 'TAMPER', CONCAT('Zero consumption with live voltage (', NEW.voltage, 'V) - possible meter bypass'));
    -- High consumption spike: usage exceeding 5.000 kWh in 1 hour
    ELSEIF NEW.units_consumed > 5.000 THEN
        INSERT INTO alert (meter_id, type, message)
        VALUES (NEW.meter_id, 'HIGH_USAGE', CONCAT('Unusual usage surge: ', NEW.units_consumed, ' kWh in 1 hour'));
    END IF;

    -- Brownout / low voltage alert
    IF NEW.voltage > 0 AND NEW.voltage < 180.00 THEN
        INSERT INTO alert (meter_id, type, message)
        VALUES (NEW.meter_id, 'LOW_VOLTAGE', CONCAT('Dangerous voltage sag: ', NEW.voltage, ' V'));
    END IF;
END$$

-- Trigger 2: Automatic bill payment status reconciliation
CREATE TRIGGER trg_payment_status
AFTER INSERT ON payment
FOR EACH ROW
BEGIN
    DECLARE v_paid DECIMAL(12,2);
    DECLARE v_amt DECIMAL(12,2);

    -- Calculate cumulative payments made toward this bill
    SELECT COALESCE(SUM(amount), 0) INTO v_paid
    FROM payment
    WHERE bill_id = NEW.bill_id;

    -- Retrieve total bill invoice amount
    SELECT amount INTO v_amt
    FROM bill
    WHERE bill_id = NEW.bill_id;

    -- Mark status as PAID if fully settled, otherwise PARTIAL
    UPDATE bill
    SET status = IF(v_paid >= v_amt, 'PAID', 'PARTIAL')
    WHERE bill_id = NEW.bill_id;
END$$

-- Trigger 3: Full audit trail for tariff adjustments
CREATE TRIGGER trg_tariff_audit
AFTER UPDATE ON tariff
FOR EACH ROW
BEGIN
    INSERT INTO audit_log (table_name, record_id, action, old_value, new_value, changed_by)
    VALUES (
        'tariff',
        NEW.tariff_id,
        'UPDATE',
        CONCAT('category=', OLD.category, ', slab_from=', OLD.slab_from, ', slab_to=', OLD.slab_to, ', rate=', OLD.rate_per_unit, ', fixed=', OLD.fixed_charge),
        CONCAT('category=', NEW.category, ', slab_from=', NEW.slab_from, ', slab_to=', NEW.slab_to, ', rate=', NEW.rate_per_unit, ', fixed=', NEW.fixed_charge),
        COALESCE(USER(), 'SYSTEM')
    );
END$$

-- Trigger 4: Referential integrity protection preventing deletion of bills with payments
CREATE TRIGGER trg_bill_no_delete
BEFORE DELETE ON bill
FOR EACH ROW
BEGIN
    IF EXISTS (SELECT 1 FROM payment WHERE bill_id = OLD.bill_id) THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Integrity constraint violation: Cannot delete an invoice with recorded payments';
    END IF;
END$$

DELIMITER ;

