# CrewAI Chat PT Air — v1.0.0

**Copyright (c) RRECKTEK LLC**

Claude Sonnet 4 chat interface with CSV dataset awareness. Provides direct LLM access with aviation operations data context from KMMU airport.

## 🚀 Features

- **CSV Data Context**: Loads KMMU_OPS_Data_10-24-25.csv (209K+ rows, 91 columns) into system prompt
- **Pure Claude Passthrough**: Direct access to Claude Sonnet 4 with dataset awareness
- **Streaming Responses**: Real-time token-by-token output with SSE
- **Conversation History**: Maintains last 10 messages for context
- **Session Management**: Multi-user session support with SQLite storage
- **Agent-to-Agent (A2A) API**: Standard CrewAI HTTP endpoints
- **Prometheus Metrics**: Comprehensive monitoring with 6 metric families
- **Web Interface**: Clean chat UI with mask on/off commands
- **Client-Side Commands**: `mask on` / `mask off` to hide/show model name

## 📋 Quick Start

```bash
# Build the container
cd crewai-chat-pt-air
./run-chat-pt-watch.sh build

# Start the agent
./run-chat-pt-watch.sh start

# Access chat interface
open http://localhost:8089/chat

# Check health and status
./run-chat-pt-watch.sh status
curl http://localhost:8089/health

# Stop container
./run-chat-pt-watch.sh stop
```

## 📁 Directory Structure

```
crewai-chat-pt-air/
├── input/              # CSV data files (KMMU_OPS_Data_10-24-25.csv)
├── output/             # Generated outputs
│   └── logs/           # Processing logs
├── data/               # SQLite session storage
│   └── chat.db         # Session and message history (auto-created)
├── kb/
│   ├── short/          # Atomic pmem 1.0 artifacts
│   └── long/           # Consolidated pmem artifacts
├── app/
│   ├── main.py         # Flask chat agent with Claude + CSV integration
│   └── chat.html       # Web chat interface with mask commands
├── metrics/
│   ├── chat-pt-dashboard.json  # Grafana dashboard
│   └── prometheus.yml          # Prometheus scrape configuration
├── Dockerfile
├── run-chat-pt-watch.sh        # Container management script
└── README.md
```

## 🔧 Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `API_PORT` | `8080` | Internal API port (mapped to 8089 externally) |
| `METRICS_PORT` | `9090` | Internal metrics port (mapped to 9099 externally) |
| `DATA_DIR` | `./data` | Directory for SQLite database |
| `OUTPUT_DIR` | `./output` | Directory for logs |
| `INPUT_DIR` | `./input` | Directory for CSV data files |
| `CSV_FILE` | `KMMU_OPS_Data_10-24-25.csv` | CSV filename to load |
| `PIDFILE` | `/var/run/crewai-chat-pt-air.pid` | PID file location |
| `C2_REGISTRY_URL` | `http://crewai-c2-dc1-prod-001-v1-0-0:8080` | Consul registry URL |

### Claude API Key

The agent requires a Claude API key from Anthropic. Store it in one of these locations:
- `~/.anthropic/api_key` (recommended, auto-mounted read-only)
- `~/.config/claude/api_key`
- `~/.claude/api_key`
- Environment variable: `ANTHROPIC_API_KEY` or `CLAUDE_API_KEY`

Get your API key at: https://console.anthropic.com/settings/keys

### Container Ports

- **8089**: Chat API and web interface (external)
- **9099**: Prometheus metrics endpoint (external)

## 🖥️ Usage

### Container Management

```bash
# Build Docker image
./run-chat-pt-watch.sh build

# Start agent
./run-chat-pt-watch.sh start

# Stop agent
./run-chat-pt-watch.sh stop

# Restart agent
./run-chat-pt-watch.sh restart

# Show status
./run-chat-pt-watch.sh status

# View logs
./run-chat-pt-watch.sh logs

# Cleanup (stop and remove)
./run-chat-pt-watch.sh cleanup
```

### Chat Interface

Access the web interface at: **http://localhost:8089/chat**

#### Special Commands

- **`mask on`**: Hide "Claude Sonnet 4" from title bar (client-side only, not sent to LLM)
- **`mask off`**: Show "Claude Sonnet 4" in title bar (default)

These commands are handled entirely in the browser and do not appear in chat history.

#### Chat Features

- Real-time streaming responses
- Markdown formatting (bold, code blocks, lists)
- Persistent sessions
- Multi-user support
- Message history
- Aviation dataset context automatically included

### CSV Data Context

The agent automatically loads CSV metadata on startup:

```
✓ Loaded CSV: 209,737 rows, 91 columns
✓ Claude Sonnet 4 initialized with CSV context
```

All 91 columns from KMMU_OPS_Data_10-24-25.csv are included in the system prompt:
- Aircraft details (N_Number, manufacturer, model, type)
- Operations (takeoff/landing, datetime, runway)
- Owner/registration information
- Technical specifications (engines, weights, speeds)
- Airport classifications (ADG, TDG, weather category)
- Route data (origin/destination with coordinates)

### API Usage

#### Create Session

```bash
curl -X POST http://localhost:8089/chat/session/new \
  -H "Content-Type: application/json" \
  -d '{"user_id": "alice", "metadata": {"source": "api"}}'
```

