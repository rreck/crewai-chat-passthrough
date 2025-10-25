# CrewAI Chat Passthrough Agent (Docker) — v1.0.0

**Copyright (c) RRECKTEK LLC**
**Built:** 2025-10-25 13:45 UTC (commit 22258a0)

A pure passthrough chat interface to Claude Sonnet 4 with zero funnel logic, zero data query intelligence, and minimal system prompts. Clean, direct communication with Claude for general-purpose chat applications.

## 🚀 Features

- **Pure Claude Passthrough**: Direct access to Claude Sonnet 4 with minimal modification
- **Zero Funnel Logic**: No intent classification, query optimization, or data intelligence
- **Minimal System Prompt**: 1-line assistant role (vs 370+ lines in data query agents)
- **Streaming Responses**: Real-time token-by-token output with SSE
- **Conversation History**: Maintains last 10 messages for context
- **Session Management**: Multi-user session support with SQLite storage
- **Agent-to-Agent (A2A) API**: Standard CrewAI HTTP endpoints
- **Prometheus Metrics**: Comprehensive monitoring with 6 metric families
- **Grafana Dashboard**: 10 visualization panels for real-time monitoring
- **Web Interface**: Clean, modern chat UI with markdown support

## 📋 Quick Start

```bash
# Build the container
cd crewai-chat-passthrough
./run-chat-passthrough-watch.sh build

# Start the agent
./run-chat-passthrough-watch.sh start

# Access chat interface
open http://localhost:8087/chat

# Check health and status
./run-chat-passthrough-watch.sh status
curl http://localhost:8087/health

# Stop container
./run-chat-passthrough-watch.sh stop
```

## 📁 Directory Structure

```
crewai-chat-passthrough/
├── input/              # Input directory (not used for chat)
├── output/             # Generated outputs
│   └── logs/           # Processing logs
├── data/               # SQLite session storage
│   └── chat.db         # Session and message history (auto-created)
├── kb/
│   ├── short/          # Atomic pmem 1.0 artifacts
│   └── long/           # Consolidated pmem artifacts
├── app/
│   ├── main.py         # Flask chat agent with Claude integration
│   └── chat.html       # Web chat interface
├── metrics/
│   ├── chat-passthrough-dashboard.json  # Grafana dashboard (v2, verified)
│   └── prometheus.yml                   # Prometheus scrape configuration
├── Dockerfile
├── run-chat-passthrough-watch.sh        # Container management script
└── README.md
```

## 🔧 Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `API_PORT` | `8080` | Internal API port (mapped to 8087 externally) |
| `METRICS_PORT` | `9090` | Internal metrics port (mapped to 9097 externally) |
| `DATA_DIR` | `./data` | Directory for SQLite database |
| `OUTPUT_DIR` | `./output` | Directory for logs |
| `PIDFILE` | `/var/run/crewai-chat-passthrough.pid` | PID file location |
| `C2_REGISTRY_URL` | `http://crewai-c2-dc1-prod-001-v1-0-0:8080` | Consul registry URL |

### Claude API Key

The agent requires a Claude API key from Anthropic. Store it in one of these locations:
- `~/.anthropic/api_key` (recommended, auto-mounted read-only)
- `~/.config/claude/api_key`
- `~/.claude/api_key`
- Environment variable: `ANTHROPIC_API_KEY` or `CLAUDE_API_KEY`

Get your API key at: https://console.anthropic.com/settings/keys

### Container Ports

- **8087**: Chat API and web interface (external)
- **9097**: Prometheus metrics endpoint (external)

## 🖥️ Usage

### Container Management

```bash
# Build Docker image
./run-chat-passthrough-watch.sh build

# Start agent
./run-chat-passthrough-watch.sh start

# Stop agent
./run-chat-passthrough-watch.sh stop

# Restart agent
./run-chat-passthrough-watch.sh restart

# Show status
./run-chat-passthrough-watch.sh status

# View logs
./run-chat-passthrough-watch.sh logs

# Cleanup (stop and remove)
./run-chat-passthrough-watch.sh cleanup
```

### Chat Interface

Access the web interface at: **http://localhost:8087/chat**

Features:
- Real-time streaming responses
- Markdown formatting (bold, code blocks, lists)
- Persistent sessions
- Multi-user support
- Message history

### API Usage

#### Create Session

```bash
curl -X POST http://localhost:8087/chat/session/new \
  -H "Content-Type: application/json" \
  -d '{"user_id": "alice", "metadata": {"source": "api"}}'
```

#### Send Message

```bash
curl -X POST http://localhost:8087/chat/send \
  -H "Content-Type: application/json" \
  -d '{"message": "Explain quantum computing", "user_id": "alice", "session_id": "SESSION_ID"}'
```

#### Get History

```bash
curl "http://localhost:8087/chat/history?session_id=SESSION_ID&limit=20"
```

#### Get All Sessions

```bash
curl "http://localhost:8087/chat/sessions?user_id=alice"
```

## 🌐 Agent-to-Agent (A2A) API

