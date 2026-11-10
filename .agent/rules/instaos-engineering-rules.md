# InstaOS Engineering & Multi-Agent Rules

## 1. Zero Unhandled Exceptions
Every incoming HTTP request to the Nonilion Virtual Office webhook endpoint (`POST /webhook`) must execute within a resilient error-handling boundary and return an **HTTP 200** with a valid Nonilion JSON response schema:
```json
{
  "text": "Human-readable chat summary for Nonilion room",
  "content": "Rich markdown details / tables / receipts",
  "files": [
    {"name": "File_Name.ext", "url": "http://.../files/File_Name.ext"}
  ],
  "actions": [
    {"type": "walk_to_user", "target": "@StoreManager"}
  ]
}
```
No unhandled 500 exceptions may ever reach the Nonilion room or judging panel.

## 2. LLM Safety Floor & Deterministic Fallback
1. Always govern open-source LLM API network calls (Groq / Together / Ollama) inside `app/agents/dm_parser_agent.py` with an explicit **4.0-second timeout**.
2. If the API key is missing, invalid, unreachable, times out, or returns HTTP 429 (Rate Limit Exceeded), the parser MUST immediately switch to the built-in deterministic Python regex parser without raising an exception.
3. The deterministic regex fallback must accurately parse all 6 demo scenarios in `DUMMY_DM_QUEUE` and arbitrary user DMs containing product names, sizes, quantities, addresses, phone numbers, and payment modes.

## 3. Dark-Mode Visual Authority
1. All generated HTML invoices and shipping labels (`Invoice_Label_<ORD_ID>.html`) must implement an executive dark-mode theme:
   - Primary Background: `#0f172a` (Slate 900)
   - Card/Surface Background: `#1e293b` (Slate 800)
   - Primary Brand Accent: `#6366f1` (Indigo 500)
   - Success / Verification Accent: `#10b981` (Emerald 500)
   - Border Color: `#334155` (Slate 700)
   - Text Colors: `#f8fafc` (Slate 50) and `#94a3b8` (Slate 400)
2. All Matplotlib dashboard charts (`analytics_charts.py`) must use the non-interactive `Agg` backend and adhere strictly to the dark slate palette with explicit text/tick styling.

## 4. Mandatory Verification Before Completion
Any modification to backend endpoints, agent logic, risk calculations, or file generators MUST be verified by executing:
```bash
python scripts/verify_system.py
```
A code change is only deemed complete when all 12 automated verification checks pass with **100% VERIFIED**.
