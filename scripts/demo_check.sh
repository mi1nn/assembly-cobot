#!/usr/bin/env bash

set -u

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
WEB_APP_DIR="$PROJECT_ROOT/web_app"
ENV_FILE="$WEB_APP_DIR/.env"
BACKEND_URL="http://127.0.0.1:5000"
BRIDGE_URL="http://127.0.0.1:8001"
FAILED=0

print_ok() {
    printf '[OK] %s\n' "$1"
}

print_fail() {
    printf '[FAIL] %s\n' "$1" >&2
    FAILED=1
}

if [[ ! -f "$ENV_FILE" ]]; then
    print_fail "$ENV_FILE does not exist"
    exit 1
fi

set -a
# shellcheck disable=SC1090
source "$ENV_FILE"
set +a

: "${DB_HOST:?DB_HOST is required in web_app/.env}"
: "${DB_PORT:?DB_PORT is required in web_app/.env}"
: "${DB_NAME:?DB_NAME is required in web_app/.env}"
: "${DB_USER:?DB_USER is required in web_app/.env}"
: "${DB_PASSWORD:?DB_PASSWORD is required in web_app/.env}"

if command -v pg_isready >/dev/null 2>&1 \
    && pg_isready -h "$DB_HOST" -p "$DB_PORT" >/dev/null 2>&1
then
    print_ok "PostgreSQL is accepting connections"
else
    print_fail "PostgreSQL is not ready at $DB_HOST:$DB_PORT"
fi

if command -v psql >/dev/null 2>&1; then
    if PGPASSWORD="$DB_PASSWORD" psql \
        -h "$DB_HOST" \
        -p "$DB_PORT" \
        -U "$DB_USER" \
        -d "$DB_NAME" \
        -tAc "SELECT 1" >/dev/null 2>&1
    then
        print_ok "Application DB login succeeded"
    else
        print_fail "Application DB login failed"
    fi
else
    print_fail "psql is not installed"
fi

if curl --fail --silent --show-error --max-time 3 \
    "$BACKEND_URL/api/v1/health" >/dev/null
then
    print_ok "Backend health check succeeded"
else
    print_fail "Backend is unavailable at $BACKEND_URL"
fi

if curl --fail --silent --show-error --max-time 3 \
    "$BRIDGE_URL/health" >/dev/null
then
    print_ok "Bridge health check succeeded"
else
    print_fail "Bridge is unavailable at $BRIDGE_URL"
fi

if curl --fail --silent --show-error --max-time 3 \
    "$BRIDGE_URL/status" >/dev/null
then
    print_ok "Bridge status endpoint succeeded"
else
    print_fail "Bridge status endpoint failed"
fi

if [[ "$FAILED" -ne 0 ]]; then
    echo "=== Demo check failed ===" >&2
    exit 1
fi

echo "=== All demo checks passed ==="
