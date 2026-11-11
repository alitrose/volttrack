from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt
from werkzeug.security import generate_password_hash
from backend.auth import role_required
from backend.db import query_all, query_one, execute_write

customers_bp = Blueprint("customers", __name__, url_prefix="/api/customers")

@customers_bp.route("", methods=["GET"])
@role_required("ADMIN", "BILLING_OFFICER")
def list_customers():
    search = request.args.get("search", "").strip()
    category = request.args.get("category", "").strip()
    area_id = request.args.get("area_id", "").strip()

    sql = """
        SELECT c.customer_id, c.name, c.email, c.phone, c.category, c.address, c.created_at,
               a.area_id, a.area_name, a.city,
               COUNT(m.meter_id) AS meter_count
        FROM customer c
        JOIN area a ON a.area_id = c.area_id
        LEFT JOIN meter m ON m.customer_id = c.customer_id
        WHERE 1=1
    """
    params = []
    if search:
        sql += " AND (c.name LIKE %s OR c.email LIKE %s OR c.phone LIKE %s)"
        params.extend([f"%{search}%", f"%{search}%", f"%{search}%"])
    if category:
        sql += " AND c.category = %s"
        params.append(category)
    if area_id:
        sql += " AND c.area_id = %s"
        params.append(area_id)

    sql += " GROUP BY c.customer_id, a.area_id, a.area_name, a.city ORDER BY c.customer_id ASC"
    rows = query_all(sql, params)
    return jsonify({"success": True, "data": rows})

@customers_bp.route("/<int:customer_id>", methods=["GET"])
@jwt_required()
def get_customer(customer_id):
    claims = get_jwt()
    role = claims.get("role")
    token_cid = claims.get("customer_id")

    # Enforce customer isolation: customers can only view their own record
    if role == "CUSTOMER" and token_cid != customer_id:
        return jsonify({"success": False, "error": "Access denied: cannot access another customer's record"}), 403

    cust = query_one("""
        SELECT c.*, a.area_name, a.substation, a.city
        FROM customer c
        JOIN area a ON a.area_id = c.area_id
        WHERE c.customer_id = %s
    """, (customer_id,))

    if not cust:
        return jsonify({"success": False, "error": "Customer not found"}), 404

    meters = query_all("SELECT * FROM meter WHERE customer_id = %s", (customer_id,))
    recent_bills = query_all("""
        SELECT * FROM v_customer_bill_summary
        WHERE customer_id = %s
        ORDER BY billing_period DESC LIMIT 6
    """, (customer_id,))

    cust["meters"] = meters
    cust["recent_bills"] = recent_bills
    return jsonify({"success": True, "data": cust})

@customers_bp.route("", methods=["POST"])
@role_required("ADMIN")
def create_customer():
    data = request.get_json() or {}
    name = data.get("name", "").strip()
    address = data.get("address", "").strip()
    area_id = data.get("area_id")
    phone = data.get("phone", "").strip()
    email = data.get("email", "").strip()
    category = data.get("category", "DOMESTIC")

    if not all([name, address, area_id, phone, email]):
        return jsonify({"success": False, "error": "All fields are required"}), 400

    try:
        res = execute_write("""
            INSERT INTO customer (name, address, area_id, phone, email, category)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (name, address, area_id, phone, email, category))
        new_cid = res["last_id"]

        # Automatically create application user login for the customer
        username = f"customer{new_cid}"
        pw_hash = generate_password_hash("Volt@123")
        execute_write("""
            INSERT INTO app_user (username, password_hash, role, customer_id, is_active)
            VALUES (%s, %s, 'CUSTOMER', %s, TRUE)
        """, (username, pw_hash, new_cid))

        return jsonify({
            "success": True,
            "data": {
                "customer_id": new_cid,
                "username": username,
                "default_password": "Volt@123"
            }
        }), 201
    except Exception as e:
        err_msg = str(e)
        if "chk_phone" in err_msg:
            return jsonify({"success": False, "error": "Invalid Indian mobile number: must start with 6-9 and have 10 digits."}), 400
        if "Duplicate entry" in err_msg:
            return jsonify({"success": False, "error": "Phone number or email already registered."}), 409
        return jsonify({"success": False, "error": err_msg}), 400