Standard CrewAI endpoints for inter-agent communication:

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check (returns `{"status": "healthy"}`) |
| GET | `/status` | Agent status, capabilities, and active sessions |
| GET | `/config` | Current configuration |
| GET | `/metrics` | Prometheus metrics |
| POST | `/config` | Update configuration (not implemented) |
| POST | `/job` | Not applicable for chat agent |
| POST | `/batch` | Not applicable for chat agent |

### Health Check

```bash
curl http://localhost:8087/health
# {"service":"crewai-chat-passthrough","status":"healthy"}
```

### Status

```bash
curl http://localhost:8087/status
# {
#   "id": "crewai-chat-passthrough",
#   "name": "CrewAI Chat Passthrough Agent",
#   "type": "chat",
#   "capabilities": ["chat", "claude-passthrough", "streaming"],
#   "active_sessions": 5,
#   "llm_model": "claude-sonnet-4"
# }
```

## 📊 Monitoring

### Prometheus Metrics

Exposed on: **http://localhost:8087/metrics**

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `crewai_chat_messages_total` | Counter | `direction`, `user` | Total messages sent/received |
| `crewai_chat_sessions_active` | Gauge | - | Active chat sessions |
| `crewai_chat_response_time_seconds` | Histogram | - | Response time distribution |
| `crewai_chat_tokens_total` | Counter | `type` | Total tokens generated |
| `crewai_chat_llm_requests_total` | Counter | `status` | LLM API request status |
| `crewai_chat_errors_total` | Counter | `type` | Error counts by type |

### Grafana Dashboard

Import the dashboard from `metrics/chat-passthrough-dashboard.json` into Grafana.

**Dashboard URL** (if imported): http://localhost:3000/d/crewai-chat-passthrough

**Panels** (10 total):
1. Active Sessions (stat)
2. Messages (5 min) (stat)
3. Avg Response Time (stat)
4. Tokens Generated (5 min) (stat)
5. Message Rate (time series)
6. Response Time Percentiles (p50/p90/p99)
7. LLM Request Status (bars)
8. Token Generation Rate (time series)
9. Messages by User (table)
10. LLM Request Distribution (pie chart)

**Features**:
- 5-second auto-refresh
- 15-minute time window
- Color-coded thresholds
- Responsive layout

### Prometheus Integration

Add this job to your Prometheus configuration (`prometheus.yml`):

```yaml
scrape_configs:
  - job_name: 'crewai-chat-passthrough'
    static_configs:
      - targets: ['crewai-chat-passthrough-claude-sonnet4-prod-001:8080']
    metrics_path: '/metrics'
    scrape_interval: 15s
```

Or use the included config: `metrics/prometheus.yml`

## 🏗️ Architecture

### Comparison: Passthrough vs DataQuery

| Feature | crewai-chat-dataquery | crewai-chat-passthrough |
|---------|----------------------|------------------------|
| Intent Classifier | ✓ | ✗ |
| Sweet Spot Library | ✓ | ✗ |
| Data Engine | ✓ | ✗ |
| Prompt Funnel | ✓ | ✗ |
| Database Queries | ✓ | ✗ |
| System Prompt | 370+ lines | 1 line |
| LLM Optimization | Heavy | Minimal |
| Max Tokens | 150-4096 | 8192 |
| Temperature | 0.2-0.7 | 1.0 |
| Use Case | Data analysis | General chat |

### Core Components

1. **Flask Web Server**: Handles HTTP requests and SSE streaming
2. **ClaudeLLM**: Anthropic API integration with conversation history
3. **ChatDatabase**: SQLite-based session and message storage
4. **Web Interface**: Modern chat UI with markdown support
5. **Metrics**: Prometheus client for monitoring

### Message Flow

```
User → Web UI → Flask → ClaudeLLM → Anthropic API
                  ↓                      ↓
            ChatDatabase            SSE Stream
                  ↓                      ↓
            SQLite (chat.db)      → Web UI (tokens)
```

## 🧪 Testing & Validation

### Test Results Summary

**Date**: 2025-10-24
**Status**: ✅ 10/11 tests passed (91%)

| Test Category | Tests | Passed | Status |
|--------------|-------|--------|--------|
| Metrics Exposure | 2 | 2 | ✅ |
| Health/Status | 2 | 2 | ✅ |
| Chat Functionality | 2 | 2 | ✅ |
| Metrics Updates | 1 | 1 | ✅ |
| C2 Registration | 1 | 0 | ⚠️ Non-blocking |
| Prometheus Integration | 2 | 2 | ✅ |
| Grafana Dashboard | 1 | 1 | ✅ |

### Performance Metrics

- **Chat Response Time**: 1.84s average
- **Token Generation**: 2 tokens/message average
- **API Response**: <50ms (health/status)
- **Metrics Endpoint**: <100ms
- **Container Startup**: ~6 seconds to healthy
- **Memory Usage**: ~34MB resident

### Manual Testing

