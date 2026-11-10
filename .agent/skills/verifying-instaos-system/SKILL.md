---
name: verifying-instaos-system
description: Executes end-to-end automated verification of the InstaOS FastAPI server, UptimeRobot /ping keep-alive endpoint, Nonilion /webhook commands, customer verification checks, and file artifact generation via scripts/verify_system.py. Use after writing or modifying any backend code to prove runtime correctness.
---

# Verifying InstaOS System

This skill defines the automated quality gate for validating the InstaOS multi-agent backend before submitting or declaring tasks complete.

## Verification Protocol

1. **Test Runner**:
   - Location: `scripts/verify_system.py`
   - Uses FastAPI's `TestClient` to execute end-to-end integration tests without spinning up an external process.
   - Enforces 12 distinct checks covering every endpoint and operational workflow.

2. **The 12 Mandatory Checks**:
   - Check 01: Health & Ping endpoints return HTTP 200 and `"status": "ONLINE"`.
   - Check 02: `@InstaOS reset` command returns store to clean initial seed state.
   - Check 03: Scenario 1 (Hinglish product inquiry) parses and replies with real stock & pricing.
   - Check 04: Scenario 2 (Incomplete address DM) triggers EdgeCaseGuard without creating premature invoices.
   - Check 05: Scenario 3 (Complete prepaid order) confirms order `ORD-104`, deducts inventory, generates HTML invoice.
   - Check 06: Scenario 4 (Out-of-stock XL hoodie) places item on backorder waitlist and triggers `walk_to_user` alert.
   - Check 07: Scenario 5 (High-value COD > ₹2,500) places order on `AWAITING_MANAGER_APPROVAL` fraud hold.
   - Check 08: `@InstaOS verify ORD-104` returns buyer & pincode verification scorecard.
   - Check 09: `@InstaOS approve ORD-103` releases COD fraud hold and triggers logistics worker.
   - Check 10: `@InstaOS restock` adds stock and resolves queued backorders.
   - Check 11: `@InstaOS dashboard` generates `instaos_live_dashboard.png` and all 3 CSVs (verifying `size > 500` bytes).
   - Check 12: `@InstaOS run_demo` processes all 6 queued scenarios sequentially with zero failures.

3. **Execution Command**:
   ```bash
   python scripts/verify_system.py
   ```
   Must conclude with:
   `ALL 12 VERIFICATION CHECKS PASSED (100% VERIFIED)`
