#!/usr/bin/env bash
set -euo pipefail
: "${DATABASE_URL:?Set DATABASE_URL to a PostgreSQL connection URL}"
OUT_DIR="${BACKUP_DIR:-./backups}"
mkdir -p "$OUT_DIR"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
# Extract host/database/user using pg_dump's connection-string support.
pg_dump "$DATABASE_URL" --format=custom --no-owner --file "$OUT_DIR/waloma-$STAMP.dump"
find "$OUT_DIR" -type f -name 'waloma-*.dump' -mtime +30 -delete
printf 'Backup written: %s\n' "$OUT_DIR/waloma-$STAMP.dump"
