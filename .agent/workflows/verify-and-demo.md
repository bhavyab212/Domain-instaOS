# Verify and Demo Workflow for InstaOS

This workflow executes automated end-to-end verification, validates all downloadable artifacts in `generated_files/`, and provides ready-to-run curl commands for live Nonilion Virtual Office Room testing.

---

## Step 1: Run Automated Verification Suite
Run the 12-point automated verification script:

```powershell
python scripts/verify_system.py
```

Expected Result:
- All 12 checks print `[CHECK XX/12] PASS: ...`
- Terminal outputs: `ALL 12 VERIFICATION CHECKS PASSED (100% VERIFIED)` with exit code 0.

---

## Step 2: Validate Generated Artifacts
Ensure all files exist and are populated (> 500 bytes) in `generated_files/`:

```powershell
Get-ChildItem generated_files
```

Artifacts to inspect:
- `generated_files/master_orders.csv`
- `generated_files/inventory_stock_report.csv`
- `generated_files/agent_audit_log.csv`
- `generated_files/instaos_live_dashboard.png`
- `generated_files/Invoice_Label_ORD-104.html`
- `generated_files/Invoice_Label_ORD-103.html`

---

## Step 3: Live Testing with Nonilion Webhook (cURL commands)

Start the server:
```powershell
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### 1. Health & Keepalive Check:
```bash
curl -X GET http://localhost:8000/health
```

### 2. Reset Store to Seed State:
```bash
curl -X POST http://localhost:8000/webhook \
  -H "Content-Type: application/json" \
  -d '{"text": "@InstaOS reset"}'
```

### 3. Run Full 6-Scenario Batch Demo:
```bash
curl -X POST http://localhost:8000/webhook \
  -H "Content-Type: application/json" \
  -d '{"text": "@InstaOS run_demo"}'
```

### 4. Process Live Instagram DM:
```bash
curl -X POST http://localhost:8000/webhook \
  -H "Content-Type: application/json" \
  -d '{"text": "@InstaOS dm @rahul_v Bhai acid wash hoodie size M available hai kya?"}'
```

### 5. Verify Customer Identity & Risk:
```bash
curl -X POST http://localhost:8000/webhook \
  -H "Content-Type: application/json" \
  -d '{"text": "@InstaOS verify ORD-104"}'
```

### 6. Generate Live Analytics Dashboard & CSVs:
```bash
curl -X POST http://localhost:8000/webhook \
  -H "Content-Type: application/json" \
  -d '{"text": "@InstaOS dashboard"}'
```

### 7. Approve High-Value COD Fraud Hold:
```bash
curl -X POST http://localhost:8000/webhook \
  -H "Content-Type: application/json" \
  -d '{"text": "@InstaOS approve ORD-103"}'
```

### 8. Restock Inventory and Resolve Backorders:
```bash
curl -X POST http://localhost:8000/webhook \
  -H "Content-Type: application/json" \
  -d '{"text": "@InstaOS restock"}'
```
