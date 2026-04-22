#!/usr/bin/env bash
# scripts/up.sh — minimal helper to bring everything up
set -e

# Default values
RUNTIME="docker"
SEED="sandbox_setup/docker-compose.seed.yml"
BUILD_FLAG=""
BASE_LOCAL="localhost/automaestro/base:latest"
BASE_REMOTE="ghcr.io/cedarvillecs/automaestro-base:latest"
BASE_DOCKERFILE="${BASE_DOCKERFILE:-./Dockerfile}"
BASE_CONTEXT="${BASE_CONTEXT:-.}"

# Parse arguments
while [[ $# -gt 0 ]]; do
    case "$1" in
        --build)
            BUILD_FLAG="--build"
            shift
            ;;
        docker|podman)
            RUNTIME="$1"
            shift
            ;;
        *.yml)
            SEED="$1"
            shift
            ;;
        *)
            shift
            ;;
    esac
done

# Validate runtime argument
if [[ "$RUNTIME" != "docker" && "$RUNTIME" != "podman" ]]; then
  echo "Error: RUNTIME must be either 'docker' or 'podman'" >&2
  exit 1
fi

ensure_base_image() {
  if [[ -n "${BASE_IMAGE:-}" ]]; then
    if $RUNTIME image inspect "$BASE_IMAGE" >/dev/null 2>&1; then
      echo "Using base image: $BASE_IMAGE"
      return
    fi

    echo "Base image not found locally. Attempting to pull: $BASE_IMAGE"
    if $RUNTIME pull "$BASE_IMAGE"; then
      echo "Pulled base image: $BASE_IMAGE"
      return
    fi

    echo "Pull failed. Building base image locally: $BASE_IMAGE"
    echo "Building with Dockerfile '$BASE_IMAGE' in context '$BASE_CONTEXT'"
    $RUNTIME build -t "$BASE_IMAGE" -f "$BASE_DOCKERFILE" "$BASE_CONTEXT"
  fi
  if $RUNTIME image inspect "$BASE_LOCAL" >/dev/null 2>&1; then
    echo "Using local base image: $BASE_LOCAL"
    export BASE_IMAGE="$BASE_LOCAL"
    return
  fi

  if $RUNTIME image inspect "$BASE_REMOTE" >/dev/null 2>&1; then
    echo "Using pulled base image: $BASE_REMOTE"
    export BASE_IMAGE="$BASE_REMOTE"
    return
  fi

  echo "Base image not found locally. Attempting to pull: $BASE_REMOTE"
  if $RUNTIME pull "$BASE_REMOTE"; then
    echo "Pulled base image: $BASE_REMOTE"
    export BASE_IMAGE="$BASE_REMOTE"
    return
  fi

  echo "Pull failed. Building base image locally: $BASE_LOCAL"
  echo "Building with Dockerfile '$BASE_DOCKERFILE' in context '$BASE_CONTEXT'"
  $RUNTIME build -t "$BASE_LOCAL" -f "$BASE_DOCKERFILE" "$BASE_CONTEXT"
  export BASE_IMAGE="$BASE_LOCAL"
}

ensure_base_image

# Select the appropriate compose command
if [[ "$RUNTIME" == "podman" ]]; then
  COMPOSE_CMD="podman-compose"
else
  COMPOSE_CMD="docker compose"
fi

$COMPOSE_CMD -f docker-compose.yml -f "$SEED" up -d $BUILD_FLAG
