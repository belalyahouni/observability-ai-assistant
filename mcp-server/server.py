"""
MCP Server for the Observability AI Assistant.

Exposes tools that let an LLM query Prometheus, Loki, and Tempo
to investigate incidents and perform root cause analysis.
"""

import json
import os
from datetime import datetime, timedelta, timezone

import httpx
from mcp.server.fastmcp import FastMCP

# Backend URLs (default to kubectl port-forward addresses)
PROMETHEUS_URL = os.getenv("PROMETHEUS_URL", "http://localhost:9090")
LOKI_URL = os.getenv("LOKI_URL", "http://localhost:3100")
TEMPO_URL = os.getenv("TEMPO_URL", "http://localhost:3200")

mcp = FastMCP(
    "Observability Assistant",
    instructions=(
        "You are an observability assistant with access to Prometheus metrics, "
        "Loki logs, and Tempo traces for a microservices application. "
        "Use these tools to investigate incidents, identify anomalies, "
        "and perform root cause analysis. The services are: gateway, "
        "user-service, content-service, and recommendation-service. "
        "The recommendation-service is known to have fault injection enabled."
    ),
)

# --- Service topology (static knowledge) ---

SERVICE_TOPOLOGY = {
    "gateway": {
        "description": "Public-facing API gateway, routes to user-service and content-service",
        "port": 8000,
        "dependencies": ["user-service", "content-service"],
    },
    "user-service": {
        "description": "Handles user lookups and profiles",
        "port": 8000,
        "dependencies": [],
    },
    "content-service": {
        "description": "Content catalog, delegates recommendations to recommendation-service",
        "port": 8000,
        "dependencies": ["recommendation-service"],
    },
    "recommendation-service": {
        "description": "Generates content recommendations per user",
        "port": 8000,
        "dependencies": [],
    },
}


@mcp.tool()
def list_services() -> str:
    """List all microservices, their descriptions, and dependency graph.

    Use this first to understand the system topology before investigating.
    """
    lines = []
    for name, info in SERVICE_TOPOLOGY.items():
        deps = ", ".join(info["dependencies"]) if info["dependencies"] else "none"
        lines.append(f"- {name}: {info['description']} (depends on: {deps})")
    return "\n".join(lines)


@mcp.tool()
async def query_prometheus(query: str, time_range_minutes: int = 15) -> str:
    """Execute a PromQL query against Prometheus and return the results.

    Args:
        query: A PromQL query string. Examples:
            - 'rate(otel_gateway_requests_total[5m])' for request rate
            - 'histogram_quantile(0.99, rate(otel_http_server_request_duration_seconds_bucket[5m]))' for p99 latency
            - 'rate(otel_http_server_request_duration_seconds_count{http_status_code="500"}[5m])' for error rate
        time_range_minutes: How far back to query (default: 15 minutes)

    Returns:
        JSON string with query results including metric names, labels, and values.
    """
    end = datetime.now(timezone.utc)
    start = end - timedelta(minutes=time_range_minutes)

    async with httpx.AsyncClient() as client:
        # Try instant query first
        resp = await client.get(
            f"{PROMETHEUS_URL}/api/v1/query",
            params={"query": query, "time": end.isoformat()},
            timeout=10.0,
        )
        data = resp.json()

        if data.get("status") != "success":
            return f"Query failed: {data.get('error', 'unknown error')}"

        results = data.get("data", {}).get("result", [])
        if not results:
            return "No data returned for this query."

        formatted = []
        for r in results:
            metric = r.get("metric", {})
            value = r.get("value", [None, None])
            formatted.append(
                {"labels": metric, "timestamp": value[0], "value": value[1]}
            )
        return json.dumps(formatted, indent=2)


@mcp.tool()
async def query_prometheus_range(
    query: str, time_range_minutes: int = 15, step_seconds: int = 60
) -> str:
    """Execute a PromQL range query to see how a metric changes over time.

    Args:
        query: A PromQL query string.
        time_range_minutes: How far back to query (default: 15 minutes).
        step_seconds: Resolution step in seconds (default: 60).

    Returns:
        JSON string with time series data.
    """
    end = datetime.now(timezone.utc)
    start = end - timedelta(minutes=time_range_minutes)

    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{PROMETHEUS_URL}/api/v1/query_range",
            params={
                "query": query,
                "start": start.isoformat(),
                "end": end.isoformat(),
                "step": f"{step_seconds}s",
            },
            timeout=10.0,
        )
        data = resp.json()

        if data.get("status") != "success":
            return f"Query failed: {data.get('error', 'unknown error')}"

        results = data.get("data", {}).get("result", [])
        if not results:
            return "No data returned for this query."

        formatted = []
        for r in results:
            metric = r.get("metric", {})
            values = [
                {"time": v[0], "value": v[1]} for v in r.get("values", [])
            ]
            formatted.append({"labels": metric, "values": values})
        return json.dumps(formatted, indent=2)


