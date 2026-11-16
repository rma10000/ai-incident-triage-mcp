import os
import pytest
from fastapi.testclient import TestClient
from triage_agent import app, init_logs_db, mcp_lookup_runbook

TEST_DB = "test_incident_logs.db"

@pytest.fixture(autouse=True)
def setup_test_env():
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)
    init_logs_db(TEST_DB)
    app.state.db_path = TEST_DB
    yield
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)
    if os.path.exists("triage_report.txt"):
        os.remove("triage_report.txt")

client = TestClient(app)

def test_mcp_tool_discovery_and_runbook_lookup():
    tools_res = client.get("/mcp/tools")
    assert tools_res.status_code == 200
    assert tools_res.json().get("protocol") == "mcp-context-provider-v1"

    runbook = mcp_lookup_runbook("ERR_WEBHOOK_401")
    assert "HTTP 401 Unauthorised" in runbook

def test_alert_webhook_correlates_logs_and_runbook():
    res = client.post("/webhook/alert", json={
        "source": "pagerduty",
        "severity": "P1",
        "error_code": "ERR_AUTH_TIMEOUT"
    })
    assert res.status_code == 200
    body = res.json()
    assert body.get("status") == "triaged"
    assert body.get("correlated_events") == 2
    assert "circuit-breaker fallback" in body.get("summary")
