#!/bin/bash
# Port-forward observability backends so the MCP server can reach them locally
set -e

echo "Starting port-forwards (run in background)..."
echo "  Prometheus -> localhost:9090"
echo "  Loki       -> localhost:3100"
echo "  Tempo      -> localhost:3200"
echo ""
echo "Press Ctrl+C to stop all."

kubectl port-forward svc/prometheus 9090:9090 &
kubectl port-forward svc/loki 3100:3100 &
kubectl port-forward svc/tempo 3200:3200 &

wait
