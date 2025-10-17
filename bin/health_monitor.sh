#!/usr/bin/env bash
set -euo pipefail

# OOS Health Monitoring System - Automated continuous health monitoring
# Usage: ./bin/health_monitor.sh [--daemon] [--interval SECONDS] [--alert-threshold N]

VERSION="1.0.0"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
HEALTH_LOG="$PROJECT_ROOT/health_monitor.log"
ALERTS_LOG="$PROJECT_ROOT/health_alerts.log"
PID_FILE="$PROJECT_ROOT/.health_monitor.pid"

# Default configuration
DAEMON_MODE=false
CHECK_INTERVAL=300  # 5 minutes
ALERT_THRESHOLD=3   # Number of consecutive failures before alerting
MAX_LOG_SIZE=10485760  # 10MB
RETENTION_DAYS=7

# Health check results
declare -A health_status
declare -A failure_counts

# Parse command line arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --daemon) DAEMON_MODE=true; shift ;;
    --interval) CHECK_INTERVAL="$2"; shift 2 ;;
    --alert-threshold) ALERT_THRESHOLD="$2"; shift 2 ;;
    --stop)
      if [[ -f "$PID_FILE" ]]; then
        pid=$(cat "$PID_FILE")
        if kill -0 "$pid" 2>/dev/null; then
          kill "$pid"
          echo "Health monitor stopped (PID: $pid)"
          rm -f "$PID_FILE"
        else
          echo "Health monitor not running"
          rm -f "$PID_FILE"
        fi
      else
        echo "Health monitor not running"
      fi
      exit 0
      ;;
    --status)
      if [[ -f "$PID_FILE" ]]; then
        pid=$(cat "$PID_FILE")
        if kill -0 "$pid" 2>/dev/null; then
          echo "Health monitor running (PID: $pid)"
          if [[ -f "$HEALTH_LOG" ]]; then
            echo "Last check: $(tail -1 "$HEALTH_LOG" | cut -d']' -f1 | tr -d '[')"
          fi
        else
          echo "Health monitor not running (stale PID file)"
          rm -f "$PID_FILE"
        fi
      else
        echo "Health monitor not running"
      fi
      exit 0
      ;;
    --help|-h)
      echo "OOS Health Monitor v$VERSION"
      echo "Usage: $0 [OPTIONS]"
      echo "Options:"
      echo "  --daemon           Run as background daemon"
      echo "  --interval SECS    Check interval in seconds (default: 300)"
      echo "  --alert-threshold N Alert after N consecutive failures (default: 3)"
      echo "  --stop             Stop running daemon"
      echo "  --status           Show daemon status"
      echo "  --help             Show this help"
      exit 0
      ;;
    *) echo "Unknown option: $1"; exit 1 ;;
  esac
done

# Logging functions
log_health() {
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" >> "$HEALTH_LOG"
}

log_alert() {
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" >> "$ALERTS_LOG"
  echo "[ALERT] $*" >> "$HEALTH_LOG"
}

# Log rotation
rotate_logs() {
  for log_file in "$HEALTH_LOG" "$ALERTS_LOG"; do
    if [[ -f "$log_file" ]] && [[ $(stat -f%z "$log_file" 2>/dev/null || stat -c%s "$log_file" 2>/dev/null || echo 0) -gt $MAX_LOG_SIZE ]]; then
      mv "$log_file" "${log_file}.old"
      touch "$log_file"
      log_health "Rotated log file: $log_file"
    fi
  done

  # Clean old logs
  find "$PROJECT_ROOT" -name "*.log.old" -mtime +$RETENTION_DAYS -delete 2>/dev/null || true
}

# Individual health checks
check_archon_mcp() {
  local archon_url="${ARCHON_URL:-https://archon.khamel.com:8051/mcp}"
  local response=$(curl -sS -o /dev/null -w "%{http_code}" --connect-timeout 10 --max-time 30 "$archon_url" 2>/dev/null || echo "000")

  if [[ "$response" == "200" ]]; then
    health_status[archon]="OK"
    failure_counts[archon]=0
    return 0
  else
    health_status[archon]="FAIL"
    ((failure_counts[archon]++))
    log_health "Archon MCP health check failed: HTTP $response"
    return 1
  fi
}

