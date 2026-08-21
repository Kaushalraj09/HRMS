#!/usr/bin/env sh
set -eu
mkdir -p backups
TIMESTAMP=$(date +%F-%H%M%S)
docker compose exec -T db pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB" | gzip > "backups/hrms-${TIMESTAMP}.sql.gz"
if docker compose exec -T api test -d /app/storage/documents 2>/dev/null; then
  docker compose exec -T api tar -czf - -C /app/storage documents > "backups/hrms-documents-${TIMESTAMP}.tar.gz"
fi
