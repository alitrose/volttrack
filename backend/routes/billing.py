from flask import Blueprint, request, jsonify, send_file
from flask_jwt_extended import jwt_required, get_jwt
from backend.auth import role_required
from backend.db import query_all, query_one, call_proc
from backend.services.pdf_bill import generate_invoice_pdf

billing_bp = Blueprint("billing", __name__, url_prefix="/api")

@billing_bp.route("/billing/generate", methods=["POST"])
@role_required("ADMIN", "BILLING_OFFICER")
def batch_generate_bills():
    data = request.get_json() or {}
    month = data.get("month") # Expected format: YYYY-MM-01 or YYYY-MM
    if not month:
        return jsonify({"success": False, "error": "Month parameter required (e.g. '2026-09-01')"}), 400

    if len(month) == 7: # YYYY-MM -> YYYY-MM-01
        month += "-01"

    try:
        call_proc("generate_all_bills", (month,))
        
        # Count total bills generated for that month
        cnt = query_one("SELECT COUNT(*) AS total FROM bill WHERE billing_period = %s", (month,))
        return jsonify({
            "success": True,
            "data": {
                "billing_period": month,
                "total_bills": cnt["total"],
                "message": f"Successfully executed batch billing procedure for {month}."
            }
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400

@billing_bp.route("/bills", methods=["GET"])
@role_required("ADMIN", "BILLING_OFFICER")
def list_bills():
    status = request.args.get("status", "").strip()
    area_id = request.args.get("area_id", "").strip()
    month = request.args.get("month", "").strip()
    search = request.args.get("search", "").strip()

    sql = """
        SELECT v.*, a.area_id, a.area_name
        FROM v_customer_bill_summary v
        JOIN customer c ON c.customer_id = v.customer_id
        JOIN area a ON a.area_id = c.area_id
        WHERE 1=1
    """
    params = []
    if status:
        sql += " AND v.status = %s"
        params.append(status)
    if area_id:
        sql += " AND a.area_id = %s"
        params.append(area_id)
    if month:
        if len(month) == 7:
            sql += " AND DATE_FORMAT(v.billing_period, '%%Y-%%m') = %s"
        else:
            sql += " AND v.billing_period = %s"
        params.append(month)
    if search:
        sql += " AND (v.customer_name LIKE %s OR v.customer_id = %s OR v.bill_id = %s)"
        params.extend([f"%{search}%", search if search.isdigit() else 0, search if search.isdigit() else 0])

    sql += " ORDER BY v.billing_period DESC, v.bill_id DESC"
    rows = query_all(sql, params)
    return jsonify({"success": True, "data": rows})

@billing_bp.route("/me/bills", methods=["GET"])
@jwt_required()
def get_my_bills():
    claims = get_jwt()
    role = claims.get("role")
    token_cid = claims.get("customer_id")

    if role != "CUSTOMER" or not token_cid:
        return jsonify({"success": False, "error": "Endpoint is strictly for registered customers"}), 403

    rows = query_all("""
        SELECT * FROM v_customer_bill_summary
        WHERE customer_id = %s
        ORDER BY billing_period DESC
    """, (token_cid,))
    return jsonify({"success": True, "data": rows})

@billing_bp.route("/bills/<int:bill_id>/pdf", methods=["GET"])
@jwt_required()
def download_bill_pdf(bill_id):
    claims = get_jwt()
    role = claims.get("role")
    token_cid = claims.get("customer_id")

    bill = query_one("""
        SELECT v.*, c.address, c.phone, a.area_name
        FROM v_customer_bill_summary v
        JOIN customer c ON c.customer_id = v.customer_id
        JOIN area a ON a.area_id = c.area_id
        WHERE v.bill_id = %s
    """, (bill_id,))

    if not bill:
        return jsonify({"success": False, "error": "Bill not found"}), 404

    # Enforce customer isolation
    if role == "CUSTOMER" and bill["customer_id"] != token_cid:
        return jsonify({"success": False, "error": "Access denied: cannot access another customer's invoice"}), 403

    tariffs = query_all("SELECT * FROM tariff ORDER BY category, slab_from ASC;")
    pdf_buffer = generate_invoice_pdf(bill, tariffs)

    filename = f"VoltTrack_Bill_{bill_id}_{bill['billing_period']}.pdf"
    return send_file(
        pdf_buffer,
        mimetype="application/pdf",
        as_attachment=True,
        download_name=filename
    )
