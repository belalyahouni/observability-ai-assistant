#!/bin/bash
# Remove all deployed resources
set -e

echo "Removing microservices..."
kubectl delete -f k8s/services/ --ignore-not-found

echo "Removing observability stack..."
kubectl delete -f k8s/observability/ --ignore-not-found

echo "Teardown complete."
