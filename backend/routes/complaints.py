from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt
from backend.auth import role_required
from backend.db import query_all, query_one, execute_write

complaints_bp = Blueprint("complaints", __name__, url_prefix="/api/complaints")

@complaints_bp.route("", methods=["GET"])
@jwt_required()
def list_complaints():
    claims = get_jwt()
    role = claims.get("role")
    token_cid = claims.get("customer_id")
    token_eid = claims.get("emp_id")

    sql = """
        SELECT comp.*, c.name AS customer_name, c.phone AS customer_phone,
               a.area_name,
               COALESCE(e.name, 'Unassigned') AS technician_name
        FROM complaint comp
        JOIN customer c ON c.customer_id = comp.customer_id
        JOIN area a ON a.area_id = c.area_id
        LEFT JOIN employee e ON e.emp_id = comp.assigned_to
        WHERE 1=1
    """
    params = []

    if role == "CUSTOMER":
        sql += " AND comp.customer_id = %s"
        params.append(token_cid)
    elif role == "TECHNICIAN":
        status = request.args.get("status")
        if status:
            sql += " AND comp.status = %s"
            params.append(status)
        else:
            # Technician sees tickets assigned to them or unassigned
            sql += " AND (comp.assigned_to = %s OR comp.assigned_to IS NULL)"
            params.append(token_eid)
    else: # ADMIN or BILLING
        status = request.args.get("status")
        if status:
            sql += " AND comp.status = %s"
            params.append(status)

    sql += " ORDER BY comp.created_at DESC"
    rows = query_all(sql, params)
    return jsonify({"success": True, "data": rows})

@complaints_bp.route("", methods=["POST"])
@jwt_required()
def raise_complaint():
    claims = get_jwt()
    role = claims.get("role")
    token_cid = claims.get("customer_id")

    data = request.get_json() or {}
    ctype = data.get("type", "BILLING")
    description = data.get("description", "").strip()

    if not description:
        return jsonify({"success": False, "error": "Complaint description is required"}), 400

    if ctype not in ("BILLING", "METER_FAULT", "OUTAGE", "OTHER"):
        return jsonify({"success": False, "error": "Invalid complaint type"}), 400

    # Determine customer_id
    if role == "CUSTOMER":
        cid = token_cid
    else:
        cid = data.get("customer_id")
        if not cid:
            return jsonify({"success": False, "error": "customer_id is required"}), 400

    try:
        res = execute_write("""
            INSERT INTO complaint (customer_id, type, description, status)
            VALUES (%s, %s, %s, 'OPEN')
        """, (cid, ctype, description))

        return jsonify({
            "success": True,
            "data": {
                "complaint_id": res["last_id"],
                "customer_id": cid,
                "type": ctype,
                "status": "OPEN",
                "message": "Complaint lodged successfully."
            }
        }), 201
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400

@complaints_bp.route("/<int:complaint_id>", methods=["PATCH"])
@role_required("ADMIN", "TECHNICIAN")
def update_complaint(complaint_id):
    claims = get_jwt()
    data = request.get_json() or {}
    status = data.get("status")
    assigned_to = data.get("assigned_to")

    updates = []
    params = []
    if status:
        if status not in ("OPEN", "ASSIGNED", "RESOLVED"):
            return jsonify({"success": False, "error": "Invalid complaint status"}), 400
        updates.append("status = %s")
        params.append(status)
    if assigned_to is not None:
        updates.append("assigned_to = %s")
        params.append(assigned_to if assigned_to != "" else None)

    if not updates:
        return jsonify({"success": False, "error": "No updates specified"}), 400

    params.append(complaint_id)
    try:
        execute_write(f"UPDATE complaint SET {', '.join(updates)} WHERE complaint_id = %s", params)
        return jsonify({"success": True, "data": {"complaint_id": complaint_id, "status": status, "assigned_to": assigned_to}})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400
