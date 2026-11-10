"""Dark-mode GST Tax Invoice and CSS Barcode Shipping Label Generator."""

import os
from pathlib import Path
from typing import Dict, Any


def generate_invoice_and_label_html(order: Dict[str, Any], output_dir: Path | str) -> str:
    """Generates an executive dark-mode HTML document containing GST tax invoice and barcode shipping label."""
    order_id = order.get("id", "ORD-UNKNOWN")
    handle = order.get("customer_handle", "@customer")
    phone = order.get("phone", "N/A")
    pincode = order.get("pincode", "N/A")
    address = order.get("address", "N/A")
    sku = order.get("sku", "SKU-001")
    item_name = order.get("item_name", "Streetwear Item")
    size = order.get("size", "Standard")
    qty = order.get("qty", 1)
    unit_price = order.get("unit_price", 0.0)
    subtotal = order.get("subtotal", unit_price * qty)
    discount = order.get("discount", 0.0)
    cod_fee = order.get("cod_fee", 0.0)
    taxable_val = order.get("taxable_value", 0.0)
    gst_amount = order.get("gst_amount", 0.0)
    cgst = order.get("cgst", round(gst_amount / 2, 2))
    sgst = order.get("sgst", round(gst_amount - cgst, 2))
    final_total = order.get("final_total", 0.0)
    payment_mode = order.get("payment_mode", "PREPAID")
    courier = order.get("courier", "Delhivery Express Air")
    awb = order.get("awb", "DL8821044")
    created_at = order.get("created_at", "2026-11-10 12:00:00")
    badge = order.get("verification_badge", "VERIFIED_BUYER")
    is_verified = (badge == "VERIFIED_BUYER")

    # Generate CSS Barcode Stripes
    # Alternating black/white widths to simulate Code 128 barcode
    bars_html = ""
    pattern = [2, 1, 3, 1, 1, 2, 3, 2, 1, 3, 2, 1, 2, 1, 3, 1, 2, 2, 1, 3, 2, 1, 1, 3, 2, 2, 1, 1, 3, 2]
    for i, w in enumerate(pattern):
        bg = "#ffffff" if i % 2 == 0 else "transparent"
        bars_html += f'<div style="display:inline-block; width:{w * 2}px; height:50px; background-color:{bg}; margin-right:1px;"></div>'

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>InstaOS Invoice & Label - {order_id}</title>
  <style>
    * {{
      box-sizing: border-box;
      margin: 0;
      padding: 0;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
    }}
    body {{
      background-color: #0f172a;
      color: #e2e8f0;
      padding: 30px;
      display: flex;
      justify-content: center;
      align-items: flex-start;
      min-height: 100vh;
    }}
    .invoice-card {{
      background-color: #1e293b;
      border: 1px solid #334155;
      border-radius: 12px;
      max-width: 850px;
      width: 100%;
      padding: 36px;
      box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.5), 0 8px 10px -6px rgba(0, 0, 0, 0.5);
    }}
    .header-row {{
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      border-bottom: 2px solid #334155;
      padding-bottom: 20px;
      margin-bottom: 24px;
    }}
    .brand-title {{
      font-size: 28px;
      font-weight: 800;
      color: #6366f1;
      letter-spacing: -0.5px;
    }}
    .gstin-pill {{
      display: inline-block;
      margin-top: 6px;
      font-size: 11px;
      font-weight: 600;
      letter-spacing: 0.5px;
      color: #94a3b8;
      background: #0f172a;
      padding: 3px 8px;
      border-radius: 4px;
      border: 1px solid #334155;
    }}
    .invoice-meta {{
      text-align: right;
    }}
    .doc-type {{
      font-size: 13px;
      text-transform: uppercase;
      font-weight: 700;
      letter-spacing: 1px;
      color: #6366f1;
    }}
    .order-id {{
      font-size: 22px;
      font-weight: 800;
      color: #f8fafc;
      margin-top: 4px;
    }}
    .badge {{
      display: inline-flex;
      align-items: center;
      padding: 4px 10px;
      font-size: 12px;
      font-weight: 700;
      border-radius: 6px;
      margin-top: 8px;
    }}
    .badge-verified {{
      background-color: rgba(16, 185, 129, 0.15);
      color: #10b981;
      border: 1px solid #10b981;
    }}
    .badge-unverified {{
      background-color: rgba(244, 63, 94, 0.15);
      color: #f43f5e;
      border: 1px solid #f43f5e;
    }}
    .grid-two {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 24px;
      margin-bottom: 24px;
    }}
    .section-box {{
      background: #0f172a;
      border: 1px solid #334155;
      border-radius: 8px;
      padding: 16px;
    }}
    .section-title {{
      font-size: 11px;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 1px;
      color: #94a3b8;
      margin-bottom: 8px;
    }}
    .data-line {{
      font-size: 14px;
      margin-bottom: 4px;
      color: #e2e8f0;
    }}
    .data-line strong {{
      color: #f8fafc;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      margin-top: 10px;
      margin-bottom: 24px;
    }}
    th {{
      background-color: #0f172a;
      color: #94a3b8;
      text-align: left;
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: 0.5px;
      padding: 10px 12px;
      border-bottom: 1px solid #334155;
    }}
    td {{
      padding: 12px;
      border-bottom: 1px solid #334155;
      font-size: 13px;
      color: #cbd5e1;
    }}
    .num {{
      text-align: right;
    }}
    .totals-grid {{
      display: flex;
      justify-content: flex-end;
      margin-bottom: 28px;
    }}
    .totals-table {{
      width: 320px;
    }}
    .totals-table td {{
      padding: 6px 10px;
      font-size: 13px;
      border: none;
    }}
    .grand-total {{
      font-size: 16px;
      font-weight: 800;
      color: #6366f1;
      border-top: 2px solid #6366f1 !important;
      padding-top: 8px !important;
    }}
    /* Shipping Label & Barcode Section */
    .shipping-label {{
      background: #0f172a;
      border: 2px dashed #6366f1;
      border-radius: 10px;
      padding: 20px;
      margin-top: 20px;
    }}
    .label-header {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 14px;
      border-bottom: 1px solid #334155;
      padding-bottom: 10px;
    }}
    .courier-name {{
      font-size: 18px;
      font-weight: 800;
      color: #f8fafc;
    }}
    .pay-tag {{
      background: #6366f1;
      color: white;
      font-size: 12px;
      font-weight: 700;
      padding: 4px 10px;
      border-radius: 4px;
    }}
    .barcode-box {{
      text-align: center;
      background: #0f172a;
      padding: 16px;
      border-radius: 8px;
      border: 1px solid #334155;
      margin-top: 14px;
    }}
    .barcode-bars {{
      display: flex;
      justify-content: center;
      align-items: center;
      height: 50px;
      margin-bottom: 8px;
    }}
    .awb-text {{
      font-family: "Courier New", Courier, monospace;
      font-size: 18px;
      font-weight: 700;
      letter-spacing: 4px;
      color: #f8fafc;
    }}
    .footer-note {{
      margin-top: 24px;
      text-align: center;
      font-size: 11px;
      color: #64748b;
    }}
  </style>
