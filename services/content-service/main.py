import os
import sys
import random
import time
import logging

import httpx
from fastapi import FastAPI, HTTPException

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from shared.telemetry import setup_telemetry

app = FastAPI(title="Content Service")
tracer, meter = setup_telemetry(app, "content-service")
logger = logging.getLogger("content-service")

# Custom metrics
request_counter = meter.create_counter(
    "content_service.requests.total",
    description="Total requests to content service",
)

from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
HTTPXClientInstrumentor().instrument()

RECOMMENDATION_SERVICE_URL = os.getenv(
    "RECOMMENDATION_SERVICE_URL", "http://recommendation-service:8000"
)

# Fault injection
FAULT_ENABLED = os.getenv("FAULT_ENABLED", "false").lower() == "true"
FAULT_LATENCY_MS = int(os.getenv("FAULT_LATENCY_MS", "0"))
FAULT_ERROR_RATE = float(os.getenv("FAULT_ERROR_RATE", "0.0"))

CONTENT = {
    "movie-1": {"id": "movie-1", "title": "The Matrix", "genre": "sci-fi", "year": 1999},
    "movie-2": {"id": "movie-2", "title": "Inception", "genre": "sci-fi", "year": 2010},
    "movie-3": {"id": "movie-3", "title": "Pulp Fiction", "genre": "crime", "year": 1994},
    "show-1": {"id": "show-1", "title": "Breaking Bad", "genre": "drama", "year": 2008},
    "show-2": {"id": "show-2", "title": "The Office", "genre": "comedy", "year": 2005},
}


def maybe_inject_fault():
    if not FAULT_ENABLED:
        return
    if FAULT_LATENCY_MS > 0:
        time.sleep(FAULT_LATENCY_MS / 1000.0)
    if FAULT_ERROR_RATE > 0 and random.random() < FAULT_ERROR_RATE:
        raise HTTPException(status_code=500, detail="Injected fault")


@app.get("/health")
def health():
    return {"status": "healthy", "service": "content-service"}


@app.get("/content")
def list_content():
    request_counter.add(1, {"endpoint": "/content", "method": "GET"})
    maybe_inject_fault()
    logger.info("Listing all content")
    return list(CONTENT.values())


@app.get("/content/{content_id}")
def get_content(content_id: str):
    request_counter.add(1, {"endpoint": "/content/id", "method": "GET"})
    maybe_inject_fault()
    item = CONTENT.get(content_id)
    if not item:
        logger.warning("Content %s not found", content_id)
        raise HTTPException(status_code=404, detail=f"Content {content_id} not found")
    logger.info("Fetched content %s", content_id)
    return item


@app.get("/recommendations/{user_id}")
async def get_recommendations(user_id: str):
    request_counter.add(1, {"endpoint": "/recommendations", "method": "GET"})
    maybe_inject_fault()
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{RECOMMENDATION_SERVICE_URL}/recommend/{user_id}", timeout=10.0
            )
            resp.raise_for_status()
            return resp.json()
    except httpx.HTTPStatusError as e:
        logger.error("Upstream error from recommendation-service: %s", e.response.status_code)
        raise HTTPException(status_code=502, detail="Recommendation service error")
