#!/usr/bin/env sh
set -eu
mkdir -p backups
docker compose exec -T db pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB" | gzip > "backups/hrms-$(date +%F-%H%M%S).sql.gz"
