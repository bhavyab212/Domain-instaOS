"""In-memory thread-safe DataStore for inventory, orders, backorders, and audit trails."""

import copy
import threading
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from app.database.seed_data import INITIAL_INVENTORY, INITIAL_ORDERS, DUMMY_DM_QUEUE


class DataStore:
    def __init__(self):
        self._lock = threading.Lock()
        self.start_time = datetime.now(timezone.utc)
        self.inventory: Dict[str, Any] = {}
        self.orders: Dict[str, Any] = {}
        self.dm_queue: List[Dict[str, Any]] = []
        self.backorders: List[Dict[str, Any]] = []
        self.audit_logs: List[Dict[str, Any]] = []
        self.customer_sessions: Dict[str, Dict[str, Any]] = {}
        self._order_counter = 103
        self.reset()

    def reset(self):
        """Restores store state to clean initial seed data."""
        with self._lock:
            self.inventory = copy.deepcopy(INITIAL_INVENTORY)
            self.orders = copy.deepcopy(INITIAL_ORDERS)
            self.dm_queue = copy.deepcopy(DUMMY_DM_QUEUE)
            self.backorders = []
            self.customer_sessions = {}
            self._order_counter = 103
            self.audit_logs = [
                {
                    "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
                    "agent": "SystemBootstrapped",
                    "event_type": "STORE_RESET",
                    "order_id": "-",
                    "details": "Store state restored to initial seed catalog and orders.",
                }
            ]

    def log_event(self, agent: str, event_type: str, details: str, order_id: str = "-"):
        """Appends an event to the persistent multi-agent audit trail."""
        with self._lock:
            entry = {
                "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
                "agent": agent,
                "event_type": event_type,
                "order_id": order_id or "-",
                "details": details,
            }
            self.audit_logs.append(entry)
            return entry

    def get_product_by_query(self, query: str) -> Optional[Dict[str, Any]]:
        """Finds product by matching name or aliases case-insensitively."""
        q = query.lower()
        with self._lock:
            for sku, prod in self.inventory.items():
                if sku.lower() in q or prod["name"].lower() in q:
                    return prod
                for alias in prod.get("aliases", []):
                    if alias in q:
                        return prod
        return None

    def get_stock(self, sku: str, size: str) -> int:
        """Returns stock for given SKU and size."""
        with self._lock:
            prod = self.inventory.get(sku)
            if not prod:
                return 0
            return prod["stock"].get(str(size).upper(), 0)

    def deduct_stock(self, sku: str, size: str, qty: int) -> bool:
        """Atomically deducts inventory stock if available."""
        with self._lock:
            prod = self.inventory.get(sku)
            if not prod:
                return False
            curr = prod["stock"].get(str(size).upper(), 0)
            if curr >= qty:
                prod["stock"][str(size).upper()] = curr - qty
                return True
            return False

    def add_stock(self, sku: str, size: str, qty: int):
        """Adds stock back to inventory."""
        with self._lock:
            prod = self.inventory.get(sku)
            if prod:
                curr = prod["stock"].get(str(size).upper(), 0)
                prod["stock"][str(size).upper()] = curr + qty

    def restock_all(self, replenishment_qty: int = 10) -> Dict[str, Any]:
        """Adds stock across all SKUs and resolves queued backorders."""
        with self._lock:
            for sku, prod in self.inventory.items():
                for size in prod["stock"]:
                    prod["stock"][size] += replenishment_qty

            cleared_backorders = len(self.backorders)
            self.backorders = []

        self.log_event(
            agent="InventoryAgent",
            event_type="RESTOCK_COMPLETED",
            details=f"Replenished +{replenishment_qty} units across all sizes. Cleared {cleared_backorders} backorders.",
        )
        return {
            "replenished_per_item": replenishment_qty,
            "cleared_backorders": cleared_backorders,
        }

    def generate_next_order_id(self) -> str:
        """Increments and returns next available Order ID (ORD-104, ORD-105...)."""
        with self._lock:
            self._order_counter += 1
            return f"ORD-{self._order_counter}"

    def add_order(self, order: Dict[str, Any]) -> str:
        """Stores a new order."""
        with self._lock:
            order_id = order.get("id") or f"ORD-{self._order_counter + 1}"
            self.orders[order_id] = order
            return order_id

    def get_order(self, order_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves order by ID."""
        with self._lock:
            return copy.deepcopy(self.orders.get(order_id))

    def update_order(self, order_id: str, updates: Dict[str, Any]) -> bool:
        """Updates attributes of an existing order."""
        with self._lock:
            if order_id in self.orders:
                self.orders[order_id].update(updates)
                return True
            return False

    def add_backorder(self, backorder: Dict[str, Any]):
        """Records an out-of-stock backorder."""
        with self._lock:
            backorder["timestamp"] = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
            self.backorders.append(backorder)

    def save_customer_session(self, handle: str, session_data: Dict[str, Any]):
        """Saves intermediate conversation context for multi-turn DMs."""
        with self._lock:
            if handle not in self.customer_sessions:
                self.customer_sessions[handle] = {}
            self.customer_sessions[handle].update(session_data)

    def get_customer_session(self, handle: str) -> Dict[str, Any]:
        """Retrieves pending session context for a handle."""
        with self._lock:
            return copy.deepcopy(self.customer_sessions.get(handle, {}))

    def clear_customer_session(self, handle: str):
        """Clears completed session context."""
        with self._lock:
            if handle in self.customer_sessions:
                del self.customer_sessions[handle]

    def get_stats(self) -> Dict[str, Any]:
        """Computes summary operational metrics."""
        with self._lock:
            total_orders = len(self.orders)
            delivered = sum(1 for o in self.orders.values() if o.get("stage") == "DELIVERED")
            in_transit = sum(1 for o in self.orders.values() if o.get("stage") == "IN_TRANSIT")
            packed = sum(1 for o in self.orders.values() if o.get("stage") == "PACKED")
            on_hold = sum(1 for o in self.orders.values() if "ON_HOLD" in o.get("status", ""))
            total_revenue = sum(o.get("final_total", 0.0) for o in self.orders.values() if "ON_HOLD" not in o.get("status", ""))
            
            return {
                "total_orders": total_orders,
                "delivered": delivered,
                "in_transit": in_transit,
                "packed": packed,
                "on_hold": on_hold,
                "backorders_queued": len(self.backorders),
                "audit_events_logged": len(self.audit_logs),
                "total_revenue": round(total_revenue, 2),
            }


# Singleton database instance
db = DataStore()
