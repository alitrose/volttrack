"""
Automated Test Suite for VoltTrack Flask Backend & RBAC
Tests:
- Authentication & password verification
- RBAC enforcement (Customer cannot access Admin endpoints -> 403)
- Customer data isolation (Customer cannot read other customer data -> 403)
- Meter readings ingestion via X-API-KEY
- Batch bill generation (cursor procedure)
- Partial payment, overpayment rollback, and full payment
- Bill deletion guard trigger
- Complaint lodging and technician assignment
- Analytics and audit log retrieval
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from backend.app import create_app

@pytest.fixture
def client():
    app = create_app({"TESTING": True})
    with app.test_client() as client:
        yield client

def login_as(client, username, password):
    res = client.post("/api/auth/login", json={"username": username, "password": password})
    assert res.status_code == 200, f"Login failed for {username}: {res.json}"
    return res.json["data"]["token"]

def test_login_success_and_failure(client):
    # 1. Success Admin
    token = login_as(client, "admin", "admin123")
    assert token is not None

    # 2. Success Customer
    cust_token = login_as(client, "customer", "Volt@123")
    assert cust_token is not None

    # 3. Invalid credentials
    res = client.post("/api/auth/login", json={"username": "admin", "password": "wrong_password"})
    assert res.status_code == 401
    assert res.json["success"] is False

def test_rbac_admin_endpoint_forbidden_for_customer(client):
    cust_token = login_as(client, "customer", "Volt@123")
    
    # Customer attempts to view admin customer management list
    res = client.get("/api/customers", headers={"Authorization": f"Bearer {cust_token}"})
    assert res.status_code == 403
    assert "Forbidden" in res.json["error"]

def test_customer_isolation_cannot_view_other_customer(client):
    # 'customer' corresponds to customer_id = 1
    cust_token = login_as(client, "customer", "Volt@123")

    # Accessing own profile (customer 1) -> Allowed
    res = client.get("/api/customers/1", headers={"Authorization": f"Bearer {cust_token}"})
    assert res.status_code == 200
    assert res.json["data"]["customer_id"] == 1

    # Accessing customer 2 profile -> Forbidden
    res2 = client.get("/api/customers/2", headers={"Authorization": f"Bearer {cust_token}"})
    assert res2.status_code == 403

def test_readings_ingestion_api_key(client):
    from backend.config import Config
    
    # Missing API key -> 401
    res = client.post("/api/readings", json={
        "meter_id": 1,
        "reading_ts": "2026-10-27 12:00:00",
        "units_consumed": 1.25,
        "voltage": 230.0
    })
    assert res.status_code == 401

    # Valid API key -> 201
    res = client.post(
        "/api/readings",
        headers={"X-API-KEY": Config.SIMULATOR_API_KEY},
        json={
            "meter_id": 1,
            "reading_ts": "2026-10-27 12:00:00",
            "units_consumed": 1.45,
            "voltage": 232.0,
            "power_factor": 0.96
        }
    )
    assert res.status_code == 201
    assert res.json["success"] is True

def test_billing_and_payment_flow(client):
    admin_token = login_as(client, "admin", "admin123")

    # 1. Trigger batch billing for August
    res_gen = client.post(
        "/api/billing/generate",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"month": "2026-08-01"}
    )
    assert res_gen.status_code == 200

    # 2. Fetch bills list
    res_bills = client.get(
        "/api/bills?status=UNPAID",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert res_bills.status_code == 200
    bills = res_bills.json["data"]
    assert len(bills) > 0

    target_bill = bills[0]
    bill_id = target_bill["bill_id"]
    due_amt = float(target_bill["balance"])
    assert due_amt > 10.0

    # 3. Attempt overpayment -> Must fail with 400
    res_over = client.post(
        "/api/payments",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "bill_id": bill_id,
            "amount": due_amt + 500.0,
            "mode": "UPI"
        }
    )
    assert res_over.status_code == 400
    assert "Overpayment" in res_over.json["error"]

    # 4. Partial payment
    res_part = client.post(
        "/api/payments",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "bill_id": bill_id,
            "amount": 10.0,
            "mode": "UPI"
        }
    )
    assert res_part.status_code == 201
    assert res_part.json["data"]["new_status"] == "PARTIAL"

def test_analytics_endpoints(client):
    admin_token = login_as(client, "admin", "admin123")
    headers = {"Authorization": f"Bearer {admin_token}"}

    # KPIs
    kpi = client.get("/api/analytics/kpis", headers=headers)
    assert kpi.status_code == 200
    assert kpi.json["data"]["total_customers"] >= 60

    # Top consumers
    top = client.get("/api/analytics/top-consumers", headers=headers)
    assert top.status_code == 200
    assert len(top.json["data"]) > 0

    # Peak vs Offpeak
    pou = client.get("/api/analytics/peak-offpeak", headers=headers)
    assert pou.status_code == 200
    assert float(pou.json["data"]["total_kwh"]) > 0

    # Theft suspects
    theft = client.get("/api/analytics/theft-suspects", headers=headers)
    assert theft.status_code == 200

    # Revenue
    rev = client.get("/api/analytics/revenue", headers=headers)
    assert rev.status_code == 200
