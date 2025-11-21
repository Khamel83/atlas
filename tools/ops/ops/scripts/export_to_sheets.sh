#!/usr/bin/env bash
set -euo pipefail

DB="${OOS_DB:-/opt/oos/data/oos.db}"

echo "[export-to-sheets] Starting export process..."

# Check prerequisites
if [[ ! -f "$DB" ]]; then
    echo "ERROR: Database not found: $DB"
    exit 1
fi

if [[ -z "${GOOGLE_SERVICE_ACCOUNT_JSON:-}" || -z "${GOOGLE_SPREADSHEET_ID:-}" ]]; then
    echo "WARN: Google Sheets not configured, skipping export"
    exit 0
fi

# Log export start
sqlite3 "$DB" "INSERT INTO events_log (event_id, event_type, actor, resource_type, resource_id, details) VALUES ('export-$(date +%s)', 'export_started', 'system', 'sheets', '$GOOGLE_SPREADSHEET_ID', json_object('timestamp', datetime('now')));" || echo "WARN: Could not log export start"

echo "[stub] Export curated views to Google Sheets."
echo "Implement Python sync and call it here, e.g.:"
echo "python -m ops.sync.export_to_sheets --db \"$DB\" --sheet \"$GOOGLE_SPREADSHEET_ID\""

# TODO: Implement actual Google Sheets export
# For now, create a stub that shows what would be exported

echo "Would export the following data to Google Sheets:"

echo ""
echo "=== Pending Approvals ==="
sqlite3 "$DB" -header -column "SELECT approval_id, item_type, action, status, requested_at FROM approvals WHERE status = 'pending' ORDER BY requested_at DESC LIMIT 10;"

echo ""
echo "=== Recent Runs ==="
sqlite3 "$DB" -header -column "SELECT run_id, status, started_at, finished_at, items_processed, errors FROM runs ORDER BY started_at DESC LIMIT 10;"

echo ""
echo "=== Error Hotlist ==="
sqlite3 "$DB" -header -column "SELECT error_id, stage, message, severity, created_at FROM errors WHERE resolved = 0 ORDER BY created_at DESC LIMIT 10;"

echo ""
echo "=== Daily KPIs ==="
sqlite3 "$DB" -header -column "SELECT date, items_ingested, items_indexed, errors, success_rate FROM daily_kpis ORDER BY date DESC LIMIT 7;"

# Log export completion
sqlite3 "$DB" "INSERT INTO events_log (event_id, event_type, actor, resource_type, resource_id, details) VALUES ('export-$(date +%s)', 'export_completed', 'system', 'sheets', '$GOOGLE_SPREADSHEET_ID', json_object('timestamp', datetime('now'), 'status', 'stub_completed'));" || echo "WARN: Could not log export completion"

echo "[export-to-sheets] Export process completed (stub mode)"