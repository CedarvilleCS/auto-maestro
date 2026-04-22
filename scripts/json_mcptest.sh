#!/usr/bin/env bash
# -----------------------------------------------------------------------------
# test_mcp.sh — In-depth MCP server test (CLI only, colorized JSON output)
# -----------------------------------------------------------------------------
# Usage:
#   chmod +x test_mcp.sh
#   ./test_mcp.sh [MCP_URL]
# Defaults to http://localhost:5000
# -----------------------------------------------------------------------------

set -uo pipefail
MCP_URL="${1:-http://localhost:5000}"

# Requirements
for cmd in curl jq; do
  if ! command -v "$cmd" >/dev/null 2>&1; then
    echo "ERROR: required command not found: $cmd"
    exit 2
  fi
done

say() { printf "\n🔎 %s\n" "$*"; }

# GET helper
api_get() {
  curl -sS "$1"
}

# POST helper
api_post_json() {
  local url="$1"; local data="$2"
  curl -sS -H 'Content-Type: application/json' -d "$data" "$url"
}

# -------------------------------------------------------------------
say "Health check"
api_get "${MCP_URL}/health" | jq --color-output .

# -------------------------------------------------------------------
say "List containers"
CONTAINERS_JSON=$(api_get "${MCP_URL}/containers")
echo "$CONTAINERS_JSON" | jq --color-output .

# Grab A1 and B1 names/IPs
A1_NAME=$(echo "$CONTAINERS_JSON" | jq -r '.containers[]?.name | select(test("^A1-"))' | head -n1)
B1_IP=$(echo "$CONTAINERS_JSON" | jq -r '.containers[]? | select(.name|test("^B1-")) | .ips[]?' | head -n1)

# -------------------------------------------------------------------
say "Exec test: router-firewall uname -a"
api_post_json "${MCP_URL}/exec" '{"container":"router-firewall","cmd":["uname","-a"]}' \
  | jq --color-output .

say "Exec test: router-firewall ip route"
api_post_json "${MCP_URL}/exec" '{"container":"router-firewall","cmd":["ip","route"]}' \
  | jq --color-output .

if [ -n "$A1_NAME" ] && [ "$A1_NAME" != "null" ]; then
  say "Exec test: $A1_NAME ip route"
  api_post_json "${MCP_URL}/exec" "$(jq -nc --arg c "$A1_NAME" '{container:$c, cmd:["ip","route"]}')" \
    | jq --color-output .
fi

# -------------------------------------------------------------------
if [ -n "$A1_NAME" ] && [ -n "$B1_IP" ] && [ "$B1_IP" != "null" ]; then
  say "Ping test: $A1_NAME -> $B1_IP"
  api_post_json "${MCP_URL}/ping" "$(jq -nc --arg c "$A1_NAME" --arg t "$B1_IP" '{container:$c,target:$t}')" \
    | jq --color-output .
else
  echo "⚠️ Skipping ping test (A1 or B1 not found)"
fi

# -------------------------------------------------------------------
say "Forward test (web -> /)"
WEB_NAME=$(echo "$CONTAINERS_JSON" | jq -r '.containers[]?.name | select(test("web"))' | head -n1)
if [ -n "$WEB_NAME" ] && [ "$WEB_NAME" != "null" ]; then
  api_post_json "${MCP_URL}/forward" "$(jq -nc --arg c "$WEB_NAME" --arg url "http://localhost:8866" '{container:$c,url:$url}')" \
    | jq --color-output .
else
  echo "⚠️ Skipping forward test (no web container found)"
fi

echo -e "\n🎉 MCP test completed!"

