#!/usr/bin/env bash
set -euo pipefail

DB="${OOS_DB:-/opt/oos/data/oos.db}"

echo "[writeback-from-sheets] Starting writeback process..."

# Check prerequisites
if [[ ! -f "$DB" ]]; then
    echo "ERROR: Database not found: $DB"
    exit 1
fi

if [[ -z "${GOOGLE_SERVICE_ACCOUNT_JSON:-}" || -z "${GOOGLE_SPREADSHEET_ID:-}" ]]; then
    echo "WARN: Google Sheets not configured, skipping writeback"
    exit 0
fi

# Log writeback start
sqlite3 "$DB" "INSERT INTO events_log (event_id, event_type, actor, resource_type, resource_id, details) VALUES ('writeback-$(date +%s)', 'writeback_started', 'system', 'sheets', '$GOOGLE_SPREADSHEET_ID', json_object('timestamp', datetime('now')));" || echo "WARN: Could not log writeback start"

echo "[stub] Apply whitelisted fields from Sheets to DB."
echo "Implement Python sync and call it here, e.g.:"
echo "python -m ops.sync.writeback --db \"$DB\" --sheet \"$GOOGLE_SPREADSHEET_ID\" --fields approved,notes"

# TODO: Implement actual Google Sheets writeback
# For now, create a stub that shows what would be processed

echo "Would process the following writeback operations:"

echo ""
echo "=== Whitelisted Fields for Writeback ==="
echo "- approvals.approved (BOOLEAN)"
echo "- approvals.notes (TEXT)"
echo "- errors.resolution (TEXT) - when marked as resolved"

echo ""
echo "=== Current Pending Approvals ==="
pending_count=$(sqlite3 "$DB" "SELECT COUNT(*) FROM approvals WHERE status = 'pending';")
echo "Pending approvals that could be updated: $pending_count"

if [[ $pending_count -gt 0 ]]; then
    echo ""
    echo "Sample pending approvals:"
    sqlite3 "$DB" -header -column "SELECT approval_id, item_type, action, requested_at FROM approvals WHERE status = 'pending' ORDER BY requested_at DESC LIMIT 5;"
fi

echo ""
echo "=== Unresolved Errors ==="
error_count=$(sqlite3 "$DB" "SELECT COUNT(*) FROM errors WHERE resolved = 0;")
echo "Unresolved errors that could be updated: $error_count"

# Simulate some approvals being processed (in real implementation, this would come from Sheets)
echo ""
echo "=== Simulated Writeback Actions ==="
echo "Would check Google Sheets for:"
echo "- New approvals (approved=true/false)"
echo "- Updated notes on existing items"
echo "- Error resolutions"

# Log writeback completion
sqlite3 "$DB" "INSERT INTO events_log (event_id, event_type, actor, resource_type, resource_id, details) VALUES ('writeback-$(date +%s)', 'writeback_completed', 'system', 'sheets', '$GOOGLE_SPREADSHEET_ID', json_object('timestamp', datetime('now'), 'status', 'stub_completed', 'pending_approvals', $pending_count, 'unresolved_errors', $error_count));" || echo "WARN: Could not log writeback completion"

echo "[writeback-from-sheets] Writeback process completed (stub mode)"