#!/usr/bin/env bash
set -e

#podman compose -f docker-compose.yml -f "$SEED" down

SEED="${1:-sandbox_setup/docker-compose.seed.yml}"

# If the next argument is --volumes, enable volume removal
VOLUME_FLAG=""
if [[ "${2:-}" == "--volumes" ]]; then
  VOLUME_FLAG="--volumes"
fi

echo "Running: docker compose -f docker-compose.yml -f $SEED down $VOLUME_FLAG"
docker compose -f docker-compose.yml -f "$SEED" down $VOLUME_FLAG
