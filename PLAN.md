# AI-Powered Observability Assistant

An MCP server that connects an LLM to a local observability stack (OpenTelemetry, Prometheus, Grafana), enabling conversational troubleshooting and root cause analysis across a microservices environment running on Kubernetes.

## Tech Stack

- **Microservices:** Python (FastAPI) — 3-4 small services that call each other
- **Instrumentation:** OpenTelemetry SDK + OpenTelemetry Collector
- **Metrics:** Prometheus
- **Dashboards & Logs:** Grafana (with Loki for log aggregation — needed to make logs queryable by the LLM)
- **Orchestration:** Minikube (local Kubernetes cluster)
- **AI Layer:** MCP server (TypeScript or Python) exposing observability tools to Claude

---

## Phase 1 — Microservices

Build 3-4 simple services that form a realistic dependency chain.

- [ ] `gateway` — public-facing, routes requests to downstream services
- [ ] `user-service` — handles user lookups
- [ ] `content-service` — returns content/catalog data, calls `recommendation-service`
- [ ] `recommendation-service` — returns recommendations (slowest, most likely to fail)
- [ ] Each service exposes a `/health` endpoint and at least one business endpoint
- [ ] Services call each other via HTTP — keep the logic trivial, the topology is what matters
- [ ] Add a configurable fault injection flag (env var) to any service — introduce latency, errors, or timeouts on demand

## Phase 2 — OpenTelemetry Instrumentation

Instrument the services so they emit traces, metrics, and logs.

- [ ] Add `opentelemetry-sdk`, `opentelemetry-instrumentation-fastapi`, `opentelemetry-instrumentation-requests` to each service
- [ ] Configure trace context propagation between services (W3C TraceContext)
- [ ] Emit custom metrics: request count, request duration histogram, error count (per service)
- [ ] Structured logging with trace/span IDs embedded so logs correlate to traces
- [ ] Deploy an **OpenTelemetry Collector** as a central pipeline
  - Receives traces, metrics, and logs from all services
  - Exports metrics to Prometheus (via Prometheus exporter or remote write)
  - Exports logs to Loki
  - Exports traces to Grafana Tempo (lightweight trace backend that plugs into Grafana)

## Phase 3 — Observability Backend on Kubernetes

Deploy the full stack on Minikube.

- [ ] Install and start Minikube
- [ ] Write Kubernetes manifests (Deployments + Services) for:
  - The 4 microservices
  - OpenTelemetry Collector
  - Prometheus (use `kube-prometheus-stack` Helm chart or manual manifests)
  - Grafana
  - Loki (simple single-binary mode)
  - Grafana Tempo (single-binary mode — needed for trace queries)
- [ ] Configure Prometheus to scrape the OpenTelemetry Collector's metrics endpoint
- [ ] Configure Grafana datasources: Prometheus, Loki, Tempo
- [ ] Build a basic Grafana dashboard: request rate, error rate, latency per service
- [ ] Verify the full pipeline works: make requests → see traces, metrics, and logs in Grafana

## Phase 4 — MCP Server

Build an MCP server that exposes the observability stack as tools an LLM can call.

- [ ] Set up the MCP server project (using `@modelcontextprotocol/sdk` or `mcp` Python package)
- [ ] Implement tools:
  - `query_prometheus` — accepts a PromQL query + time range, returns metric results
  - `search_logs` — queries Loki by service name, severity, keyword, time range
  - `get_traces` — queries Tempo for traces by service, min duration, or error status
  - `list_services` — returns the known services and their dependencies
  - `get_service_health` — convenience tool that checks error rate + latency for a given service
- [ ] Each tool should return structured, concise data (not raw dumps) — the LLM needs digestible context
- [ ] Test each tool individually against the running stack

## Phase 5 — Root Cause Analysis Workflow

Wire it all together — the LLM uses the MCP tools to investigate an incident.

- [ ] Write a system prompt that gives the LLM a troubleshooting methodology:
  1. Check overall service health / error rates
  2. Identify the service(s) with anomalies
  3. Pull logs for the affected service(s)
  4. Trace a failing request through the dependency chain
  5. Identify the root cause and summarise findings
- [ ] Trigger a fault (e.g., `recommendation-service` starts returning 500s or adding 5s latency)
- [ ] Ask the LLM: *"Users are reporting slow load times on the content page. Investigate."*
- [ ] Capture the full conversation — the sequence of tool calls and reasoning is the key artifact
- [ ] Document where the LLM succeeded and where it struggled

## Phase 6 — Polish & Stretch Goals

Optional improvements if time allows.

- [ ] **Anomaly detection prompt** — a scheduled/periodic query that scans key metrics and flags anything unusual without a human asking
- [ ] **Kubernetes-aware tools** — add `get_pod_status`, `get_events` tools to the MCP server so the LLM can also inspect cluster state
- [ ] **Grafana annotations** — have the LLM write annotations back to Grafana when it identifies an incident
- [ ] **Compare models** — try the same RCA workflow with different models and note differences in reasoning quality

---

## Key Learnings to Capture

After each phase, note down what you learned — these become your interview talking points.

- **OpenTelemetry:** How the SDK, auto-instrumentation, and Collector pipeline work. The relationship between traces, metrics, and logs. Context propagation.
- **Prometheus:** Pull-based model, PromQL, recording rules, alerting.
- **Grafana:** Datasource abstraction, dashboard design, correlating signals.
- **Kubernetes:** Pods, Deployments, Services, Helm, `kubectl` debugging, why orchestration matters at scale.
- **MCP:** Designing tool interfaces for LLMs, what makes a good tool boundary, structured vs unstructured output.
- **LLM reasoning:** How well LLMs handle multi-step diagnostic chains, context window management, when they hallucinate vs when they're genuinely useful.
