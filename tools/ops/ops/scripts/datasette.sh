#!/usr/bin/env bash
set -euo pipefail

DB="${OOS_DB:-/opt/oos/data/oos.db}"
HOST="${DATASETTE_HOST:-127.0.0.1}"
PORT="${DATASETTE_PORT:-9090}"

if [[ ! -f "$DB" ]]; then
    echo "Database not found: $DB"
    echo "Run: make -C ops bootstrap && sqlite3 \"$DB\" < ops/schema.sql"
    exit 1
fi

echo "Starting Datasette (read-only) on $HOST:$PORT"
echo "Access via SSH tunnel: ssh -L $PORT:$HOST:$PORT user@host"
echo "Then browse: http://localhost:$PORT"

exec datasette "$DB" \
    --immutable \
    --host "$HOST" \
    --port "$PORT" \
    --setting sql_time_limit_ms 10000 \
    --setting max_returned_rows 1000