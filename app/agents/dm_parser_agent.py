"""DM Parser Sub-Agent with 4-second LLM safety floor and deterministic regex fallback."""

import json
import logging
import re
from typing import Dict, Any, Optional
import httpx

from app.config import LLM_BASE_URL, LLM_API_KEY, LLM_MODEL, LLM_TIMEOUT_SECONDS
from app.database.store import db

logger = logging.getLogger("DMParserAgent")

SYSTEM_EXTRACTION_PROMPT = """You are an expert NLP parser for an Instagram Streetwear D2C brand in India.
Analyze the customer's message (which may be in English or Hinglish).
Extract the following JSON fields strictly:
{
  "intent": "INQUIRY" | "NEW_ORDER" | "TRACK_ORDER" | "EXCHANGE_REQUEST" | "GENERAL",
  "item_key": string (one of "oversized black tee", "acid wash hoodie", "olive cargo pants", "cyberpunk varsity jacket" or null),
  "size": string (e.g. "S", "M", "L", "XL", "30", "32", "34" or null),
  "qty": integer (default 1),
  "payment_mode": "PREPAID" | "COD",
  "address": string or null,
  "pincode": string (6-digit postal code) or null,
  "phone": string (10-digit mobile) or null,
  "email": string or null,
  "order_id": string (e.g. "ORD-102") or null
}
Return ONLY raw valid JSON, no markdown formatting, no explanations.
"""


def _parse_with_regex_fallback(text: str, sender: str = "") -> Dict[str, Any]:
    """Deterministic regex extraction ensuring 100% demo resilience without external APIs."""
    t = text.lower()
    
    # 1. Order ID detection
    order_id_match = re.search(r"\b(ORD-\d{3,})\b", text, re.IGNORECASE)
    order_id = order_id_match.group(1).upper() if order_id_match else None

    # 2. Intent Detection
    if order_id or any(k in t for k in ["track", "kaha pahuncha", "status", "where is my order", "where's my order"]):
        intent = "TRACK_ORDER"
    elif any(k in t for k in ["return", "exchange", "replace", "defect"]):
        intent = "EXCHANGE_REQUEST"
    elif any(k in t for k in ["price", "kya hai", "rate", "cost", "available", "stock"]) and not any(k in t for k in ["order", "buy", "book", "ship to", "send"]):
        intent = "INQUIRY"
    elif any(k in t for k in ["order", "buy", "book", "need", "ship to", "send", "pincode", "paid", "upi", "cod"]):
        intent = "NEW_ORDER"
    else:
        intent = "INQUIRY"

    # 3. Product / Item Key
    item_key = None
    if any(k in t for k in ["black tee", "oversized black", "tee", "tshirt", "t-shirt"]):
        item_key = "oversized black tee"
    elif any(k in t for k in ["hoodie", "acid wash"]):
        item_key = "acid wash hoodie"
    elif any(k in t for k in ["cargo", "cargos", "olive cargo"]):
        item_key = "olive cargo pants"
    elif any(k in t for k in ["jacket", "varsity", "cyberpunk"]):
        item_key = "cyberpunk varsity jacket"

    # 4. Size Detection
    size = None
    size_match = re.search(r"\b(size\s*[:=]?\s*)?(s|m|l|xl|xxl|30|32|34)\b", t)
    if size_match:
        size = size_match.group(2).upper()

    # 5. Quantity Detection
    qty = 1
    qty_match = re.search(r"\b(\d+)\s*(?:x|units|pieces|pairs)?\s*(?:oversized|acid|olive|cyberpunk|tee|hoodie|cargo|jacket|tshirt)", t)
    if qty_match:
        qty = int(qty_match.group(1))
    else:
        num_word = re.search(r"\b(one|two|three|four)\b", t)
        if num_word:
            mapping = {"one": 1, "two": 2, "three": 3, "four": 4}
            qty = mapping[num_word.group(1)]
        else:
            simple_digit = re.search(r"\b(?:order|buy|need|get)\s+(\d+)\b", t)
            if simple_digit:
                qty = int(simple_digit.group(1))

    # 6. Payment Mode
    if any(k in t for k in ["cash on delivery", "cod"]):
        payment_mode = "COD"
    elif any(k in t for k in ["upi", "prepaid", "paid", "gpay", "paytm", "phonepe"]):
        payment_mode = "PREPAID"
    else:
        payment_mode = "PREPAID"

    # 7. Indian Mobile Number (10 digits starting with 6-9)
    phone = None
    phone_match = re.search(r"\b([6-9]\d{9})\b", text)
    if phone_match:
        phone = phone_match.group(1)

    # 8. Indian Postal Pincode (6 digits)
    pincode = None
    pincode_match = re.search(r"\b([1-9]\d{5})\b", text)
    if pincode_match:
        pincode = pincode_match.group(1)

    # 9. Address Extraction
    address = None
    addr_match = re.search(r"(?:ship to|to|deliver to|address is|address:)\s+([^.\n]+)", text, re.IGNORECASE)
    if addr_match:
        raw_addr = addr_match.group(1).strip()
        # strip out phone/pincode tokens if they bled in
        if phone:
            raw_addr = raw_addr.replace(phone, "")
        if pincode:
            raw_addr = raw_addr.replace(pincode, "")
        address = raw_addr.strip(" ,.")
    elif "jaipur" in t:
        address = "Jaipur"
    elif "delhi" in t:
        address = "Delhi"

    # Check if there is an active incomplete session for this sender
    if sender and sender in db.customer_sessions:
        session = db.get_customer_session(sender)
        item_key = item_key or session.get("item_key")
        size = size or session.get("size")
        qty = qty if qty > 1 else session.get("qty", qty)
        address = address or session.get("address")
        pincode = pincode or session.get("pincode")
        phone = phone or session.get("phone")
        if payment_mode == "PREPAID" and session.get("payment_mode") == "COD":
            payment_mode = session.get("payment_mode")

    return {
        "intent": intent,
        "item_key": item_key,
        "size": size,
        "qty": qty,
        "payment_mode": payment_mode,
        "address": address,
        "pincode": pincode,
        "phone": phone,
        "email": None,
        "order_id": order_id,
        "parser_source": "regex_deterministic",
    }


