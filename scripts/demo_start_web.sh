#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
WEB_APP_DIR="$PROJECT_ROOT/web_app"
ENV_FILE="$WEB_APP_DIR/.env"
PYTHON_BIN="$WEB_APP_DIR/.venv/bin/python"

if [[ ! -f "$ENV_FILE" ]]; then
    echo "Error: $ENV_FILE does not exist." >&2
    echo "Run ./scripts/demo_setup.sh first." >&2
    exit 1
fi

if [[ ! -x "$PYTHON_BIN" ]]; then
    echo "Error: web_app virtual environment does not exist." >&2
    echo "Run ./scripts/demo_setup.sh first." >&2
    exit 1
fi

set -a
# shellcheck disable=SC1090
source "$ENV_FILE"
set +a

: "${DB_HOST:?DB_HOST is required in web_app/.env}"
: "${DB_PORT:?DB_PORT is required in web_app/.env}"

if command -v pg_isready >/dev/null 2>&1; then
    if ! pg_isready -h "$DB_HOST" -p "$DB_PORT" >/dev/null; then
        echo "Error: PostgreSQL is not ready at $DB_HOST:$DB_PORT." >&2
        echo "Start it with: sudo systemctl start postgresql" >&2
        exit 1
    fi
fi

echo "Starting Assembly Cobot web app at http://127.0.0.1:5000"
cd "$WEB_APP_DIR"
exec "$PYTHON_BIN" run.py
