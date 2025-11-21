#!/usr/bin/env bash
set -euo pipefail

# Handle both absolute and relative paths, context-aware resolution
if [[ -n "${OOS_DB:-}" ]] && [[ "$OOS_DB" == /* ]]; then
    # Absolute path provided
    DB="$OOS_DB"
elif [[ -n "${OOS_DB:-}" ]]; then
    # Relative path provided - check if it exists as-is
    if [[ -f "$OOS_DB" ]]; then
        DB="$OOS_DB"
    elif [[ -f "../$OOS_DB" ]]; then
        # We're in ops/ directory, database is relative to project root
        DB="../$OOS_DB"
    else
        # Use as provided, will error if not found
        DB="$OOS_DB"
    fi
elif [[ -f "../data/oos.db" ]]; then
    # Default: ops/ directory context
    DB="../data/oos.db"
elif [[ -f "data/oos.db" ]]; then
    # Default: project root context
    DB="data/oos.db"
elif [[ -f "/opt/oos/data/oos.db" ]]; then
    # Default: production context
    DB="/opt/oos/data/oos.db"
else
    # Final fallback
    DB="${OOS_DB:-data/oos.db}"
fi
REQUIRED_TABLES=("runs" "items" "admin_changes" "approvals" "errors" "daily_kpis" "events_log")

echo "== Preflight =="

# Check database exists
if [[ ! -f "$DB" ]]; then
  echo "ERR: missing DB at $DB"
  echo "FIX: mkdir -p $(dirname "$DB") && sqlite3 \"$DB\" < ops/schema.sql"
  exit 1
fi

# Check and set WAL mode
WAL=$(sqlite3 "$DB" "PRAGMA journal_mode;")
if [[ "$WAL" != "wal" ]]; then
  echo "Setting WAL mode..."
  sqlite3 "$DB" "PRAGMA journal_mode=WAL;"
fi

# Set busy timeout
sqlite3 "$DB" "PRAGMA busy_timeout=5000;"

# Check required tables exist
missing_tables=()
for table in "${REQUIRED_TABLES[@]}"; do
  if ! sqlite3 "$DB" "SELECT name FROM sqlite_master WHERE type='table' AND name='$table';" | grep -q "$table"; then
    missing_tables+=("$table")
  fi
done

if [[ ${#missing_tables[@]} -gt 0 ]]; then
  echo "ERR: missing tables: ${missing_tables[*]}"
  echo "FIX: sqlite3 \"$DB\" < ops/schema.sql"
  exit 1
fi

# Check database integrity
if ! sqlite3 "$DB" "PRAGMA integrity_check;" | grep -q "ok"; then
  echo "ERR: database integrity check failed"
  echo "FIX: restore from backup or reinitialize"
  exit 1
fi

# Check essential tools
missing_tools=()
command -v datasette >/dev/null || missing_tools+=("datasette")
command -v sqlite_web >/dev/null || missing_tools+=("sqlite_web")
command -v sops >/dev/null || missing_tools+=("sops")
command -v age >/dev/null || missing_tools+=("age")

if [[ ${#missing_tools[@]} -gt 0 ]]; then
  echo "WARN: missing tools: ${missing_tools[*]}"
  echo "FIX: pip install datasette sqlite-web && make -C ops install-sops"
fi

# Check systemd timers
inactive_timers=()
for timer in export-to-sheets writeback-from-sheets backup-sqlite; do
  if ! systemctl is-active --quiet "${timer}.timer" 2>/dev/null; then
    inactive_timers+=("${timer}.timer")
  fi
done

if [[ ${#inactive_timers[@]} -gt 0 ]]; then
  echo "WARN: inactive timers: ${inactive_timers[*]}"
  echo "FIX: make -C ops enable-timers"
fi

# Check Google Sheets configuration
if [[ -z "${GOOGLE_SERVICE_ACCOUNT_JSON:-}" || -z "${GOOGLE_SPREADSHEET_ID:-}" ]]; then
  echo "WARN: Sheets not fully configured; mirrors will be skipped."
  echo "FIX: configure GOOGLE_SERVICE_ACCOUNT_JSON and GOOGLE_SPREADSHEET_ID in ops/.env"
fi

# Check disk space
data_dir=$(dirname "$DB")
if command -v df >/dev/null; then
  usage=$(df "$data_dir" | awk 'NR==2 {print $5}' | sed 's/%//')
  if [[ $usage -gt 80 ]]; then
    echo "WARN: disk usage high: ${usage}%"
    echo "FIX: clean old backups or extend storage"
  fi
fi

# Check recent backup
backup_dir="${OOS_BACKUP_DIR:-/opt/oos/backups}"
if [[ -d "$backup_dir" ]]; then
  latest_backup=$(find "$backup_dir" -name "oos_*.db" -type f -printf '%T@ %p\n' 2>/dev/null | sort -n | tail -1 | cut -d' ' -f2-)
  if [[ -n "$latest_backup" ]]; then
    backup_age=$(( $(date +%s) - $(stat -c %Y "$latest_backup") ))
    if [[ $backup_age -gt 86400 ]]; then # 24 hours
      echo "WARN: latest backup is $(( backup_age / 3600 )) hours old"
      echo "FIX: make -C ops backup"
    fi
  else
    echo "WARN: no backups found"
    echo "FIX: make -C ops backup"
  fi
fi

echo "Preflight OK."