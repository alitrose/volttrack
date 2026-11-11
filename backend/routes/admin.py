import os
import shutil
import subprocess
from datetime import datetime
from flask import Blueprint, request, jsonify
from backend.auth import role_required
from backend.config import Config
from backend.db import query_all, query_one

admin_bp = Blueprint("admin", __name__, url_prefix="/api")

@admin_bp.route("/audit", methods=["GET"])
@role_required("ADMIN")
def list_audit_logs():
    table_name = request.args.get("table")
    limit = int(request.args.get("limit", 100))

    sql = "SELECT * FROM audit_log WHERE 1=1"
    params = []
    if table_name:
        sql += " AND table_name = %s"
        params.append(table_name)

    sql += " ORDER BY log_id DESC LIMIT %s"
    params.append(limit)

    rows = query_all(sql, params)
    return jsonify({"success": True, "data": rows})

@admin_bp.route("/areas", methods=["GET"])
def list_areas():
    rows = query_all("SELECT * FROM area ORDER BY area_name ASC")
    return jsonify({"success": True, "data": rows})

@admin_bp.route("/admin/backup", methods=["POST"])
@role_required("ADMIN")
def trigger_backup():
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    backup_dir = os.path.join(base_dir, "backups")
    os.makedirs(backup_dir, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = os.path.join(backup_dir, f"smartmeter_backup_{timestamp}.sql")

    mysqldump_exe = shutil.which("mysqldump")
    if not mysqldump_exe:
        candidate = os.path.join(Config.MYSQL_BIN_PATH, "mysqldump.exe")
        if os.path.exists(candidate):
            mysqldump_exe = candidate
        else:
            mysqldump_exe = r"C:\Program Files\MySQL\MySQL Server 8.0\bin\mysqldump.exe"

    if not os.path.exists(mysqldump_exe):
        return jsonify({
            "success": False,
            "error": "mysqldump client binary is not available in this runtime environment."
        }), 501

    cmd = [
        mysqldump_exe,
        f"--host={Config.DB_HOST}",
        f"--port={Config.DB_PORT}",
        f"--user={Config.DB_USER}",
        f"--password={Config.DB_PASS}",
        "--single-transaction",
        "--routines",
        "--triggers",
        "--events",
        "--hex-blob",
        "--default-character-set=utf8mb4",
        Config.DB_NAME
    ]

    try:
        with open(backup_file, "w", encoding="utf-8") as f:
            res = subprocess.run(cmd, stdout=f, stderr=subprocess.PIPE, text=True)
            if res.returncode != 0:
                return jsonify({"success": False, "error": f"mysqldump failed: {res.stderr}"}), 500

        file_size = os.path.getsize(backup_file)
        return jsonify({
            "success": True,
            "data": {
                "backup_file": os.path.basename(backup_file),
                "full_path": backup_file,
                "file_size_kb": round(file_size / 1024.0, 2),
                "timestamp": timestamp,
                "message": "ACID snapshot backup created successfully with routines, triggers, and events."
            }
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
