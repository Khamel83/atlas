#!/usr/bin/env bash
set -euo pipefail

# Bootstrap Script Post-Deployment Monitoring
# Tracks usage patterns, errors, and user satisfaction
# Implements product launch monitoring principles

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Configuration
MONITOR_LOG="$PROJECT_ROOT/.bootstrap_monitor.log"
USAGE_STATS="$PROJECT_ROOT/.bootstrap_usage.json"
ERROR_LOG="$PROJECT_ROOT/.bootstrap_errors.log"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Utilities
log() { echo -e "${BLUE}[MONITOR]${NC} $*"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $*"; }
error() { echo -e "${RED}[ERROR]${NC} $*"; }
success() { echo -e "${GREEN}[SUCCESS]${NC} $*"; }

# Record bootstrap execution
record_execution() {
    local exit_code="$1"
    local flags="$2"
    local timestamp=$(date -Iseconds)
    local duration="${3:-0}"

    # Create monitoring log entry
    cat >> "$MONITOR_LOG" <<EOF
TIMESTAMP: $timestamp
EXIT_CODE: $exit_code
FLAGS: $flags
DURATION: ${duration}s
---
EOF

    # Update usage statistics (JSON format for easy parsing)
    update_usage_stats "$exit_code" "$flags" "$timestamp"

    log "Execution recorded: exit_code=$exit_code, flags='$flags', duration=${duration}s"
}

# Update usage statistics
update_usage_stats() {
    local exit_code="$1"
    local flags="$2"
    local timestamp="$3"

    # Initialize stats file if it doesn't exist
    if [[ ! -f "$USAGE_STATS" ]]; then
        cat > "$USAGE_STATS" <<'EOF'
{
  "total_executions": 0,
  "successful_executions": 0,
  "failed_executions": 0,
  "common_flags": {},
  "error_patterns": {},
  "first_run": "",
  "last_run": "",
  "version": "2.0.0"
}
EOF
    fi

    # Update statistics using python for JSON manipulation
    python3 -c "
import json
import sys
from datetime import datetime

try:
    with open('$USAGE_STATS', 'r') as f:
        stats = json.load(f)

    # Update counters
    stats['total_executions'] += 1
    if $exit_code == 0:
        stats['successful_executions'] += 1
    else:
        stats['failed_executions'] += 1

    # Track common flags
    flags = '$flags'
    if flags not in stats['common_flags']:
        stats['common_flags'][flags] = 0
    stats['common_flags'][flags] += 1

    # Update timestamps
    if not stats['first_run']:
        stats['first_run'] = '$timestamp'
    stats['last_run'] = '$timestamp'

    # Write back
    with open('$USAGE_STATS', 'w') as f:
        json.dump(stats, f, indent=2)

except Exception as e:
    print(f'Error updating stats: {e}', file=sys.stderr)
"
}

# Record error details
record_error() {
    local error_type="$1"
    local error_message="$2"
    local context="$3"
    local timestamp=$(date -Iseconds)

    cat >> "$ERROR_LOG" <<EOF
TIMESTAMP: $timestamp
ERROR_TYPE: $error_type
MESSAGE: $error_message
CONTEXT: $context
---
EOF

    warn "Error recorded: $error_type - $error_message"
}

# Generate usage report
generate_report() {
    local report_type="${1:-summary}"

    echo "📊 Bootstrap Script Usage Report"
    echo "=================================="
    echo

    if [[ ! -f "$USAGE_STATS" ]]; then
        warn "No usage statistics available"
        return 0
    fi

    # Extract key metrics using python
    python3 -c "
import json
from datetime import datetime

try:
    with open('$USAGE_STATS', 'r') as f:
        stats = json.load(f)

    total = stats.get('total_executions', 0)
    successful = stats.get('successful_executions', 0)
    failed = stats.get('failed_executions', 0)

    print(f'Total Executions: {total}')
    print(f'Successful: {successful} ({100*successful/total:.1f}% if total > 0 else 0.0}%)')
    print(f'Failed: {failed} ({100*failed/total:.1f}% if total > 0 else 0.0}%)')
    print(f'Success Rate: {100*successful/total:.1f}% if total > 0 else 0.0}%')
    print()

    if '$report_type' == 'detailed':
        print('Common Flag Combinations:')
        flags = stats.get('common_flags', {})
        for flag_combo, count in sorted(flags.items(), key=lambda x: x[1], reverse=True)[:5]:
            print(f'  {flag_combo or \"(no flags)\"}: {count} times')
        print()

        first = stats.get('first_run', 'Unknown')
        last = stats.get('last_run', 'Unknown')
        print(f'First Run: {first}')
        print(f'Last Run: {last}')
        print()

except Exception as e:
    print(f'Error generating report: {e}')
"

    # Show recent errors if any
    if [[ -f "$ERROR_LOG" && "$report_type" == "detailed" ]]; then
        echo "Recent Errors:"
        echo "=============="
        tail -20 "$ERROR_LOG" | grep -E "^(TIMESTAMP|ERROR_TYPE|MESSAGE)" | head -15
        echo
    fi
}

# Check for concerning patterns
check_health() {
    if [[ ! -f "$USAGE_STATS" ]]; then
        log "No usage data yet - monitoring starting"
        return 0
    fi

    local issues_found=0

    # Check error rate
    local error_rate
    error_rate=$(python3 -c "
import json
try:
    with open('$USAGE_STATS', 'r') as f:
        stats = json.load(f)
    total = stats.get('total_executions', 0)
    failed = stats.get('failed_executions', 0)
    if total > 0:
        print(failed * 100 / total)
    else:
        print(0)
except:
    print(0)
")

    if (( $(echo "$error_rate > 20" | bc -l) )); then
        warn "High error rate detected: ${error_rate}%"
        ((issues_found++))
    fi

    # Check for recent errors
    if [[ -f "$ERROR_LOG" ]]; then
        local recent_errors
        recent_errors=$(tail -50 "$ERROR_LOG" | grep "^TIMESTAMP:" | wc -l)
        if [[ $recent_errors -gt 5 ]]; then
            warn "Multiple recent errors: $recent_errors in last 50 entries"
            ((issues_found++))
        fi
    fi

    if [[ $issues_found -eq 0 ]]; then
        success "Bootstrap script health looks good"
    else
        warn "Found $issues_found potential issues - check logs"
    fi

    return $issues_found
}

# Collect user feedback
collect_feedback() {
    echo "📝 Bootstrap Script Feedback Collection"
    echo "========================================"
    echo
    echo "Help us improve the bootstrap script experience!"
    echo

    read -p "Rate your confidence in the script (1-5): " confidence
    read -p "Any data loss incidents? (y/n): " data_loss
    read -p "Were warnings clear and helpful? (y/n): " warnings_clear
    read -p "Additional feedback (optional): " additional_feedback

    local timestamp=$(date -Iseconds)
    cat >> "$PROJECT_ROOT/.bootstrap_feedback.log" <<EOF
TIMESTAMP: $timestamp
CONFIDENCE: $confidence
DATA_LOSS: $data_loss
WARNINGS_CLEAR: $warnings_clear
FEEDBACK: $additional_feedback
---
EOF

    success "Thank you for your feedback!"
}

# Export data for analysis
export_data() {
    local export_dir="bootstrap_analytics_$(date +%Y%m%d_%H%M%S)"
    mkdir -p "$export_dir"

    # Copy all monitoring data
    [[ -f "$MONITOR_LOG" ]] && cp "$MONITOR_LOG" "$export_dir/"
    [[ -f "$USAGE_STATS" ]] && cp "$USAGE_STATS" "$export_dir/"
    [[ -f "$ERROR_LOG" ]] && cp "$ERROR_LOG" "$export_dir/"
    [[ -f "$PROJECT_ROOT/.bootstrap_feedback.log" ]] && cp "$PROJECT_ROOT/.bootstrap_feedback.log" "$export_dir/"

    # Generate summary report
    generate_report "detailed" > "$export_dir/summary_report.txt"

    success "Analytics data exported to: $export_dir"
}

# Show help
show_help() {
    cat <<'EOF'
Bootstrap Script Monitoring Tool

Usage: ./bin/bootstrap_monitor.sh [COMMAND]

Commands:
  record <exit_code> <flags> [duration]  Record a bootstrap execution
  error <type> <message> <context>       Record an error
  report [detailed]                      Show usage report
  health                                 Check for concerning patterns
  feedback                               Collect user feedback
  export                                 Export data for analysis
  help                                   Show this help

Examples:
  ./bin/bootstrap_monitor.sh record 0 "--force --verbose" 45
  ./bin/bootstrap_monitor.sh error "file_conflict" "Directory exists" "docs/CLAUDE.md"
  ./bin/bootstrap_monitor.sh report detailed
  ./bin/bootstrap_monitor.sh health

Monitoring Philosophy:
  - Track user behavior patterns
  - Identify pain points and failure modes
  - Measure impact of improvements
  - Guide future development priorities
EOF
}

# Main function
main() {
    case "${1:-help}" in
        record)
            record_execution "${2:-1}" "${3:-}" "${4:-0}"
            ;;
        error)
            record_error "${2:-unknown}" "${3:-no message}" "${4:-no context}"
            ;;
        report)
            generate_report "${2:-summary}"
            ;;
        health)
            check_health
            ;;
        feedback)
            collect_feedback
            ;;
        export)
            export_data
            ;;
        help|--help|-h)
            show_help
            ;;
        *)
            error "Unknown command: $1"
            show_help
            exit 1
            ;;
    esac
}

main "$@"