"""
Cross-platform, idempotent Pure-Python database initializer for VoltTrack.
Used during cloud deployments (e.g., Railway preDeployCommand) where mysql.exe
or the mysql CLI binary may not be present in the application runtime image.
"""

import os
import re
import sys
import time
import pymysql

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from backend.config import Config
from simulator.meter_simulator import run_bulk_simulation

DB_DIR = os.path.dirname(os.path.abspath(__file__))

PRE_BULK_SQL_FILES = [
    "01_schema.sql",
    "02_seed_data.sql",
    "03_functions_procedures.sql",
]

POST_BULK_SQL_FILES = [
    "04_triggers.sql",
    "05_views.sql",
]

OPTIONAL_SQL_FILES = [
    "06_roles_privileges.sql",
]

_DELIMITER_RE = re.compile(r"[ \t]*DELIMITER[ \t]+(\S+)[ \t]*(?:\n|$)", re.IGNORECASE)


def split_sql_statements(sql_text: str) -> list[str]:
    """
    Splits a MySQL script into executable statements, respecting dynamic
    DELIMITER directives, quoted literals ('...', "...", `...`), and SQL comments.
    """
    text = sql_text.replace("\r\n", "\n").replace("\r", "\n")
    n = len(text)
    i = 0
    delimiter = ";"
    buf: list[str] = []
    has_code = False
    statements: list[str] = []

    in_quote: str | None = None
    in_line_comment = False
    in_block_comment = False

    while i < n:
        # Handle active single-line comment
        if in_line_comment:
            if text[i] == "\n":
                in_line_comment = False
                if has_code:
                    buf.append("\n")
            i += 1
            continue

        # Handle active block comment
        if in_block_comment:
            if text[i:i + 2] == "*/":
                in_block_comment = False
                if has_code:
                    buf.append("*/")
                i += 2
            else:
                if has_code:
                    buf.append(text[i])
                i += 1
            continue

        # Handle active quoted string or identifier
        if in_quote is not None:
            ch = text[i]
            buf.append(ch)
            if in_quote in ("'", '"') and ch == "\\" and i + 1 < n:
                buf.append(text[i + 1])
                i += 2
                continue
            if ch == in_quote:
                if i + 1 < n and text[i + 1] == in_quote:
                    buf.append(text[i + 1])
                    i += 2
                    continue
                in_quote = None
            i += 1
            continue

        # Detect client-side DELIMITER directives at start of line
        if i == 0 or text[i - 1] == "\n":
            m = _DELIMITER_RE.match(text, i)
            if m:
                if has_code:
                    stmt = "".join(buf).strip()
                    if stmt:
                        statements.append(stmt)
                buf.clear()
                has_code = False
                delimiter = m.group(1)
                i = m.end()
                continue

        # Start of line comment (-- or #)
        if text[i:i + 2] == "--" and (i + 2 == n or text[i + 2] in (" ", "\t", "\n")):
            in_line_comment = True
            i += 2
            continue
        if text[i] == "#":
            in_line_comment = True
            i += 1
            continue

        # Start of block comment /* ... */
        if text[i:i + 2] == "/*":
            in_block_comment = True
            if has_code:
                buf.append("/*")
            i += 2
            continue

        # Delimiter match outside quotes and comments
        if text.startswith(delimiter, i):
            if has_code:
                stmt = "".join(buf).strip()
                if stmt:
                    statements.append(stmt)
            buf.clear()
            has_code = False
            i += len(delimiter)
            continue

        ch = text[i]
        if ch in ("'", '"', "`"):
            in_quote = ch
            has_code = True
            buf.append(ch)
            i += 1
            continue

        if not ch.isspace():
            has_code = True
            buf.append(ch)
        elif has_code:
            buf.append(ch)

        i += 1

    if has_code:
        stmt = "".join(buf).strip()
        if stmt:
            statements.append(stmt)

    return statements


def connect_with_retry(max_attempts: int = 15, delay_seconds: float = 2.0):
    last_err = None
    for attempt in range(1, max_attempts + 1):
        try:
            return pymysql.connect(
                host=Config.DB_HOST,
                port=Config.DB_PORT,
                user=Config.DB_USER,
                password=Config.DB_PASS,
                charset="utf8mb4",
                autocommit=True,
                cursorclass=pymysql.cursors.DictCursor,
                connect_timeout=10,
            )
        except Exception as exc:
            last_err = exc
            print(f"[*] Waiting for MySQL ({attempt}/{max_attempts}): {exc}")
            time.sleep(delay_seconds)
    raise RuntimeError(f"Unable to connect to MySQL at {Config.DB_HOST}:{Config.DB_PORT}: {last_err}")