@mcp.tool()
async def search_logs(
    service: str = "",
    level: str = "",
    keyword: str = "",
    time_range_minutes: int = 15,
    limit: int = 50,
) -> str:
    """Search logs in Loki by service, severity level, or keyword.

    Args:
        service: Filter by service name (e.g., 'gateway', 'recommendation-service').
        level: Filter by log level ('INFO', 'WARNING', 'ERROR').
        keyword: Search for a keyword in log messages.
        time_range_minutes: How far back to search (default: 15 minutes).
        limit: Maximum number of log lines to return (default: 50).

    Returns:
        Log lines matching the filters, with timestamps and service info.
    """
    # Build LogQL query
    label_filters = []
    if service:
        label_filters.append(f'service_name="{service}"')

    label_selector = "{" + ",".join(label_filters) + "}" if label_filters else '{}'

    line_filters = []
    if level:
        line_filters.append(f'| json | level="{level}"')
    elif keyword:
        line_filters.append(f"|~ `{keyword}`")

    if keyword and level:
        line_filters.append(f"|~ `{keyword}`")

    logql = label_selector + " ".join(line_filters)

    end = datetime.now(timezone.utc)
    start = end - timedelta(minutes=time_range_minutes)

    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{LOKI_URL}/loki/api/v1/query_range",
            params={
                "query": logql,
                "start": str(int(start.timestamp() * 1e9)),
                "end": str(int(end.timestamp() * 1e9)),
                "limit": limit,
            },
            timeout=10.0,
        )

        data = resp.json()
        if data.get("status") != "success":
            return f"Log query failed: {data.get('error', json.dumps(data))}"

        results = data.get("data", {}).get("result", [])
        if not results:
            return f"No logs found matching: {logql}"

        lines = []
        for stream in results:
            labels = stream.get("stream", {})
            for ts, line in stream.get("values", []):
                # Convert nanosecond timestamp
                t = datetime.fromtimestamp(int(ts) / 1e9, tz=timezone.utc)
                lines.append(f"[{t.strftime('%H:%M:%S')}] {line}")

        return f"Query: {logql}\nResults ({len(lines)} lines):\n" + "\n".join(
            lines[:limit]
        )


@mcp.tool()
async def get_traces(
    service: str = "",
    min_duration_ms: int = 0,
    limit: int = 10,
    time_range_minutes: int = 15,
) -> str:
    """Search for distributed traces in Tempo.

    Args:
        service: Filter traces by service name.
        min_duration_ms: Minimum trace duration in milliseconds (useful for finding slow requests).
        limit: Maximum number of traces to return (default: 10).
        time_range_minutes: How far back to search (default: 15 minutes).

    Returns:
        Trace summaries including trace ID, duration, service, and span count.
    """
    end = datetime.now(timezone.utc)
    start = end - timedelta(minutes=time_range_minutes)

    # Build TraceQL query
    conditions = []
    if service:
        conditions.append(f'resource.service.name = "{service}"')
    if min_duration_ms > 0:
        conditions.append(f"duration > {min_duration_ms}ms")

    traceql = "{ " + " && ".join(conditions) + " }" if conditions else "{}"

    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{TEMPO_URL}/api/search",
            params={
                "q": traceql,
                "start": str(int(start.timestamp())),
                "end": str(int(end.timestamp())),
                "limit": limit,
            },
            timeout=10.0,
        )

        data = resp.json()
        traces = data.get("traces", [])
        if not traces:
            return f"No traces found matching: {traceql}"

        formatted = []
        for t in traces:
            formatted.append(
                {
                    "traceID": t.get("traceID"),
                    "rootServiceName": t.get("rootServiceName"),
                    "rootTraceName": t.get("rootTraceName"),
                    "durationMs": t.get("durationMs"),
                    "spanCount": t.get("spanSets", [{}])[0].get("matched", 0)
                    if t.get("spanSets")
                    else 0,
                }
            )
        return json.dumps(formatted, indent=2)


