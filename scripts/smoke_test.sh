#!/usr/bin/env bash
# Hits every endpoint and checks the expected status code (CLAUDE.md §13).
# Usage: BASE_URL=http://localhost:8001 bash scripts/smoke_test.sh
set -u

BASE_URL="${BASE_URL:-http://localhost:8000}"
PASS=0
FAIL=0

check() {
  local label="$1" expected="$2" actual="$3"
  if [ "$actual" = "$expected" ]; then
    echo "PASS  $label ($actual)"
    PASS=$((PASS + 1))
  else
    echo "FAIL  $label (expected $expected, got $actual)"
    FAIL=$((FAIL + 1))
  fi
}

status() { curl -s -o /dev/null -w "%{http_code}" "$@"; }

check "GET /health"                 200 "$(status "$BASE_URL/health")"
check "GET /fixtures"               200 "$(status "$BASE_URL/fixtures")"
check "GET /fixtures?status=live"   200 "$(status "$BASE_URL/fixtures?status=live")"
check "GET /standings"              200 "$(status "$BASE_URL/standings")"
check "GET /standings?group=A"      200 "$(status "$BASE_URL/standings?group=A")"
check "GET /scorers"                200 "$(status "$BASE_URL/scorers?sort=goals&limit=50")"

# A real fixture id from the list endpoint
FIXTURE_ID=$(curl -s "$BASE_URL/fixtures" | python -c "import sys,json;d=json.load(sys.stdin);print(d['fixtures'][0]['id'] if d['fixtures'] else '')" 2>/dev/null)
if [ -n "$FIXTURE_ID" ]; then
  check "GET /fixtures/{id}"        200 "$(status "$BASE_URL/fixtures/$FIXTURE_ID")"
  TEAM_ID=$(curl -s "$BASE_URL/fixtures/$FIXTURE_ID" | python -c "import sys,json;print(json.load(sys.stdin)['fixture']['home_team']['id'])" 2>/dev/null)
  check "GET /teams/{id}"           200 "$(status "$BASE_URL/teams/$TEAM_ID")"
else
  echo "FAIL  no fixtures returned — is the DB seeded?"
  FAIL=$((FAIL + 1))
fi

check "GET /fixtures/999999 (404)"  404 "$(status "$BASE_URL/fixtures/999999")"
check "POST /query (501 stub)"      501 "$(status -X POST -H 'Content-Type: application/json' -d '{"question":"top scorer?"}' "$BASE_URL/query")"
check "POST /ingest no secret 401"  401 "$(status -X POST "$BASE_URL/ingest")"

echo
echo "smoke test: $PASS passed, $FAIL failed"
[ "$FAIL" -eq 0 ]
