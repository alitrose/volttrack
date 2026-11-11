from functools import wraps
from flask import Blueprint, request, jsonify
from flask_jwt_extended import (
    create_access_token,
    jwt_required,
    get_jwt,
    get_jwt_identity
)
from werkzeug.security import check_password_hash, generate_password_hash
from backend.db import query_one, execute_write

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")

def role_required(*roles):
    """
    Decorator to restrict route access by role.
    Roles: 'ADMIN', 'CUSTOMER', 'TECHNICIAN', 'BILLING_OFFICER'
    """
    def decorator(fn):
        @wraps(fn)
        @jwt_required()
        def wrapper(*args, **kwargs):
            claims = get_jwt()
            user_role = claims.get("role")
            if user_role not in roles:
                return jsonify({
                    "success": False,
                    "error": f"Forbidden: user role '{user_role}' lacks required permissions."
                }), 403
            return fn(*args, **kwargs)
        return wrapper
    return decorator

@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json() or {}
    username = data.get("username", "").strip()
    password = data.get("password", "")

    if not username or not password:
        return jsonify({"success": False, "error": "Username and password required"}), 400

    user = query_one("""
        SELECT u.user_id, u.username, u.password_hash, u.role, u.customer_id, u.emp_id, u.is_active,
               COALESCE(c.name, e.name) AS display_name,
               COALESCE(c.email, '') AS email
        FROM app_user u
        LEFT JOIN customer c ON c.customer_id = u.customer_id
        LEFT JOIN employee e ON e.emp_id = u.emp_id
        WHERE u.username = %s
    """, (username,))

    if not user:
        return jsonify({"success": False, "error": "Invalid username or password"}), 401

    if not user["is_active"]:
        return jsonify({"success": False, "error": "Account is disabled"}), 403

    if not check_password_hash(user["password_hash"], password):
        return jsonify({"success": False, "error": "Invalid username or password"}), 401

    additional_claims = {
        "role": user["role"],
        "user_id": user["user_id"],
        "customer_id": user["customer_id"],
        "emp_id": user["emp_id"],
        "display_name": user["display_name"]
    }

    token = create_access_token(identity=username, additional_claims=additional_claims)

    return jsonify({
        "success": True,
        "data": {
            "token": token,
            "user": {
                "user_id": user["user_id"],
                "username": user["username"],
                "role": user["role"],
                "customer_id": user["customer_id"],
                "emp_id": user["emp_id"],
                "display_name": user["display_name"],
                "email": user["email"]
            }
        }
    })

@auth_bp.route("/me", methods=["GET"])
@jwt_required()
def me():
    claims = get_jwt()
    username = get_jwt_identity()
    return jsonify({
        "success": True,
        "data": {
            "username": username,
            "role": claims.get("role"),
            "customer_id": claims.get("customer_id"),
            "emp_id": claims.get("emp_id"),
            "display_name": claims.get("display_name")
        }
    })