#### Send Message

```bash
curl -X POST http://localhost:8089/chat/send \
  -H "Content-Type: application/json" \
  -d '{"message": "How many aircraft operations in the dataset?", "user_id": "alice", "session_id": "SESSION_ID"}'
```

#### Get History

```bash
curl "http://localhost:8089/chat/history?session_id=SESSION_ID&limit=20"
```

#### Get All Sessions

```bash
curl "http://localhost:8089/chat/sessions?user_id=alice"
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
curl http://localhost:8089/health
# {"service":"crewai-chat-pt-air","status":"healthy"}
```

### Status

```bash
curl http://localhost:8089/status
# {
#   "id": "crewai-chat-pt-air",
#   "name": "CrewAI Chat PT Air Agent",
#   "type": "chat",
#   "capabilities": ["chat", "claude-passthrough", "streaming"],
#   "active_sessions": 5,
#   "llm_model": "claude-sonnet-4"
# }
```

## 📊 Monitoring

### Prometheus Metrics

Exposed on: **http://localhost:8089/metrics**

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `crewai_chat_messages_total` | Counter | `direction`, `user` | Total messages sent/received |
| `crewai_chat_sessions_active` | Gauge | - | Active chat sessions |
| `crewai_chat_response_time_seconds` | Histogram | - | Response time distribution |
| `crewai_chat_tokens_total` | Counter | `type` | Total tokens generated |
| `crewai_chat_llm_requests_total` | Counter | `status` | LLM API request status |
| `crewai_chat_errors_total` | Counter | `type` | Error counts by type |

### Grafana Dashboard

Import the dashboard from `metrics/chat-pt-dashboard.json` into Grafana.

### Prometheus Integration

Add this job to your Prometheus configuration:

```yaml
scrape_configs:
  - job_name: 'crewai-chat-pt-air'
    static_configs:
      - targets: ['crewai-chat-pt-air-claude-sonnet4-prod-002:8080']
    metrics_path: '/metrics'
    scrape_interval: 15s
```

Or use the included config: `metrics/prometheus.yml`

## 🏗️ Architecture

### Core Components

1. **Flask Web Server**: Handles HTTP requests and SSE streaming
2. **ClaudeLLM**: Anthropic API integration with CSV context
3. **CSVDataLoader**: Loads CSV metadata into system prompt
4. **ChatDatabase**: SQLite-based session and message storage
5. **Web Interface**: Modern chat UI with mask commands and markdown support
6. **Metrics**: Prometheus client for monitoring

### CSV Context Flow

```
Startup → CSVDataLoader → Load metadata (columns, row count)
                       → Generate system prompt context
                       → Pass to ClaudeLLM
                       → Include in every conversation
```

### Message Flow

```
User → Web UI → Flask → ClaudeLLM (w/ CSV context) → Anthropic API
                 ↓                                      ↓
           ChatDatabase                            SSE Stream
                 ↓                                      ↓
           SQLite (chat.db)                    → Web UI (tokens)
```

## 🔒 Security

- **Non-root user**: Container runs as uid 1000 (crewai user)
- **Read-only mounts**: API key and input data mounted read-only
- **Security opt**: `no-new-privileges:true`
- **Network isolation**: Runs on `crewai-network` bridge
- **Parameterized SQL**: No SQL injection vulnerabilities
- **Session isolation**: User sessions stored separately
- **No secrets in logs**: API keys never logged
- **HTML escaping**: All user input sanitized before rendering

## 🐛 Troubleshooting

### CSV Not Loading

**Issue**: "WARNING: CSV file not found"

**Solutions**:
1. Verify CSV file exists: `ls input/KMMU_OPS_Data_10-24-25.csv`
2. Check container mount: `docker inspect crewai-chat-pt-air-claude-sonnet4-prod-002 | grep input`
3. Restart container: `./run-chat-pt-watch.sh restart`

### Mask Commands Not Working

**Issue**: "mask on" / "mask off" sent to Claude instead of handled locally

**Solutions**:
1. Hard refresh browser: Ctrl+Shift+R (Windows/Linux) or Cmd+Shift+R (Mac)
2. Clear browser cache
3. Check JavaScript console for errors (F12)

### No Claude Responses

**Issue**: Chat sends message but no response appears

**Solutions**:
1. Check API key exists: `cat ~/.anthropic/api_key`
2. Verify API key is valid at https://console.anthropic.com/settings/keys
3. Check API credits: https://console.anthropic.com/settings/billing
4. View container logs: `./run-chat-pt-watch.sh logs`

## 🔗 Links

- **Chat Interface**: http://localhost:8089/chat
- **Health Check**: http://localhost:8089/health
- **Metrics**: http://localhost:8089/metrics
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

### v1.0.0 (2025-10-27)
- Initial release
- CSV dataset integration (KMMU_OPS_Data_10-24-25.csv)
- Claude Sonnet 4 with full column awareness (91 columns)
- Client-side mask on/off commands
- Streaming SSE responses
- Session management with SQLite
- Grafana dashboard with Prometheus metrics
- Production deployment verified

---

**Built with Claude Code**
Co-Authored-By: Claude <noreply@anthropic.com>
