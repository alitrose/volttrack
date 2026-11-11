"""
Automated Database Migrator for VoltTrack
Reads DB credentials from .env and executes SQL files using mysql.exe.
"""

import os
import subprocess
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(BASE_DIR, ".env"))

MYSQL_BIN = os.getenv("MYSQL_BIN_PATH", r"C:\Program Files\MySQL\MySQL Server 8.0\bin").strip('"').strip("'")
MYSQL_EXE = os.path.join(MYSQL_BIN, "mysql.exe")
if not os.path.exists(MYSQL_EXE):
    MYSQL_EXE = r"C:\Program Files\MySQL\MySQL Server 8.0\bin\mysql.exe"

HOST = os.getenv("DB_HOST", "localhost")
PORT = os.getenv("DB_PORT", "3306")
USER = os.getenv("DB_USER", "root")
PASS = os.getenv("DB_PASS", "")

SQL_FILES = [
    "01_schema.sql",
    "02_seed_data.sql",
    "03_functions_procedures.sql",
    "04_triggers.sql",
    "05_views.sql",
    "06_roles_privileges.sql"
]

def run_sql_file(file_name):
    file_path = os.path.join(BASE_DIR, "database", file_name)
    print(f"[*] Executing {file_name}...")
    
    cmd = [
        MYSQL_EXE,
        f"--host={HOST}",
        f"--port={PORT}",
        f"--user={USER}",
        f"--password={PASS}",
        "--default-character-set=utf8mb4"
    ]
    
    with open(file_path, "r", encoding="utf-8") as f:
        res = subprocess.run(cmd, stdin=f, capture_output=True, text=True)
        if res.returncode != 0:
            print(f"[-] ERROR executing {file_name}:")
            print(res.stderr)
            return False
        else:
            if res.stdout.strip():
                print(res.stdout.strip())
            print(f"[+] Successfully executed {file_name}.")
            return True

def main():
    print(f"=== Applying VoltTrack Database Migrations ===")
    for sql_file in SQL_FILES:
        ok = run_sql_file(sql_file)
        if not ok:
            print(f"[-] Migration stopped at {sql_file}")
            sys.exit(1)
    print("[+] All SQL scripts executed successfully!")

if __name__ == "__main__":
    import sys
    main()