</head>
<body>
  <div class="invoice-card">
    <div class="header-row">
      <div>
        <div class="brand-title">InstaOS Streetwear</div>
        <div class="gstin-pill">GSTIN: 07AAAAA0000A1Z5</div>
        <p style="font-size:12px; color:#94a3b8; margin-top:4px;">InstaOS Apparel Technologies Pvt Ltd &bull; New Delhi</p>
      </div>
      <div class="invoice-meta">
        <div class="doc-type">Official Tax Invoice</div>
        <div class="order-id">{order_id}</div>
        <div style="font-size:12px; color:#94a3b8; margin-top:2px;">Date: {created_at}</div>
        <div>
          <span class="badge {'badge-verified' if is_verified else 'badge-unverified'}">
            {'&#x2713; ' + badge if is_verified else '&#x26A0; ' + badge}
          </span>
        </div>
      </div>
    </div>

    <div class="grid-two">
      <div class="section-box">
        <div class="section-title">Billed & Shipped To</div>
        <div class="data-line"><strong>Handle:</strong> {handle}</div>
        <div class="data-line"><strong>Phone:</strong> +91 {phone}</div>
        <div class="data-line"><strong>Delivery Address:</strong> {address}</div>
        <div class="data-line"><strong>Pincode:</strong> {pincode}</div>
      </div>
      <div class="section-box">
        <div class="section-title">Order Logistics & Payment</div>
        <div class="data-line"><strong>Payment Mode:</strong> {payment_mode}</div>
        <div class="data-line"><strong>Courier Partner:</strong> {courier}</div>
        <div class="data-line"><strong>Tracking AWB:</strong> {awb}</div>
        <div class="data-line"><strong>Channel:</strong> Instagram DM &bull; Nonilion Room</div>
      </div>
    </div>

    <table>
      <thead>
        <tr>
          <th>Item & Description</th>
          <th>SKU</th>
          <th>Size</th>
          <th class="num">Qty</th>
          <th class="num">Unit Price</th>
          <th class="num">Discount</th>
          <th class="num">Taxable Value</th>
          <th class="num">GST (12%)</th>
          <th class="num">Total (INR)</th>
        </tr>
      </thead>
      <tbody>
        <tr>
          <td><strong>{item_name}</strong></td>
          <td><code>{sku}</code></td>
          <td>{size}</td>
          <td class="num">{qty}</td>
          <td class="num">&#8377;{unit_price:,.2f}</td>
          <td class="num">&#8377;{discount:,.2f}</td>
          <td class="num">&#8377;{taxable_val:,.2f}</td>
          <td class="num">&#8377;{gst_amount:,.2f}</td>
          <td class="num"><strong>&#8377;{final_total - cod_fee:,.2f}</strong></td>
        </tr>
      </tbody>
    </table>

    <div class="totals-grid">
      <table class="totals-table">
        <tr>
          <td>Item Subtotal:</td>
          <td class="num">&#8377;{subtotal:,.2f}</td>
        </tr>
        <tr>
          <td>10% Bulk Discount:</td>
          <td class="num" style="color:#10b981;">-&#8377;{discount:,.2f}</td>
        </tr>
        <tr>
          <td>Taxable Value:</td>
          <td class="num">&#8377;{taxable_val:,.2f}</td>
        </tr>
        <tr>
          <td>CGST (6.0%):</td>
          <td class="num">&#8377;{cgst:,.2f}</td>
        </tr>
        <tr>
          <td>SGST (6.0%):</td>
          <td class="num">&#8377;{sgst:,.2f}</td>
        </tr>
        <tr>
          <td>COD Cash Surcharge:</td>
          <td class="num">&#8377;{cod_fee:,.2f}</td>
        </tr>
        <tr class="grand-total">
          <td>Grand Total:</td>
          <td class="num">&#8377;{final_total:,.2f}</td>
        </tr>
      </table>
    </div>

    <!-- Integrated Barcode Shipping Label -->
    <div class="shipping-label">
      <div class="label-header">
        <div>
          <span style="font-size:11px; text-transform:uppercase; color:#94a3b8; font-weight:700;">AIRWAY CARGO DISPATCH</span>
          <div class="courier-name">{courier}</div>
        </div>
        <div>
          <span class="pay-tag">{payment_mode}</span>
        </div>
      </div>
      <div style="font-size:13px; color:#cbd5e1; margin-bottom:8px;">
        <strong>Deliver To:</strong> {address}, Pincode: <strong>{pincode}</strong> &bull; Contact: <strong>+91 {phone}</strong>
      </div>
      <div class="barcode-box">
        <div class="barcode-bars">
          {bars_html}
        </div>
        <div class="awb-text">*{awb}*</div>
        <div style="font-size:11px; color:#94a3b8; margin-top:4px;">STANDARD AIR EXPRESS SCAN CODE</div>
      </div>
    </div>

    <div class="footer-note">
      This is a computer-generated tax invoice & shipping slip created autonomously by <strong>InstaOS</strong> within the <strong>Nonilion Virtual Office</strong>.
    </div>
  </div>
</body>
</html>
"""
    out_path = Path(output_dir) / f"Invoice_Label_{order_id}.html"
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    return str(out_path)
