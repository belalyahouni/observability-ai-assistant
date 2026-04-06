import os
import sys
import random
import time
import logging

from fastapi import FastAPI, HTTPException

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from shared.telemetry import setup_telemetry

app = FastAPI(title="Recommendation Service")
tracer, meter = setup_telemetry(app, "recommendation-service")
logger = logging.getLogger("recommendation-service")

# Custom metrics
request_counter = meter.create_counter(
    "recommendation_service.requests.total",
    description="Total requests to recommendation service",
)
recommendations_generated = meter.create_histogram(
    "recommendation_service.recommendations.count",
    description="Number of recommendations generated per request",
)

# Fault injection
FAULT_ENABLED = os.getenv("FAULT_ENABLED", "false").lower() == "true"
FAULT_LATENCY_MS = int(os.getenv("FAULT_LATENCY_MS", "0"))
FAULT_ERROR_RATE = float(os.getenv("FAULT_ERROR_RATE", "0.0"))

RECOMMENDATIONS = {
    "user-1": ["movie-1", "show-1", "movie-2"],
    "user-2": ["show-2", "movie-3"],
    "user-3": ["movie-2", "movie-1", "show-1", "movie-3"],
    "user-4": ["show-2", "movie-3", "show-1"],
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
    return {"status": "healthy", "service": "recommendation-service"}


@app.get("/recommend/{user_id}")
def recommend(user_id: str):
    request_counter.add(1, {"endpoint": "/recommend", "method": "GET"})
    maybe_inject_fault()
    recs = RECOMMENDATIONS.get(user_id)
    if not recs:
        logger.warning("No recommendations found for user %s, returning defaults", user_id)
        recs = ["movie-1", "show-2"]
    recommendations_generated.record(len(recs), {"user_id": user_id})
    logger.info("Generated %d recommendations for user %s", len(recs), user_id)
    return {"user_id": user_id, "recommendations": recs}
