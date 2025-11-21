#!/usr/bin/env bash
set -euo pipefail

DB="${OOS_DB:-/opt/oos/data/oos.db}"
HOST="${SQLITE_WEB_HOST:-127.0.0.1}"
PORT="${SQLITE_WEB_PORT:-8080}"

if [[ ! -f "$DB" ]]; then
    echo "Database not found: $DB"
    echo "Run: make -C ops bootstrap && sqlite3 \"$DB\" < ops/schema.sql"
    exit 1
fi

echo "⚠️  WARNING: Starting sqlite-web in EDIT mode"
echo "This allows direct database modifications!"
echo ""
echo "SAFETY CHECKLIST:"
echo "1. ✅ Have you paused all workers?"
echo "2. ✅ Have you created a backup?"
echo "3. ✅ Do you have a valid reason for direct editing?"
echo ""
echo "Access via SSH tunnel: ssh -L $PORT:$HOST:$PORT user@host"
echo "Then browse: http://localhost:$PORT"
echo ""
echo "Press Ctrl+C to cancel, or Enter to continue..."
read -r

# Record admin session start
if command -v sqlite3 >/dev/null; then
    session_id="admin-$(date +%s)-$$"
    sqlite3 "$DB" "INSERT INTO admin_changes (change_id, actor, table_name, record_key, reason, session_id) VALUES ('session-start-$(date +%s)', '$(whoami)', 'admin_session', '$session_id', 'Direct database edit session started', '$session_id');" || true
    echo "Session ID: $session_id"
fi

exec sqlite_web "$DB" \
    -H "$HOST" \
    -p "$PORT" \
    --read-only false