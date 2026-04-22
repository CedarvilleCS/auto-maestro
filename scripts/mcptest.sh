#!/usr/bin/env bash
# test_mcp.sh
# Validates the MCP REST API endpoints and basic functionality.

set -u
BASE_URL="${1:-http://localhost:5000}"   # override: ./test_mcp.sh http://192.168.56.101:5000
START_TS=$(date -Iseconds)
FAIL=0
PASS=0

need() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "WARN: '$1' not found. Install it for best output."
  fi
}
need curl
need jq

say() { printf "\n=== %s ===\n" "$*"; }
ok()  { echo "PASS: $*"; PASS=$((PASS+1)); }
bad() { echo "FAIL: $*"; FAIL=$((FAIL+1)); }

api_get() {
  curl -sS -w '\n%{http_code}\n' "$1"
}
api_post_json() {
  local url="$1"; shift
  curl -sS -w '\n%{http_code}\n' -H 'Content-Type: application/json' -d "$*" "$url"
}

say "Health check: $BASE_URL/health"
R=$(api_get "$BASE_URL/health")
BODY=$(printf "%s" "$R" | sed -n '1,${p}' | sed -n '1,$p' | head -n -1)
CODE=$(printf "%s" "$R" | tail -n1)
echo "$BODY"
if [ "$CODE" = "200" ] && echo "$BODY" | jq -e '.status=="alive"' >/dev/null 2>&1; then
  ok "/health"
else
  bad "/health (code=$CODE)"
fi

say "List containers: $BASE_URL/containers"
R=$(api_get "$BASE_URL/containers")
BODY=$(printf "%s" "$R" | head -n -1)
CODE=$(printf "%s" "$R" | tail -n1)
echo "$BODY" | jq -r '.containers[]?| "\(.name)  \(.status)"' 2>/dev/null || true
if [ "$CODE" = "200" ] && echo "$BODY" | jq -e '.status=="ok"' >/dev/null 2>&1; then
  ok "/containers"
else
  bad "/containers (code=$CODE)"
fi

# Try to auto-detect A1 and B1 containers for a cross-subnet ping via MCP
A1=$(echo "$BODY" | jq -r '.containers[]?|select(.name|test("^A1-")).name' 2>/dev/null | head -n1)
B1_IP=$(echo "$BODY" | jq -r '.containers[]?|select(.name|test("^B1-")).ips[]?' 2>/dev/null | head -n1)

say "Cross-subnet ping via MCP /ping (A1 -> B1)"
if [ -n "$A1" ] && [ -n "$B1_IP" ] && [ "$A1" != "null" ] && [ "$B1_IP" != "null" ]; then
  R=$(api_post_json "$BASE_URL/ping" "$(jq -nc --arg c "$A1" --arg t "$B1_IP" '{container:$c, target:$t}')")
  BODY=$(printf "%s" "$R" | head -n -1)
  CODE=$(printf "%s" "$R" | tail -n1)
  echo "$BODY" | jq -r '.output' 2>/dev/null | sed 's/^/  /' | head -n 5
  if [ "$CODE" = "200" ] && echo "$BODY" | jq -e '.status=="ok"' >/dev/null 2>&1; then
    ok "/ping $A1 -> $B1_IP"
  else
    bad "/ping $A1 -> $B1_IP (code=$CODE)"
  fi
else
  bad "Could not auto-detect A1 or B1 IP from /containers"
fi

# Run a couple of execs via MCP (/exec)
say "Exec via MCP: uname -a in router-firewall"
R=$(api_post_json "$BASE_URL/exec" '{"container":"router-firewall","cmd":["uname","-a"]}')
BODY=$(printf "%s" "$R" | head -n -1)
CODE=$(printf "%s" "$R" | tail -n1)
echo "$BODY" | jq -r '.output' 2>/dev/null | sed 's/^/  /' | head -n 2
if [ "$CODE" = "200" ] && echo "$BODY" | jq -e '.status=="ok"' >/dev/null 2>&1; then
  ok "/exec uname -a (router)"
else
  bad "/exec uname -a (router) (code=$CODE)"
fi

say "Exec via MCP: ip route in A-10.8.0.99"
R=$(api_post_json "$BASE_URL/exec" '{"container":"A-10.8.0.99","cmd":["ip","route"]}')
BODY=$(printf "%s" "$R" | head -n -1)
CODE=$(printf "%s" "$R" | tail -n1)
echo "$BODY" | jq -r '.output' 2>/dev/null | sed 's/^/  /' | head -n 5
if [ "$CODE" = "200" ] && echo "$BODY" | jq -e '.status=="ok"' >/dev/null 2>&1; then
  ok "/exec ip route (A)"
else
  bad "/exec ip route (A) (code=$CODE)"
fi

# Optional: forward test if you want (web is exposed on host; internal reachability may vary)
# say "Forward test (optional) - disabled by default"

say "Summary"
echo "PASS=$PASS FAIL=$FAIL base_url=$BASE_URL started=$START_TS finished=$(date -Iseconds)"
[ "$FAIL" -eq 0 ] && exit 0 || exit 1