def execute_sql_file(conn, filename: str):
    path = os.path.join(DB_DIR, filename)
    print(f"[*] Executing {filename}...")
    with open(path, "r", encoding="utf-8") as f:
        sql_text = f.read()

    statements = split_sql_statements(sql_text)
    with conn.cursor() as cur:
        for idx, stmt in enumerate(statements, start=1):
            try:
                cur.execute(stmt)
                while cur.nextset():
                    pass
            except Exception as exc:
                preview = stmt[:160].replace("\n", " ")
                raise RuntimeError(f"{filename} statement #{idx} failed ({preview}...): {exc}") from exc
    print(f"[+] Completed {filename} ({len(statements)} statements).")


def check_db_state(conn) -> dict:
    db_name = Config.DB_NAME
    with conn.cursor() as cur:
        cur.execute(
            "SELECT SCHEMA_NAME FROM information_schema.SCHEMATA WHERE SCHEMA_NAME = %s",
            (db_name,),
        )
        schema_exists = cur.fetchone() is not None
        if not schema_exists:
            return {"schema_exists": False, "customer_count": 0, "reading_count": 0, "has_routines": False}

        cur.execute(
            "SELECT TABLE_NAME FROM information_schema.TABLES WHERE TABLE_SCHEMA = %s",
            (db_name,),
        )
        tables = {row["TABLE_NAME"] for row in cur.fetchall()}

        customer_count = 0
        if "customer" in tables:
            cur.execute(f"SELECT COUNT(*) AS cnt FROM `{db_name}`.`customer`")
            customer_count = int(cur.fetchone()["cnt"])

        reading_count = 0
        if "meter_reading" in tables:
            cur.execute(f"SELECT COUNT(*) AS cnt FROM `{db_name}`.`meter_reading`")
            reading_count = int(cur.fetchone()["cnt"])

        cur.execute(
            "SELECT COUNT(*) AS cnt FROM information_schema.ROUTINES WHERE ROUTINE_SCHEMA = %s AND ROUTINE_NAME = 'process_payment'",
            (db_name,),
        )
        has_routines = int(cur.fetchone()["cnt"]) > 0

        cur.execute(
            "SELECT COUNT(*) AS cnt FROM information_schema.VIEWS WHERE TABLE_SCHEMA = %s AND TABLE_NAME = 'v_customer_bill_summary'",
            (db_name,),
        )
        has_views = int(cur.fetchone()["cnt"]) > 0

        return {
            "schema_exists": True,
            "customer_count": customer_count,
            "reading_count": reading_count,
            "has_routines": has_routines,
            "has_views": has_views,
        }


def init_cloud_database():
    print(f"=== VoltTrack Cloud DB Initializer ({Config.DB_HOST}:{Config.DB_PORT}/{Config.DB_NAME}) ===")
    conn = connect_with_retry()
    try:
        state = check_db_state(conn)
        print(f"[*] Current database state: {state}")

        needs_full_init = not (
            state["schema_exists"]
            and state["customer_count"] > 0
            and state["has_routines"]
            and state.get("has_views", False)
        )

        if needs_full_init:
            print("[*] Provisioning schema, seed data, routines, telemetry, triggers, and views...")
            for sql_file in PRE_BULK_SQL_FILES:
                if sql_file == "03_functions_procedures.sql":
                    try:
                        with conn.cursor() as cur:
                            cur.execute("SET GLOBAL log_bin_trust_function_creators = 1")
                    except Exception:
                        pass
                execute_sql_file(conn, sql_file)

            print("[*] Generating initial 4-month hourly telemetry dataset (35 meters ~102k readings)...")
            run_bulk_simulation(months=4, target_meters=35)

            for sql_file in POST_BULK_SQL_FILES:
                execute_sql_file(conn, sql_file)

            for sql_file in OPTIONAL_SQL_FILES:
                try:
                    execute_sql_file(conn, sql_file)
                except Exception as exc:
                    print(f"[!] Optional RBAC role script warning ({sql_file}): {exc}")

            print("[+] VoltTrack database initialization complete!")
        elif state["reading_count"] == 0:
            print("[*] Core schema exists but meter_reading is empty. Running bulk telemetry seed...")
            run_bulk_simulation(months=4, target_meters=35)
        else:
            print("[+] Database already initialized and populated. Skipping destructive reset.")
    finally:
        conn.close()


if __name__ == "__main__":
    init_cloud_database()
