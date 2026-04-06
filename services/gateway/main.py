import os
import sys
import random
import time
import logging

import httpx
from fastapi import FastAPI, HTTPException

# Add shared module to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from shared.telemetry import setup_telemetry

app = FastAPI(title="Gateway Service")
tracer, meter = setup_telemetry(app, "gateway")
logger = logging.getLogger("gateway")

# Custom metrics
request_counter = meter.create_counter(
    "gateway.requests.total",
    description="Total requests handled by gateway",
)
upstream_errors = meter.create_counter(
    "gateway.upstream_errors.total",
    description="Errors from upstream services",
)

USER_SERVICE_URL = os.getenv("USER_SERVICE_URL", "http://user-service:8000")
CONTENT_SERVICE_URL = os.getenv("CONTENT_SERVICE_URL", "http://content-service:8000")

# Fault injection
FAULT_ENABLED = os.getenv("FAULT_ENABLED", "false").lower() == "true"
FAULT_LATENCY_MS = int(os.getenv("FAULT_LATENCY_MS", "0"))
FAULT_ERROR_RATE = float(os.getenv("FAULT_ERROR_RATE", "0.0"))


def maybe_inject_fault():
    if not FAULT_ENABLED:
        return
    if FAULT_LATENCY_MS > 0:
        time.sleep(FAULT_LATENCY_MS / 1000.0)
    if FAULT_ERROR_RATE > 0 and random.random() < FAULT_ERROR_RATE:
        raise HTTPException(status_code=500, detail="Injected fault")


# Instrument httpx for trace propagation
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
HTTPXClientInstrumentor().instrument()


@app.get("/health")
def health():
    return {"status": "healthy", "service": "gateway"}


@app.get("/api/user/{user_id}")
async def get_user(user_id: str):
    request_counter.add(1, {"endpoint": "/api/user", "method": "GET"})
    maybe_inject_fault()
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{USER_SERVICE_URL}/users/{user_id}", timeout=10.0)
            resp.raise_for_status()
            return resp.json()
    except httpx.HTTPStatusError as e:
        upstream_errors.add(1, {"upstream": "user-service", "status": str(e.response.status_code)})
        logger.error("Upstream error from user-service: %s", e.response.status_code)
        raise HTTPException(status_code=502, detail="User service error")


@app.get("/api/content")
async def get_content():
    request_counter.add(1, {"endpoint": "/api/content", "method": "GET"})
    maybe_inject_fault()
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{CONTENT_SERVICE_URL}/content", timeout=10.0)
            resp.raise_for_status()
            return resp.json()
    except httpx.HTTPStatusError as e:
        upstream_errors.add(1, {"upstream": "content-service", "status": str(e.response.status_code)})
        logger.error("Upstream error from content-service: %s", e.response.status_code)
        raise HTTPException(status_code=502, detail="Content service error")


@app.get("/api/content/{content_id}")
async def get_content_item(content_id: str):
    request_counter.add(1, {"endpoint": "/api/content/item", "method": "GET"})
    maybe_inject_fault()
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{CONTENT_SERVICE_URL}/content/{content_id}", timeout=10.0)
            resp.raise_for_status()
            return resp.json()
    except httpx.HTTPStatusError as e:
        upstream_errors.add(1, {"upstream": "content-service", "status": str(e.response.status_code)})
        logger.error("Upstream error from content-service: %s", e.response.status_code)
        raise HTTPException(status_code=502, detail="Content service error")


@app.get("/api/recommendations/{user_id}")
async def get_recommendations(user_id: str):
    request_counter.add(1, {"endpoint": "/api/recommendations", "method": "GET"})
    maybe_inject_fault()
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{CONTENT_SERVICE_URL}/recommendations/{user_id}", timeout=10.0
            )
            resp.raise_for_status()
            return resp.json()
    except httpx.HTTPStatusError as e:
        upstream_errors.add(1, {"upstream": "content-service", "status": str(e.response.status_code)})
        logger.error("Upstream error from content-service: %s", e.response.status_code)
        raise HTTPException(status_code=502, detail="Content service error")
