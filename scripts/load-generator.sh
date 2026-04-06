#!/bin/bash
# Generate traffic to produce telemetry data
set -e

GATEWAY_URL="${1:-$(minikube service gateway --url)}"
INTERVAL="${2:-2}"

echo "Sending traffic to ${GATEWAY_URL} every ${INTERVAL}s..."
echo "Press Ctrl+C to stop."
echo ""

USERS=("user-1" "user-2" "user-3" "user-4")
CONTENT=("movie-1" "movie-2" "movie-3" "show-1" "show-2")

while true; do
    # Random user lookup
    user=${USERS[$RANDOM % ${#USERS[@]}]}
    echo "[$(date +%H:%M:%S)] GET /api/user/${user}"
    curl -s "${GATEWAY_URL}/api/user/${user}" > /dev/null 2>&1 || echo "  -> FAILED"

    sleep 0.5

    # Content listing
    echo "[$(date +%H:%M:%S)] GET /api/content"
    curl -s "${GATEWAY_URL}/api/content" > /dev/null 2>&1 || echo "  -> FAILED"

    sleep 0.5

    # Random content item
    item=${CONTENT[$RANDOM % ${#CONTENT[@]}]}
    echo "[$(date +%H:%M:%S)] GET /api/content/${item}"
    curl -s "${GATEWAY_URL}/api/content/${item}" > /dev/null 2>&1 || echo "  -> FAILED"

    sleep 0.5

    # Recommendations (this hits the fault-injected service)
    user=${USERS[$RANDOM % ${#USERS[@]}]}
    echo "[$(date +%H:%M:%S)] GET /api/recommendations/${user}"
    curl -s -m 10 "${GATEWAY_URL}/api/recommendations/${user}" > /dev/null 2>&1 || echo "  -> FAILED (expected — fault injection)"

    echo ""
    sleep "${INTERVAL}"
done
