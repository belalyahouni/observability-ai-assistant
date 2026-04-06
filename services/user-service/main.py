import os
import sys
import random
import time
import logging

from fastapi import FastAPI, HTTPException

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from shared.telemetry import setup_telemetry

app = FastAPI(title="User Service")
tracer, meter = setup_telemetry(app, "user-service")
logger = logging.getLogger("user-service")

# Custom metrics
request_counter = meter.create_counter(
    "user_service.requests.total",
    description="Total requests to user service",
)

# Fault injection
FAULT_ENABLED = os.getenv("FAULT_ENABLED", "false").lower() == "true"
FAULT_LATENCY_MS = int(os.getenv("FAULT_LATENCY_MS", "0"))
FAULT_ERROR_RATE = float(os.getenv("FAULT_ERROR_RATE", "0.0"))

USERS = {
    "user-1": {"id": "user-1", "name": "Alice Johnson", "plan": "premium"},
    "user-2": {"id": "user-2", "name": "Bob Smith", "plan": "free"},
    "user-3": {"id": "user-3", "name": "Charlie Brown", "plan": "premium"},
    "user-4": {"id": "user-4", "name": "Diana Prince", "plan": "free"},
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
    return {"status": "healthy", "service": "user-service"}


@app.get("/users/{user_id}")
def get_user(user_id: str):
    request_counter.add(1, {"endpoint": "/users/id", "method": "GET"})
    maybe_inject_fault()
    user = USERS.get(user_id)
    if not user:
        logger.warning("User %s not found", user_id)
        raise HTTPException(status_code=404, detail=f"User {user_id} not found")
    logger.info("Fetched user %s", user_id)
    return user


@app.get("/users")
def list_users():
    request_counter.add(1, {"endpoint": "/users", "method": "GET"})
    maybe_inject_fault()
    logger.info("Listing all users")
    return list(USERS.values())
