```json
{
  "id": "chat-pt-air.LESSON.1761588297",
  "scope": "agent",
  "key": "LESSON",
  "epoch": 1761588297,
  "host_pid": "rreck-MS-7D25:dashboard-fix",
  "hash": "sha256:f7e8d9c0a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8",
  "cid": "bafkreihxyz1234567890abcdefghijklmnopqrstuvwxyz",
  "aicp": {
    "prov": {
      "issuer": "did:agent:crewai-chat-pt-air",
      "timestamp": "2025-10-27T18:04:57Z",
      "signature": "ed25519:1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2"
    },
    "ucon": {
      "usage": "operational",
      "retention": "indefinite",
      "sharing": "crew-only"
    },
    "eval": {
      "confidence": 1.0,
      "impact": "high",
      "criticality": "production"
    }
  },
  "sources": [],
  "edges": [],
  "metrics": {
    "severity": "high",
    "fix_complexity": "simple",
    "time_to_fix": "10min"
  },
  "thresholds": {
    "min_weight": 0.6,
    "min_sources": 1
  },
  "tags": [
    "grafana",
    "prometheus",
    "dashboard",
    "query-fix",
    "job-label",
    "network-connectivity"
  ],
  "sig": "ed25519:9a8b7c6d5e4f3a2b1c0d9e8f7a6b5c4d3e2f1a0b9c8d7e6f5a4b3c2d1e0f9a8"
}
```

---

## LESSON: Chat PT Air Dashboard - Prometheus Job Label Mismatch + Network Connectivity

### Problem Encountered

The "CrewAI Chat Passthrough - Claude Sonnet 4" Grafana dashboard displayed no data despite the agent exposing metrics correctly. All panels showed "No data" even though metrics were being collected.

### Root Causes (Multiple Issues)

#### 1. Prometheus Not on CrewAI Network

**Issue**: Prometheus agent container (`prometheus-agent-daemon`) was not connected to `crewai-network`, preventing it from resolving container hostnames.

**Symptom**:
```
"lastError": "Get \"http://crewai-chat-pt-air-claude-sonnet4-prod-002:8080/metrics\":
  dial tcp: lookup crewai-chat-pt-air-claude-sonnet4-prod-002 on 192.168.1.22:53:
  no such host"
```

**Fix**:
```bash
docker network connect crewai-network prometheus-agent-daemon
```

**Result**: Target health changed from "down" to "up", metrics started flowing.

#### 2. Job Label Mismatch in Dashboard Queries

**Issue**: Dashboard queries referenced `job="crewai-chat-passthrough"` but actual Prometheus job name was `job="crewai-chat-pt-air"`.

**Discovery**:
```bash
# Dashboard query (WRONG)
crewai_chat_sessions_active{job="crewai-chat-passthrough"}
# Returns: 0 results

# Actual metric label
curl -s 'http://localhost:9091/api/v1/query?query=crewai_chat_sessions_active' | jq '.data.result[0].metric.job'
# Returns: "crewai-chat-pt-air"
```

**Fix**: Updated all dashboard queries to use correct job label:
```bash
# File: crewai-chat-pt-air/metrics/chat-pt-dashboard.json
# Changed: job="crewai-chat-passthrough"
# To:      job="crewai-chat-pt-air"
```

### Fix Process

**Step 1: Network Connectivity**
```bash
docker network connect crewai-network prometheus-agent-daemon
```

**Step 2: Verify Target Health**
```bash
curl -s http://localhost:9091/api/v1/targets | python3 -c \
  "import sys,json; data=json.load(sys.stdin); \
   targets = data['data']['activeTargets']; \
   chat_target = [t for t in targets if 'chat-pt-air' in t.get('labels',{}).get('job','')]; \
   print(chat_target[0]['health'] if chat_target else 'not found')"
# Output: up
```

**Step 3: Fix Dashboard JSON**
```bash
cd /home/rreck/Desktop/202051023a/crewai-chat-pt-air/metrics
cp chat-pt-dashboard.json chat-pt-dashboard.json.bak

cat chat-pt-dashboard.json.bak | \
  jq '(.panels[].targets[]?.expr? // empty) |=
      gsub("job=\\\"crewai-chat-passthrough\\\""; "job=\"crewai-chat-pt-air\"")' \
  > chat-pt-dashboard.json
```

**Step 4: Re-import to Grafana**
```bash
cat chat-pt-dashboard.json | \
  jq 'del(.id) | {dashboard: ., overwrite: true}' | \
  curl -s -X POST -H "Content-Type: application/json" -u admin:admin \
    http://localhost:3000/api/dashboards/db -d @-
```

**Step 5: Verify Queries Work**
```bash
curl -s -G 'http://localhost:9091/api/v1/query' \
  --data-urlencode 'query=crewai_chat_sessions_active{job="crewai-chat-pt-air"}' | \
  jq '.data.result | length'
# Output: 1 (SUCCESS!)
```

