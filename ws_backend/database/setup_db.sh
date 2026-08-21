#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="$SCRIPT_DIR/.env"
SCHEMA_FILE="$SCRIPT_DIR/schema.sql"
GRANT_FILE="$SCRIPT_DIR/grant.sql"

echo "=== PostgreSQL setup start ==="

# 1. 환경변수 파일 확인

if [ ! -f "$ENV_FILE" ]; then
    echo "Error: .env file not found."
    echo "Create .env from .env.example first."
    exit 1
fi

source "$ENV_FILE"

# 필수 환경변수 확인
: "${DB_HOST:?DB_HOST is required}"
: "${DB_PORT:?DB_PORT is required}"
: "${DB_NAME:?DB_NAME is required}"
: "${DB_USER:?DB_USER is required}"
: "${DB_PASSWORD:?DB_PASSWORD is required}"

# 2. PostgreSQL 설치 확인


if ! command -v psql &> /dev/null; then
    echo "PostgreSQL is not installed."
    echo "Installing PostgreSQL..."

    sudo apt update
    sudo apt install -y postgresql postgresql-contrib
else
    echo "PostgreSQL already installed."
fi

# 3. PostgreSQL 서비스 시작

echo "Starting PostgreSQL service..."

sudo systemctl enable postgresql
sudo systemctl start postgresql

# 4. DB 사용자 생성

echo "Checking database user: $DB_USER"

ROLE_EXISTS=$(sudo -u postgres psql -tAc \
    "SELECT 1 FROM pg_catalog.pg_roles WHERE rolname='$DB_USER'")

if [ "$ROLE_EXISTS" != "1" ]; then
    echo "Creating database user: $DB_USER"

    sudo -u postgres psql -c \
        "CREATE ROLE \"$DB_USER\" LOGIN PASSWORD '$DB_PASSWORD';"
else
    echo "Database user already exists."
fi

# 5. Database 생성

echo "Checking database: $DB_NAME"

DB_EXISTS=$(sudo -u postgres psql -tAc \
    "SELECT 1 FROM pg_database WHERE datname='$DB_NAME'")

if [ "$DB_EXISTS" != "1" ]; then
    echo "Creating database: $DB_NAME"

    sudo -u postgres createdb \
        -O "$DB_USER" \
        "$DB_NAME"
else
    echo "Database already exists."
fi

# 6. schema.sql 확인

if [ ! -f "$SCHEMA_FILE" ]; then
    echo "Error: schema.sql not found."
    exit 1
fi

# 7. Schema 적용

echo "Applying schema.sql..."

export PGPASSWORD="$DB_PASSWORD"

psql \
    -h "$DB_HOST" \
    -p "$DB_PORT" \
    -U "$DB_USER" \
    -d "$DB_NAME" \
    -v ON_ERROR_STOP=1 \
    -f "$SCHEMA_FILE"

# 8. 권한 부여

if [ -f "$GRANT_FILE" ]; then
    echo "Applying grants..."
    psql \
        -h "$DB_HOST" \
        -p "$DB_PORT" \
        -U "$DB_USER" \
        -d "$DB_NAME" \
        -v ON_ERROR_STOP=1 \
        -v db_name="$DB_NAME" \
        -v app_user="$DB_USER" \
        -f "$SCRIPT_DIR/grants.sql"
fi

unset PGPASSWORD

echo "=== PostgreSQL setup complete ==="