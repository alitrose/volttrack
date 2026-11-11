import os
import sys

# Ensure root directory is in sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from flask import Flask, jsonify, send_from_directory, redirect, request
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from backend.config import Config
from backend.db import close_db, query_one
from backend.auth import auth_bp
from backend.routes.customers import customers_bp
from backend.routes.meters import meters_bp
from backend.routes.readings import readings_bp
from backend.routes.billing import billing_bp
from backend.routes.payments import payments_bp
from backend.routes.complaints import complaints_bp
from backend.routes.alerts import alerts_bp
from backend.routes.tariffs import tariffs_bp
from backend.routes.analytics import analytics_bp
from backend.routes.admin import admin_bp
from backend.services.scheduler import start_scheduler

def create_app(test_config=None):
    frontend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "frontend"))
    app = Flask(__name__, static_folder=frontend_dir, static_url_path="")
    app.config.from_object(Config)

    if test_config:
        app.config.update(test_config)

    # Initialize extensions
    CORS(app, resources={r"/api/*": {"origins": "*"}})
    jwt = JWTManager(app)

    # Register database teardown
    app.teardown_appcontext(close_db)

    # Register API Blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(customers_bp)
    app.register_blueprint(meters_bp)
    app.register_blueprint(readings_bp)
    app.register_blueprint(billing_bp)
    app.register_blueprint(payments_bp)
    app.register_blueprint(complaints_bp)
    app.register_blueprint(alerts_bp)
    app.register_blueprint(tariffs_bp)
    app.register_blueprint(analytics_bp)
    app.register_blueprint(admin_bp)

    # JWT Error handlers
    @jwt.unauthorized_loader
    def unauthorized_callback(err_str):
        return jsonify({"success": False, "error": "Authorization token is missing or invalid"}), 401

    @jwt.invalid_token_loader
    def invalid_token_callback(err_str):
        return jsonify({"success": False, "error": f"Invalid token: {err_str}"}), 401

    @jwt.expired_token_loader
    def expired_token_callback(jwt_header, jwt_payload):
        return jsonify({"success": False, "error": "Session token has expired. Please log in again."}), 401

    # Standard error handlers
    @app.errorhandler(404)
    def not_found(e):
        if request.path.startswith("/api/"):
            return jsonify({"success": False, "error": "Requested API resource not found"}), 404
        return send_from_directory(frontend_dir, "index.html")

    @app.errorhandler(500)
    def internal_error(e):
        return jsonify({"success": False, "error": "Internal server error occurred"}), 500

    # Healthcheck Endpoint
    @app.route("/api/health", methods=["GET"])
    def health_check():
        try:
            row = query_one("SELECT 1 AS ok")
            db_ok = bool(row and row.get("ok") == 1)
            return jsonify({
                "success": True,
                "status": "healthy" if db_ok else "degraded",
                "database": "connected" if db_ok else "unknown",
            }), 200
        except Exception as e:
            return jsonify({
                "success": False,
                "status": "unhealthy",
                "error": str(e),
            }), 503

    # Frontend Page Routes
    @app.route("/")
    def index():
        return send_from_directory(frontend_dir, "index.html")

    @app.route("/admin")
    def admin_page():
        return send_from_directory(frontend_dir, "admin.html")

    @app.route("/customer")
    def customer_page():
        return send_from_directory(frontend_dir, "customer.html")

    @app.route("/technician")
    def technician_page():
        return send_from_directory(frontend_dir, "technician.html")

    @app.route("/billing")
    def billing_page():
        return send_from_directory(frontend_dir, "billing.html")

    # Start background scheduler if not in debug reload child or test mode
    if not app.config.get("TESTING") and (os.environ.get("WERKZEUG_RUN_MAIN") == "true" or not app.debug):
        try:
            start_scheduler()
        except Exception as e:
            print(f"[*] Scheduler startup skipped: {e}")

    return app

if __name__ == "__main__":
    app = create_app()
    print(f"[*] VoltTrack Smart Meter Server running at: http://localhost:{Config.FLASK_PORT}")
    app.run(host="0.0.0.0", port=Config.FLASK_PORT, debug=Config.FLASK_DEBUG)
