#!/usr/bin/env bash
set -euo pipefail

DB="${OOS_DB:-/opt/oos/data/oos.db}"

# Configuration
TELEGRAM_BOT_TOKEN="${TELEGRAM_BOT_TOKEN:-}"
TELEGRAM_CHAT_ID="${TELEGRAM_CHAT_ID:-}"
UPTIME_KUMA_URL="${UPTIME_KUMA_URL:-}"
UPTIME_KUMA_PUSH_KEY="${UPTIME_KUMA_PUSH_KEY:-}"

# Generate heartbeat data
generate_heartbeat() {
    local status="healthy"
    local details=""

    # Basic health checks
    if [[ ! -f "$DB" ]]; then
        status="unhealthy"
        details="Database file missing"
    elif ! sqlite3 "$DB" "PRAGMA integrity_check;" 2>/dev/null | grep -q "ok"; then
        status="unhealthy"
        details="Database integrity check failed"
    fi

    # Get basic stats
    local total_items=0
    local total_runs=0
    local unresolved_errors=0
    local recent_events=0

    if [[ -f "$DB" ]]; then
        total_items=$(sqlite3 "$DB" "SELECT COUNT(*) FROM items;" 2>/dev/null || echo "0")
        total_runs=$(sqlite3 "$DB" "SELECT COUNT(*) FROM runs;" 2>/dev/null || echo "0")
        unresolved_errors=$(sqlite3 "$DB" "SELECT COUNT(*) FROM errors WHERE resolved = 0;" 2>/dev/null || echo "0")
        recent_events=$(sqlite3 "$DB" "SELECT COUNT(*) FROM events_log WHERE timestamp > datetime('now', '-24 hours');" 2>/dev/null || echo "0")
    fi

    # Check disk usage
    local disk_usage="unknown"
    if command -v df >/dev/null && [[ -f "$DB" ]]; then
        disk_usage=$(df "$(dirname "$DB")" | awk 'NR==2 {print $5}' | sed 's/%//')
        if [[ $disk_usage -gt 85 ]]; then
            status="warning"
            details="High disk usage: ${disk_usage}%"
        fi
    fi

    # Check backup freshness
    local backup_age="unknown"
    if [[ -d "${OOS_BACKUP_DIR:-/opt/oos/backups}" ]]; then
        local latest_backup=$(find "${OOS_BACKUP_DIR:-/opt/oos/backups}" -name "oos_*.db" -type f -printf '%T@ %p\n' 2>/dev/null | sort -n | tail -1 | cut -d' ' -f2-)
        if [[ -n "$latest_backup" ]]; then
            backup_age=$(( $(date +%s) - $(stat -c %Y "$latest_backup") ))
            backup_hours=$((backup_age / 3600))
            if [[ $backup_hours -gt 48 ]]; then
                status="warning"
                details="Old backup: ${backup_hours}h"
            fi
        fi
    fi

    # Create JSON payload
    cat << EOF
{
  "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "status": "$status",
  "details": "$details",
  "metrics": {
    "total_items": $total_items,
    "total_runs": $total_runs,
    "unresolved_errors": $unresolved_errors,
    "recent_events": $recent_events,
    "disk_usage_percent": "$disk_usage",
    "backup_age_hours": "$backup_hours"
  },
  "hostname": "$(hostname)",
  "version": "oos-agent-os-v1"
}
EOF
}

# Send to Telegram
send_telegram() {
    local message="$1"

    if [[ -n "$TELEGRAM_BOT_TOKEN" && -n "$TELEGRAM_CHAT_ID" ]]; then
        curl -s -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
            -d "chat_id=${TELEGRAM_CHAT_ID}" \
            -d "text=${message}" \
            -d "parse_mode=HTML" >/dev/null || echo "WARN: Failed to send Telegram message"
    fi
}

# Send to Uptime Kuma
send_uptime_kuma() {
    local status="$1"
    local message="$2"

    if [[ -n "$UPTIME_KUMA_URL" && -n "$UPTIME_KUMA_PUSH_KEY" ]]; then
        local url="${UPTIME_KUMA_URL}/api/push/${UPTIME_KUMA_PUSH_KEY}"

        case "$status" in
            "healthy")
                curl -s "${url}?status=up&msg=${message}" >/dev/null || echo "WARN: Failed to send Uptime Kuma heartbeat"
                ;;
            "warning")
                curl -s "${url}?status=up&msg=${message}" >/dev/null || echo "WARN: Failed to send Uptime Kuma heartbeat"
                ;;
            "unhealthy")
                curl -s "${url}?status=down&msg=${message}" >/dev/null || echo "WARN: Failed to send Uptime Kuma heartbeat"
                ;;
        esac
    fi
}

# Main execution
main() {
    echo "Sending daily heartbeat..."

    # Generate heartbeat data
    heartbeat_json=$(generate_heartbeat)
    status=$(echo "$heartbeat_json" | jq -r '.status' 2>/dev/null || echo "unknown")
    details=$(echo "$heartbeat_json" | jq -r '.details' 2>/dev/null || echo "")

    # Log heartbeat to database
    if [[ -f "$DB" ]]; then
        sqlite3 "$DB" "INSERT INTO events_log (event_id, event_type, actor, resource_type, resource_id, details) VALUES ('heartbeat-$(date +%s)', 'heartbeat_sent', 'system', 'monitoring', 'daily_status', '$heartbeat_json');" || echo "WARN: Could not log heartbeat to database"
    fi

    # Create human-readable message
    local message="🏥 OOS Daily Health Report\n\n"
    message+="<b>Status:</b> "
    case "$status" in
        "healthy") message+="✅ Healthy" ;;
        "warning") message+="⚠️ Warning" ;;
        "unhealthy") message+="❌ Unhealthy" ;;
        *) message+="❓ Unknown" ;;
    esac

    if [[ -n "$details" ]]; then
        message+="\n<b>Issue:</b> $details"
    fi

    # Extract metrics
    local total_items=$(echo "$heartbeat_json" | jq -r '.metrics.total_items' 2>/dev/null || echo "0")
    local unresolved_errors=$(echo "$heartbeat_json" | jq -r '.metrics.unresolved_errors' 2>/dev/null || echo "0")
    local disk_usage=$(echo "$heartbeat_json" | jq -r '.metrics.disk_usage_percent' 2>/dev/null || echo "unknown")

    message+="\n\n<b>Metrics:</b>"
    message+="\n• Items: $total_items"
    message+="\n• Unresolved Errors: $unresolved_errors"
    message+="\n• Disk Usage: $disk_usage%"
    message+="\n• Hostname: $(hostname)"

    # Send notifications
    send_telegram "$message"
    send_uptime_kuma "$status" "OOS: $status $(if [[ -n "$details" ]]; then echo "- $details"; fi)"

    echo "Heartbeat sent:"
    echo "  Status: $status"
    if [[ -n "$details" ]]; then
        echo "  Details: $details"
    fi
    echo "  Notifications: $(if [[ -n "$TELEGRAM_BOT_TOKEN" ]]; then echo "Telegram "; fi)$(if [[ -n "$UPTIME_KUMA_URL" ]]; then echo "Uptime-Kuma"; fi)"
}

# Check dependencies
if ! command -v jq >/dev/null; then
    echo "WARN: jq not available, using basic parsing"
fi

if ! command -v curl >/dev/null; then
    echo "ERROR: curl required for sending notifications"
    exit 1
fi

main "$@"