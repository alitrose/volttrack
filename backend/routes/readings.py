from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt
from backend.config import Config
from backend.db import query_all, query_one, execute_write

readings_bp = Blueprint("readings", __name__, url_prefix="/api/readings")

@readings_bp.route("", methods=["POST"])
def ingest_reading():
    """
    Ingestion endpoint for smart meter simulator or IoT gateway.
    Requires X-API-KEY header matching Config.SIMULATOR_API_KEY.
    """
    api_key = request.headers.get("X-API-KEY")
    if api_key != Config.SIMULATOR_API_KEY:
        return jsonify({"success": False, "error": "Unauthorized: invalid or missing X-API-KEY"}), 401

    data = request.get_json() or {}
    meter_id = data.get("meter_id")
    reading_ts = data.get("reading_ts")
    units = data.get("units_consumed")
    voltage = data.get("voltage")
    pf = data.get("power_factor", 0.95)

    if meter_id is None or reading_ts is None or units is None or voltage is None:
        return jsonify({"success": False, "error": "meter_id, reading_ts, units_consumed, and voltage are required"}), 400

    try:
        res = execute_write("""
            INSERT INTO meter_reading (meter_id, reading_ts, units_consumed, voltage, power_factor)
            VALUES (%s, %s, %s, %s, %s)
        """, (meter_id, reading_ts, units, voltage, pf))

        # Check if an alert was automatically triggered
        recent_alert = query_one("""
            SELECT * FROM alert 
            WHERE meter_id = %s AND raised_at >= DATE_SUB(NOW(), INTERVAL 2 SECOND)
            ORDER BY alert_id DESC LIMIT 1
        """, (meter_id,))

        return jsonify({
            "success": True,
            "data": {
                "reading_id": res["last_id"],
                "alert_triggered": recent_alert is not None,
                "alert": recent_alert
            }
        }), 201
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400

@readings_bp.route("/meter/<int:meter_id>", methods=["GET"])
@jwt_required()
def get_meter_readings(meter_id):
    claims = get_jwt()
    role = claims.get("role")
    token_cid = claims.get("customer_id")

    # Verify customer ownership
    meter = query_one("SELECT customer_id FROM meter WHERE meter_id = %s", (meter_id,))
    if not meter:
        return jsonify({"success": False, "error": "Meter not found"}), 404

    if role == "CUSTOMER" and meter["customer_id"] != token_cid:
        return jsonify({"success": False, "error": "Access denied: cannot view readings of another customer"}), 403

    from_date = request.args.get("from")
    to_date = request.args.get("to")
    group = request.args.get("group", "day").lower() # hour, day, month

    params = [meter_id]
    where_clause = " WHERE meter_id = %s"
    if from_date:
        where_clause += " AND reading_ts >= %s"
        params.append(from_date)
    if to_date:
        where_clause += " AND reading_ts <= %s"
        params.append(to_date)

    if group == "hour":
        sql = f"""
            SELECT DATE_FORMAT(reading_ts, '%%Y-%%m-%%d %%H:00') AS label,
                   ROUND(SUM(units_consumed), 3) AS units,
                   ROUND(AVG(voltage), 1) AS avg_voltage,
                   ROUND(AVG(power_factor), 2) AS avg_pf
            FROM meter_reading
            {where_clause}
            GROUP BY label
            ORDER BY label DESC
            LIMIT 168
        """
    elif group == "month":
        sql = f"""
            SELECT DATE_FORMAT(reading_ts, '%%Y-%%m') AS label,
                   ROUND(SUM(units_consumed), 2) AS units,
                   ROUND(AVG(voltage), 1) AS avg_voltage,
                   ROUND(AVG(power_factor), 2) AS avg_pf
            FROM meter_reading
            {where_clause}
            GROUP BY label
            ORDER BY label ASC
        """
    else: # Default: day
        sql = f"""
            SELECT DATE_FORMAT(reading_ts, '%%Y-%%m-%%d') AS label,
                   ROUND(SUM(units_consumed), 2) AS units,
                   ROUND(AVG(voltage), 1) AS avg_voltage,
                   ROUND(AVG(power_factor), 2) AS avg_pf
            FROM meter_reading
            {where_clause}
            GROUP BY label
            ORDER BY label DESC
            LIMIT 30
        """

    rows = query_all(sql, params)
    # Order ascending for chart timelines
    rows.reverse()
    return jsonify({"success": True, "data": rows})
