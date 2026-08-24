#!/usr/bin/env bash

set -euo pipefail

# --------------------------------------------------
# Path
# --------------------------------------------------

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

ENV_FILE="$PROJECT_ROOT/.env"
SETUP_SCRIPT="$SCRIPT_DIR/setup_db.sh"


echo "=== PostgreSQL reset start ==="


# --------------------------------------------------
# 1. 환경변수 파일 확인
# --------------------------------------------------

if [ ! -f "$ENV_FILE" ]; then
    echo "Error: .env file not found."
    echo "Create $PROJECT_ROOT/.env from $PROJECT_ROOT/.env.example first."
    exit 1
fi

source "$ENV_FILE"


# --------------------------------------------------
# 2. 필수 환경변수 확인
# --------------------------------------------------

: "${DB_NAME:?DB_NAME is required}"


# --------------------------------------------------
# 3. setup_db.sh 확인
# --------------------------------------------------

if [ ! -f "$SETUP_SCRIPT" ]; then
    echo "Error: setup_db.sh not found."
    exit 1
fi


# --------------------------------------------------
# 4. 삭제 확인
# --------------------------------------------------

echo
echo "WARNING:"
echo "Database '$DB_NAME' will be completely deleted."
echo "All data in the database will be lost."
echo

read -r -p "Continue? [y/N]: " CONFIRM

if [[ "$CONFIRM" != "y" && "$CONFIRM" != "Y" ]]; then
    echo "Reset cancelled."
    exit 0
fi


# --------------------------------------------------
# 5. 기존 연결 종료
# --------------------------------------------------

echo "Terminating active connections to database: $DB_NAME"

sudo -u postgres psql -v ON_ERROR_STOP=1 -c \
    "SELECT pg_terminate_backend(pid)
     FROM pg_stat_activity
     WHERE datname = '$DB_NAME'
       AND pid <> pg_backend_pid();"


# --------------------------------------------------
# 6. Database 삭제
# --------------------------------------------------

echo "Dropping database: $DB_NAME"

sudo -u postgres dropdb \
    --if-exists \
    "$DB_NAME"


# --------------------------------------------------
# 7. Database 재구축
# --------------------------------------------------

echo "Rebuilding database..."

"$SETUP_SCRIPT"


echo "=== PostgreSQL reset complete ==="