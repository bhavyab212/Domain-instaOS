"""Autonomous Logistics & Courier Worker advancing confirmed orders through fulfillment stages."""

import asyncio
import logging
from typing import Optional

from app.config import SHIPPING_STAGE_DELAY_SEC, STATIC_DIR
from app.database.store import db
from app.generators.csv_exporter import export_all_csvs
from app.agents.nonilion_office_client import push_async_room_notification

logger = logging.getLogger("LogisticsWorker")


async def run_autonomous_shipping_pipeline(order_id: str, delay_sec: Optional[int] = None):
    """Background coroutine that advances order through PACKED -> IN_TRANSIT -> OUT_FOR_DELIVERY -> DELIVERED."""
    delay = delay_sec if delay_sec is not None else SHIPPING_STAGE_DELAY_SEC
    stages = [
        ("PACKED", "Order packed in custom streetwear poly-mailer with barcode label attached."),
        ("IN_TRANSIT", "Handed over to courier hub and scanned into line-haul air express network."),
        ("OUT_FOR_DELIVERY", "Courier delivery rider assigned for final destination drop."),
        ("DELIVERED", "Package successfully delivered to customer doorstep."),
    ]

    logger.info(f"Starting autonomous shipping pipeline for {order_id} (stage delay: {delay}s)")

    for stage_name, description in stages:
        await asyncio.sleep(delay)
        
        # Verify order still exists and is not cancelled
        order = db.get_order(order_id)
        if not order:
            logger.warning(f"Order {order_id} no longer exists. Halting shipping pipeline.")
            break
        if "CANCELLED" in order.get("status", ""):
            logger.info(f"Order {order_id} was cancelled. Halting shipping pipeline.")
            break

        db.update_order(order_id, {"stage": stage_name})
        db.log_event(
            agent="LogisticsWorker",
            event_type="STAGE_UPDATE",
            details=f"[{stage_name}] {description} (Courier: {order.get('courier')}, AWB: {order.get('awb')})",
            order_id=order_id,
        )

        # Regenerate master CSVs
        try:
            export_all_csvs(db, STATIC_DIR)
        except Exception as exc:
            logger.error(f"Failed to export CSVs during stage update: {exc}")

        # Push notification to Nonilion room
        room_payload = {
            "text": f"🚚 Order {order_id} update: {stage_name}",
            "content": f"### 🚚 Autonomous Fulfillment Update\n\n**Order:** `{order_id}`\n**Courier:** {order.get('courier')} (AWB: `{order.get('awb')}`)\n**New Stage:** `{stage_name}`\n\n_{description}_",
            "files": [],
            "actions": [],
            "voice_text": f"Order {order_id} has advanced to {stage_name.lower().replace('_', ' ')}.",
        }
        await push_async_room_notification(room_payload)

    logger.info(f"Autonomous shipping pipeline completed for {order_id}.")
