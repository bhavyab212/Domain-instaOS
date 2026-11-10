"""Automated Verification Suite for InstaOS Autonomous Engine.

Executes and asserts all 12 operational checks via FastAPI TestClient.
"""

import os
import sys
from pathlib import Path

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from fastapi.testclient import TestClient
from app.main import app
from app.config import STATIC_DIR
from app.database.store import db


def run_all_verification_checks():
    print("=" * 65)
    print("INSTAOS AUTONOMOUS ENGINE — 12-POINT AUTOMATED VERIFICATION")
    print("=" * 65)

    client = TestClient(app)

    # -------------------------------------------------------------
    # Check 01: Health & Ping Endpoints
    # -------------------------------------------------------------
    resp_ping = client.get("/ping")
    resp_health = client.get("/health")
    assert resp_ping.status_code == 200, f"Ping failed: {resp_ping.status_code}"
    assert resp_ping.json().get("status") == "ONLINE"
    assert resp_health.status_code == 200, f"Health failed: {resp_health.status_code}"
    health_data = resp_health.json()
    assert health_data.get("status") == "ONLINE"
    assert "uptime_seconds" in health_data
    assert "active_orders" in health_data
    print("[CHECK 01/12] PASS: Health & Ping endpoints return HTTP 200 and ONLINE")

    # -------------------------------------------------------------
    # Check 02: Store Reset
    # -------------------------------------------------------------
    resp_reset = client.post("/webhook", json={"text": "@InstaOS reset"})
    assert resp_reset.status_code == 200
    assert "reset" in resp_reset.json().get("text", "").lower()
    assert len(db.orders) == 3
    assert len(db.backorders) == 0
    print("[CHECK 02/12] PASS: @InstaOS reset restores seed state cleanly")

    # -------------------------------------------------------------
    # Check 03: Scenario 1 — Hinglish Product & Stock Inquiry
    # -------------------------------------------------------------
    sc1_dm = "Bhai acid wash hoodie size L ka price kya hai? Available hai kya?"
    resp_sc1 = client.post("/webhook", json={"text": sc1_dm, "sender": "@arjun_lifts"})
    assert resp_sc1.status_code == 200
    data_sc1 = resp_sc1.json()
    assert "1,499" in data_sc1.get("text", "") or "1499" in data_sc1.get("text", "").replace(",", "") or "1,499" in data_sc1.get("content", "")
    assert "stock" in data_sc1.get("content", "").lower()
    print("[CHECK 03/12] PASS: Scenario 1 (Hinglish product & stock inquiry) parsed correctly")

    # -------------------------------------------------------------
    # Check 04: Scenario 2 — Incomplete Address Edge Case (Rule #5 Guard)
    # -------------------------------------------------------------
    sc2_dm = "Hey! I want to order 2 oversized black tees in size M. Please ship to Flat 402, Sunshine Apts, Delhi."
    resp_sc2 = client.post("/webhook", json={"text": sc2_dm, "sender": "@sneha_kapoor"})
    assert resp_sc2.status_code == 200
    data_sc2 = resp_sc2.json()
    # Must reject incomplete address and prompt for pincode / phone
    assert "pincode" in data_sc2.get("text", "").lower() or "missing" in data_sc2.get("content", "").lower()
    assert "@sneha_kapoor" in db.customer_sessions
    # Confirm no premature invoice generated for sneha yet
    assert not (STATIC_DIR / "Invoice_Label_ORD-104.html").exists()
    print("[CHECK 04/12] PASS: Scenario 2 (Incomplete address DM) caught by EdgeCaseGuard")

    # -------------------------------------------------------------
    # Check 05: Scenario 3 — Complete Order Confirmation & Invoice Generation
    # -------------------------------------------------------------
    stock_before_tee_m = db.get_stock("TEE-BLK-01", "M")
    sc3_dm = "Pincode is 110085 and phone is 9876543210. Paid via UPI!"
    resp_sc3 = client.post("/webhook", json={"text": sc3_dm, "sender": "@sneha_kapoor"})
    assert resp_sc3.status_code == 200
    data_sc3 = resp_sc3.json()
    assert "ORD-104" in data_sc3.get("content", "") or "ORD-104" in data_sc3.get("text", "")
    # Verify stock deduction (2 units)
    stock_after_tee_m = db.get_stock("TEE-BLK-01", "M")
    assert stock_after_tee_m == stock_before_tee_m - 2, f"Stock not deducted properly: before {stock_before_tee_m}, after {stock_after_tee_m}"
    # Verify HTML invoice & label generated
    inv_file_104 = STATIC_DIR / "Invoice_Label_ORD-104.html"
    assert inv_file_104.exists(), f"Expected invoice file {inv_file_104} not found"
    assert os.path.getsize(inv_file_104) > 1000
    print("[CHECK 05/12] PASS: Scenario 3 (Complete prepaid DM) confirms ORD-104 and generates invoice")

    # -------------------------------------------------------------
    # Check 06: Scenario 4 — Out-of-Stock Backorder Queuing
    # -------------------------------------------------------------
    sc4_dm = "Bro need acid wash hoodie size XL asap, please book one."
    resp_sc4 = client.post("/webhook", json={"text": sc4_dm, "sender": "@dev_streetwear"})
    assert resp_sc4.status_code == 200
    data_sc4 = resp_sc4.json()
    assert "backorder" in data_sc4.get("text", "").lower() or "waitlist" in data_sc4.get("content", "").lower()
    assert len(db.backorders) > 0
    # Verify walk_to_user action for store manager
    actions = data_sc4.get("actions", [])
    assert any(a.get("type") == "walk_to_user" and a.get("target") == "@StoreManager" for a in actions)
    print("[CHECK 06/12] PASS: Scenario 4 (Out-of-stock backorder) queued with manager alert action")

    # -------------------------------------------------------------
    # Check 07: Scenario 5 — High-Value COD Fraud Hold (> ₹2500)
    # -------------------------------------------------------------
    sc5_dm = "I want to order 3 cyberpunk varsity jackets size M cash on delivery to Jaipur 302017 phone 9829012345."
    resp_sc5 = client.post("/webhook", json={"text": sc5_dm, "sender": "@vikram_07"})
    assert resp_sc5.status_code == 200
    data_sc5 = resp_sc5.json()
    assert "ORD-105" in data_sc5.get("content", "") or "ORD-105" in data_sc5.get("text", "")
    assert "hold" in data_sc5.get("text", "").lower() or "approval" in data_sc5.get("content", "").lower()
    order_105 = db.get_order("ORD-105")
    assert order_105 is not None
    assert "ON_HOLD" in order_105.get("status", "")
    assert order_105.get("stage") == "AWAITING_MANAGER_APPROVAL"
    # Verify 10% bulk discount: 3 * 2199 = 6597 - 10% (659.70) + 50 COD = 5987.30
    assert abs(order_105["final_total"] - 5987.30) < 1.0
    print("[CHECK 07/12] PASS: Scenario 5 (High-value COD > ₹2500) enforces fraud hold & bulk discount")

    # -------------------------------------------------------------
    # Check 08: Customer Verification Check
    # -------------------------------------------------------------
    resp_ver = client.post("/webhook", json={"text": "@InstaOS verify ORD-104"})
    assert resp_ver.status_code == 200
    data_ver = resp_ver.json()
    assert "VERIFIED_BUYER" in data_ver.get("content", "")
    assert "100" in data_ver.get("content", "")
    print("[CHECK 08/12] PASS: @InstaOS verify ORD-104 produces buyer verification scorecard")

    # -------------------------------------------------------------
    # Check 09: Manager Approval of Held COD Order
    # -------------------------------------------------------------
    resp_appr = client.post("/webhook", json={"text": "@InstaOS approve ORD-103"})
    assert resp_appr.status_code == 200
    data_appr = resp_appr.json()
    assert "approved" in data_appr.get("text", "").lower()
    order_103 = db.get_order("ORD-103")
    assert order_103["status"] == "CONFIRMED"
    inv_file_103 = STATIC_DIR / "Invoice_Label_ORD-103.html"
    assert inv_file_103.exists()
    print("[CHECK 09/12] PASS: @InstaOS approve ORD-103 overrides fraud hold and issues invoice")

    # -------------------------------------------------------------
    # Check 10: Inventory Restock & Backorder Resolution
    # -------------------------------------------------------------
    resp_restock = client.post("/webhook", json={"text": "@InstaOS restock"})
    assert resp_restock.status_code == 200
    data_restock = resp_restock.json()
    assert "restocked" in data_restock.get("text", "").lower()
    assert len(db.backorders) == 0
    # XL hoodie was 0, after restock must be >= 10
    assert db.get_stock("HD-ACID-02", "XL") >= 10
    print("[CHECK 10/12] PASS: @InstaOS restock adds inventory and clears backorder waitlist")

    # -------------------------------------------------------------
    # Check 11: Live Analytics Dashboard & Non-Empty CSV Exports
    # -------------------------------------------------------------
    resp_dash = client.post("/webhook", json={"text": "@InstaOS dashboard"})
    assert resp_dash.status_code == 200
    data_dash = resp_dash.json()
    assert len(data_dash.get("files", [])) >= 4

    chart_file = STATIC_DIR / "instaos_live_dashboard.png"
    orders_csv = STATIC_DIR / "master_orders.csv"
    inv_csv = STATIC_DIR / "inventory_stock_report.csv"
    audit_csv = STATIC_DIR / "agent_audit_log.csv"

    assert chart_file.exists(), f"Dashboard chart {chart_file} missing"
    assert orders_csv.exists(), f"Orders CSV {orders_csv} missing"
    assert inv_csv.exists(), f"Inventory CSV {inv_csv} missing"
    assert audit_csv.exists(), f"Audit CSV {audit_csv} missing"

    chart_sz = os.path.getsize(chart_file)
    orders_sz = os.path.getsize(orders_csv)
    inv_sz = os.path.getsize(inv_csv)
    audit_sz = os.path.getsize(audit_csv)

    assert chart_sz > 500, f"Chart file too small: {chart_sz} bytes"
    assert orders_sz > 500, f"Orders CSV too small: {orders_sz} bytes"
    assert inv_sz > 500, f"Inventory CSV too small: {inv_sz} bytes"
    assert audit_sz > 500, f"Audit CSV too small: {audit_sz} bytes"
    print(f"[CHECK 11/12] PASS: Dashboard PNG ({chart_sz}B) & 3 CSVs (>500B each) generated")

    # -------------------------------------------------------------
    # Check 12: Full Demo Scenario Batch Run
    # -------------------------------------------------------------
    resp_demo = client.post("/webhook", json={"text": "@InstaOS run_demo"})
    assert resp_demo.status_code == 200
    data_demo = resp_demo.json()
    assert "Scenario 1" in data_demo.get("content", "")
    assert "Scenario 2" in data_demo.get("content", "")
    assert "Scenario 3" in data_demo.get("content", "")
    assert "Scenario 4" in data_demo.get("content", "")
    assert "Scenario 5" in data_demo.get("content", "")
    assert "Scenario 6" in data_demo.get("content", "")
    print("[CHECK 12/12] PASS: Full 6-scenario demo stream executes without errors")

    print("=" * 65)
    print("ALL 12 VERIFICATION CHECKS PASSED (100% VERIFIED)")
    print("=" * 65)


if __name__ == "__main__":
    run_all_verification_checks()
