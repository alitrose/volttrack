from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt
from backend.auth import role_required
from backend.db import query_all, query_one, execute_write

meters_bp = Blueprint("meters", __name__, url_prefix="/api/meters")

@meters_bp.route("", methods=["GET"])
@jwt_required()
def list_meters():
    claims = get_jwt()
    role = claims.get("role")
    token_cid = claims.get("customer_id")

    sql = """
        SELECT m.meter_id, m.customer_id, m.meter_type, m.install_date, m.status, m.location,
               c.name AS customer_name, c.phone, c.category,
               a.area_name, a.substation
        FROM meter m
        JOIN customer c ON c.customer_id = m.customer_id
        JOIN area a ON a.area_id = c.area_id
        WHERE 1=1
    """
    params = []

    # If customer, only return own meters
    if role == "CUSTOMER":
        sql += " AND m.customer_id = %s"
        params.append(token_cid)
    else:
        status = request.args.get("status", "").strip()
        area_id = request.args.get("area_id", "").strip()
        search = request.args.get("search", "").strip()

        if status:
            sql += " AND m.status = %s"
            params.append(status)
        if area_id:
            sql += " AND a.area_id = %s"
            params.append(area_id)
        if search:
            sql += " AND (c.name LIKE %s OR m.location LIKE %s OR m.meter_id = %s)"
            params.extend([f"%{search}%", f"%{search}%", search if search.isdigit() else 0])

    sql += " ORDER BY m.meter_id ASC"
    rows = query_all(sql, params)
    return jsonify({"success": True, "data": rows})

@meters_bp.route("/<int:meter_id>", methods=["GET"])
@jwt_required()
def get_meter(meter_id):
    claims = get_jwt()
    role = claims.get("role")
    token_cid = claims.get("customer_id")

    meter = query_one("""
        SELECT m.*, c.name AS customer_name, c.category, a.area_name
        FROM meter m
        JOIN customer c ON c.customer_id = m.customer_id
        JOIN area a ON a.area_id = c.area_id
        WHERE m.meter_id = %s
    """, (meter_id,))

    if not meter:
        return jsonify({"success": False, "error": "Meter not found"}), 404

    if role == "CUSTOMER" and meter["customer_id"] != token_cid:
        return jsonify({"success": False, "error": "Access denied"}), 403

    return jsonify({"success": True, "data": meter})

@meters_bp.route("", methods=["POST"])
@role_required("ADMIN", "TECHNICIAN")
def install_meter():
    data = request.get_json() or {}
    customer_id = data.get("customer_id")
    meter_type = data.get("meter_type", "SINGLE_PHASE")
    install_date = data.get("install_date")
    status = data.get("status", "ACTIVE")
    location = data.get("location", "").strip()

    if not customer_id or not install_date:
        return jsonify({"success": False, "error": "Customer ID and Install Date are required"}), 400

    try:
        res = execute_write("""
            INSERT INTO meter (customer_id, meter_type, install_date, status, location)
            VALUES (%s, %s, %s, %s, %s)
        """, (customer_id, meter_type, install_date, status, location))

        return jsonify({
            "success": True,
            "data": {
                "meter_id": res["last_id"],
                "customer_id": customer_id,
                "status": status
            }
        }), 201
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400

@meters_bp.route("/<int:meter_id>/status", methods=["PATCH"])
@role_required("ADMIN", "TECHNICIAN")
def update_meter_status(meter_id):
    data = request.get_json() or {}
    new_status = data.get("status")
    if new_status not in ("ACTIVE", "FAULTY", "DISCONNECTED"):
        return jsonify({"success": False, "error": "Invalid meter status"}), 400

    try:
        execute_write("UPDATE meter SET status = %s WHERE meter_id = %s", (new_status, meter_id))
        return jsonify({"success": True, "data": {"meter_id": meter_id, "status": new_status}})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400
