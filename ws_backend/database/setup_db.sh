#!/usr/bin/env bash

set -euo pipefail

# --------------------------------------------------
# Path
# --------------------------------------------------

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

ENV_FILE="$SCRIPT_DIR/.env"
SCHEMA_FILE="$SCRIPT_DIR/schema.sql"
GRANT_FILE="$SCRIPT_DIR/grant.sql"
SEED_FILE="$SCRIPT_DIR/seed.sql"

APPLY_SEED=false


echo "=== PostgreSQL setup start ==="


# --------------------------------------------------
# 1. 실행 옵션 확인
# --------------------------------------------------

if [[ "${1:-}" == "--seed" ]]; then
    APPLY_SEED=true
elif [[ -n "${1:-}" ]]; then
    echo "Error: Unknown option '$1'"
    echo "Usage: $0 [--seed]"
    exit 1
fi


# --------------------------------------------------
# 2. 환경변수 파일 확인
# --------------------------------------------------

if [ ! -f "$ENV_FILE" ]; then
    echo "Error: .env file not found."
    echo "Create .env from .env.example first."
    exit 1
fi

source "$ENV_FILE"


# --------------------------------------------------
# 3. 필수 환경변수 확인
# --------------------------------------------------

: "${DB_HOST:?DB_HOST is required}"
: "${DB_PORT:?DB_PORT is required}"
: "${DB_NAME:?DB_NAME is required}"
: "${DB_USER:?DB_USER is required}"
: "${DB_PASSWORD:?DB_PASSWORD is required}"


# --------------------------------------------------
# 4. PostgreSQL 설치 확인
# --------------------------------------------------

if ! command -v psql &> /dev/null; then

    echo "PostgreSQL is not installed."
    echo "Installing PostgreSQL..."

    sudo apt update
    sudo apt install -y postgresql postgresql-contrib

else

    echo "PostgreSQL already installed."

fi


# --------------------------------------------------
# 5. PostgreSQL 서비스 시작
# --------------------------------------------------

echo "Starting PostgreSQL service..."

sudo systemctl enable postgresql
sudo systemctl start postgresql


# --------------------------------------------------
# 6. DB 사용자 확인 및 생성
# --------------------------------------------------

echo "Checking database user: $DB_USER"

ROLE_EXISTS=$(
    sudo -u postgres psql -tAc \
        "SELECT 1
         FROM pg_catalog.pg_roles
         WHERE rolname='$DB_USER'"
)

if [ "$ROLE_EXISTS" != "1" ]; then

    echo "Creating database user: $DB_USER"

    sudo -u postgres psql -v ON_ERROR_STOP=1 -c \
        "CREATE ROLE \"$DB_USER\"
         LOGIN
         PASSWORD '$DB_PASSWORD';"

else

    echo "Database user already exists: $DB_USER"

fi


# --------------------------------------------------
# 7. Database 확인 및 생성
# --------------------------------------------------

echo "Checking database: $DB_NAME"

DB_EXISTS=$(
    sudo -u postgres psql -tAc \
        "SELECT 1
         FROM pg_database
         WHERE datname='$DB_NAME'"
)

if [ "$DB_EXISTS" != "1" ]; then

    echo "Creating database: $DB_NAME"

    sudo -u postgres createdb \
        -O "$DB_USER" \
        "$DB_NAME"

else

    echo "Database already exists: $DB_NAME"

fi


# --------------------------------------------------
# 8. SQL 파일 확인
# --------------------------------------------------

if [ ! -f "$SCHEMA_FILE" ]; then
    echo "Error: schema.sql not found."
    exit 1
fi

if [ ! -f "$GRANT_FILE" ]; then
    echo "Error: grant.sql not found."
    exit 1
fi

if [ "$APPLY_SEED" = true ] && [ ! -f "$SEED_FILE" ]; then
    echo "Error: seed.sql not found."
    exit 1
fi


# --------------------------------------------------
# 9. PostgreSQL 접속 비밀번호 설정
# --------------------------------------------------

export PGPASSWORD="$DB_PASSWORD"


# --------------------------------------------------
# 10. Schema 적용
# --------------------------------------------------

echo "Applying schema.sql..."

psql \
    -h "$DB_HOST" \
    -p "$DB_PORT" \
    -U "$DB_USER" \
    -d "$DB_NAME" \
    -v ON_ERROR_STOP=1 \
    -f "$SCHEMA_FILE"


# --------------------------------------------------
# 11. 권한 적용
# --------------------------------------------------

echo "Applying grant.sql..."

psql \
    -h "$DB_HOST" \
    -p "$DB_PORT" \
    -U "$DB_USER" \
    -d "$DB_NAME" \
    -v ON_ERROR_STOP=1 \
    -v db_name="$DB_NAME" \
    -v app_user="$DB_USER" \
    -f "$GRANT_FILE"


# --------------------------------------------------
# 12. Seed Data 적용
# --------------------------------------------------

if [ "$APPLY_SEED" = true ]; then

    echo "Applying seed.sql..."

    psql \
        -h "$DB_HOST" \
        -p "$DB_PORT" \
        -U "$DB_USER" \
        -d "$DB_NAME" \
        -v ON_ERROR_STOP=1 \
        -f "$SEED_FILE"

else

    echo "Skipping seed data."

fi


# --------------------------------------------------
# 13. 환경변수 정리
# --------------------------------------------------

unset PGPASSWORD


echo "=== PostgreSQL setup complete ==="