check_openrouter_keys() {
  local working_keys=0
  local total_keys=0

  if [[ -f "$PROJECT_ROOT/.env" ]]; then
    cd "$PROJECT_ROOT"
    source bin/safe_source_env.sh .env 2>/dev/null || return 1

    if [[ -n "${OPENROUTER_KEYS:-}" ]]; then
      IFS=',' read -ra KEYS <<< "$OPENROUTER_KEYS"
      total_keys=${#KEYS[@]}

      for key in "${KEYS[@]}"; do
        key=$(echo "$key" | tr -d ' "'"'"'')
        if [[ -n "$key" ]]; then
          local response=$(curl -sS -o /dev/null -w "%{http_code}" \
            --connect-timeout 10 --max-time 30 \
            -H "Authorization: Bearer $key" \
            https://openrouter.ai/api/v1/models 2>/dev/null || echo "000")

          if [[ "$response" == "200" ]]; then
            ((working_keys++))
          fi
        fi
      done

      if [[ $working_keys -gt 0 ]]; then
        health_status[openrouter]="OK ($working_keys/$total_keys keys working)"
        failure_counts[openrouter]=0
        return 0
      else
        health_status[openrouter]="FAIL (0/$total_keys keys working)"
        ((failure_counts[openrouter]++))
        log_health "OpenRouter keys health check failed: no working keys"
        return 1
      fi
    else
      health_status[openrouter]="SKIP (no keys configured)"
      failure_counts[openrouter]=0
      return 0
    fi
  else
    health_status[openrouter]="SKIP (no .env file)"
    failure_counts[openrouter]=0
    return 0
  fi
}

check_onepassword_cli() {
  if command -v op >/dev/null 2>&1; then
    if timeout 10 op whoami >/dev/null 2>&1; then
      health_status[onepassword]="OK"
      failure_counts[onepassword]=0
      return 0
    else
      health_status[onepassword]="FAIL (not signed in)"
      ((failure_counts[onepassword]++))
      log_health "1Password CLI health check failed: not signed in"
      return 1
    fi
  else
    health_status[onepassword]="SKIP (not installed)"
    failure_counts[onepassword]=0
    return 0
  fi
}

check_github_cli() {
  if command -v gh >/dev/null 2>&1; then
    if timeout 10 gh auth status >/dev/null 2>&1; then
      health_status[github]="OK"
      failure_counts[github]=0
      return 0
    else
      health_status[github]="FAIL (not authenticated)"
      ((failure_counts[github]++))
      log_health "GitHub CLI health check failed: not authenticated"
      return 1
    fi
  else
    health_status[github]="SKIP (not installed)"
    failure_counts[github]=0
    return 0
  fi
}

check_mcp_registration() {
  if command -v claude >/dev/null 2>&1; then
    if timeout 10 claude mcp list >/dev/null 2>&1; then
      local registered_mcps=$(claude mcp list 2>/dev/null | grep -c '^\s*\w' || echo 0)
      health_status[mcp_registration]="OK ($registered_mcps MCPs registered)"
      failure_counts[mcp_registration]=0
      return 0
    else
      health_status[mcp_registration]="FAIL (claude mcp list failed)"
      ((failure_counts[mcp_registration]++))
      log_health "MCP registration health check failed"
      return 1
    fi
  else
    health_status[mcp_registration]="SKIP (Claude CLI not installed)"
    failure_counts[mcp_registration]=0
    return 0
  fi
}

check_disk_space() {
  local usage=$(df "$PROJECT_ROOT" | tail -1 | awk '{print $5}' | tr -d '%')
  if [[ $usage -lt 90 ]]; then
    health_status[disk_space]="OK (${usage}% used)"
    failure_counts[disk_space]=0
    return 0
  else
    health_status[disk_space]="WARN (${usage}% used)"
    ((failure_counts[disk_space]++))
    log_health "Disk space warning: ${usage}% used"
    if [[ $usage -gt 95 ]]; then
      return 1
    fi
    return 0
  fi
}

check_file_permissions() {
  local issues=0

  # Check bin directory permissions
  if [[ -d "$PROJECT_ROOT/bin" ]]; then
    find "$PROJECT_ROOT/bin" -name "*.sh" -type f ! -perm -u+x | while read -r file; do
      ((issues++))
      log_health "File permission issue: $file not executable"
    done
  fi

  if [[ $issues -eq 0 ]]; then
    health_status[file_permissions]="OK"
    failure_counts[file_permissions]=0
    return 0
  else
    health_status[file_permissions]="FAIL ($issues issues)"
    ((failure_counts[file_permissions]++))
    return 1
  fi
}

# Run all health checks
run_health_checks() {
  local start_time=$(date +%s)
  local total_checks=0
  local failed_checks=0

  log_health "Starting health check cycle"

  # Initialize failure counts if not set
  for service in archon openrouter onepassword github mcp_registration disk_space file_permissions; do
    [[ -z "${failure_counts[$service]:-}" ]] && failure_counts[$service]=0
  done

  # Run individual checks
  check_archon_mcp || ((failed_checks++))
  ((total_checks++))

  check_openrouter_keys || ((failed_checks++))
  ((total_checks++))

  check_onepassword_cli || ((failed_checks++))
  ((total_checks++))

  check_github_cli || ((failed_checks++))
  ((total_checks++))

  check_mcp_registration || ((failed_checks++))
  ((total_checks++))

  check_disk_space || ((failed_checks++))
  ((total_checks++))

  check_file_permissions || ((failed_checks++))
  ((total_checks++))

  local end_time=$(date +%s)
  local duration=$((end_time - start_time))

  # Check for services that need alerts
  for service in "${!failure_counts[@]}"; do
    if [[ ${failure_counts[$service]} -ge $ALERT_THRESHOLD ]]; then
      log_alert "Service $service has failed ${failure_counts[$service]} consecutive times: ${health_status[$service]}"
    fi
  done

  local status_summary=""
  if [[ $failed_checks -eq 0 ]]; then
    status_summary="ALL OK"
  else
    status_summary="$failed_checks/$total_checks FAILED"
  fi

  log_health "Health check completed: $status_summary (${duration}s)"

  # Log individual service statuses
  for service in "${!health_status[@]}"; do
    log_health "  $service: ${health_status[$service]}"
  done
}

# Generate health report
generate_health_report() {
  local report_file="$PROJECT_ROOT/health_report.txt"

  {
    echo "OOS Health Report"
    echo "Generated: $(date)"
    echo "========================="
    echo

    echo "Service Status:"
    for service in "${!health_status[@]}"; do
      printf "  %-20s %s\n" "$service:" "${health_status[$service]}"
    done
    echo

    echo "Failure Counts:"
    for service in "${!failure_counts[@]}"; do
      printf "  %-20s %d\n" "$service:" "${failure_counts[$service]}"
    done
    echo

    if [[ -f "$ALERTS_LOG" ]]; then
      echo "Recent Alerts:"
      tail -10 "$ALERTS_LOG" 2>/dev/null || echo "  No recent alerts"
      echo
    fi

    echo "System Information:"
    echo "  Disk Usage: $(df -h "$PROJECT_ROOT" | tail -1)"
    echo "  Load Average: $(uptime | awk -F'load average:' '{print $2}')"
    echo "  Memory: $(free -h | grep Mem: || echo 'N/A')"

  } > "$report_file"

  echo "Health report generated: $report_file"
}

# Daemon mode
run_daemon() {
  echo "Starting OOS Health Monitor daemon..."
  echo "PID: $$"
  echo "Interval: ${CHECK_INTERVAL}s"
  echo "Alert threshold: $ALERT_THRESHOLD"
  echo "Log file: $HEALTH_LOG"

  # Save PID
  echo $$ > "$PID_FILE"

  # Setup signal handlers
  cleanup() {
    log_health "Health monitor daemon stopping"
    rm -f "$PID_FILE"
    exit 0
  }

  trap cleanup TERM INT

  log_health "Health monitor daemon started (PID: $$)"

  # Main monitoring loop
  while true; do
    rotate_logs
    run_health_checks

    # Sleep in chunks to allow for signal handling
    local remaining=$CHECK_INTERVAL
    while [[ $remaining -gt 0 ]]; do
      sleep 1
      ((remaining--))
    done
  done
}

# One-time health check
run_single_check() {
  echo "Running single health check..."
  run_health_checks

  echo
  echo "Health Status Summary:"
  echo "======================"
  for service in "${!health_status[@]}"; do
    printf "%-20s %s\n" "$service:" "${health_status[$service]}"
  done

  # Check if any service needs immediate attention
  local critical_issues=0
  for service in "${!failure_counts[@]}"; do
    if [[ ${failure_counts[$service]} -gt 0 ]] && [[ "${health_status[$service]}" == *"FAIL"* ]]; then
      ((critical_issues++))
    fi
  done

  if [[ $critical_issues -gt 0 ]]; then
    echo
    echo "⚠️  $critical_issues service(s) require attention"
    echo "Run './bin/diagnose.sh' for detailed diagnostics"
  else
    echo
    echo "✅ All services are healthy"
  fi

  generate_health_report
}

# Check if already running
check_running_daemon() {
  if [[ -f "$PID_FILE" ]]; then
    local pid=$(cat "$PID_FILE")
    if kill -0 "$pid" 2>/dev/null; then
      echo "Health monitor is already running (PID: $pid)"
      echo "Use --stop to stop the daemon or --status to check status"
      exit 1
    else
      echo "Removing stale PID file"
      rm -f "$PID_FILE"
    fi
  fi
}

# Initialize
init_monitoring() {
  cd "$PROJECT_ROOT"

  # Create log files if they don't exist
  touch "$HEALTH_LOG" "$ALERTS_LOG"

  # Initialize failure counts
  for service in archon openrouter onepassword github mcp_registration disk_space file_permissions; do
    failure_counts[$service]=0
  done
}

# Main execution
main() {
  init_monitoring

  if [[ "$DAEMON_MODE" == "true" ]]; then
    check_running_daemon
    run_daemon
  else
    run_single_check
  fi
}

# Run main function
main "$@"