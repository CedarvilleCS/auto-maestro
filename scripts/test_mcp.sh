#!/bin/bash
# --------------------------------------------------------------------
# MCP Server Quick Test Script
# --------------------------------------------------------------------
# This script verifies that the MCP server is alive and can interact
# with sandbox containers. Run it from inside the VM host (not inside
# a container).
#
# Usage:
#   chmod +x test_mcp.sh
#   ./test_mcp.sh
# --------------------------------------------------------------------

MCP_URL="http://localhost:5000"

echo "🔎 Checking MCP health..."
curl -s ${MCP_URL}/health | jq .

echo -e "\n🔎 Listing running containers..."
curl -s ${MCP_URL}/containers | jq .

# Grab first container name from /containers for testing
CONTAINER=$(curl -s ${MCP_URL}/containers | jq -r '.containers[0].name')

if [ -n "$CONTAINER" ] && [ "$CONTAINER" != "null" ]; then
  echo -e "\n✅ Found container: $CONTAINER"
else
  echo -e "\n❌ No containers found! Exiting."
  exit 1
fi

echo -e "\n🔎 Running ls / inside $CONTAINER..."
curl -s -X POST ${MCP_URL}/exec \
  -H "Content-Type: application/json" \
  -d "{\"container\":\"$CONTAINER\",\"cmd\":[\"ls\",\"/\"]}" | jq .

echo -e "\n🎉 MCP test completed!"

