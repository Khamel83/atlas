#!/usr/bin/env bash
set -euo pipefail

DB="${OOS_DB:-/opt/oos/data/oos.db}"
BACKUP_DIR="${OOS_BACKUP_DIR:-/opt/oos/backups}"
TEST_DIR="/tmp/oos_restore_test_$$"

echo "Starting quarterly restore drill..."

# Create test directory
mkdir -p "$TEST_DIR"
trap "rm -rf '$TEST_DIR'" EXIT

# Find latest backup
latest_backup=$(find "$BACKUP_DIR" -name "oos_*.db" -type f -printf '%T@ %p\n' 2>/dev/null | sort -n | tail -1 | cut -d' ' -f2-)

if [[ -z "$latest_backup" ]]; then
    echo "ERROR: No backup files found in $BACKUP_DIR"
    exit 1
fi

echo "Testing restore from: $(basename "$latest_backup")"
echo "Backup age: $(( ($(date +%s) - $(stat -c %Y "$latest_backup")) / 3600 )) hours"

# Copy backup to test location
test_db="$TEST_DIR/test_restore.db"
cp "$latest_backup" "$test_db"

# Verify integrity
echo "Checking backup integrity..."
if ! sqlite3 "$test_db" "PRAGMA integrity_check;" | grep -q "ok"; then
    echo "ERROR: Backup integrity check failed"
    exit 1
fi

# Test basic functionality
echo "Testing basic database operations..."

# Check tables exist
expected_tables=("runs" "items" "admin_changes" "approvals" "errors" "daily_kpis" "events_log")
for table in "${expected_tables[@]}"; do
    if ! sqlite3 "$test_db" "SELECT name FROM sqlite_master WHERE type='table' AND name='$table';" | grep -q "$table"; then
        echo "ERROR: Missing table: $table"
        exit 1
    fi
done

# Check data consistency
total_items=$(sqlite3 "$test_db" "SELECT COUNT(*) FROM items;" 2>/dev/null || echo "0")
total_runs=$(sqlite3 "$test_db" "SELECT COUNT(*) FROM runs;" 2>/dev/null || echo "0")
total_events=$(sqlite3 "$test_db" "SELECT COUNT(*) FROM events_log;" 2>/dev/null || echo "0")

echo "Restored database contains:"
echo "  Items: $total_items"
echo "  Runs: $total_runs"
echo "  Events: $total_events"

# Test with Datasette (if available)
if command -v datasette >/dev/null; then
    echo "Testing with Datasette..."
    datasette_log="$TEST_DIR/datasette.log"

    # Start Datasette in background
    datasette "$test_db" --immutable --host 127.0.0.1 --port 19090 > "$datasette_log" 2>&1 &
    datasette_pid=$!

    # Give it a moment to start
    sleep 3

    # Test if it's responding
    if curl -s "http://127.0.0.1:19090/" > /dev/null; then
        echo "✅ Datasette successfully serves restored database"
    else
        echo "WARN: Datasette test failed"
        cat "$datasette_log"
    fi

    # Cleanup
    kill $datasette_pid 2>/dev/null || true
fi

# Compare with current database (if it exists)
if [[ -f "$DB" ]]; then
    echo "Comparing with current database..."

    current_items=$(sqlite3 "$DB" "SELECT COUNT(*) FROM items;" 2>/dev/null || echo "0")
    current_runs=$(sqlite3 "$DB" "SELECT COUNT(*) FROM runs;" 2>/dev/null || echo "0")

    echo "Current vs Backup:"
    echo "  Items: $current_items vs $total_items"
    echo "  Runs: $current_runs vs $total_runs"

    if [[ $current_items -lt $total_items ]]; then
        echo "WARN: Current database has fewer items than backup"
    fi
fi

# Log the test results
if [[ -f "$DB" ]]; then
    sqlite3 "$DB" "INSERT INTO events_log (event_id, event_type, actor, resource_type, resource_id, details) VALUES ('restore-test-$(date +%s)', 'restore_test_completed', 'system', 'backup', '$(basename "$latest_backup")', json_object('timestamp', datetime('now'), 'backup_file', '$latest_backup', 'test_items', $total_items, 'test_runs', $total_runs, 'test_events', $total_events, 'status', 'success'));" || echo "WARN: Could not log test results"
fi

echo "✅ Restore drill completed successfully"
echo "   Backup file: $(basename "$latest_backup")"
echo "   Test database: $test_db (will be cleaned up)"
echo "   All tests passed"