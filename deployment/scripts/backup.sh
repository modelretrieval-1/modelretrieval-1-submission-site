#!/usr/bin/env bash
set -euo pipefail

APP_ROOT="${APP_ROOT:-/opt/modelretrieval}"
ENVIRONMENT="${ENVIRONMENT:-production}"
ENV_DIR="${ENV_DIR:-${APP_ROOT}/${ENVIRONMENT}}"
BACKUP_ROOT="${BACKUP_ROOT:-${APP_ROOT}/backups}"
DATABASE_PATH="${DATABASE_PATH:-${ENV_DIR}/data/app.sqlite3}"
STORAGE_ROOT="${STORAGE_ROOT:-${ENV_DIR}/data/storage}"
ENV_FILE="${ENV_FILE:-${ENV_DIR}/.env}"
TIMESTAMP="${TIMESTAMP:-$(date -u +%Y%m%d-%H%M%S)}"
BACKUP_DIR="${BACKUP_DIR:-${BACKUP_ROOT}/${ENVIRONMENT}-${TIMESTAMP}}"

require_command() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Required command not found: $1" >&2
    exit 1
  fi
}

require_path() {
  if [ ! -e "$1" ]; then
    echo "Required path not found: $1" >&2
    exit 1
  fi
}

require_command sqlite3
require_command tar
require_path "$DATABASE_PATH"
require_path "$STORAGE_ROOT"

umask 077
mkdir -p "$BACKUP_DIR"

sqlite3 "$DATABASE_PATH" ".backup '${BACKUP_DIR}/app.sqlite3'"
tar -C "$(dirname "$STORAGE_ROOT")" -czf "${BACKUP_DIR}/storage.tar.gz" "$(basename "$STORAGE_ROOT")"

if [ -f "$ENV_FILE" ]; then
  cp "$ENV_FILE" "${BACKUP_DIR}/env.snapshot"
fi

cat >"${BACKUP_DIR}/manifest.txt" <<EOF
environment=${ENVIRONMENT}
created_at_utc=${TIMESTAMP}
database_path=${DATABASE_PATH}
storage_root=${STORAGE_ROOT}
env_file=${ENV_FILE}
backup_dir=${BACKUP_DIR}
sqlite_backup=app.sqlite3
storage_archive=storage.tar.gz
env_snapshot=$(if [ -f "${BACKUP_DIR}/env.snapshot" ]; then echo "env.snapshot"; else echo ""; fi)
EOF

echo "Backup created: ${BACKUP_DIR}"
