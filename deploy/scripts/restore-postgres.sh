#!/usr/bin/env sh
set -eu

compose() {
  if docker compose version >/dev/null 2>&1; then
    docker compose "$@"
  else
    docker-compose "$@"
  fi
}

if [ "$#" -ne 3 ]; then
  echo "Usage: $0 <database-backup.sql.gz> <documents-backup.tar.gz> <trainings-backup.tar.gz>" >&2
  exit 64
fi

DATABASE_BACKUP=$1
DOCUMENTS_BACKUP=$2
TRAININGS_BACKUP=$3
test -f "$DATABASE_BACKUP"
test -f "$DOCUMENTS_BACKUP"
test -f "$TRAININGS_BACKUP"

# Prevent new writes while restoring a matching database and file snapshot.
compose stop api
gzip -dc "$DATABASE_BACKUP" | compose exec -T db sh -c 'psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" "$POSTGRES_DB"'
compose run --rm --no-deps api sh -c 'rm -rf /app/storage/documents/* /app/storage/trainings/*'
compose run --rm --no-deps -T api tar -xzf - -C /app/storage < "$DOCUMENTS_BACKUP"
compose run --rm --no-deps -T api tar -xzf - -C /app/storage < "$TRAININGS_BACKUP"
compose up -d api
