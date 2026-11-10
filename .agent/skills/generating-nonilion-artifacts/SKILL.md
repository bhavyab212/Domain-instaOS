---
name: generating-nonilion-artifacts
description: Generates downloadable dark-mode HTML GST tax invoices with AWB barcodes, Master Orders and Inventory Audit CSV spreadsheets, and 3-panel Matplotlib executive PNG charts for Nonilion chat responses. Use when creating or updating file exports, invoices, shipping labels, or dashboard visuals.
---

# Generating Nonilion Artifacts

This skill governs the generation of multi-format deliverables produced by InstaOS for display and download inside Nonilion Virtual Office Rooms.

## Deliverables & Formatting Standards

1. **Dark-Mode GST Tax Invoice & Shipping Label (`.html`)**:
   - Location: `generated_files/Invoice_Label_<ORD_ID>.html`
   - Palette: Slate-900 background (`#0f172a`), Slate-800 container (`#1e293b`), Indigo-500 accent (`#6366f1`).
   - Content:
     - GSTIN: `07AAAAA0000A1Z5`
     - Verification Badge: `VERIFIED_BUYER` (Emerald) or `UNVERIFIED_SYNTAX` (Rose)
     - Itemized pricing breakdown with 12% included GST (CGST 6% + SGST 6%)
     - Courier Zone Assignment & Tracking AWB
     - Visual CSS barcode lines representing the AWB code.

2. **Master CSV Spreadsheets (`.csv`)**:
   - `generated_files/master_orders.csv`: Comprehensive log of all confirmed, held, and delivered orders with full pricing and courier data.
   - `generated_files/inventory_stock_report.csv`: Real-time warehouse inventory levels by SKU, size, unit price, and stock status.
   - `generated_files/agent_audit_log.csv`: Chronological audit trail of all multi-agent actions, state transitions, and manager overrides.

3. **Executive Analytics Dashboard (`.png`)**:
   - Location: `generated_files/instaos_live_dashboard.png`
   - Generated with `matplotlib` using the `Agg` headless backend.
   - 3-Panel Visual Layout:
     - Panel 1: Bar chart of Warehouse Stock by SKU.
     - Panel 2: Pie/Donut chart of Orders by Fulfilment Stage.
     - Panel 3: Revenue comparison bar chart: Prepaid UPI vs COD.
   - Applied dark theme styling matching the Nonilion room aesthetics.
