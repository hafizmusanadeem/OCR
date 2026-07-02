#!/bin/bash
# Scale OCR workers horizontally
# Usage: ./scripts/scale-workers.sh [N]
#   N = number of worker replicas (default: 3)

set -euo pipefail

REPLICAS="${1:-3}"

echo "Scaling OCR workers to $REPLICAS replicas..."
docker-compose up -d --scale worker=$REPLICAS worker

echo "Current worker containers:"
docker-compose ps | grep worker || true