@mcp.tool()
async def get_trace_detail(trace_id: str) -> str:
    """Get detailed span information for a specific trace.

    Args:
        trace_id: The trace ID to look up.

    Returns:
        Detailed breakdown of all spans in the trace, showing the request flow.
    """
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{TEMPO_URL}/api/traces/{trace_id}",
            timeout=10.0,
        )

        data = resp.json()
        batches = data.get("batches", [])
        if not batches:
            return f"No trace found with ID: {trace_id}"

        spans = []
        for batch in batches:
            resource = batch.get("resource", {})
            service_name = "unknown"
            for attr in resource.get("attributes", []):
                if attr.get("key") == "service.name":
                    service_name = attr.get("value", {}).get("stringValue", "unknown")

            for scope_spans in batch.get("scopeSpans", []):
                for span in scope_spans.get("spans", []):
                    duration_ns = int(span.get("endTimeUnixNano", 0)) - int(
                        span.get("startTimeUnixNano", 0)
                    )
                    status = span.get("status", {})
                    spans.append(
                        {
                            "service": service_name,
                            "name": span.get("name"),
                            "kind": span.get("kind"),
                            "durationMs": round(duration_ns / 1e6, 2),
                            "status": status.get("code", "OK"),
                            "statusMessage": status.get("message", ""),
                        }
                    )

        spans.sort(key=lambda s: s["durationMs"], reverse=True)
        return json.dumps(spans, indent=2)


@mcp.tool()
async def get_service_health(service: str, time_range_minutes: int = 5) -> str:
    """Get a health summary for a specific service: request rate, error rate, and latency.

    Args:
        service: The service name (e.g., 'gateway', 'recommendation-service').
        time_range_minutes: Time window to evaluate (default: 5 minutes).

    Returns:
        Health summary with request rate, error rate percentage, and p50/p95/p99 latency.
    """
    queries = {
        "request_rate": f'sum(rate(otel_http_server_request_duration_seconds_count{{service_name="{service}"}}[{time_range_minutes}m]))',
        "error_rate": f'sum(rate(otel_http_server_request_duration_seconds_count{{service_name="{service}",http_status_code=~"5.."}}[{time_range_minutes}m])) / sum(rate(otel_http_server_request_duration_seconds_count{{service_name="{service}"}}[{time_range_minutes}m])) * 100',
        "p50_latency": f'histogram_quantile(0.50, sum by(le) (rate(otel_http_server_request_duration_seconds_bucket{{service_name="{service}"}}[{time_range_minutes}m])))',
        "p95_latency": f'histogram_quantile(0.95, sum by(le) (rate(otel_http_server_request_duration_seconds_bucket{{service_name="{service}"}}[{time_range_minutes}m])))',
        "p99_latency": f'histogram_quantile(0.99, sum by(le) (rate(otel_http_server_request_duration_seconds_bucket{{service_name="{service}"}}[{time_range_minutes}m])))',
    }

    results = {}
    async with httpx.AsyncClient() as client:
        for name, query in queries.items():
            try:
                resp = await client.get(
                    f"{PROMETHEUS_URL}/api/v1/query",
                    params={"query": query},
                    timeout=10.0,
                )
                data = resp.json()
                if data.get("status") == "success":
                    result = data.get("data", {}).get("result", [])
                    if result:
                        value = result[0].get("value", [None, None])[1]
                        results[name] = value
                    else:
                        results[name] = "no data"
                else:
                    results[name] = "query error"
            except Exception as e:
                results[name] = f"error: {str(e)}"

    return json.dumps(
        {
            "service": service,
            "time_window": f"{time_range_minutes}m",
            "request_rate_per_second": results.get("request_rate", "N/A"),
            "error_rate_percent": results.get("error_rate", "N/A"),
            "p50_latency_seconds": results.get("p50_latency", "N/A"),
            "p95_latency_seconds": results.get("p95_latency", "N/A"),
            "p99_latency_seconds": results.get("p99_latency", "N/A"),
        },
        indent=2,
    )


@mcp.tool()
async def check_all_services_health(time_range_minutes: int = 5) -> str:
    """Quick health check across all services. Use this to identify which service has issues.

    Args:
        time_range_minutes: Time window to evaluate (default: 5 minutes).

    Returns:
        Health summary for every service, highlighting any with elevated error rates or latency.
    """
    all_health = []
    for service in SERVICE_TOPOLOGY:
        health = await get_service_health(service, time_range_minutes)
        all_health.append(json.loads(health))

    return json.dumps(all_health, indent=2)


if __name__ == "__main__":
    mcp.run()
