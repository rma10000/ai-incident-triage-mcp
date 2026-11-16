import os
import sqlite3
import threading
import time
import requests
import uvicorn
from fastapi import FastAPI, Request

app = FastAPI(title="AI Incident Triage & MCP Runbook Agent")
DB_PATH = "incident_logs.db"
RUNBOOK_PATH = "runbooks.md"
BASE_URL = "http://" + "127.0.0.1" + ":8001"

def init_logs_db(db_path=DB_PATH):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS incident_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            service TEXT,
            error_code TEXT,
            status_code INTEGER,
            merchant_id TEXT,
            details TEXT
        )
    """)
    sample_logs = [
        ("auth-gateway", "ERR_AUTH_TIMEOUT", 504, "merch_uk_01", "Upstream scheme timeout after 3000ms"),
        ("auth-gateway", "ERR_AUTH_TIMEOUT", 504, "merch_uk_01", "Upstream scheme timeout after 3010ms"),
        ("webhook-dispatcher", "ERR_WEBHOOK_401", 401, "merch_uk_09", "Invalid HMAC signature header"),
        ("settlement-worker", "ERR_DB_LOCK", 500, "internal", "Row lock timeout on settlement_ledger"),
    ]
    cur.executemany(
        "INSERT INTO incident_logs (service, error_code, status_code, merchant_id, details) VALUES (?, ?, ?, ?, ?)",
        sample_logs
    )
    conn.commit()
    conn.close()

def mcp_lookup_runbook(error_code: str, runbook_path=RUNBOOK_PATH) -> str:
    if not os.path.exists(runbook_path):
        return "No runbook file found."
    with open(runbook_path, "r", encoding="utf-8") as f:
        content = f.read()

    sections = content.split("## ")
    for section in sections:
        if section.startswith(error_code):
            return "## " + section.strip()
    return f"No matching runbook entry found for {error_code}."

def mcp_query_recent_logs(error_code: str, db_path=DB_PATH) -> list:
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    rows = cur.execute(
        "SELECT service, status_code, merchant_id, details FROM incident_logs WHERE error_code = ?",
        (error_code,)
    ).fetchall()
    conn.close()
    return rows

@app.get("/mcp/tools")
async def list_mcp_tools():
    return {
        "protocol": "mcp-context-provider-v1",
        "tools": [
            {"name": "lookup_runbook", "description": "Fetches markdown runbook steps for an error code"},
            {"name": "query_recent_logs", "description": "Queries SQLite incident logs by error_code"}
        ]
    }

@app.post("/webhook/alert")
async def handle_alert(request: Request):
    alert = await request.json()
    error_code = alert.get("error_code", "UNKNOWN")
    severity = alert.get("severity", "P2")
    db_path = getattr(app.state, "db_path", DB_PATH)

    matched_logs = mcp_query_recent_logs(error_code, db_path=db_path)
    runbook_guidance = mcp_lookup_runbook(error_code)

    summary_lines = [
        f"=== Automated Incident Triage Summary ({severity}) ===",
        f"Alert Code: {error_code}",
        f"Correlated Log Events Found: {len(matched_logs)}",
    ]
    for svc, status, merch, detail in matched_logs:
        summary_lines.append(f" - [{svc}] HTTP {status} | Merchant: {merch} | {detail}")

    summary_lines.append("\n--- Recommended Runbook Action ---")
    summary_lines.append(runbook_guidance)

    report = "\n".join(summary_lines) + "\n"
    with open("triage_report.txt", "w", encoding="utf-8") as f:
        f.write(report)

    return {
        "status": "triaged",
        "error_code": error_code,
        "correlated_events": len(matched_logs),
        "summary": report
    }

def simulate_alert():
    time.sleep(1.5)
    alert_payload = {
        "source": "datadog-monitor",
        "severity": "P1",
        "error_code": "ERR_AUTH_TIMEOUT",
        "message": "Spike in HTTP 504 gateway timeouts detected"
    }
    res = requests.post(f"{BASE_URL}/webhook/alert", json=alert_payload, timeout=3)
    data = res.json()
    print(data.get("summary"))
    print("Report saved to triage_report.txt")
    print("Task complete. Press Ctrl+C to stop server.")

if __name__ == "__main__":
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
    init_logs_db()
    threading.Thread(target=simulate_alert, daemon=True).start()
    uvicorn.run(app, host="127.0.0.1", port=8001, log_level="error")
