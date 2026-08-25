#!/usr/bin/env sh
set -eu

compose() {
  if docker compose version >/dev/null 2>&1; then
    docker compose "$@"
  else
    docker-compose "$@"
  fi
}

mkdir -p backups
TIMESTAMP=$(date +%F-%H%M%S)
compose exec -T db sh -c 'pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB"' | gzip > "backups/hrms-${TIMESTAMP}.sql.gz"
if compose exec -T api test -d /app/storage/documents 2>/dev/null; then
  compose exec -T api tar -czf - -C /app/storage documents > "backups/hrms-documents-${TIMESTAMP}.tar.gz"
fi
if compose exec -T api test -d /app/storage/trainings 2>/dev/null; then
  compose exec -T api tar -czf - -C /app/storage trainings > "backups/hrms-trainings-${TIMESTAMP}.tar.gz"
fi