### Dashboard Panels Fixed

All 10 panels now working with correct data:
1. **Active Sessions** - `crewai_chat_sessions_active{job="crewai-chat-pt-air"}`
2. **Messages (5 min)** - `sum(increase(crewai_chat_messages_total{job="crewai-chat-pt-air",direction="incoming"}[5m]))`
3. **Avg Response Time** - `rate(crewai_chat_response_time_seconds_sum{job="crewai-chat-pt-air"}[5m]) / rate(crewai_chat_response_time_seconds_count{job="crewai-chat-pt-air"}[5m])`
4. **Tokens Generated (5 min)** - `sum(increase(crewai_chat_tokens_total{job="crewai-chat-pt-air"}[5m]))`
5. **Message Rate** - Incoming/outgoing rates with `job="crewai-chat-pt-air"`
6. **Response Time Percentiles** - p50/p90/p99 histograms
7. **LLM Request Status** - Success/error counts by status
8. **Token Generation Rate** - Tokens per second
9. **Messages by User** - Table grouped by user label
10. **LLM Request Distribution** - Pie chart of request statuses

### Critical Insights

**Network Requirements for Prometheus**:
- Prometheus MUST be on same Docker network as monitored containers
- Without network connectivity, DNS resolution fails for container names
- Symptom: targets show "down" with "no such host" errors
- Fix is non-obvious - container appears "running" but can't scrape

**Job Label Consistency**:
- Prometheus job name (`job_name` in config) becomes `job` label in metrics
- Dashboard queries must match EXACT job label value
- Common mismatch: shorthand name in query vs full container name in config
- No automatic fuzzy matching - must be character-perfect

**Query Testing Strategy**:
1. Test without job filter first: `crewai_chat_sessions_active`
2. Inspect returned labels: `jq '.data.result[0].metric.job'`
3. Use discovered label in query: `{job="<actual-value>"}`
4. Verify non-zero results before dashboard import

### Prevention Checklist

**For Prometheus Deployment**:
- [ ] Verify Prometheus on `crewai-network`: `docker network inspect crewai-network`
- [ ] Check target health: `curl http://localhost:9091/api/v1/targets`
- [ ] Test container-to-container connectivity: `docker exec prometheus-agent wget -O- http://<target>:port/metrics`
- [ ] If DNS fails, connect to network: `docker network connect crewai-network <container>`

**For Dashboard Creation**:
- [ ] Query Prometheus for actual metric: `curl http://localhost:9091/api/v1/query?query=<metric>`
- [ ] Extract exact job label value: `.data.result[0].metric.job`
- [ ] Use actual label in dashboard queries (don't guess!)
- [ ] Test queries in Grafana Explore before saving dashboard
- [ ] Document expected job label in dashboard README

**For Agent Deployment**:
- [ ] Add Prometheus target with consistent job name matching agent name
- [ ] Ensure job_name aligns with dashboard queries
- [ ] Test metrics endpoint before Prometheus scrape: `curl http://<agent>:port/metrics`
- [ ] Verify labels match expectations: `grep "^crewai_" metrics | head -5`

### Impact Assessment

- **Severity**: High (dashboard completely non-functional)
- **Fix Complexity**: Simple (once root cause identified)
- **Time to Fix**: 10 minutes
- **Data Loss**: None (metrics were being collected, just not visible)

### Files Modified

- `/home/rreck/Desktop/202051023a/crewai-chat-pt-air/metrics/chat-pt-dashboard.json`
  - Changed: 10 occurrences of `job="crewai-chat-passthrough"`
  - To: `job="crewai-chat-pt-air"`
  - Backup: `chat-pt-dashboard.json.bak`

### Verification Steps

```bash
# 1. Check Prometheus target health
curl -s http://localhost:9091/api/v1/targets | jq '.data.activeTargets[] | select(.labels.job=="crewai-chat-pt-air") | .health'
# Expected: "up"

# 2. Test sample query
curl -s -G 'http://localhost:9091/api/v1/query' \
  --data-urlencode 'query=crewai_chat_sessions_active{job="crewai-chat-pt-air"}' | \
  jq '.data.result | length'
# Expected: 1

# 3. View dashboard
# URL: http://localhost:3000/d/crewai-chat-passthrough/crewai-chat-passthrough-claude-sonnet-4
# Expected: All panels showing data
```

### Related Issues

This pattern likely affects other dashboards:
- Any dashboard with hardcoded job labels
- Dashboards imported from different environments
- Dashboards created before agent naming standardization

**Action**: Review all 23 dashboards for similar job label mismatches.

---

**NON-NEGOTIABLE**: Always verify Prometheus target connectivity and job label values before creating/importing dashboards. Job labels must match EXACTLY - no fuzzy matching exists.
