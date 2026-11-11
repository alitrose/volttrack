from flask import Blueprint, request, jsonify
from backend.auth import role_required
from backend.db import query_all, query_one, execute_write

tariffs_bp = Blueprint("tariffs", __name__, url_prefix="/api/tariffs")

@tariffs_bp.route("", methods=["GET"])
def list_tariffs():
    rows = query_all("SELECT * FROM tariff ORDER BY category, slab_from ASC")
    return jsonify({"success": True, "data": rows})

@tariffs_bp.route("/<int:tariff_id>", methods=["PUT"])
@role_required("ADMIN")
def update_tariff(tariff_id):
    data = request.get_json() or {}
    rate = data.get("rate_per_unit")
    fixed = data.get("fixed_charge")

    if rate is None or fixed is None:
        return jsonify({"success": False, "error": "rate_per_unit and fixed_charge are required"}), 400

    try:
        rate = float(rate)
        fixed = float(fixed)
        if rate < 0 or fixed < 0:
            return jsonify({"success": False, "error": "Rates and charges must be non-negative"}), 400

        execute_write("""
            UPDATE tariff 
            SET rate_per_unit = %s, fixed_charge = %s
            WHERE tariff_id = %s
        """, (rate, fixed, tariff_id))

        # Retrieve the updated row and the audit log entry automatically logged by trg_tariff_audit
        updated = query_one("SELECT * FROM tariff WHERE tariff_id = %s", (tariff_id,))
        audit = query_one("SELECT * FROM audit_log WHERE table_name = 'tariff' AND record_id = %s ORDER BY log_id DESC LIMIT 1", (str(tariff_id),))

        return jsonify({
            "success": True,
            "data": {
                "tariff": updated,
                "audit_log": audit,
                "message": "Tariff slab updated successfully and change recorded in audit log."
            }
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400
