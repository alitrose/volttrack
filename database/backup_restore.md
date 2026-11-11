# VoltTrack Database Backup, Disaster Recovery & Concurrency Guide

This document describes the backup, point-in-time recovery (PITR), and disaster recovery procedures for the **VoltTrack Smart Meter Data Management System** running on **MySQL 8.0**.

---

## 1. Full Logical Backup (`mysqldump`)

To create an ACID-consistent snapshot including stored procedures, functions, triggers, and events without locking read/write tables:

```powershell
# In PowerShell (Windows)
$MYSQL_BIN = "C:\Program Files\MySQL\MySQL Server 8.0\bin"
$TIMESTAMP = (Get-Date).ToString("yyyyMMdd_HHmmss")
$BACKUP_FILE = "smartmeter_backup_$TIMESTAMP.sql"

& "$MYSQL_BIN\mysqldump.exe" -u root -p `
    --single-transaction `
    --routines `
    --triggers `
    --events `
    --hex-blob `
    --default-character-set=utf8mb4 `
    smartmeter > $BACKUP_FILE
```

### Explanation of Flags:
- `--single-transaction`: Uses InnoDB snapshot isolation (`REPEATABLE READ`) to take a non-blocking backup while readings continue to stream.
- `--routines`: Exports functions (`calculate_slab_amount`) and stored procedures (`generate_bill`, `generate_all_bills`, `process_payment`).
- `--triggers`: Exports triggers (`trg_reading_alerts`, `trg_payment_status`, `trg_tariff_audit`, `trg_bill_no_delete`).
- `--events`: Exports MySQL scheduled events (such as daily overdue marking).

---

## 2. Disaster Recovery Simulation

### Step 1: Simulate Total Database Loss
```powershell
& "$MYSQL_BIN\mysql.exe" -u root -p -e "DROP DATABASE smartmeter;"
```

### Step 2: Recreate Empty Schema
```powershell
& "$MYSQL_BIN\mysql.exe" -u root -p -e "CREATE DATABASE smartmeter CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
```

### Step 3: Restore Database Snapshot
```powershell
Get-Content $BACKUP_FILE | & "$MYSQL_BIN\mysql.exe" -u root -p smartmeter
```

### Step 4: Verify Integrity
```powershell
& "$MYSQL_BIN\mysql.exe" -u root -p -e "USE smartmeter; SHOW TABLES; SELECT COUNT(*) FROM customer; SELECT COUNT(*) FROM meter_reading;"
```

---

## 3. Point-In-Time Recovery (PITR) with Binary Logs

1. Ensure binary logging is active in `my.ini`:
   ```ini
   [mysqld]
   log-bin=mysql-bin
   binlog_format=ROW
   expire_logs_days=7
   ```
2. When restoring after a crash:
   - Restore the latest full backup snapshot first.
   - Replay subsequent transaction binary logs up to the exact target timestamp using `mysqlbinlog`:
     ```powershell
     & "$MYSQL_BIN\mysqlbinlog.exe" --start-datetime="2026-10-27 10:00:00" --stop-datetime="2026-10-27 14:15:00" "C:\ProgramData\MySQL\MySQL Server 8.0\Data\binlog.000001" | & "$MYSQL_BIN\mysql.exe" -u root -p smartmeter
     ```

---

## 4. Concurrency Control & Row Locking

VoltTrack guarantees transactional consistency and prevents race conditions under high concurrent workloads:

- **Row-Level Locking**: In `process_payment`, `SELECT ... FOR UPDATE` acquires an exclusive X-lock on the specific `bill` row being paid. If two users attempt to pay the exact same bill simultaneously, the second transaction blocks until the first completes.
- **Savepoints & Rollback**: A `SAVEPOINT before_pay` is established. If an overpayment is detected, the transaction rolls back specifically to the savepoint and aborts safely with `SIGNAL SQLSTATE '45000'`.
- **Isolation Level**: MySQL defaults to `REPEATABLE READ`, preventing non-repeatable reads and dirty reads.

