---
name: orchestrating-d2c-orders
description: Parses Hinglish and English Instagram DMs, validates customer phone, pincode, and email/UTR authenticity, computes GST and 10% bulk discounts, enforces high-value COD fraud holds above 2500 INR, and manages inventory and backorders. Use when modifying DM parsing, order state transitions, pricing math, or fraud rules.
---

# Orchestrating D2C Orders

This skill guides the implementation and lifecycle of direct-to-consumer Instagram orders handled by InstaOS.

## Core Capabilities

1. **Hinglish & English NLP Extraction**:
   - Parses incoming customer DMs into structured entities: `intent`, `item_key`, `size`, `qty`, `payment_mode`, `address`, `pincode`, `phone`, `order_id`.
   - Executes with a 4.0-second timeout on open-source LLM calls with a deterministic regex safety net.

2. **Customer Identity & Address Verification**:
   - Validates 10-digit Indian phone syntax (`^[6-9]\d{9}$`).
   - Validates 6-digit Indian postal pincodes (`^\d{6}$`).
   - Rejects disposable email patterns or synthetic handle noise.
   - Enforces Mandatory Qualification Rule #5: Incomplete addresses missing a phone number or pincode are caught with an EdgeCaseGuard, preventing premature invoices.

3. **Pricing & Tax Calculations**:
   - Base Price inclusive of 12% GST (`gst_amount = round(total * 12 / 112, 2)`).
   - 10% Volume Bulk Discount when `qty >= 3`.
   - ₹50 COD Fee for Cash-on-Delivery orders (Prepaid has ₹0 surcharge).

4. **Risk & Fraud Controls**:
   - High-Value COD Hold: Any COD order exceeding ₹2,500 is assigned status `ON_HOLD (High Value COD > ₹2500)` and stage `AWAITING_MANAGER_APPROVAL`.
   - Requires explicit manager approval (`@InstaOS approve <ORD_ID>`) before stock deduction and packing label creation.

5. **Inventory & Backorders**:
   - Checks available stock for requested size.
   - If stock is 0, registers customer into `backorders` queue and triggers a Nonilion room `walk_to_user` alert.
   - When restocked via `@InstaOS restock`, automatically fulfills queued backorders.
