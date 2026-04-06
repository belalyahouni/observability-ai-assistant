#!/bin/bash
# Deploy the full stack to Minikube
set -e

echo "=== Deploying observability stack ==="
kubectl apply -f k8s/observability/

echo ""
echo "=== Waiting for observability pods ==="
kubectl wait --for=condition=ready pod -l app=otel-collector --timeout=120s
kubectl wait --for=condition=ready pod -l app=prometheus --timeout=120s
kubectl wait --for=condition=ready pod -l app=loki --timeout=120s
kubectl wait --for=condition=ready pod -l app=tempo --timeout=120s
kubectl wait --for=condition=ready pod -l app=grafana --timeout=120s

echo ""
echo "=== Deploying microservices ==="
kubectl apply -f k8s/services/

echo ""
echo "=== Waiting for service pods ==="
kubectl wait --for=condition=ready pod -l app=gateway --timeout=120s
kubectl wait --for=condition=ready pod -l app=user-service --timeout=120s
kubectl wait --for=condition=ready pod -l app=content-service --timeout=120s
kubectl wait --for=condition=ready pod -l app=recommendation-service --timeout=120s

echo ""
echo "=== Deployment complete ==="
echo ""
echo "Access points:"
echo "  Gateway:    $(minikube service gateway --url)"
echo "  Grafana:    $(minikube service grafana --url)"
echo "  Prometheus: kubectl port-forward svc/prometheus 9090:9090"
