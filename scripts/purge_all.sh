#!/usr/bin/env bash
set -e

echo "Stopping all running containers..."
docker stop $(docker ps -aq) 2>/dev/null || true

echo "Removing all containers..."
docker rm -f $(docker ps -aq) 2>/dev/null || true

echo "Removing all images..."
docker rmi -f $(docker images -aq) 2>/dev/null || true

echo "Removing all unused networks..."
docker network prune -f

# Uncomment the next line if you also want to remove ALL volumes
# echo "Removing all volumes..."
# docker volume prune -f

echo "Running a full system prune to clean up any leftovers..."
docker system prune -af

echo "Docker purge complete ✅"
