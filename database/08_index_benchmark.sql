-- ==============================================================================
-- VoltTrack: Smart Meter Data Management System
-- File: 08_index_benchmark.sql
-- Description: Index performance benchmark script (EXPLAIN & EXPLAIN ANALYZE)
--              comparing query execution plan with and without composite index.
-- Target DBMS: MySQL 8.0
-- ==============================================================================

USE smartmeter;

-- Benchmark Query:
-- Aggregates 1 month of hourly consumption for a specific meter out of 100k+ records.

-- ------------------------------------------------------------------------------
-- SCENARIO A: Benchmark WITH Composite Index (idx_reading_meter_ts)
-- ------------------------------------------------------------------------------
EXPLAIN
SELECT SUM(units_consumed) 
FROM meter_reading 
WHERE meter_id = 1 
  AND reading_ts BETWEEN '2026-08-01 00:00:00' AND '2026-08-31 23:59:59';

EXPLAIN ANALYZE
SELECT SUM(units_consumed) 
FROM meter_reading 
WHERE meter_id = 1 
  AND reading_ts BETWEEN '2026-08-01 00:00:00' AND '2026-08-31 23:59:59';

-- Observation A:
-- Type: range
-- Possible Keys: idx_reading_meter_ts
-- Key: idx_reading_meter_ts
-- Rows Examined: ~744 rows (31 days * 24 hours)
-- Execution Time: < 1.0 ms

-- ------------------------------------------------------------------------------
-- SCENARIO B: Benchmark WITHOUT Composite Index (Full Table Scan Simulation)
-- ------------------------------------------------------------------------------
-- In MySQL, dropping an index required by a FOREIGN KEY is blocked.
-- Therefore, we benchmark against reading_benchmark table (identical copy without the index).

DROP TABLE IF EXISTS reading_benchmark;
CREATE TABLE reading_benchmark LIKE meter_reading;
ALTER TABLE reading_benchmark DROP INDEX idx_reading_meter_ts;

-- Populate benchmark table with the same volume
INSERT INTO reading_benchmark SELECT * FROM meter_reading;

EXPLAIN
SELECT SUM(units_consumed) 
FROM reading_benchmark 
WHERE meter_id = 1 
  AND reading_ts BETWEEN '2026-08-01 00:00:00' AND '2026-08-31 23:59:59';

EXPLAIN ANALYZE
SELECT SUM(units_consumed) 
FROM reading_benchmark 
WHERE meter_id = 1 
  AND reading_ts BETWEEN '2026-08-01 00:00:00' AND '2026-08-31 23:59:59';

-- Observation B:
-- Type: ALL (Full Table Scan)
-- Possible Keys: NULL
-- Key: NULL
-- Rows Examined: 100,000+ rows
-- Execution Time: 40x - 100x slower

-- Clean up temporary benchmark table
DROP TABLE IF EXISTS reading_benchmark;

