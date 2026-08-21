#!/usr/bin/env sh
set -eu

if [ "$#" -ne 2 ]; then
  echo "Usage: $0 <database-backup.sql.gz> <documents-backup.tar.gz>" >&2
  exit 64
fi

DATABASE_BACKUP=$1
DOCUMENTS_BACKUP=$2
test -f "$DATABASE_BACKUP"
test -f "$DOCUMENTS_BACKUP"

# Prevent new writes while restoring a matching database and file snapshot.
docker compose stop api
gzip -dc "$DATABASE_BACKUP" | docker compose exec -T db psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" "$POSTGRES_DB"
docker compose run --rm --no-deps api sh -c 'rm -rf /app/storage/documents/*'
docker compose run --rm --no-deps -T api tar -xzf - -C /app/storage < "$DOCUMENTS_BACKUP"
docker compose up -d api
