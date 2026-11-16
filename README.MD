# AI Incident Triage & MCP Runbook Agent

When a P1 alert fires during peak payment traffic, the first 10 minutes are usually spent jumping between Datadog logs, SQL queries, and markdown runbooks just to figure out what broke.

I built this lightweight Model Context Protocol (MCP) triage service to automate that first-response step: when an alert webhook arrives, it queries recent SQLite error logs, pulls the relevant remediation steps from `runbooks.md`, and generates a clean triage summary.

## What's Inside

* `triage_agent.py` — Exposes an MCP tool discovery endpoint (`/mcp/tools`) and an alert webhook (`/webhook/alert`) that correlates incoming alerts with local SQL error logs and writes a summary to `triage_report.txt`.
* `runbooks.md` — Structured markdown runbooks covering common payment gateway timeouts, database lock contention, and webhook `401` signature failures.
* `test_triage.py` — Pytest suite verifying MCP tool discovery, runbook lookups, and end-to-end alert correlation.

## Running It Locally

```bash
git clone https://github.com/rma10000/ai-incident-triage-mcp.git
cd ai-incident-triage-mcp

python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
python -m pip install -r requirements.txt

# Run unit tests
python -m pytest -v

# Start the agent and trigger a simulated P1 alert (press Ctrl+C once complete)
python triage_agent.py
```

### Alternative Quick Run (Windows PowerShell)

```powershell
python -m pip install -r requirements.txt; python -m pytest -v; python triage_agent.py
```

## Example Output

```text
=== Automated Incident Triage Summary (P1) ===
Alert Code: ERR_AUTH_TIMEOUT
Correlated Log Events Found: 2
 - [auth-gateway] HTTP 504 | Merchant: merch_uk_01 | Upstream scheme timeout after 3000ms
 - [auth-gateway] HTTP 504 | Merchant: merch_uk_01 | Upstream scheme timeout after 3010ms

--- Recommended Runbook Action ---
## ERR_AUTH_TIMEOUT
- **Symptom**: High latency or HTTP 504 timeouts from upstream card scheme gateway.
- **Triage Action**: Query `incident_logs` for `status_code = 504` over the last 15 minutes and verify retry queue depth.
- **Remediation**: Enable circuit-breaker fallback routing and notify merchant technical contacts if error rate exceeds 5%.

Report saved to triage_report.txt
Task complete. Press Ctrl+C to stop server.
```

## Notes & Next Steps

* **Plug-in LLM Synthesis:** Right now the agent uses deterministic MCP context retrieval so anyone cloning the repo can run it offline with zero API keys. Next step is adding an optional Claude/OpenAI client wrapper to draft customer-facing incident updates from the correlated context.
