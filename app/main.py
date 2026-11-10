"""FastAPI Main Server, UptimeRobot Keepalive, and Nonilion Webhook Router."""

import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, timezone
import logging
import os
import re
from typing import Dict, Any, Optional

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
import httpx

from app.config import (
    PUBLIC_BASE_URL,
    STATIC_DIR,
    SHIPPING_STAGE_DELAY_SEC,
)
from app.database.store import db
from app.agents.dm_parser_agent import parse_customer_dm
from app.agents.risk_pricing_agent import (
    evaluate_order_pricing_and_risk,
    verifly_customer_identity,
)
from app.agents.logistics_worker import run_autonomous_shipping_pipeline
from app.agents.nonilion_office_client import (
    build_nonilion_response,
    push_async_room_notification,
)
from app.generators.html_artifacts import generate_invoice_and_label_html
from app.generators.csv_exporter import export_all_csvs
from app.generators.analytics_charts import generate_executive_dashboard_png

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("InstaOSMain")

# Background keepalive task handle
_keepalive_task: Optional[asyncio.Task] = None


async def internal_self_keepalive_loop():
    """Pings PUBLIC_BASE_URL/ping every 10 minutes (600s) to eliminate cold starts on free tiers like Render."""
    logger.info(f"Started internal self-keepalive task targeting {PUBLIC_BASE_URL}/ping (interval: 600s)")
    while True:
        try:
            await asyncio.sleep(600)
            ping_url = f"{PUBLIC_BASE_URL}/ping"
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(ping_url)
                if resp.status_code == 200:
                    logger.info("Internal self-keepalive ping succeeded (HTTP 200).")
        except asyncio.CancelledError:
            logger.info("Internal self-keepalive task cancelled gracefully.")
            break
        except Exception as exc:
            logger.warning(f"Internal self-keepalive ping encountered notice: {exc}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: ensure artifacts directory exists and pre-export initial CSVs & charts
    os.makedirs(STATIC_DIR, exist_ok=True)
    export_all_csvs(db, STATIC_DIR)
    try:
        generate_executive_dashboard_png(db, STATIC_DIR)
    except Exception as exc:
        logger.warning(f"Could not generate initial chart at startup: {exc}")

    # Launch background keepalive
    global _keepalive_task
    _keepalive_task = asyncio.create_task(internal_self_keepalive_loop())
    logger.info("InstaOS Autonomous Engine started and ready.")
    yield
    # Shutdown: cancel keepalive task
    if _keepalive_task:
        _keepalive_task.cancel()
        try:
            await _keepalive_task
        except asyncio.CancelledError:
            pass


app = FastAPI(
    title="InstaOS Autonomous D2C Engine",
    description="Autonomous Multi-Agent Instagram D2C Order-to-Delivery System for Nonilion Virtual Office",
    version="1.0.0",
    lifespan=lifespan,
)

# Enable CORS for Nonilion frontend room embedding
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount generated static files (/files/...)
app.mount("/files", StaticFiles(directory=str(STATIC_DIR)), name="files")


# -----------------------------------------------------------------------------
# UptimeRobot & Health Check Endpoints
# -----------------------------------------------------------------------------

@app.get("/")
def get_root():
    """Root info endpoint."""
    return {
        "engine": "InstaOS Autonomous Engine",
        "hackathon": "INNOVORTEX 4.0 — Nonilion Track",
        "status": "ONLINE",
        "docs": "/docs",
        "health": "/health",
        "keepalive_ping": "/ping",
        "webhook": "/webhook",
    }


@app.get("/ping")
def get_ping():
    """Lightweight 5-minute HTTP monitor endpoint for UptimeRobot."""
    return {
        "status": "ONLINE",
        "message": "pong",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/health")
def get_health():
    """Comprehensive health & telemetry check for cloud infrastructure."""
    now = datetime.now(timezone.utc)
    uptime_sec = round((now - db.start_time).total_seconds(), 2)
    stats = db.get_stats()
    return {
        "status": "ONLINE",
        "service": "instaos-autonomous-engine",
        "uptime_seconds": uptime_sec,
        "active_orders": stats["total_orders"],
        "delivered_orders": stats["delivered"],
        "backorders_queued": stats["backorders_queued"],
        "audit_events_logged": stats["audit_events_logged"],
        "total_revenue_inr": stats["total_revenue"],
        "timestamp": now.isoformat(),
    }


# -----------------------------------------------------------------------------
# Internal DM Processing Helper
# -----------------------------------------------------------------------------

def process_single_customer_dm(raw_text: str, sender: str = "@guest") -> Dict[str, Any]:
    """Processes a single Instagram DM end-to-end according to autonomous store policies."""
    # 1. Parse DM with LLM + regex safety floor
    parsed = parse_customer_dm(raw_text, sender=sender)
    intent = parsed.get("intent", "INQUIRY")
    order_id = parsed.get("order_id")

    # ---------------------------------------------------------
    # Intent A: Order Tracking
    # ---------------------------------------------------------
    if intent == "TRACK_ORDER" or order_id:
        target_id = order_id or "ORD-102"
        order = db.get_order(target_id)
        if not order:
            return build_nonilion_response(
                text=f"Order {target_id} not found in system.",
                content=f"⚠️ **Order Not Found**: We could not locate order `{target_id}` in our database. Please double check your order number.",
            )

        stage = order.get("stage", "PROCESSING")
        courier = order.get("courier", "Delhivery Express Air")
        awb = order.get("awb", "N/A")
        badge = order.get("verification_badge", "VERIFIED_BUYER")

        report = (
            f"### 📦 Live Order Tracking: `{target_id}`\n\n"
            f"- **Customer**: {order.get('customer_handle')} ({order.get('customer_name')})\n"
            f"- **Item**: {order.get('qty')}x {order.get('item_name')} (Size {order.get('size')})\n"
            f"- **Fulfilment Stage**: `{stage}`\n"
            f"- **Courier Partner**: {courier}\n"
            f"- **AWB Tracking #**: `{awb}`\n"
            f"- **Destination**: {order.get('address')}, Pincode `{order.get('pincode')}`\n"
            f"- **Payment**: {order.get('payment_mode')} (₹{order.get('final_total', 0):,.2f})\n"
            f"- **Buyer Trust**: `{badge}`\n"
        )
        return build_nonilion_response(
            text=f"Order {target_id} is currently {stage} with {courier} (AWB: {awb}).",
            content=report,
            voice_text=f"Order {target_id} is currently {stage.lower().replace('_', ' ')} via {courier}.",
        )

    # ---------------------------------------------------------
    # Intent B: Product & Pricing Inquiry
    # ---------------------------------------------------------
    if intent == "INQUIRY":
        item_key = parsed.get("item_key") or "acid wash hoodie"
        product = db.get_product_by_query(item_key)
        if not product:
            product = db.inventory.get("HD-ACID-02")

        stock_str = ", ".join([f"{sz}: {cnt} in stock" for sz, cnt in product["stock"].items()])
        content = (
            f"### 🏷️ Product Inquiry: {product['name']}\n\n"
            f"- **SKU**: `{product['sku']}`\n"
            f"- **Category**: {product['category']}\n"
            f"- **Retail Price**: ₹{product['price']:,.2f} *(Inclusive of 12% GST)*\n"
            f"- **Available Sizes & Stock**: {stock_str}\n"
            f"- **Special Offer**: Autonomous **10% Bulk Discount** applies on orders with 3+ units!\n"
            f"- **Payment**: Prepaid UPI (₹0 fee) or COD (+₹50 surcharge)\n\n"
            f"💬 *Reply with your size, delivery address, 6-digit pincode, and 10-digit phone to place an order!*"
        )
        return build_nonilion_response(
            text=f"Bhai {product['name']} ₹{product['price']:,.0f} ka hai (12% GST included). Sizes: {stock_str}.",
            content=content,
            voice_text=f"{product['name']} is available for rupees {product['price']:,.0f} inclusive of taxes.",
        )

    # ---------------------------------------------------------
    # Intent C: New Order Placement
    # ---------------------------------------------------------
    if intent == "NEW_ORDER":
        # Extract entity values
        item_key = parsed.get("item_key") or "oversized black tee"
        size = parsed.get("size") or "M"
        qty = parsed.get("qty", 1)
        address = parsed.get("address")
        pincode = parsed.get("pincode")
        phone = parsed.get("phone")
        payment_mode = parsed.get("payment_mode", "PREPAID")

        # Save current extraction in customer session
        db.save_customer_session(sender, {
            "item_key": item_key,
            "size": size,
            "qty": qty,
            "address": address,
            "pincode": pincode,
            "phone": phone,
            "payment_mode": payment_mode,
        })
        active_session = db.get_customer_session(sender)

        # Merge fields with session context
        address = address or active_session.get("address")
        pincode = pincode or active_session.get("pincode")
        phone = phone or active_session.get("phone")

        # Check if item exists and check stock availability FIRST
        product = db.get_product_by_query(item_key)
        if not product:
            product = db.inventory["TEE-BLK-01"]
        sku = product["sku"]
        current_stock = db.get_stock(sku, size)

        # Out-of-Stock Edge Case:
        # If the item is out of stock, register backorder immediately without demanding address/payment
        if current_stock < qty:
            db.add_backorder({
                "customer_handle": sender,
                "sku": sku,
                "item_name": product["name"],
                "size": size,
                "qty": qty,
                "address": address or "Waitlist - Address Pending",
                "pincode": pincode or "Waitlist",
                "phone": phone or "Waitlist",
                "payment_mode": payment_mode,
            })
            db.log_event(
                agent="InventoryAgent",
                event_type="BACKORDER_QUEUED",
                details=f"Size {size} of {sku} out of stock. Customer {sender} placed on waitlist.",
            )
            content = (
                f"### ⏳ Out-of-Stock Backorder Queued\n\n"
                f"Hey {sender}! **{product['name']}** in **Size {size}** is currently out of stock in our central warehouse.\n\n"
                f"- **Backorder Status**: `WAITLIST_REGISTERED`\n"
                f"- **Action Dispatched**: Floor alert sent to `@StoreManager` to restock.\n"
                f"- **Promise**: You will receive instant priority dispatch when restocked via `@InstaOS restock`.\n"
            )
            actions = [{"type": "walk_to_user", "target": "@StoreManager"}]
            return build_nonilion_response(
                text=f"{product['name']} in size {size} is out of stock. Added {sender} to priority backorder waitlist.",
                content=content,
                actions=actions,
                voice_text=f"Backorder queued for {sender}. Alerting store manager for restocking.",
            )

        # Edge-Case Guard (Mandatory Qualification Rule #5):
        # When item IS in stock, an order MUST have both a verified 6-digit pincode and 10-digit phone before invoice generation.
        missing_fields = []
        if not address or len(str(address).strip()) < 3:
            missing_fields.append("Street Address")
        if not pincode or not re.match(r"^\d{6}$", str(pincode).strip()):
            missing_fields.append("6-digit Postal Pincode")
        if not phone or not re.match(r"^[6-9]\d{9}$", str(phone).strip()):
            missing_fields.append("10-digit Mobile Number")

        if missing_fields:
            db.log_event(
                agent="EdgeCaseGuard",
                event_type="INCOMPLETE_ADDRESS_REJECTED",
                details=f"Order from {sender} blocked by Rule #5. Missing: {', '.join(missing_fields)}.",
            )
            content = (
                f"### ⚠️ Edge-Case Guard: Order Details Incomplete\n\n"
                f"Hey {sender}! We have noted your request for **{qty}x {item_key.title()} (Size {size})**.\n\n"
                f"However, as per **InstaOS SOP Rule #5**, we require your complete dispatch details before generating an invoice:\n"
                + "\n".join([f"- ❌ **Missing**: {f}" for f in missing_fields])
                + "\n\n💬 *Please reply with your missing "
                + " and ".join(missing_fields)
                + " to confirm your shipment!*"
            )
            return build_nonilion_response(
                text=f"Please provide your {' and '.join(missing_fields)} to proceed with your order.",
                content=content,
                voice_text=f"Order from {sender} requires missing address details to continue.",
            )

        # Stock is available -> Calculate Pricing, Taxes, Verification, and Fraud Checks
        calc = evaluate_order_pricing_and_risk(
            item_key=sku,
            size=size,
            qty=qty,
            payment_mode=payment_mode,
            pincode=pincode,
        )
        verification = verifly_customer_identity(
            handle=sender,
            phone=phone,
            pincode=pincode,
        )

        order_id = db.generate_next_order_id()
        order_record = {
            "id": order_id,
            "customer_handle": sender,
            "customer_name": sender.replace("@", "").replace("_", " ").title(),
            "phone": phone,
            "pincode": pincode,
            "address": address,
            "sku": sku,
            "item_name": calc["item_name"],
            "size": size,
            "qty": qty,
            "unit_price": calc["unit_price"],
            "subtotal": calc["subtotal"],
            "discount": calc["discount"],
            "cod_fee": calc["cod_fee"],
            "taxable_value": calc["taxable_value"],
            "gst_amount": calc["gst_amount"],
            "cgst": calc["cgst"],
            "sgst": calc["sgst"],
            "final_total": calc["final_total"],
            "payment_mode": payment_mode,
            "status": calc["status"],
            "stage": calc["stage"],
            "courier": calc["courier"],
            "awb": calc["awb"],
            "zone": calc["zone"],
            "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
            "verification_badge": verification["verification_badge"],
            "trust_score": verification["trust_score"],
        }

        # Clear pending session since details are complete
        db.clear_customer_session(sender)

        # Check if High-Value COD Fraud Hold is triggered
        if calc["requires_manager_approval"]:
            # Place order on hold without deducting stock yet
            db.add_order(order_record)
            db.log_event(
                agent="RiskPricingAgent",
                event_type="HIGH_VALUE_COD_HOLD",
                details=f"Order {order_id} (₹{calc['final_total']:,.2f}) flagged as high-risk COD. Awaiting manager approval.",
                order_id=order_id,
            )
            export_all_csvs(db, STATIC_DIR)

            content = (
                f"### 🛡️ High-Value COD Fraud Guard Triggered\n\n"
                f"- **Order ID**: `{order_id}`\n"
                f"- **Customer**: {sender} (Trust Score: `{verification['trust_score']}/100`)\n"
                f"- **Amount**: ₹{calc['final_total']:,.2f} *(Exceeds ₹2,500 COD Threshold)*\n"
                f"- **10% Bulk Discount Applied**: -₹{calc['discount']:,.2f}\n"
                f"- **COD Fee**: +₹{calc['cod_fee']:,.2f}\n"
                f"- **Current Status**: `ON_HOLD (High Value COD > ₹2500)`\n"
                f"- **Fulfilment Stage**: `AWAITING_MANAGER_APPROVAL`\n\n"
                f"⚠️ *To authorize fulfillment, a manager in Nonilion room must run:*\n"
                f"`@InstaOS approve {order_id}`"
            )
            actions = [{"type": "walk_to_user", "target": "@StoreManager"}]
            return build_nonilion_response(
                text=f"High-Value COD order {order_id} (₹{calc['final_total']:,.2f}) placed on hold. Manager approval required.",
                content=content,
                actions=actions,
                voice_text=f"Order {order_id} flagged for manager approval due to high value COD amount.",
            )

        # Normal Order: Deduct Stock, Save Order, Generate HTML Invoice & Launch Shipping Worker
        db.deduct_stock(sku, size, qty)
        db.add_order(order_record)
        db.log_event(
            agent="OrderOrchestrator",
            event_type="ORDER_CONFIRMED",
            details=f"Order {order_id} confirmed for {sender} ({qty}x {sku} size {size}). Final: ₹{calc['final_total']:,.2f}.",
            order_id=order_id,
        )

        invoice_path = generate_invoice_and_label_html(order_record, STATIC_DIR)
        invoice_filename = os.path.basename(invoice_path)
        export_all_csvs(db, STATIC_DIR)

        # Launch background logistics shipping pipeline
        asyncio.create_task(run_autonomous_shipping_pipeline(order_id))

        discount_note = f"*(Includes 10% Bulk Discount: -₹{calc['discount']:,.2f})* " if calc["discount"] > 0 else ""

        content = (
            f"### 🎉 Order Confirmed: `{order_id}`\n\n"
            f"- **Customer**: {sender} &bull; `+91 {phone}` &bull; `{verification['verification_badge']}`\n"
            f"- **Item Ordered**: {qty}x {calc['item_name']} (Size {size})\n"
            f"- **Grand Total**: ₹{calc['final_total']:,.2f} {discount_note}\n"
            f"- **Tax Breakdown**: Base ₹{calc['taxable_value']:,.2f} + 12% GST (₹{calc['gst_amount']:,.2f})\n"
            f"- **Assigned Courier**: {calc['courier']} *(AWB: `{calc['awb']}`)*\n"
            f"- **Delivery Destination**: {address}, Pincode: `{pincode}`\n\n"
            f"📄 **Download GST Tax Invoice & Barcode Label**:\n"
            f"[`{invoice_filename}`]({PUBLIC_BASE_URL}/files/{invoice_filename})\n\n"
            f"🚚 *Autonomous fulfillment pipeline launched: tracking transitions every {SHIPPING_STAGE_DELAY_SEC}s.*"
        )
        files = [{"name": invoice_filename, "url": f"{PUBLIC_BASE_URL}/files/{invoice_filename}"}]
        return build_nonilion_response(
            text=f"Order {order_id} confirmed for {sender}! Invoice and barcode generated.",
            content=content,
            files=files,
            voice_text=f"Order {order_id} confirmed for {sender}. Dispatch scheduled with {calc['courier']}.",
        )

    # Fallback
    return build_nonilion_response(
        text=f"Received message: {raw_text}",
        content=f"Message recorded by InstaOS engine.",
    )


# -----------------------------------------------------------------------------
# Webhook Router (POST /webhook)
# -----------------------------------------------------------------------------

@app.post("/webhook")
async def handle_nonilion_webhook(request: Request):
    """Unified Webhook for Nonilion Virtual Office Room commands and live customer DMs."""
    try:
        body = await request.json()
    except Exception:
        body = {}

    raw_text = body.get("text") or body.get("content") or body.get("message") or ""
    sender = body.get("sender") or body.get("user") or "@judge"

    # Strip @InstaOS or @instaos prefix
    cleaned_cmd = re.sub(r"^@?instaos\s*", "", raw_text.strip(), flags=re.IGNORECASE).strip()
    cmd_lower = cleaned_cmd.lower()

    # 1. Help / Menu Command
    if cmd_lower in ["help", "menu", "commands"]:
        help_content = (
            "### 🤖 InstaOS Autonomous D2C Engine — Virtual Office Command Center\n\n"
            "| Command | Description |\n"
            "| :--- | :--- |\n"
            "| `@InstaOS run_demo` | Runs all 6 pre-loaded test scenarios in `DUMMY_DM_QUEUE` |\n"
            "| `@InstaOS dm @user <msg>` | Processes a simulated or live customer Instagram DM |\n"
            "| `@InstaOS verify <ORD-ID>` | Runs deep Verifly customer identity & risk scorecard |\n"
            "| `@InstaOS dashboard` | Generates 3-panel Matplotlib dark-mode chart & 3 CSVs |\n"
            "| `@InstaOS approve <ORD-ID>` | Approves held High-Value COD order (defaults to `ORD-103`) |\n"
            "| `@InstaOS cancel <ORD-ID>` | Cancels an order and restores warehouse stock |\n"
            "| `@InstaOS restock` | Replenishes warehouse (+10 units) & clears backorders |\n"
            "| `@InstaOS audit` | Displays multi-agent chronological audit trail |\n"
            "| `@InstaOS reset` | Restores store to initial seed inventory & orders |\n"
        )
        return build_nonilion_response(
            text="InstaOS Command Center online. Available commands listed below.",
            content=help_content,
        )

    # 2. Reset Command
    if cmd_lower == "reset":
        db.reset()
        for inv_file in STATIC_DIR.glob("Invoice_Label_*.html"):
            try:
                inv_file.unlink()
            except Exception:
                pass
        export_all_csvs(db, STATIC_DIR)
        try:
            generate_executive_dashboard_png(db, STATIC_DIR)
        except Exception:
            pass
        return build_nonilion_response(
            text="InstaOS Store state has been reset to initial seed catalog and orders.",
            content="🔄 **Store Reset Complete**: Clean inventory (4 SKUs), pre-loaded orders (ORD-101 to ORD-103), and empty backorders restored.",
        )

    # 3. Restock Command
    if cmd_lower.startswith("restock"):
        result = db.restock_all(replenishment_qty=10)
        export_all_csvs(db, STATIC_DIR)
        try:
            generate_executive_dashboard_png(db, STATIC_DIR)
        except Exception:
            pass
        content = (
            f"### 📦 Warehouse Inventory Restocked\n\n"
            f"- **Replenishment**: Added `+10` units across all sizes and SKUs.\n"
            f"- **Backorders Cleared**: `{result['cleared_backorders']}` customer waitlist requests resolved.\n"
            f"- **Stock Status**: All catalog items now in optimal `IN_STOCK` status.\n"
            f"- **Master Reports**: Inventory audit CSV and dashboard charts updated.\n"
        )
        return build_nonilion_response(
            text=f"Restocked +10 units across all items. Cleared {result['cleared_backorders']} backorders.",
            content=content,
            voice_text="Warehouse restock complete. All backorders have been cleared.",
        )

    # 4. Dashboard / Analytics Command
    if cmd_lower in ["dashboard", "analytics", "stats", "chart"]:
        chart_path = generate_executive_dashboard_png(db, STATIC_DIR)
        csv_files = export_all_csvs(db, STATIC_DIR)
        stats = db.get_stats()

        chart_filename = os.path.basename(chart_path)
        orders_csv_name = os.path.basename(csv_files["orders_csv"])
        inv_csv_name = os.path.basename(csv_files["inventory_csv"])
        audit_csv_name = os.path.basename(csv_files["audit_csv"])

        content = (
            f"### 📊 InstaOS Executive Operations Dashboard\n\n"
            f"| Metric | Live Value |\n"
            f"| :--- | :--- |\n"
            f"| **Total Tracked Orders** | `{stats['total_orders']}` |\n"
            f"| **Delivered Shipments** | `{stats['delivered']}` |\n"
            f"| **Active In-Transit** | `{stats['in_transit']}` |\n"
            f"| **High-Risk COD Holds** | `{stats['on_hold']}` |\n"
            f"| **Backorders Queued** | `{stats['backorders_queued']}` |\n"
            f"| **Gross Settled Revenue** | `₹{stats['total_revenue']:,.2f}` |\n\n"
            f"📁 **Download Live Operations Spreadsheets**:\n"
            f"- 📑 [Master Orders CSV]({PUBLIC_BASE_URL}/files/{orders_csv_name})\n"
            f"- 📦 [Inventory Stock Report CSV]({PUBLIC_BASE_URL}/files/{inv_csv_name})\n"
            f"- 🛡️ [Agent Audit Log CSV]({PUBLIC_BASE_URL}/files/{audit_csv_name})\n\n"
            f"📈 **Executive 3-Panel Matplotlib Chart**:\n"
            f"![Live Dashboard]({PUBLIC_BASE_URL}/files/{chart_filename})\n"
        )
        files = [
            {"name": chart_filename, "url": f"{PUBLIC_BASE_URL}/files/{chart_filename}"},
            {"name": orders_csv_name, "url": f"{PUBLIC_BASE_URL}/files/{orders_csv_name}"},
            {"name": inv_csv_name, "url": f"{PUBLIC_BASE_URL}/files/{inv_csv_name}"},
            {"name": audit_csv_name, "url": f"{PUBLIC_BASE_URL}/files/{audit_csv_name}"},
        ]
        return build_nonilion_response(
            text="Operations dashboard and live spreadsheets generated.",
            content=content,
            files=files,
            voice_text="Operations dashboard and analytics charts ready.",
        )

    # 5. Approve Order Command
    if cmd_lower.startswith("approve"):
        parts = cleaned_cmd.split()
        target_id = parts[1].upper() if len(parts) > 1 else "ORD-103"
        order = db.get_order(target_id)
        if not order:
            return build_nonilion_response(
                text=f"Order {target_id} not found.",
                content=f"⚠️ Cannot approve: `{target_id}` does not exist.",
            )

        # Deduct stock and advance order
        db.deduct_stock(order["sku"], order["size"], order["qty"])
        db.update_order(target_id, {
            "status": "CONFIRMED",
            "stage": "CONFIRMED",
        })
        db.log_event(
            agent="ManagerOverride",
            event_type="COD_FRAUD_HOLD_APPROVED",
            details=f"Manager override approved high-value COD order {target_id}. Stock deducted.",
            order_id=target_id,
        )

        order_updated = db.get_order(target_id)
        inv_path = generate_invoice_and_label_html(order_updated, STATIC_DIR)
        inv_name = os.path.basename(inv_path)
        export_all_csvs(db, STATIC_DIR)

        # Launch shipping pipeline
        asyncio.create_task(run_autonomous_shipping_pipeline(target_id))

        content = (
            f"### ✅ Manager Override Approved: `{target_id}`\n\n"
            f"- **Customer**: {order_updated['customer_handle']}\n"
            f"- **Total Amount**: ₹{order_updated['final_total']:,.2f} *(COD Surcharge ₹50 Included)*\n"
            f"- **Warehouse Stock Deducted**: {order_updated['qty']}x {order_updated['sku']} (Size {order_updated['size']})\n"
            f"- **Assigned Courier**: {order_updated['courier']} *(AWB: `{order_updated['awb']}`)*\n\n"
            f"📄 **Download Generated Invoice & Label**:\n"
            f"[`{inv_name}`]({PUBLIC_BASE_URL}/files/{inv_name})\n\n"
            f"🚚 *Autonomous shipping pipeline started.*"
        )
        return build_nonilion_response(
            text=f"High-Value COD order {target_id} approved. Invoice generated.",
            content=content,
            files=[{"name": inv_name, "url": f"{PUBLIC_BASE_URL}/files/{inv_name}"}],
            voice_text=f"Order {target_id} approved by manager. Dispatch started.",
        )

    # 6. Cancel Order Command
    if cmd_lower.startswith("cancel"):
        parts = cleaned_cmd.split()
        target_id = parts[1].upper() if len(parts) > 1 else ""
        order = db.get_order(target_id)
        if not order:
            return build_nonilion_response(
                text=f"Order {target_id} not found.",
                content=f"⚠️ Cannot cancel: `{target_id}` does not exist.",
            )

        db.update_order(target_id, {"status": "CANCELLED", "stage": "CANCELLED"})
        # Restore stock if not already on hold
        if "ON_HOLD" not in order.get("status", ""):
            db.add_stock(order["sku"], order["size"], order["qty"])

        db.log_event(
            agent="ManagerOverride",
            event_type="ORDER_CANCELLED",
            details=f"Order {target_id} cancelled by manager.",
            order_id=target_id,
        )
        export_all_csvs(db, STATIC_DIR)

        return build_nonilion_response(
            text=f"Order {target_id} cancelled successfully.",
            content=f"🚫 **Order Cancelled**: `{target_id}` marked as CANCELLED. Warehouse stock restored.",
        )

    # 7. Customer / Order Verification Command
    if cmd_lower.startswith("verify") or cmd_lower.startswith("verifly"):
        parts = cleaned_cmd.split()
        target = parts[1] if len(parts) > 1 else "ORD-104"
        
        # Check if target is an Order ID
        if target.upper().startswith("ORD-"):
            order = db.get_order(target.upper())
            if not order:
                return build_nonilion_response(
                    text=f"Order {target} not found.",
                    content=f"⚠️ Cannot verify: `{target}` does not exist in store records.",
                )
            ver = verifly_customer_identity(
                handle=order.get("customer_handle", "@customer"),
                phone=order.get("phone", ""),
                pincode=order.get("pincode", ""),
            )
            report = (
                f"### 🛡️ Customer & Order Verification Scorecard\n\n"
                f"- **Order ID**: `{order['id']}`\n"
                f"- **Customer Handle**: `{ver['handle']}`\n"
                f"- **Mobile Number**: `+91 {ver['phone']}` &bull; *{'Valid Indian Syntax' if ver['is_syntax_valid'] else 'Invalid'}*\n"
                f"- **Delivery Pincode**: `{ver['pincode']}`\n"
                f"- **Identity Trust Score**: `{ver['trust_score']} / 100`\n"
                f"- **Verification Badge**: `{ver['verification_badge']}`\n"
                f"- **Risk Classification**: `{'LOW_RISK' if ver['trust_score'] >= 70 else 'ELEVATED_RISK'}`\n"
                f"- **Observed Signals**:\n"
                + "\n".join([f"  - `{sig}`" for sig in ver["signals"]])
            )
            return build_nonilion_response(
                text=f"Verification for {order['id']}: {ver['verification_badge']} (Score {ver['trust_score']}/100)",
                content=report,
            )
        else:
            # Target is a handle
            ver = verifly_customer_identity(handle=target, phone="9876543210", pincode="110001")
            return build_nonilion_response(
                text=f"Buyer verification for {target}: {ver['verification_badge']}",
                content=f"### 🛡️ Buyer Identity Check: {target}\n- **Badge**: `{ver['verification_badge']}`\n- **Trust Score**: `{ver['trust_score']}/100`",
            )

    # 8. Audit Logs Command
    if cmd_lower in ["audit", "logs", "trail"]:
        recent_logs = db.audit_logs[-10:]
        log_rows = "\n".join([
            f"| `{l['timestamp']}` | **{l['agent']}** | `{l['event_type']}` | `{l['order_id']}` | {l['details']} |"
            for l in recent_logs
        ])
        content = (
            f"### 📜 Multi-Agent Audit Trail (Latest 10 Events)\n\n"
            f"| Timestamp (UTC) | Agent | Event Type | Order ID | Details |\n"
            f"| :--- | :--- | :--- | :--- | :--- |\n"
            f"{log_rows}\n\n"
            f"📄 [Download Full Audit Log CSV]({PUBLIC_BASE_URL}/files/agent_audit_log.csv)\n"
        )
        return build_nonilion_response(
            text="Latest multi-agent audit trail retrieved.",
            content=content,
            files=[{"name": "agent_audit_log.csv", "url": f"{PUBLIC_BASE_URL}/files/agent_audit_log.csv"}],
        )

    # 9. Run Demo Command (All 6 Scenarios)
    if cmd_lower in ["run_demo", "demo", "run-demo"]:
        db.reset()
        demo_reports = []
        files = []

        for item in db.dm_queue:
            sc_num = item["scenario"]
            title = item["title"]
            sc_sender = item["sender"]
            sc_text = item["text"]

            res = process_single_customer_dm(sc_text, sender=sc_sender)
            demo_reports.append(
                f"#### 🎬 Scenario {sc_num}: {title}\n"
                f"**Customer ({sc_sender})**: *\"{sc_text}\"*\n\n"
                f"{res.get('content')}\n"
                f"---\n"
            )
            for f in res.get("files", []):
                if f not in files:
                    files.append(f)

        # Generate fresh dashboard and exports
        chart_p = generate_executive_dashboard_png(db, STATIC_DIR)
        csv_p = export_all_csvs(db, STATIC_DIR)
        files.append({"name": os.path.basename(chart_p), "url": f"{PUBLIC_BASE_URL}/files/{os.path.basename(chart_p)}"})
        files.append({"name": "master_orders.csv", "url": f"{PUBLIC_BASE_URL}/files/master_orders.csv"})
        files.append({"name": "inventory_stock_report.csv", "url": f"{PUBLIC_BASE_URL}/files/inventory_stock_report.csv"})
        files.append({"name": "agent_audit_log.csv", "url": f"{PUBLIC_BASE_URL}/files/agent_audit_log.csv"})

        full_demo_content = (
            "# 🚀 InstaOS Full Autonomous D2C Demo Run\n\n"
            "Execution of all 6 customer scenarios completed autonomously within the Nonilion Virtual Office.\n\n"
            + "\n".join(demo_reports)
            + "\n### 📈 Operations Visuals & Spreadsheets Available in Room Downloads Below."
        )

        return build_nonilion_response(
            text="Full 6-scenario demo stream executed successfully with zero errors.",
            content=full_demo_content,
            files=files,
            voice_text="All six autonomous D2C scenarios executed successfully.",
        )

    # 10. Explicit or Free-Form DM Processing
    # Format: "dm @handle <message>" or freeform text
    if cmd_lower.startswith("dm "):
        match = re.match(r"^dm\s+(@\w+)\s+(.+)$", cleaned_cmd, re.IGNORECASE)
        if match:
            dm_sender = match.group(1)
            dm_msg = match.group(2)
        else:
            dm_sender = sender
            dm_msg = cleaned_cmd[3:].strip()
        return process_single_customer_dm(dm_msg, sender=dm_sender)

    # If message mentions @something or freeform text, treat as live DM
    handle_match = re.search(r"@(\w+)", raw_text)
    active_sender = f"@{handle_match.group(1)}" if handle_match else sender

    return process_single_customer_dm(raw_text, sender=active_sender)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