def parse_customer_dm(text: str, sender: str = "") -> Dict[str, Any]:
    """Parses customer Instagram DM using OpenAI-compatible LLM with 4s timeout & regex fallback."""
    # If no LLM API key is provided, execute deterministic regex immediately
    if not LLM_API_KEY or LLM_API_KEY.startswith("dummy"):
        db.log_event("DMParserAgent", "PARSE_REGEX_MODE", f"Fast deterministic regex parsed DM from {sender or 'guest'}")
        return _parse_with_regex_fallback(text, sender)

    # Attempt LLM call with 4.0s timeout
    try:
        url = f"{LLM_BASE_URL.rstrip('/')}/chat/completions"
        headers = {
            "Authorization": f"Bearer {LLM_API_KEY}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": LLM_MODEL,
            "messages": [
                {"role": "system", "content": SYSTEM_EXTRACTION_PROMPT},
                {"role": "user", "content": f"Customer Handle: {sender}\nCustomer Message: {text}"},
            ],
            "temperature": 0.0,
            "response_format": {"type": "json_object"},
        }
        with httpx.Client(timeout=LLM_TIMEOUT_SECONDS) as client:
            resp = client.post(url, headers=headers, json=payload)
            if resp.status_code == 200:
                data = resp.json()
                content = data["choices"][0]["message"]["content"]
                parsed = json.loads(content)
                parsed["parser_source"] = "llm_openai_compatible"
                db.log_event("DMParserAgent", "PARSE_LLM_SUCCESS", f"LLM parsed DM from {sender or 'guest'}")
                return parsed
            else:
                logger.warning(f"LLM API returned status {resp.status_code}. Using regex fallback.")
    except Exception as exc:
        logger.warning(f"LLM call failed or timed out ({exc}). Engaging deterministic regex fallback.")

    db.log_event("DMParserAgent", "PARSE_FALLBACK_ENGAGED", f"Engaged regex fallback for {sender or 'guest'}")
    return _parse_with_regex_fallback(text, sender)
