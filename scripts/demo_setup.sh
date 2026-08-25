#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
WEB_APP_DIR="$PROJECT_ROOT/web_app"
ENV_FILE="$WEB_APP_DIR/.env"
ENV_EXAMPLE_FILE="$WEB_APP_DIR/.env.example"
VENV_DIR="$WEB_APP_DIR/.venv"
REQUIREMENTS_FILE="$WEB_APP_DIR/requirements.txt"
DB_SETUP_SCRIPT="$WEB_APP_DIR/database/setup_db.sh"
PROJECT_DATA_FILE="$WEB_APP_DIR/database/solar_panel.sql"

echo "=== Assembly Cobot demo setup ==="

for required_file in \
    "$ENV_EXAMPLE_FILE" \
    "$REQUIREMENTS_FILE" \
    "$DB_SETUP_SCRIPT" \
    "$PROJECT_DATA_FILE"
do
    if [[ ! -f "$required_file" ]]; then
        echo "Error: required file not found: $required_file" >&2
        exit 1
    fi
done

if ! command -v python3 >/dev/null 2>&1; then
    echo "Error: python3 is required." >&2
    exit 1
fi

if [[ ! -f "$ENV_FILE" ]]; then
    cp "$ENV_EXAMPLE_FILE" "$ENV_FILE"
    echo "Created $ENV_FILE"
    echo "Review DB_PASSWORD before running this script again."
    exit 0
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

if [[ ! -x "$VENV_DIR/bin/python" ]]; then
    echo "Creating Python virtual environment..."

    if ! python3 -m venv "$VENV_DIR"; then
        echo "Error: could not create virtual environment." >&2
        echo "Install python3-venv or python3-full and retry." >&2
        exit 1
    fi
fi

echo "Installing Python dependencies..."
"$VENV_DIR/bin/python" -m pip install --upgrade pip
"$VENV_DIR/bin/python" -m pip install -r "$REQUIREMENTS_FILE"

chmod +x "$DB_SETUP_SCRIPT"

echo "Creating local PostgreSQL schema..."
"$DB_SETUP_SCRIPT"

export PGPASSWORD="$DB_PASSWORD"

REFERENCE_ROW_COUNT="$({
    psql \
        -h "$DB_HOST" \
        -p "$DB_PORT" \
        -U "$DB_USER" \
        -d "$DB_NAME" \
        -tAc \
        "SELECT
            (SELECT COUNT(*) FROM installation)
          + (SELECT COUNT(*) FROM operation)
          + (SELECT COUNT(*) FROM robot)
          + (SELECT COUNT(*) FROM sensor);"
} | tr -d '[:space:]')"

if [[ "$REFERENCE_ROW_COUNT" == "0" ]]; then
    echo "Applying solar_panel.sql..."

    psql \
        -h "$DB_HOST" \
        -p "$DB_PORT" \
        -U "$DB_USER" \
        -d "$DB_NAME" \
        -v ON_ERROR_STOP=1 \
        -f "$PROJECT_DATA_FILE"
else
    echo "Reference data already exists; solar_panel.sql was not applied."
    echo "Existing reference row count: $REFERENCE_ROW_COUNT"
fi

unset PGPASSWORD

echo "Checking Backend import..."
(
    cd "$WEB_APP_DIR"
    "$VENV_DIR/bin/python" -c "from app import create_app; create_app()"
)

echo "=== Demo setup complete ==="
echo "Start the web app with: ./scripts/demo_start_web.sh"
