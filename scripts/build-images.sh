#!/bin/bash
# Build Docker images for all services using Minikube's Docker daemon
set -e

echo "Switching to Minikube Docker daemon..."
eval $(minikube docker-env)

SERVICES=("gateway" "user-service" "content-service" "recommendation-service")

for svc in "${SERVICES[@]}"; do
    echo "Building obs-${svc}..."
    docker build -t "obs-${svc}:latest" \
        --build-arg SERVICE_NAME="${svc}" \
        -f services/Dockerfile services/
done

echo "All images built successfully."
docker images | grep obs-
