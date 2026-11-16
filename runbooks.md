# Payment Production Support Runbooks

## ERR_AUTH_TIMEOUT
- **Symptom**: High latency or HTTP 504 timeouts from upstream card scheme gateway.
- **Triage Action**: Query `incident_logs` for `status_code = 504` over the last 15 minutes and verify retry queue depth.
- **Remediation**: Enable circuit-breaker fallback routing and notify merchant technical contacts if error rate exceeds 5%.

## ERR_DB_LOCK
- **Symptom**: Settlement ledger writes failing with lock contention during batch window.
- **Triage Action**: Check active long-running SQL queries on `settlement_ledger` and verify connection pool saturation.
- **Remediation**: Throttle batch worker concurrency and replay queued settlement events once lock clears.

## ERR_WEBHOOK_401
- **Symptom**: Merchant endpoint rejecting webhooks with HTTP 401 Unauthorised.
- **Triage Action**: Inspect recent key rotation timestamps and HMAC signature headers.
- **Remediation**: Re-sync shared webhook signing secret with merchant engineering team and trigger DLQ replay.
