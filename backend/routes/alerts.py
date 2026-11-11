from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt
from backend.auth import role_required
from backend.db import query_all, query_one, execute_write

alerts_bp = Blueprint("alerts", __name__, url_prefix="/api/alerts")

@alerts_bp.route("", methods=["GET"])
@jwt_required()
def list_alerts():
    claims = get_jwt()
    role = claims.get("role")
    token_cid = claims.get("customer_id")

    resolved = request.args.get("resolved")
    alert_type = request.args.get("type")

    sql = """
        SELECT al.alert_id, al.meter_id, al.type, al.message, al.raised_at, al.is_resolved,
               m.customer_id, m.location,
               c.name AS customer_name, c.phone AS customer_phone,
               a.area_name
        FROM alert al
        JOIN meter m ON m.meter_id = al.meter_id
        JOIN customer c ON c.customer_id = m.customer_id
        JOIN area a ON a.area_id = c.area_id
        WHERE 1=1
    """
    params = []

    if role == "CUSTOMER":
        sql += " AND m.customer_id = %s"
        params.append(token_cid)
    else:
        if resolved is not None:
            sql += " AND al.is_resolved = %s"
            params.append(resolved.lower() in ("true", "1"))
        if alert_type:
            sql += " AND al.type = %s"
            params.append(alert_type)

    sql += " ORDER BY al.raised_at DESC LIMIT 100"
    rows = query_all(sql, params)
    return jsonify({"success": True, "data": rows})

@alerts_bp.route("/<int:alert_id>/resolve", methods=["PATCH"])
@role_required("ADMIN", "TECHNICIAN")
def resolve_alert(alert_id):
    try:
        execute_write("UPDATE alert SET is_resolved = TRUE WHERE alert_id = %s", (alert_id,))
        return jsonify({"success": True, "data": {"alert_id": alert_id, "is_resolved": True}})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400
