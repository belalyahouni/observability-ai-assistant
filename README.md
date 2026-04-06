# Observability AI Assistant

An AI-powered observability assistant that uses the [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) to let an LLM query a full observability stack — Prometheus, Loki, and Tempo — for automated incident investigation and root cause analysis.

## Architecture

```
Kubernetes (Minikube)
├── Microservices (FastAPI)
│   ├── gateway → user-service
│   │           → content-service → recommendation-service
│   └── Fault injection on recommendation-service
│
├── Telemetry Pipeline
│   └── Services → [OTLP] → OpenTelemetry Collector
│                              → Prometheus (metrics)
│                              → Loki (logs)
│                              → Tempo (traces)
│
└── Visualization: Grafana (all datasources pre-configured)

MCP Server (local)
└── Exposes 8 tools for querying the observability stack
    → Connected to Claude for conversational RCA
```

## Tech Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| Microservices | Python / FastAPI | 4 services with inter-service calls |
| Instrumentation | OpenTelemetry SDK + Collector | Traces, metrics, structured logs |
| Metrics | Prometheus | Time-series storage, PromQL |
| Logs | Loki | Log aggregation, LogQL |
| Traces | Grafana Tempo | Distributed trace storage, TraceQL |
| Dashboards | Grafana | Visualization with cross-signal correlation |
| Orchestration | Kubernetes (Minikube) | Container orchestration |
| AI Layer | MCP Server (Python) | LLM-accessible observability tools |

## Quick Start

### Prerequisites

- Docker
- Minikube
- kubectl
- Python 3.12+

### 1. Start the cluster and build images

```bash
minikube start
./scripts/build-images.sh
```

### 2. Deploy everything

```bash
./scripts/deploy.sh
```

### 3. Generate traffic

```bash
./scripts/load-generator.sh
```

### 4. Access Grafana

```bash
minikube service grafana --url
# Open the URL — datasources are pre-configured
```

### 5. Run the MCP server

```bash
# In a separate terminal — port-forward the backends
./scripts/port-forward.sh

# Install MCP dependencies
pip install -r mcp-server/requirements.txt

# Run the server (connect via Claude Desktop or Claude Code)
python mcp-server/server.py
```

### 6. Investigate an incident

The `recommendation-service` is deployed with fault injection enabled (3s latency, 30% error rate). Ask the LLM:

> "Users are reporting slow load times on the content page. Investigate."

The LLM will use the MCP tools to check service health, search logs, find slow traces, and identify the root cause.

## MCP Tools

| Tool | Description |
|------|-------------|
| `list_services` | Service topology and dependency graph |
| `query_prometheus` | Execute arbitrary PromQL queries |
| `query_prometheus_range` | Time-series range queries |
| `search_logs` | Search Loki logs by service, level, keyword |
| `get_traces` | Find traces by service, duration, error status |
| `get_trace_detail` | Detailed span breakdown for a trace |
| `get_service_health` | Health summary for one service |
| `check_all_services_health` | Quick triage across all services |

## Project Structure

```
.
├── services/                  # Microservices
│   ├── gateway/
│   ├── user-service/
│   ├── content-service/
│   ├── recommendation-service/
│   ├── shared/telemetry.py    # OpenTelemetry setup
│   └── Dockerfile
├── k8s/                       # Kubernetes manifests
│   ├── services/              # App deployments
│   ├── observability/         # Prometheus, Grafana, Loki, Tempo, OTel Collector
│   └── config/                # Collector config
├── mcp-server/                # MCP server
│   ├── server.py
│   ├── rca_prompt.md          # RCA system prompt for the LLM
│   └── claude_desktop_config.json
├── scripts/                   # Helper scripts
│   ├── build-images.sh
│   ├── deploy.sh
│   ├── load-generator.sh
│   ├── port-forward.sh
│   └── teardown.sh
└── PLAN.md
```

## Teardown

```bash
./scripts/teardown.sh
minikube stop
```