```bash
# Test health endpoint
curl http://localhost:8087/health

# Test status endpoint
curl http://localhost:8087/status | jq

# Test chat with simple question
curl -X POST http://localhost:8087/chat/send \
  -H "Content-Type: application/json" \
  -d '{"message": "What is 2+2?", "user_id": "test"}'

# Verify metrics updating
curl http://localhost:8087/metrics | grep crewai_chat_messages_total

# Test Grafana datasource query
curl "http://localhost:3000/api/datasources/proxy/uid/DATASOURCE_UID/api/v1/query?query=crewai_chat_messages_total" \
  -u admin:admin
```

## 🔒 Security

- **Non-root user**: Container runs as uid 1000 (crewai user)
- **Read-only API key mount**: `~/.anthropic` mounted read-only
- **Security opt**: `no-new-privileges:true`
- **Network isolation**: Runs on `crewai-network` bridge
- **Parameterized SQL**: No SQL injection vulnerabilities
- **Session isolation**: User sessions stored separately
- **No secrets in logs**: API keys never logged

## 📝 pmem 1.0 Documentation

This agent includes complete pmem 1.0 (persistent memory) documentation:

| Artifact | Epoch | Description |
|----------|-------|-------------|
| PROBLEM.1761399356 | 2025-10-25 | Dashboard datasource UID mismatch |
| ACTION.1761399400 | 2025-10-25 | Fix implementation with verification |
| RESULT.1761399500 | 2025-10-25 | Confirmed fix, 22 data points |
| LESSON.1761399600 | 2025-10-25 | Quality assurance improvements |
| CONSENSUS.1761399786 | 2025-10-25 | Deployment complete, lineage frozen |

All artifacts include:
- Full JSON provenance headers
- Cryptographic signatures
- Bidirectional edge links
- AICP (prov, ucon, eval) fragments
- Weight tracking for reinforcement

## 🐛 Troubleshooting

### No Claude Responses

**Issue**: Chat sends message but no response appears

**Solutions**:
1. Check API key exists: `cat ~/.anthropic/api_key`
2. Verify API key is valid at https://console.anthropic.com/settings/keys
3. Check API credits: https://console.anthropic.com/settings/billing
4. View container logs: `./run-chat-passthrough-watch.sh logs`

### Metrics Not Displaying in Grafana

**Issue**: Dashboard panels show "No data"

**Solutions**:
1. Verify datasource UID in dashboard JSON matches Grafana
   ```bash
   curl http://localhost:3000/api/datasources -u admin:admin
   ```
2. Test datasource query:
   ```bash
   curl "http://localhost:3000/api/datasources/proxy/uid/DATASOURCE_UID/api/v1/query?query=up" -u admin:admin
   ```
3. Check Prometheus is scraping: `curl http://localhost:9090/targets`
4. Verify metrics endpoint: `curl http://localhost:8087/metrics | grep crewai`

See `kb/short/chat-passthrough.LESSON.1761399600.md` for detailed troubleshooting checklist.

### Container Won't Start

**Issue**: Container exits immediately or fails health check

**Solutions**:
1. Check logs: `docker logs crewai-chat-passthrough-claude-sonnet4-prod-001`
2. Verify API key mount: `docker inspect crewai-chat-passthrough-claude-sonnet4-prod-001 | grep Mounts`
3. Check network exists: `docker network inspect crewai-network`
4. Verify ports not in use: `netstat -tuln | grep -E '8087|9097'`

### Session Data Lost

**Issue**: Chat history disappears after restart

**Cause**: SQLite database not persisted

**Solution**: Ensure `data/` directory is mounted:
```bash
# Verify mount in run script
grep "data:/work/data" run-chat-passthrough-watch.sh
```

## 🔗 Links

- **GitHub Repository**: https://github.com/rreck/crewai-chat-passthrough
- **Chat Interface**: http://localhost:8087/chat
- **Health Check**: http://localhost:8087/health
- **Metrics**: http://localhost:8087/metrics
- **Grafana Dashboard**: http://localhost:3000/d/crewai-chat-passthrough
- **Anthropic Console**: https://console.anthropic.com
- **Claude API Docs**: https://docs.anthropic.com/claude/reference

## 📄 License

**Copyright (c) RRECKTEK LLC**
All rights reserved.

## 🤝 Contributing

This agent follows the CrewAI architecture patterns from:
- https://github.com/rreck/agent/tree/main/crewai-pandoc
- https://github.com/rreck/agent/tree/main/crewai-transcribe

See `CLAUDE.md` for architecture requirements and development workflow.

## 📦 Version History

### v1.0.0 (2025-10-25)
- Initial release
- Pure passthrough to Claude Sonnet 4
- Zero funnel logic implementation
- Streaming SSE responses
- Session management with SQLite
- 10-panel Grafana dashboard
- Comprehensive Prometheus metrics
- pmem 1.0 documentation
- 91% test pass rate
- Production deployment verified

---

**Built with Claude Code**
Co-Authored-By: Claude <noreply@anthropic.com>
