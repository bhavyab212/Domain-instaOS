"""CSV Master Exporters for Orders, Inventory, and Multi-Agent Audit Trails."""

import csv
from pathlib import Path
from typing import Dict, Any


def export_all_csvs(store: Any, output_dir: Path | str) -> Dict[str, str]:
    """Generates master_orders.csv, inventory_stock_report.csv, and agent_audit_log.csv."""
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    orders_path = out_dir / "master_orders.csv"
    inventory_path = out_dir / "inventory_stock_report.csv"
    audit_path = out_dir / "agent_audit_log.csv"

    # 1. Master Orders CSV
    orders_fields = [
        "order_id",
        "customer_handle",
        "phone",
        "pincode",
        "address",
        "sku",
        "item_name",
        "size",
        "qty",
        "subtotal",
        "discount",
        "cod_fee",
        "taxable_value",
        "gst_amount",
        "final_total",
        "payment_mode",
        "status",
        "stage",
        "courier",
        "awb",
        "created_at",
        "verification_badge",
    ]
    with open(orders_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=orders_fields)
        writer.writeheader()
        for oid, order in store.orders.items():
            row = {
                "order_id": order.get("id", oid),
                "customer_handle": order.get("customer_handle", ""),
                "phone": order.get("phone", ""),
                "pincode": order.get("pincode", ""),
                "address": order.get("address", ""),
                "sku": order.get("sku", ""),
                "item_name": order.get("item_name", ""),
                "size": order.get("size", ""),
                "qty": order.get("qty", 1),
                "subtotal": order.get("subtotal", 0.0),
                "discount": order.get("discount", 0.0),
                "cod_fee": order.get("cod_fee", 0.0),
                "taxable_value": order.get("taxable_value", 0.0),
                "gst_amount": order.get("gst_amount", 0.0),
                "final_total": order.get("final_total", 0.0),
                "payment_mode": order.get("payment_mode", "PREPAID"),
                "status": order.get("status", "CONFIRMED"),
                "stage": order.get("stage", "CONFIRMED"),
                "courier": order.get("courier", ""),
                "awb": order.get("awb", ""),
                "created_at": order.get("created_at", ""),
                "verification_badge": order.get("verification_badge", "VERIFIED_BUYER"),
            }
            writer.writerow(row)

    # 2. Inventory Stock Report CSV
    inv_fields = [
        "sku",
        "product_name",
        "category",
        "size",
        "stock_available",
        "unit_price_inr",
        "status",
    ]
    with open(inventory_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=inv_fields)
        writer.writeheader()
        for sku, prod in store.inventory.items():
            for size, stock in prod["stock"].items():
                if stock == 0:
                    status = "OUT_OF_STOCK"
                elif stock <= 2:
                    status = "LOW_STOCK"
                else:
                    status = "IN_STOCK"

                writer.writerow({
                    "sku": sku,
                    "product_name": prod["name"],
                    "category": prod["category"],
                    "size": size,
                    "stock_available": stock,
                    "unit_price_inr": prod["price"],
                    "status": status,
                })

    # 3. Agent Audit Trail CSV
    audit_fields = ["timestamp", "agent", "event_type", "order_id", "details"]
    with open(audit_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=audit_fields)
        writer.writeheader()
        for entry in store.audit_logs:
            writer.writerow({
                "timestamp": entry.get("timestamp", ""),
                "agent": entry.get("agent", ""),
                "event_type": entry.get("event_type", ""),
                "order_id": entry.get("order_id", "-"),
                "details": entry.get("details", ""),
            })

    return {
        "orders_csv": str(orders_path),
        "inventory_csv": str(inventory_path),
        "audit_csv": str(audit_path),
    }
