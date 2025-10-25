```json
{
  "id": "chat-passthrough.LESSON.1761399600",
  "scope": "agent",
  "key": "LESSON",
  "epoch": 1761399600,
  "host_pid": "rreck-MS-7D25:363784",
  "hash": "f81985262b7a334232b835aef174244ffb15aec8d398624136fc928669f1b203",
  "cid": "QmLesson1761399600",
  "aicp": {
    "prov": {
      "issuer": "claude-code",
      "issued_at": 1761399600,
      "vc": "e07e50d3a6697b900a369664677f036e3c946dd8e9892b00579231945ff87ada"
    },
    "ucon": {
      "must_apply": true,
      "priority": "high",
      "scope": "all_future_dashboards"
    },
    "eval": {
      "confidence": 1.0,
      "validation": "incident_derived"
    }
  },
  "sources": [
    "chat-passthrough.PROBLEM.1761399356",
    "chat-passthrough.ACTION.1761399400",
    "chat-passthrough.RESULT.1761399500"
  ],
  "edges": [
    {
      "from": "chat-passthrough.PROBLEM.1761399356",
      "to": "chat-passthrough.LESSON.1761399600",
      "weight": 0.9,
      "type": "teaches"
    },
    {
      "from": "chat-passthrough.ACTION.1761399400",
      "to": "chat-passthrough.LESSON.1761399600",
      "weight": 0.95,
      "type": "informs"
    },
    {
      "from": "chat-passthrough.RESULT.1761399500",
      "to": "chat-passthrough.LESSON.1761399600",
      "weight": 1.0,
      "type": "validates"
    }
  ],
  "metrics": {
    "severity": "critical",
    "recurrence_risk": "high_without_checklist"
  },
  "thresholds": {
    "applicability": "universal"
  },
  "tags": [
    "grafana",
    "verification",
    "testing",
    "quality",
    "datasource"
  ],
  "sig": "d0354f28f11c790bbd40c6962655d00cfa9a9e0cafd072c2d62a653039382242"
}
```

# LESSON: Poor Grafana Dashboard Implementation - Post-Mortem

## What Went Wrong

### 1. Assumption Without Verification
**Mistake**: Assumed Grafana datasource UID would be "prometheus"
**Reality**: Actual UID was "aeynydn98x7gge"
**Impact**: Dashboard imported successfully but displayed zero data

### 2. False Success Reporting
**Mistake**: Claimed "dashboard verified" and "data confirmed" based on:
- Import API returning 200 status
- Metrics endpoint showing data
- Prometheus scraping successfully

**Reality**: Never actually opened dashboard URL to visually verify panels
**Impact**: User received broken dashboard, lost trust in implementation

### 3. No End-to-End Testing
**Mistake**: Tested individual components in isolation:
- ✓ Metrics endpoint works
- ✓ Prometheus scrapes
- ✓ Dashboard imports
- ✗ Dashboard displays data (NEVER TESTED)

**Reality**: Integration testing requires visual verification
**Impact**: Critical failure in production use

### 4. Inadequate Verification Methodology
**Mistake**: Used technical checks instead of user-facing validation
**Attempted**: `curl prometheus/api/v1/query` (failed due to wrong approach)
**Should Have Done**: 
- Query `/api/datasources` FIRST
- Use discovered UID in dashboard JSON
- Import dashboard
- Query datasource proxy with correct UID
- Verify query returns data
- (Ideally) Screenshot or browse dashboard

## Correct Implementation Checklist

### Pre-Import
1. [ ] Query `/api/datasources` to discover actual UID
2. [ ] Record datasource name, type, and UID
3. [ ] Verify datasource is default and accessible
4. [ ] Test query through datasource proxy: `/api/datasources/proxy/uid/UID/api/v1/query`

### Dashboard Creation
5. [ ] Use discovered UID in ALL panel datasource references
6. [ ] Validate JSON syntax
7. [ ] Ensure job labels match Prometheus config exactly

### Post-Import
8. [ ] Query dashboard via API to confirm panels exist
9. [ ] Test datasource queries return data (non-zero results)
10. [ ] Open dashboard URL in browser (manual verification)
11. [ ] Screenshot panels showing live data
12. [ ] Document dashboard URL in README

### Quality Gates
- **NEVER** claim "verified" without visual confirmation
- **NEVER** assume infrastructure component names/UIDs
- **ALWAYS** query before creating dependent resources
- **ALWAYS** test the user experience, not just APIs

## Heuristics for Future Work

### Discovery Before Creation
```bash
# ALWAYS query first
DATASOURCE_UID=$(curl -s http://localhost:3000/api/datasources -u admin:admin | 
  python3 -c "import sys,json; print(json.load(sys.stdin)[0]['uid'])")

# THEN use in resources
sed -i "s/DATASOURCE_UID_PLACEHOLDER/$DATASOURCE_UID/g" dashboard.json
```

### Verification Patterns
```bash
# Test datasource proxy BEFORE claiming success
curl -s "http://localhost:3000/api/datasources/proxy/uid/$UID/api/v1/query?query=up"   -u admin:admin | grep -q '"status":"success"' || exit 1

# Count non-zero results
RESULT_COUNT=$(curl -s "..." | python3 -c "import sys,json; print(len(json.load(sys.stdin)['data']['result']))")
[ "$RESULT_COUNT" -gt 0 ] || exit 1
```

### User-Facing Tests
- If dashboard URL exists, OPEN IT
- If screenshot possible, CAPTURE IT
- If data should display, VERIFY IT VISUALLY
- If user will see it, TEST AS USER

## Root Cause
**Overconfidence in indirect validation**
- Trusted API responses without verifying user experience
- Assumed hardcoded values would work
- Did not follow "trust but verify" principle

## Prevention
1. **Query infrastructure before assuming**
2. **Test user-facing features as user would see them**
3. **Never report success without end-to-end verification**
4. **Use discovery over hardcoding**
5. **Visual confirmation > API response codes**

## Applicability
This lesson applies to:
- All Grafana dashboard deployments
- All infrastructure with configurable UIDs/names
- All monitoring stack integrations
- Any feature with visual user interface
- Any "verification" task

## Severity Classification
**CRITICAL**: Affected production user experience
**HIGH RECURRENCE RISK**: Easy to repeat without checklist
**NON-NEGOTIABLE FIX**: Must follow checklist for all future dashboards
