#!/usr/bin/env bash
# test_containers.sh
# Validates container status, IPs, intra- and inter-network connectivity, and host-mapped ports.

set -u
START_TS=$(date -Iseconds)
FAIL=0
PASS=0

need() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "WARN: '$1' not found. Install it for best output."
  fi
}

say() { printf "\n=== %s ===\n" "$*"; }
ok()  { echo "PASS: $*"; PASS=$((PASS+1)); }
bad() { echo "FAIL: $*"; FAIL=$((FAIL+1)); }

# Tools check
need docker
need jq
need curl

# Expected containers from your compose
C_A="A-10.8.0.99"
C_A1="A1-10.8.0.5"
C_A2="A2-10.8.0.6"
C_B="B-192.168.20.99"
C_B1="B1-192.168.20.5"
C_B2="B2-192.168.20.6"
C_R="router-firewall"
C_MCP="mcp-server"
C_WEB="web"

CONTAINERS=("$C_A" "$C_A1" "$C_A2" "$C_B" "$C_B1" "$C_B2" "$C_R" "$C_MCP" "$C_WEB")

say "Docker state"
docker ps --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}'
docker network ls

say "Verify containers are running"
for c in "${CONTAINERS[@]}"; do
  if docker inspect "$c" >/dev/null 2>&1; then
    st=$(docker inspect -f '{{.State.Status}}' "$c" 2>/dev/null || echo "?")
    if [ "$st" = "running" ]; then ok "$c running"
    else bad "$c not running (status: $st)"
    fi
  else
    bad "$c not found"
  fi
done

say "Show IPs by network (per container)"
for c in "${CONTAINERS[@]}"; do
  echo "- $c"
  docker inspect -f '{{range $k,$v := .NetworkSettings.Networks}}{{printf "  %s -> %s\n" $k $v.IPAddress}}{{end}}' "$c" 2>/dev/null || echo "  (inspect failed)"
done

say "Check ping/curl available in key containers"
for c in "$C_A" "$C_B" "$C_R" "$C_MCP"; do
  echo "- $c"
  docker exec -it "$c" sh -lc 'which ping >/dev/null 2>&1 && echo "  ping: ok" || echo "  ping: MISSING"; which curl >/dev/null 2>&1 && echo "  curl: ok" || echo "  curl: MISSING"' || echo "  (exec failed)"
done

# Helper to run a short ping test
tp() {
  local from="$1" to="$2" label="$3"
  if docker exec -it "$from" sh -lc "ping -c 3 -W 2 $to" >/dev/null 2>&1; then
    ok "ping $label"
  else
    bad "ping $label"
  fi
}

say "Same-subnet pings (10.8.0.0/24)"
tp "$C_A"  "10.8.0.5"   "$C_A -> $C_A1"
tp "$C_A1" "10.8.0.6"   "$C_A1 -> $C_A2"
tp "$C_A"  "10.8.0.11"  "$C_A -> router (10.8.0.11)"

say "Same-subnet pings (192.168.20.0/24)"
tp "$C_B"  "192.168.20.5" "$C_B -> $C_B1"
tp "$C_B1" "192.168.20.6" "$C_B1 -> $C_B2"
tp "$C_B"  "192.168.20.11" "$C_B -> router (192.168.20.11)"

say "Cross-subnet pings (via router)"
tp "$C_A" "192.168.20.99" "$C_A -> $C_B"
tp "$C_B" "10.8.0.99"     "$C_B -> $C_A"

say "Router sanity (addresses, routes, iptables)"
docker exec -it "$C_R" ip addr | sed 's/^/  /'
docker exec -it "$C_R" ip route | sed 's/^/  /'
docker exec -it "$C_R" bash -lc 'iptables -L -n; echo "--- nat"; iptables -t nat -L -n' | sed 's/^/  /'

say "Host-mapped ports reachable from VM host"
# Web on 8866, MCP on 5000 (per compose)
if curl -s -I --max-time 5 http://localhost:8866 >/dev/null; then ok "curl localhost:8866"
else bad "curl localhost:8866"
fi
if curl -s -I --max-time 5 http://localhost:5000 >/dev/null; then ok "curl localhost:5000"
else bad "curl localhost:5000"
fi

say "Optional external reachability from router (may be blocked by rules)"
if docker exec -it "$C_R" bash -lc "ping -c 2 -W 2 8.8.8.8" >/dev/null 2>&1; then
  ok "router -> 8.8.8.8"
else
  echo "  (ICMP may be blocked; trying HTTP to example.com)"
  if docker exec -it "$C_R" bash -lc "curl -s --max-time 5 http://93.184.216.34 >/dev/null"; then
    ok "router -> example.com (HTTP)"
  else
    bad "router external egress"
  fi
fi

say "Summary"
echo "PASS=$PASS FAIL=$FAIL started=$START_TS finished=$(date -Iseconds)"
[ "$FAIL" -eq 0 ] && exit 0 || exit 1

