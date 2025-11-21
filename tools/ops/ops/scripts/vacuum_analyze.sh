#!/usr/bin/env bash
set -euo pipefail

DB="${OOS_DB:-/opt/oos/data/oos.db}"

if [[ ! -f "$DB" ]]; then
    echo "ERROR: Database not found: $DB"
    exit 1
fi

echo "Starting weekly database maintenance..."

# Log maintenance start
sqlite3 "$DB" "INSERT INTO events_log (event_id, event_type, actor, resource_type, resource_id, details) VALUES ('maint-$(date +%s)', 'maintenance_started', 'system', 'database', 'oos.db', json_object('timestamp', datetime('now'), 'operation', 'vacuum_analyze'));" || echo "WARN: Could not log maintenance start"

# Get database size before
size_before=$(stat -c%s "$DB" 2>/dev/null || echo "0")
echo "Database size before: $(du -h "$DB" 2>/dev/null | cut -f1 || echo "unknown")"

echo "Running VACUUM..."
if ! sqlite3 "$DB" "VACUUM;"; then
    echo "ERROR: VACUUM failed"
    exit 1
fi

echo "Running ANALYZE..."
if ! sqlite3 "$DB" "ANALYZE;"; then
    echo "ERROR: ANALYZE failed"
    exit 1
fi

# Get database size after
size_after=$(stat -c%s "$DB" 2>/dev/null || echo "0")
size_saved=$((size_before - size_after))

echo "Database size after: $(du -h "$DB" 2>/dev/null | cut -f1 || echo "unknown")"
if [[ $size_saved -gt 0 ]]; then
    echo "Space reclaimed: $(( size_saved / 1024 )) KB"
else
    echo "No space reclaimed"
fi

# Update statistics
total_items=$(sqlite3 "$DB" "SELECT COUNT(*) FROM items;" 2>/dev/null || echo "0")
total_runs=$(sqlite3 "$DB" "SELECT COUNT(*) FROM runs;" 2>/dev/null || echo "0")
total_errors=$(sqlite3 "$DB" "SELECT COUNT(*) FROM errors WHERE resolved = 0;" 2>/dev/null || echo "0")

echo "Database statistics:"
echo "  Total items: $total_items"
echo "  Total runs: $total_runs"
echo "  Unresolved errors: $total_errors"

# Log maintenance completion
sqlite3 "$DB" "INSERT INTO events_log (event_id, event_type, actor, resource_type, resource_id, details) VALUES ('maint-$(date +%s)', 'maintenance_completed', 'system', 'database', 'oos.db', json_object('timestamp', datetime('now'), 'operation', 'vacuum_analyze', 'size_before', $size_before, 'size_after', $size_after, 'space_saved', $size_saved, 'total_items', $total_items, 'total_runs', $total_runs, 'unresolved_errors', $total_errors));" || echo "WARN: Could not log maintenance completion"

echo "✅ Weekly database maintenance completed"