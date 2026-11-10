"""Risk, Pricing, Verification, Tax, and Courier Allocation Agent."""

import random
import re
from typing import Dict, Any
from app.database.store import db

DISPOSABLE_DOMAINS = ["mailinator.com", "tempmail.com", "10minutemail.com", "guerrillamail.com"]


def verifly_customer_identity(
    handle: str,
    phone: str = "",
    pincode: str = "",
    email: str = ""
) -> Dict[str, Any]:
    """Evaluates customer identity, phone syntax, pincode syntax, and returns trust scorecard."""
    signals = []
    trust_score = 50

    # 1. Instagram Handle Assessment
    cleaned_handle = (handle or "@guest").strip()
    if any(b in cleaned_handle.lower() for b in ["bot", "fake", "spam", "test"]):
        signals.append("SUSPICIOUS_HANDLE_PATTERN")
        trust_score -= 30
    else:
        signals.append("AUTHENTIC_INSTAGRAM_HANDLE")
        trust_score += 15

    # 2. Indian Mobile Number Syntax (10 digits starting with 6-9)
    phone_clean = re.sub(r"[^\d]", "", phone or "")
    if re.match(r"^[6-9]\d{9}$", phone_clean):
        signals.append("VALID_INDIAN_MOBILE_10DIGIT")
        trust_score += 20
        phone_valid = True
    else:
        signals.append("INVALID_OR_MISSING_MOBILE")
        phone_valid = False

    # 3. Indian Postal Pincode Syntax (6 digits)
    pincode_clean = re.sub(r"[^\d]", "", pincode or "")
    if re.match(r"^\d{6}$", pincode_clean):
        signals.append("VALID_POSTAL_PINCODE_6DIGIT")
        trust_score += 15
        pincode_valid = True
    else:
        signals.append("INVALID_OR_MISSING_PINCODE")
        pincode_valid = False

    # 4. Email Syntax & Disposable check
    if email:
        domain = email.split("@")[-1].lower() if "@" in email else ""
        if domain in DISPOSABLE_DOMAINS:
            signals.append("DISPOSABLE_EMAIL_DOMAIN_REJECTED")
            trust_score -= 40
        else:
            signals.append("LEGITIMATE_EMAIL_DOMAIN")
            trust_score += 10

    # Final Badge Assignment
    if phone_valid and pincode_valid and trust_score >= 70:
        badge = "VERIFIED_BUYER"
        status_color = "#10b981"  # Emerald
    else:
        badge = "UNVERIFIED_SYNTAX"
        status_color = "#f43f5e"  # Rose

    trust_score = max(5, min(99, trust_score))

    return {
        "handle": cleaned_handle,
        "phone": phone_clean,
        "pincode": pincode_clean,
        "trust_score": trust_score,
        "verification_badge": badge,
        "status_color": status_color,
        "signals": signals,
        "is_syntax_valid": phone_valid and pincode_valid,
    }


def evaluate_order_pricing_and_risk(
    item_key: str,
    size: str,
    qty: int,
    payment_mode: str,
    pincode: str
) -> Dict[str, Any]:
    """Calculates subtotal, 10% volume discount, ₹50 COD fee, 12% included GST, courier zone, and COD fraud hold."""
    product = db.get_product_by_query(item_key)
    if not product:
        # Fallback default product if uncatalogued
        sku = "TEE-BLK-01"
        item_name = "Oversized Black Tee"
        unit_price = 699.0
    else:
        sku = product["sku"]
        item_name = product["name"]
        unit_price = float(product["price"])

    qty = max(1, int(qty or 1))
    subtotal = round(unit_price * qty, 2)

    # 1. Volume Discount: 10% off when ordering 3 or more items
    if qty >= 3:
        discount = round(subtotal * 0.10, 2)
        bulk_discount_applied = True
    else:
        discount = 0.0
        bulk_discount_applied = False

    discounted_subtotal = round(subtotal - discount, 2)

    # 2. Payment Surcharge: ₹50 for Cash on Delivery
    payment_mode = (payment_mode or "PREPAID").upper()
    if payment_mode == "COD":
        cod_fee = 50.0
    else:
        cod_fee = 0.0

    final_total = round(discounted_subtotal + cod_fee, 2)

    # 3. 12% Included GST Calculation (Apparel tax policy)
    # Total includes 12% GST: Base = DiscountedSubtotal * 100 / 112
    gst_amount = round((discounted_subtotal * 12.0) / 112.0, 2)
    taxable_value = round(discounted_subtotal - gst_amount, 2)
    cgst = round(gst_amount / 2.0, 2)
    sgst = round(gst_amount - cgst, 2)

    # 4. Courier Zone Allocation by Indian Pincode Prefix
    pin_str = str(pincode or "").strip()
    first_digit = pin_str[0] if pin_str else "1"
    random_awb_suffix = random.randint(1000000, 9999999)

    if first_digit in ["1", "2", "3"]:
        courier = "Delhivery Express Air"
        awb = f"DL{random_awb_suffix}"
        zone = "North Zone (Air Express)"
    elif first_digit in ["4", "5", "6"]:
        courier = "BlueDart Priority"
        awb = f"BD{random_awb_suffix}"
        zone = "West/South Zone (Priority Air)"
    else:
        courier = "XpressBees D2C"
        awb = f"XB{random_awb_suffix}"
        zone = "East/Metro Zone (Surface D2C)"

    # 5. High-Value COD Fraud Guard (> ₹2,500)
    requires_manager_approval = False
    if payment_mode == "COD" and final_total > 2500.0:
        status = "ON_HOLD (High Value COD > ₹2500)"
        stage = "AWAITING_MANAGER_APPROVAL"
        risk_grade = "HIGH_RISK_COD"
        requires_manager_approval = True
        fraud_alert_msg = f"High-Value COD order (₹{final_total:,.2f} > ₹2,500 threshold). Order placed on hold awaiting human manager approval."
    else:
        status = "CONFIRMED"
        stage = "CONFIRMED"
        risk_grade = "LOW_RISK_VERIFIED"
        fraud_alert_msg = "Order cleared risk checks and is ready for fulfillment."

    return {
        "sku": sku,
        "item_name": item_name,
        "unit_price": unit_price,
        "qty": qty,
        "subtotal": subtotal,
        "discount": discount,
        "bulk_discount_applied": bulk_discount_applied,
        "discounted_subtotal": discounted_subtotal,
        "cod_fee": cod_fee,
        "taxable_value": taxable_value,
        "gst_amount": gst_amount,
        "cgst": cgst,
        "sgst": sgst,
        "final_total": final_total,
        "payment_mode": payment_mode,
        "courier": courier,
        "awb": awb,
        "zone": zone,
        "status": status,
        "stage": stage,
        "risk_grade": risk_grade,
        "requires_manager_approval": requires_manager_approval,
        "fraud_alert_msg": fraud_alert_msg,
    }
