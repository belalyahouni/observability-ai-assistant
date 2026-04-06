import os
import random
import time
import logging

import httpx
from fastapi import FastAPI, HTTPException

app = FastAPI(title="Gateway Service")
logger = logging.getLogger("gateway")

USER_SERVICE_URL = os.getenv("USER_SERVICE_URL", "http://localhost:8001")
CONTENT_SERVICE_URL = os.getenv("CONTENT_SERVICE_URL", "http://localhost:8002")

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


@app.get("/health")
def health():
    return {"status": "healthy", "service": "gateway"}


@app.get("/api/user/{user_id}")
async def get_user(user_id: str):
    maybe_inject_fault()
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{USER_SERVICE_URL}/users/{user_id}", timeout=10.0)
        resp.raise_for_status()
        return resp.json()


@app.get("/api/content")
async def get_content():
    maybe_inject_fault()
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{CONTENT_SERVICE_URL}/content", timeout=10.0)
        resp.raise_for_status()
        return resp.json()


@app.get("/api/content/{content_id}")
async def get_content_item(content_id: str):
    maybe_inject_fault()
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{CONTENT_SERVICE_URL}/content/{content_id}", timeout=10.0
        )
        resp.raise_for_status()
        return resp.json()


@app.get("/api/recommendations/{user_id}")
async def get_recommendations(user_id: str):
    maybe_inject_fault()
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{CONTENT_SERVICE_URL}/recommendations/{user_id}", timeout=10.0
        )
        resp.raise_for_status()
        return resp.json()
