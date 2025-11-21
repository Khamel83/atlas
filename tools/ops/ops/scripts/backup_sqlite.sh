#!/usr/bin/env bash
set -euo pipefail

DB="${OOS_DB:-/opt/oos/data/oos.db}"
OUT_DIR="${OOS_BACKUP_DIR:-/opt/oos/backups}"
RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-7}"

# Create backup directory
mkdir -p "$OUT_DIR"

# Generate backup filename with timestamp
STAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$OUT_DIR/oos_${STAMP}.db"

if [[ ! -f "$DB" ]]; then
    echo "ERROR: Database not found: $DB"
    exit 1
fi

echo "Creating backup: $BACKUP_FILE"

# Create backup using SQLite's backup command
if ! sqlite3 "$DB" ".backup '$BACKUP_FILE'"; then
    echo "ERROR: Backup failed"
    exit 1
fi

# Verify backup integrity
if ! sqlite3 "$BACKUP_FILE" "PRAGMA integrity_check;" | grep -q "ok"; then
    echo "ERROR: Backup integrity check failed"
    rm -f "$BACKUP_FILE"
    exit 1
fi

# Log backup creation
backup_size=$(stat -c%s "$BACKUP_FILE" 2>/dev/null || echo "unknown")
sqlite3 "$DB" "INSERT INTO events_log (event_id, event_type, actor, resource_type, resource_id, details) VALUES ('backup-$(date +%s)', 'backup_created', '$(whoami)', 'database', 'oos.db', json_object('backup_file', '$BACKUP_FILE', 'size_bytes', $backup_size));" || echo "WARN: Could not log backup event"

# Cleanup old backups (keep last N days)
echo "Cleaning up backups older than $RETENTION_DAYS days..."
find "$OUT_DIR" -name "oos_*.db" -type f -mtime +$RETENTION_DAYS -delete 2>/dev/null || true

# Show backup summary
backup_count=$(find "$OUT_DIR" -name "oos_*.db" -type f | wc -l)
total_size=$(du -sh "$OUT_DIR" 2>/dev/null | cut -f1 || echo "unknown")

echo "✅ Backup completed successfully"
echo "   File: $BACKUP_FILE"
echo "   Size: $(du -h "$BACKUP_FILE" 2>/dev/null | cut -f1 || echo "unknown")"
echo "   Total backups: $backup_count"
echo "   Total backup size: $total_size"