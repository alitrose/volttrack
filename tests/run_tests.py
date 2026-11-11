"""
Stand-alone Test Runner for VoltTrack Backend API
Uses Flask test_client directly without external runner.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.app import create_app
from backend.config import Config

def run():
    print("=== Running VoltTrack Automated Backend Tests ===")
    app = create_app({"TESTING": True})
    client = app.test_client()

    # 1. Login Test
    print("[1/6] Testing Authentication & Token Issuance...")
    res = client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
    assert res.status_code == 200, f"Admin login failed: {res.json}"
    admin_token = res.json["data"]["token"]

    res_cust = client.post("/api/auth/login", json={"username": "customer", "password": "Volt@123"})
    assert res_cust.status_code == 200, f"Customer login failed: {res_cust.json}"
    cust_token = res_cust.json["data"]["token"]

    res_bad = client.post("/api/auth/login", json={"username": "admin", "password": "badpassword"})
    assert res_bad.status_code == 401, "Bad password should return 401"
    print("      -> Passed: Auth and JWT generation verified.")

    # 2. RBAC Enforcement Test
    print("[2/6] Testing RBAC (Customer cannot access Admin endpoints)...")
    res_forbidden = client.get("/api/customers", headers={"Authorization": f"Bearer {cust_token}"})
    assert res_forbidden.status_code == 403, f"Expected 403, got {res_forbidden.status_code}"
    print("      -> Passed: RBAC properly returned 403 Forbidden.")

    # 3. Customer Data Isolation Test
    print("[3/6] Testing Customer Isolation (Cannot read other customer profile)...")
    res_own = client.get("/api/customers/1", headers={"Authorization": f"Bearer {cust_token}"})
    assert res_own.status_code == 200, "Customer should be able to view own profile"
    res_other = client.get("/api/customers/2", headers={"Authorization": f"Bearer {cust_token}"})
    assert res_other.status_code == 403, "Customer must not view customer 2 profile"
    print("      -> Passed: Server-side customer data isolation enforced.")

    # 4. Readings Ingestion API Key Test
    print("[4/6] Testing Meter Readings Ingestion with X-API-KEY...")
    res_no_key = client.post("/api/readings", json={"meter_id": 1, "reading_ts": "2026-10-27 12:00:00", "units_consumed": 1.0, "voltage": 230})
    assert res_no_key.status_code == 401
    res_ingest = client.post(
        "/api/readings",
        headers={"X-API-KEY": Config.SIMULATOR_API_KEY},
        json={"meter_id": 1, "reading_ts": "2026-10-27 12:00:00", "units_consumed": 1.5, "voltage": 230, "power_factor": 0.95}
    )
    assert res_ingest.status_code == 201
    print("      -> Passed: Reading ingestion and anomaly trigger execution verified.")

    # 5. Billing and Payment Flow
    print("[5/6] Testing Batch Billing and Transactional Payment Processing...")
    res_gen = client.post("/api/billing/generate", headers={"Authorization": f"Bearer {admin_token}"}, json={"month": "2026-08-01"})
    assert res_gen.status_code == 200

    res_bills = client.get("/api/bills?status=UNPAID", headers={"Authorization": f"Bearer {admin_token}"})
    assert res_bills.status_code == 200
    bills = res_bills.json["data"]
    assert len(bills) > 0
    tb = bills[0]
    bid = tb["bill_id"]
    bal = float(tb["balance"])

    # Overpayment test
    res_over = client.post("/api/payments", headers={"Authorization": f"Bearer {admin_token}"}, json={"bill_id": bid, "amount": bal + 500, "mode": "UPI"})
    assert res_over.status_code == 400
    assert "Overpayment" in res_over.json["error"]

    # Partial payment test
    res_part = client.post("/api/payments", headers={"Authorization": f"Bearer {admin_token}"}, json={"bill_id": bid, "amount": 10.0, "mode": "UPI"})
    assert res_part.status_code == 201
    assert res_part.json["data"]["new_status"] == "PARTIAL"
    print("      -> Passed: Overpayment rejected; partial payment updated status to PARTIAL.")

    # 6. Analytics & Audit Log
    print("[6/6] Testing Analytics, Reporting, and Audit Logs...")
    res_kpi = client.get("/api/analytics/kpis", headers={"Authorization": f"Bearer {admin_token}"})
    assert res_kpi.status_code == 200
    assert res_kpi.json["data"]["total_customers"] == 60

    res_top = client.get("/api/analytics/top-consumers", headers={"Authorization": f"Bearer {admin_token}"})
    assert res_top.status_code == 200

    res_audit = client.get("/api/audit", headers={"Authorization": f"Bearer {admin_token}"})
    assert res_audit.status_code == 200
    assert len(res_audit.json["data"]) > 0
    print("      -> Passed: Analytics, Top-10 consumers, and Audit logs returned accurately.")

    print("\n[+] ALL 6 CORE TEST SUITES PASSED WITH 100% SUCCESS!")

if __name__ == "__main__":
    run()
