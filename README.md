# 🚀 InstaOS Autonomous Engine
### Autonomous Instagram D2C Order-to-Delivery Operating System
**INNOVORTEX 4.0 — Nonilion Track Hackathon**  
*Controlled entirely inside a Nonilion.com Virtual Office Room.*

[![Python Version](https://img.shields.io/badge/python-3.11%20%7C%203.12-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115.0-009688.svg?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Architecture](https://img.shields.io/badge/Architecture-Autonomous%20Multi--Agent-indigo.svg)](https://nonilion.com)
[![Verification](https://img.shields.io/badge/Verification-12%2F12%20Checks%20Passed%20(100%25)-success.svg)](scripts/verify_system.py)
[![Keepalive](https://img.shields.io/badge/Uptime-Zero%20Cold%20Start-brightgreen.svg)](https://uptimerobot.com)

---

## 1. System Vision & Overview

**InstaOS** turns any Instagram Direct Message channel into a fully autonomous, zero-human-touch direct-to-consumer (D2C) streetwear enterprise managed from inside a **Nonilion Virtual Office Room**.

- **No live Meta/Instagram Graph API token required**: Operates autonomously on simulated and judge-dispatched customer DM streams.
- **Hybrid AI + Deterministic Safety Net**: NLP extraction uses open-source LLMs (`LLM_BASE_URL`, `LLM_API_KEY`, `LLM_MODEL`) with a strict **4.0-second timeout**, backed by an exhaustive **deterministic Python regex fallback** that guarantees 100% demo uptime under rate limits or offline conditions.
- **Autonomous D2C Business Logic**: Enforces Mandatory Rule #5 Incomplete Address Guards, Out-of-Stock Backorder Queuing, 10% Bulk Discounts, ₹50 COD fees, 12% included GST, Pincode-to-Courier zone routing (Delhivery, BlueDart, XpressBees), and High-Value COD Fraud Holds (> ₹2,500).
- **Multi-Format Deliverables**: Autonomously produces dark-mode HTML GST Invoices with visual AWB barcodes, 3 Master CSVs, and 3-panel Matplotlib operational dashboard charts.
- **Zero Cold Starts**: Includes `/ping` and `/health` endpoints for UptimeRobot (5-min HTTP monitor) plus an internal `asyncio` self-keepalive task that pings `PUBLIC_BASE_URL/ping` every 10 minutes.

---

## 2. System Architecture

```mermaid
flowchart TD
    A["Nonilion Virtual Office Room / Judge DM"] -->|HTTP POST /webhook| B["FastAPI Main Router (app/main.py)"]
    B --> C["DM Parser Sub-Agent (dm_parser_agent.py)"]
    C -->|LLM API (4s Timeout)| D["OpenAI-Compatible LLM Extraction"]
    C -->|Deterministic Fallback| E["Deterministic Regex NLP Engine"]
    
    D --> F["Structured Intent & Order Spec"]
    E --> F
    
    F --> G{"Intent Router"}
    G -->|INQUIRY| H["Stock & Pricing Response"]
    G -->|NEW_ORDER| I["Rule #5 Incomplete Address Guard"]
    G -->|TRACK_ORDER| J["Order Tracking & Courier ETA"]
    G -->|ADMIN COMMANDS| K["Approval, Restock, Dashboard, Audit"]

    I -->|Missing Phone or Pincode| L["EdgeCaseGuard: Clarification DM"]
    I -->|Complete Details| M["Risk & Pricing Agent (risk_pricing_agent.py)"]

    M --> N["Verifly Customer & Syntax Validation"]
    M --> O["Bulk Discount (10% for 3+ units) & 12% GST Calc"]
    M --> P["Courier Zone Routing (Delhivery / BlueDart / XpressBees)"]
    M --> Q{"COD Fraud Check (> ₹2,500)"}

    Q -->|COD > ₹2,500| R["High-Value COD Hold (AWAITING_MANAGER_APPROVAL)"]
    Q -->|Prepaid or Approved COD| S["Confirm Order & Deduct Inventory"]
    
    S --> T["Generators Engine (HTML Invoices, CSVs, PNG Dashboard)"]
    S --> U["Autonomous Logistics Worker (Background Async Coroutine)"]
    U -->|15s Cycle| V["PACKED -> IN_TRANSIT -> OUT_FOR_DELIVERY -> DELIVERED"]
    V --> W["Live Nonilion Room Broadcasts"]

    subgraph Resilience & Keepalive
        X["UptimeRobot (5-min HTTP monitor)"] -->|GET /ping| B
        Y["Internal Async Keepalive Task"] -->|GET /ping every 10 min| B
    end
```

---

## 3. The 4 Specialized Sub-Agents

1. **`DMParserAgent` (`app/agents/dm_parser_agent.py`)**:
   - Parses Hinglish & English messages into structured parameters (`intent`, `item_key`, `size`, `qty`, `payment_mode`, `address`, `pincode`, `phone`, `order_id`).
   - Governed by a 4.0-second timeout with deterministic regex extraction fallback.
2. **`RiskPricingAgent` (`app/agents/risk_pricing_agent.py`)**:
   - Customer identity verification (`verifly`): Validates 10-digit Indian mobile syntax (`^[6-9]\d{9}$`) and 6-digit postal pincodes (`^\d{6}$`).
   - Pricing Engine: Calculates 10% volume discount for 3+ items, ₹50 COD surcharge, and 12% included GST (CGST 6% + SGST 6%).
   - Courier Zone Router: Maps pincode prefix to Delhivery Air (`DL...`), BlueDart Priority (`BD...`), or XpressBees D2C (`XB...`).
   - Fraud Guard: Holds COD orders > ₹2,500 awaiting human manager approval.
3. **`LogisticsWorker` (`app/agents/logistics_worker.py`)**:
   - Asynchronous fulfillment pipeline advancing orders through `PACKED` $\to$ `IN_TRANSIT` $\to$ `OUT_FOR_DELIVERY` $\to$ `DELIVERED` every 15 seconds.
   - Automatically regenerates master CSVs and broadcasts updates to Nonilion.
4. **`NonilionOfficeClient` (`app/agents/nonilion_office_client.py`)**:
   - Builds Nonilion virtual office payloads with rich Markdown tables, downloadable file attachments, and `walk_to_user` office avatar actions targeting `@StoreManager`.

---

## 4. Operational File Deliverables (`generated_files/`)

| Artifact | File Name | Description |
| :--- | :--- | :--- |
| **Dark-Mode GST Invoice & Barcode Label** | `Invoice_Label_<ORD_ID>.html` | Executive dark-mode invoice with GSTIN `07AAAAA0000A1Z5`, verification badge, itemized tax table, and CSS AWB barcode block. |
| **Master Orders CSV** | `master_orders.csv` | Complete ledger of all confirmed, delivered, and held orders. |
| **Inventory Stock Report CSV** | `inventory_stock_report.csv` | Live stock levels by SKU and size with `IN_STOCK`, `LOW_STOCK`, `OUT_OF_STOCK` tags. |
| **Agent Audit Trail CSV** | `agent_audit_log.csv` | Chronological multi-agent audit trail with timestamps and event details. |
| **3-Panel Dashboard Chart** | `instaos_live_dashboard.png` | Headless Matplotlib PNG showing stock by SKU, order stage donut chart, and revenue. |

---

## 5. Automated Verification Suite (`scripts/verify_system.py`)

Run the complete 12-assertion automated test runner:

```bash
python scripts/verify_system.py
```

### Verification Output:
```text
=================================================================
INSTAOS AUTONOMOUS ENGINE — 12-POINT AUTOMATED VERIFICATION
=================================================================
[CHECK 01/12] PASS: Health & Ping endpoints return HTTP 200 and ONLINE
[CHECK 02/12] PASS: @InstaOS reset restores seed state cleanly
[CHECK 03/12] PASS: Scenario 1 (Hinglish product & stock inquiry) parsed correctly
[CHECK 04/12] PASS: Scenario 2 (Incomplete address DM) caught by EdgeCaseGuard
[CHECK 05/12] PASS: Scenario 3 (Complete prepaid DM) confirms ORD-104 and generates invoice
[CHECK 06/12] PASS: Scenario 4 (Out-of-stock backorder) queued with manager alert action
[CHECK 07/12] PASS: Scenario 5 (High-value COD > ₹2500) enforces fraud hold & bulk discount
[CHECK 08/12] PASS: @InstaOS verify ORD-104 produces buyer verification scorecard
[CHECK 09/12] PASS: @InstaOS approve ORD-103 overrides fraud hold and issues invoice
[CHECK 10/12] PASS: @InstaOS restock adds inventory and clears backorder waitlist
[CHECK 11/12] PASS: Dashboard PNG (140413B) & 3 CSVs (>500B each) generated
[CHECK 12/12] PASS: Full 6-scenario demo stream executes without errors
=================================================================
ALL 12 VERIFICATION CHECKS PASSED (100% VERIFIED)
=================================================================
```

---

## 6. Quickstart & Local Execution

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Run Server
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 3. Webhook Commands (cURL / Nonilion Room)
```bash
# Health Check
curl -X GET http://localhost:8000/health

# Run Full 6-Scenario Batch Demo
curl -X POST http://localhost:8000/webhook -H "Content-Type: application/json" -d '{"text": "@InstaOS run_demo"}'

# Process Live Instagram DM
curl -X POST http://localhost:8000/webhook -H "Content-Type: application/json" -d '{"text": "@InstaOS dm @rahul_v Bhai acid wash hoodie size M available hai kya?"}'

# Generate Analytics Dashboard & CSVs
curl -X POST http://localhost:8000/webhook -H "Content-Type: application/json" -d '{"text": "@InstaOS dashboard"}'

# Approve High-Value COD Fraud Hold
curl -X POST http://localhost:8000/webhook -H "Content-Type: application/json" -d '{"text": "@InstaOS approve ORD-103"}'

# Restock Warehouse (+10 units) & Clear Backorders
curl -X POST http://localhost:8000/webhook -H "Content-Type: application/json" -d '{"text": "@InstaOS restock"}'
```

---

## 7. Cloud Deployment on Render

This project includes a turnkey `render.yaml` and `Procfile`:
- **Service Name**: `instaos-nonilion-engine`
- **Runtime**: Python 3.11
- **Health Check Path**: `/health`
- **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`

### Zero Cold-Start Setup with UptimeRobot
1. Create a free HTTP monitor on [uptimerobot.com](https://uptimerobot.com).
2. Point monitor to: `https://<your-render-url>/ping` (5-minute interval).
3. The internal `asyncio` keepalive task in `app/main.py` provides secondary 10-minute self-ping redundancy.

---

## 8. Repository Structure

```text
.
├── .agent/
│   ├── rules/
│   │   └── instaos-engineering-rules.md
│   ├── workflows/
│   │   └── verify-and-demo.md
│   └── skills/
│       ├── orchestrating-d2c-orders/SKILL.md
│       ├── generating-nonilion-artifacts/SKILL.md
│       └── verifying-instaos-system/SKILL.md
├── nonilion_kb/
│   └── store_policies_and_sop.md
├── scripts/
│   └── verify_system.py
├── app/
│   ├── __init__.py
│   ├── config.py
│   ├── main.py
│   ├── database/
│   │   ├── __init__.py
│   │   ├── seed_data.py
│   │   └── store.py
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── dm_parser_agent.py
│   │   ├── risk_pricing_agent.py
│   │   ├── logistics_worker.py
│   │   └── nonilion_office_client.py
│   └── generators/
│       ├── __init__.py
│       ├── html_artifacts.py
│       ├── csv_exporter.py
│       └── analytics_charts.py
├── requirements.txt
├── Procfile
├── render.yaml
├── .env.example
├── .gitignore
└── README.md
```

---
*Built for INNOVORTEX 4.0 Hackathon — Nonilion Track.*
