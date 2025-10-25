```json
{
  "id": "chat-passthrough.PROBLEM.1761399356",
  "scope": "agent",
  "key": "PROBLEM",
  "epoch": 1761399356,
  "host_pid": "rreck-MS-7D25:362958",
  "hash": "a6c271f31e45b21c2cd8e9331c5dbce1a5587a92d9ae119a6a18227326e3f1bf",
  "cid": "QmProblem1761399356",
  "aicp": {
    "prov": {
      "issuer": "claude-code",
      "issued_at": 1761399356,
      "vc": "d8f67fad29153b22a775087d20661a7badce8b52fa5d399c8cd07a2696c82a7d"
    },
    "ucon": {
      "must_fix": true,
      "severity": "critical",
      "blockers": []
    },
    "eval": {
      "confidence": 0.95,
      "validation": "user_reported"
    }
  },
  "sources": [],
  "edges": [],
  "metrics": {
    "impact": "high",
    "urgency": "immediate"
  },
  "thresholds": {},
  "tags": [
    "grafana",
    "dashboard",
    "prometheus",
    "metrics",
    "visualization"
  ],
  "sig": "8afdf6284a8247d93e21200dd5cdf4e913792a0a0ac71d58efdc76bdf8812fb9"
}
```

# PROBLEM: Grafana Dashboard Shows No Data

## Issue
User reports Grafana dashboard at http://localhost:3000/d/crewai-chat-passthrough/crewai-chat-passthrough-claude-sonnet-4 displays no data despite:
- Metrics endpoint exposing data at http://localhost:8087/metrics
- Prometheus successfully scraping metrics
- Dashboard imported with 10 panels
- Test messages sent and metrics confirmed

## Root Cause Analysis Needed
1. Prometheus datasource UID mismatch
2. Job name mismatch in queries
3. Prometheus not actually scraping target
4. Time range mismatch
5. Datasource not configured in Grafana

## Evidence
- Metrics visible: `curl http://localhost:8087/metrics | grep crewai_chat_messages_total`
- Multiple users tracked: test_user, test_user_2, test_grafana, dashboard_test
- Dashboard imported successfully (10 panels)
- Poor assumption: datasource UID "prometheus" exists

## Impact
- Dashboard unusable
- No visibility into agent performance
- Monitoring incomplete
- User dissatisfied with implementation quality
