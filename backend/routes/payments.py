import uuid
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt
from backend.auth import role_required
from backend.db import query_all, query_one, call_proc

payments_bp = Blueprint("payments", __name__, url_prefix="/api/payments")

@payments_bp.route("", methods=["POST"])
@jwt_required()
def make_payment():
    claims = get_jwt()
    role = claims.get("role")
    token_cid = claims.get("customer_id")

    data = request.get_json() or {}
    bill_id = data.get("bill_id")
    amount = data.get("amount")
    mode = data.get("mode", "UPI")
    ref = data.get("transaction_ref") or f"TXN{uuid.uuid4().hex[:12].upper()}"

    if not bill_id or amount is None:
        return jsonify({"success": False, "error": "bill_id and amount are required"}), 400

    try:
        amount = float(amount)
        if amount <= 0:
            return jsonify({"success": False, "error": "Payment amount must be greater than zero"}), 400
    except ValueError:
        return jsonify({"success": False, "error": "Invalid numerical payment amount"}), 400

    if mode not in ("UPI", "CARD", "NETBANKING", "CASH"):
        return jsonify({"success": False, "error": "Invalid payment mode. Allowed: UPI, CARD, NETBANKING, CASH"}), 400

    # Verify bill exists and customer ownership
    bill = query_one("SELECT customer_id, amount, status FROM bill WHERE bill_id = %s", (bill_id,))
    if not bill:
        return jsonify({"success": False, "error": "Bill not found"}), 404

    if role == "CUSTOMER" and bill["customer_id"] != token_cid:
        return jsonify({"success": False, "error": "Access denied: cannot make payments on another customer's bill"}), 403

    try:
        call_proc("process_payment", (bill_id, amount, mode, ref))
        
        # Check new updated status
        updated_bill = query_one("SELECT status FROM bill WHERE bill_id = %s", (bill_id,))
        return jsonify({
            "success": True,
            "data": {
                "bill_id": bill_id,
                "amount_paid": amount,
                "mode": mode,
                "transaction_ref": ref,
                "new_status": updated_bill["status"],
                "message": f"Payment of ₹{amount:.2f} processed successfully. Invoice status: {updated_bill['status']}."
            }
        }), 201
    except Exception as e:
        err_msg = str(e)
        # Extract clean error message from MySQL 1644 / SIGNAL
        if "Overpayment not allowed" in err_msg:
            return jsonify({"success": False, "error": "Overpayment rejected: payment exceeds the outstanding bill balance."}), 400
        return jsonify({"success": False, "error": err_msg}), 400

@payments_bp.route("", methods=["GET"])
@jwt_required()
def list_payments():
    claims = get_jwt()
    role = claims.get("role")
    token_cid = claims.get("customer_id")

    sql = """
        SELECT p.payment_id, p.bill_id, p.amount, p.mode, p.paid_at, p.transaction_ref,
               b.billing_period, b.status AS bill_status,
               c.customer_id, c.name AS customer_name
        FROM payment p
        JOIN bill b ON b.bill_id = p.bill_id
        JOIN customer c ON c.customer_id = b.customer_id
        WHERE 1=1
    """
    params = []
    if role == "CUSTOMER":
        sql += " AND c.customer_id = %s"
        params.append(token_cid)
    else:
        bill_id = request.args.get("bill_id")
        if bill_id:
            sql += " AND p.bill_id = %s"
            params.append(bill_id)

    sql += " ORDER BY p.paid_at DESC LIMIT 100"
    rows = query_all(sql, params)
    return jsonify({"success": True, "data": rows})
