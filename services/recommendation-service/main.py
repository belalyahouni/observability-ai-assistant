import os
import random
import time
import logging

from fastapi import FastAPI, HTTPException

app = FastAPI(title="Recommendation Service")
logger = logging.getLogger("recommendation-service")

# Fault injection
FAULT_ENABLED = os.getenv("FAULT_ENABLED", "false").lower() == "true"
FAULT_LATENCY_MS = int(os.getenv("FAULT_LATENCY_MS", "0"))
FAULT_ERROR_RATE = float(os.getenv("FAULT_ERROR_RATE", "0.0"))

# Simulated recommendation engine
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
    maybe_inject_fault()
    recs = RECOMMENDATIONS.get(user_id)
    if not recs:
        logger.warning("No recommendations found for user %s, returning defaults", user_id)
        recs = ["movie-1", "show-2"]
    logger.info("Generated %d recommendations for user %s", len(recs), user_id)
    return {"user_id": user_id, "recommendations": recs}
