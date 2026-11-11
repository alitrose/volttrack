from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required
from backend.auth import role_required
from backend.db import query_all, query_one

analytics_bp = Blueprint("analytics", __name__, url_prefix="/api/analytics")

@analytics_bp.route("/kpis", methods=["GET"])
@jwt_required()
def get_kpis():
    cust_cnt = query_one("SELECT COUNT(*) AS total FROM customer")["total"]
    meter_cnt = query_one("SELECT COUNT(*) AS total, SUM(status='ACTIVE') AS active FROM meter")
    alert_cnt = query_one("SELECT COUNT(*) AS total FROM alert WHERE is_resolved = FALSE")["total"]
    
    # Financial summary
    fin = query_one("""
        SELECT 
            COALESCE(SUM(b.amount), 0) AS total_billed,
            COALESCE((SELECT SUM(amount) FROM payment), 0) AS total_collected,
            COALESCE(SUM(CASE WHEN b.status IN ('UNPAID', 'OVERDUE') THEN b.amount ELSE 0 END), 0) AS outstanding
        FROM bill b
    """)

    return jsonify({
        "success": True,
        "data": {
            "total_customers": cust_cnt,
            "total_meters": meter_cnt["total"],
            "active_meters": meter_cnt["active"] or 0,
            "open_alerts": alert_cnt,
            "total_billed": float(fin["total_billed"]),
            "total_collected": float(fin["total_collected"]),
            "outstanding_balance": float(fin["outstanding"])
        }
    })

@analytics_bp.route("/top-consumers", methods=["GET"])
@role_required("ADMIN", "BILLING_OFFICER")
def top_consumers():
    rows = query_all("""
        SELECT c.customer_id, c.name AS customer_name, c.category, a.area_name,
               ROUND(SUM(r.units_consumed), 2) AS total_kwh
        FROM meter_reading r
        JOIN meter m ON m.meter_id = r.meter_id
        JOIN customer c ON c.customer_id = m.customer_id
        JOIN area a ON a.area_id = c.area_id
        WHERE r.reading_ts >= DATE_SUB(CURDATE(), INTERVAL 60 DAY)
        GROUP BY c.customer_id, c.name, c.category, a.area_name
        ORDER BY total_kwh DESC
        LIMIT 10
    """)
    return jsonify({"success": True, "data": rows})

@analytics_bp.route("/peak-offpeak", methods=["GET"])
@jwt_required()
def peak_offpeak():
    rows = query_all("""
        SELECT 
            ROUND(SUM(CASE WHEN HOUR(r.reading_ts) BETWEEN 18 AND 21 THEN r.units_consumed ELSE 0 END), 2) AS peak_kwh,
            ROUND(SUM(CASE WHEN HOUR(r.reading_ts) NOT BETWEEN 18 AND 21 THEN r.units_consumed ELSE 0 END), 2) AS offpeak_kwh,
            ROUND(SUM(r.units_consumed), 2) AS total_kwh
        FROM meter_reading r
    """)
    summary = rows[0] if rows else {"peak_kwh": 0, "offpeak_kwh": 0, "total_kwh": 0}
    return jsonify({"success": True, "data": summary})

@analytics_bp.route("/theft-suspects", methods=["GET"])
@role_required("ADMIN", "TECHNICIAN")
def theft_suspects():
    rows = query_all("""
        WITH monthly_consumption AS (
            SELECT 
                m.meter_id,
                c.customer_id,
                c.name AS customer_name,
                c.phone,
                a.area_name,
                DATE_FORMAT(r.reading_ts, '%%Y-%%m-01') AS ym,
                ROUND(SUM(r.units_consumed), 2) AS monthly_kwh
            FROM meter_reading r
            JOIN meter m ON m.meter_id = r.meter_id
            JOIN customer c ON c.customer_id = m.customer_id
            JOIN area a ON a.area_id = c.area_id
            GROUP BY m.meter_id, c.customer_id, c.name, c.phone, a.area_name, ym
        ),
        consumption_delta AS (
            SELECT 
                meter_id, customer_id, customer_name, phone, area_name, ym, monthly_kwh,
                LAG(monthly_kwh) OVER (PARTITION BY meter_id ORDER BY ym) AS prev_month_kwh
            FROM monthly_consumption
        )
        SELECT 
            meter_id, customer_id, customer_name, phone, area_name,
            ym AS current_month,
            prev_month_kwh,
            monthly_kwh,
            ROUND(100.0 * (prev_month_kwh - monthly_kwh) / prev_month_kwh, 1) AS drop_percentage
        FROM consumption_delta
        WHERE prev_month_kwh > 50.0 
          AND monthly_kwh < (0.40 * prev_month_kwh)
        ORDER BY drop_percentage DESC
    """)
    return jsonify({"success": True, "data": rows})

@analytics_bp.route("/outages", methods=["GET"])
@jwt_required()
def outages():
    rows = query_all("""
        SELECT al.alert_id, al.meter_id, al.message, al.raised_at, al.is_resolved,
               c.name AS customer_name, a.area_name
        FROM alert al
        JOIN meter m ON m.meter_id = al.meter_id
        JOIN customer c ON c.customer_id = m.customer_id
        JOIN area a ON a.area_id = c.area_id
        WHERE al.type = 'OUTAGE'
        ORDER BY al.raised_at DESC
        LIMIT 20
    """)
    return jsonify({"success": True, "data": rows})

@analytics_bp.route("/revenue", methods=["GET"])
@role_required("ADMIN", "BILLING_OFFICER")
def revenue_breakdown():
    # Monthly revenue trend
    monthly = query_all("""
        SELECT DATE_FORMAT(paid_at, '%%Y-%%m') AS month, ROUND(SUM(amount), 2) AS revenue
        FROM payment
        GROUP BY month
        ORDER BY month ASC
    """)
    
    # Area-wise revenue
    by_area = query_all("""
        SELECT a.area_name, ROUND(SUM(p.amount), 2) AS total_revenue
        FROM payment p
        JOIN bill b ON b.bill_id = p.bill_id
        JOIN customer c ON c.customer_id = b.customer_id
        JOIN area a ON a.area_id = c.area_id
        GROUP BY a.area_name
        ORDER BY total_revenue DESC
    """)

    return jsonify({"success": True, "data": {"monthly": monthly, "by_area": by_area}})

@analytics_bp.route("/forecast", methods=["GET"])
@role_required("ADMIN", "BILLING_OFFICER")
def consumption_forecast():
    rows = query_all("""
        WITH ranked_bills AS (
            SELECT 
                b.customer_id,
                c.name AS customer_name,
                c.category,
                b.billing_period,
                b.units,
                ROW_NUMBER() OVER (PARTITION BY b.customer_id ORDER BY b.billing_period DESC) AS rn
            FROM bill b
            JOIN customer c ON c.customer_id = b.customer_id
        )
        SELECT 
            customer_id,
            customer_name,
            category,
            ROUND(AVG(units), 2) AS forecast_kwh,
            COUNT(units) AS historical_periods
        FROM ranked_bills
        WHERE rn <= 3
        GROUP BY customer_id, customer_name, category
        ORDER BY forecast_kwh DESC
        LIMIT 15
    """)
    return jsonify({"success": True, "data": rows})
