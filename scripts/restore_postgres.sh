#!/usr/bin/env bash
set -euo pipefail
: "${DATABASE_URL:?Set DATABASE_URL}"
: "${1:?Usage: restore_postgres.sh path/to/backup.dump}"
read -r -p 'This replaces database objects in the target database. Type RESTORE to continue: ' CONFIRM
[[ "$CONFIRM" == "RESTORE" ]] || { echo 'Cancelled.'; exit 1; }
pg_restore --clean --if-exists --no-owner --dbname="$DATABASE_URL" "$1"
