#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${1:-${BASE_URL:-}}"

if [ -z "$BASE_URL" ]; then
  echo "Usage: $0 https://example.com" >&2
  echo "Or set BASE_URL=https://example.com" >&2
  exit 2
fi

BASE_URL="${BASE_URL%/}"
ATTEMPTS="${ATTEMPTS:-60}"
SLEEP_SECONDS="${SLEEP_SECONDS:-2}"

check_url() {
  path="$1"
  url="${BASE_URL}${path}"
  echo "Checking ${url}"

  for attempt in $(seq 1 "$ATTEMPTS"); do
    if curl -fsS "$url" >/dev/null; then
      return 0
    fi
    if [ "$attempt" -eq "$ATTEMPTS" ]; then
      echo "Smoke check failed after ${ATTEMPTS} attempts: ${url}" >&2
      return 1
    fi
    sleep "$SLEEP_SECONDS"
  done
}

check_url /health
check_url /login

echo "Smoke check passed: ${BASE_URL}"
