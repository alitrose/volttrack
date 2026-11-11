-- ==============================================================================
-- VoltTrack: Smart Meter Data Management System
-- File: 01_schema.sql
-- Description: Core DDL definitions, tables, constraints, keys, and indexes.
-- Target DBMS: MySQL 8.0 (InnoDB)
-- ==============================================================================

CREATE DATABASE IF NOT EXISTS smartmeter;
USE smartmeter;

-- Drop child tables first in reverse dependency order
DROP TABLE IF EXISTS audit_log;
DROP TABLE IF EXISTS alert;
DROP TABLE IF EXISTS complaint;
DROP TABLE IF EXISTS payment;
DROP TABLE IF EXISTS bill;
DROP TABLE IF EXISTS tariff;
DROP TABLE IF EXISTS meter_reading;
DROP TABLE IF EXISTS meter_reading_part;
DROP TABLE IF EXISTS meter;
DROP TABLE IF EXISTS app_user;
DROP TABLE IF EXISTS employee;
DROP TABLE IF EXISTS customer;
DROP TABLE IF EXISTS area;

-- 1. Area Entity
CREATE TABLE area (
    area_id INT AUTO_INCREMENT PRIMARY KEY,
    area_name VARCHAR(60) NOT NULL UNIQUE,
    substation VARCHAR(80) NOT NULL,
    city VARCHAR(60) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 2. Customer Entity (1NF-3NF normalized; BCNF)
CREATE TABLE customer (
    customer_id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(80) NOT NULL,
    address VARCHAR(200) NOT NULL,
    area_id INT NOT NULL,
    phone CHAR(10) NOT NULL UNIQUE,
    email VARCHAR(100) NOT NULL UNIQUE,
    category ENUM('DOMESTIC', 'COMMERCIAL', 'INDUSTRIAL') NOT NULL DEFAULT 'DOMESTIC',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_phone CHECK (phone REGEXP '^[6-9][0-9]{9}$'),
    CONSTRAINT fk_customer_area FOREIGN KEY (area_id) REFERENCES area(area_id)
        ON UPDATE CASCADE ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 3. Employee Entity
CREATE TABLE employee (
    emp_id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(80) NOT NULL,
    role ENUM('ADMIN', 'TECHNICIAN', 'METER_READER', 'BILLING_OFFICER') NOT NULL,
    area_id INT NULL,
    phone CHAR(10) UNIQUE,
    CONSTRAINT fk_employee_area FOREIGN KEY (area_id) REFERENCES area(area_id)
        ON UPDATE CASCADE ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 4. App User Authentication & RBAC Entity
CREATE TABLE app_user (
    user_id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL, -- PBKDF2/Werkzeug scrypt hash
    role ENUM('ADMIN', 'CUSTOMER', 'TECHNICIAN', 'BILLING_OFFICER') NOT NULL,
    customer_id INT NULL,
    emp_id INT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    CONSTRAINT fk_user_customer FOREIGN KEY (customer_id) REFERENCES customer(customer_id)
        ON UPDATE CASCADE ON DELETE CASCADE,
    CONSTRAINT fk_user_employee FOREIGN KEY (emp_id) REFERENCES employee(emp_id)
        ON UPDATE CASCADE ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 5. Smart Meter Entity
CREATE TABLE meter (
    meter_id INT AUTO_INCREMENT PRIMARY KEY,
    customer_id INT NOT NULL,
    meter_type ENUM('SINGLE_PHASE', 'THREE_PHASE') NOT NULL DEFAULT 'SINGLE_PHASE',
    install_date DATE NOT NULL,
    status ENUM('ACTIVE', 'FAULTY', 'DISCONNECTED') NOT NULL DEFAULT 'ACTIVE',
    location VARCHAR(120),
    CONSTRAINT fk_meter_customer FOREIGN KEY (customer_id) REFERENCES customer(customer_id)
        ON UPDATE CASCADE ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 6. Meter Reading Entity (Highest Volume Table, Interval = 1 Hour)
CREATE TABLE meter_reading (
    reading_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    meter_id INT NOT NULL,
    reading_ts DATETIME NOT NULL,
    units_consumed DECIMAL(8,3) NOT NULL, -- kWh in this interval
    voltage DECIMAL(6,2) NOT NULL,
    power_factor DECIMAL(3,2) NOT NULL DEFAULT 0.95,
    CONSTRAINT chk_units CHECK (units_consumed >= 0),
    CONSTRAINT chk_pf CHECK (power_factor BETWEEN 0 AND 1),
    CONSTRAINT fk_reading_meter FOREIGN KEY (meter_id) REFERENCES meter(meter_id)
        ON UPDATE CASCADE ON DELETE CASCADE,
    INDEX idx_reading_meter_ts (meter_id, reading_ts)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 7. Tariff Slabs Entity
CREATE TABLE tariff (
    tariff_id INT AUTO_INCREMENT PRIMARY KEY,
    category ENUM('DOMESTIC', 'COMMERCIAL', 'INDUSTRIAL') NOT NULL,
    slab_from DECIMAL(10,2) NOT NULL, -- exclusive lower bound
    slab_to DECIMAL(10,2) NOT NULL,   -- inclusive upper bound
    rate_per_unit DECIMAL(6,2) NOT NULL,
    fixed_charge DECIMAL(8,2) NOT NULL DEFAULT 0,
    UNIQUE KEY uq_tariff_category_slab (category, slab_from),
    CONSTRAINT chk_slab CHECK (slab_to > slab_from AND rate_per_unit >= 0)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 8. Monthly Bill Entity
CREATE TABLE bill (
    bill_id INT AUTO_INCREMENT PRIMARY KEY,
    customer_id INT NOT NULL,
    billing_period DATE NOT NULL, -- first day of billing month (e.g., 2026-09-01)
    units DECIMAL(10,2) NOT NULL,
    amount DECIMAL(12,2) NOT NULL,
    due_date DATE NOT NULL,
    status ENUM('UNPAID', 'PARTIAL', 'PAID', 'OVERDUE') NOT NULL DEFAULT 'UNPAID',
    UNIQUE KEY uq_customer_billing_period (customer_id, billing_period),
    CONSTRAINT fk_bill_customer FOREIGN KEY (customer_id) REFERENCES customer(customer_id)
        ON UPDATE CASCADE ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 9. Payment Transaction Entity
CREATE TABLE payment (
    payment_id INT AUTO_INCREMENT PRIMARY KEY,
    bill_id INT NOT NULL,
    amount DECIMAL(12,2) NOT NULL CHECK (amount > 0),
    mode ENUM('UPI', 'CARD', 'NETBANKING', 'CASH') NOT NULL,
    paid_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    transaction_ref VARCHAR(40) NOT NULL UNIQUE,
    CONSTRAINT fk_payment_bill FOREIGN KEY (bill_id) REFERENCES bill(bill_id)
        ON UPDATE CASCADE ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 10. Customer Complaint Entity
CREATE TABLE complaint (
    complaint_id INT AUTO_INCREMENT PRIMARY KEY,
    customer_id INT NOT NULL,
    type ENUM('BILLING', 'METER_FAULT', 'OUTAGE', 'OTHER') NOT NULL,
    description VARCHAR(300) NOT NULL,
    status ENUM('OPEN', 'ASSIGNED', 'RESOLVED') NOT NULL DEFAULT 'OPEN',
    assigned_to INT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_complaint_customer FOREIGN KEY (customer_id) REFERENCES customer(customer_id)
        ON UPDATE CASCADE ON DELETE CASCADE,
    CONSTRAINT fk_complaint_employee FOREIGN KEY (assigned_to) REFERENCES employee(emp_id)
        ON UPDATE CASCADE ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 11. Automated Meter Alert Entity
CREATE TABLE alert (
    alert_id INT AUTO_INCREMENT PRIMARY KEY,
    meter_id INT NOT NULL,
    type ENUM('HIGH_USAGE', 'TAMPER', 'OUTAGE', 'LOW_VOLTAGE') NOT NULL,
    message VARCHAR(200) NOT NULL,
    raised_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    is_resolved BOOLEAN NOT NULL DEFAULT FALSE,
    CONSTRAINT fk_alert_meter FOREIGN KEY (meter_id) REFERENCES meter(meter_id)
        ON UPDATE CASCADE ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 12. Security & Compliance Audit Log
CREATE TABLE audit_log (
    log_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    table_name VARCHAR(40) NOT NULL,
    record_id VARCHAR(40) NOT NULL,
    action VARCHAR(10) NOT NULL,
    old_value TEXT,
    new_value TEXT,
    changed_by VARCHAR(80) NOT NULL,
    changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 13. Partitioned Table Demonstration (Range Partitioning by Month)
-- Note: MySQL limitation dictates partitioned tables cannot have foreign keys
-- and the partition column must be part of the primary key.
CREATE TABLE meter_reading_part (
    reading_id BIGINT NOT NULL,
    meter_id INT NOT NULL,
    reading_ts DATETIME NOT NULL,
    units_consumed DECIMAL(8,3) NOT NULL,
    voltage DECIMAL(6,2) NOT NULL,
    power_factor DECIMAL(3,2) NOT NULL DEFAULT 0.95,
    PRIMARY KEY (reading_id, reading_ts),
    INDEX idx_part_meter_ts (meter_id, reading_ts)
) ENGINE=InnoDB
PARTITION BY RANGE (TO_DAYS(reading_ts)) (
    PARTITION p_2026_06 VALUES LESS THAN (TO_DAYS('2026-07-01')),
    PARTITION p_2026_07 VALUES LESS THAN (TO_DAYS('2026-08-01')),
    PARTITION p_2026_08 VALUES LESS THAN (TO_DAYS('2026-09-01')),
    PARTITION p_2026_09 VALUES LESS THAN (TO_DAYS('2026-10-01')),
    PARTITION p_2026_10 VALUES LESS THAN (TO_DAYS('2026-11-01')),
    PARTITION p_future VALUES LESS THAN MAXVALUE
);

