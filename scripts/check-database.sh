#!/bin/sh
set -eu

# Run from the repository root after docker compose up -d --wait database.
docker compose exec -T database sh -ec \
  'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -v ON_ERROR_STOP=1 -Atc "SELECT 1"' \
  | grep -qx '1'
printf '%s\n' 'PostgreSQL query succeeded.'
