#!/bin/bash
# OOS Performance Monitoring System
# Tracks performance metrics and provides alerts

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$(dirname "$(dirname "$SCRIPT_DIR")")))"
METRICS_DIR="$PROJECT_ROOT/logs/metrics"
ALERTS_DIR="$PROJECT_ROOT/logs/alerts"
METRICS_RETENTION_DAYS=30

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Create directories
mkdir -p "$METRICS_DIR" "$ALERTS_DIR"

# Performance thresholds
CPU_WARNING=70
CPU_CRITICAL=90
MEM_WARNING=80
MEM_CRITICAL=95
DISK_WARNING=85
DISK_CRITICAL=95
LOAD_WARNING=1.0
LOAD_CRITICAL=2.0

# Logging
log_metric() {
    local metric="$1"
    local value="$2"
    local timestamp=$(date -Iseconds)
    echo "$timestamp,$metric,$value" >> "$METRICS_DIR/performance.csv"
}

send_alert() {
    local level="$1"
    local message="$2"
    local timestamp=$(date -Iseconds)
    local alert_file="$ALERTS_DIR/alert_$(date +%s).json"

    cat << EOF > "$alert_file"
{
  "timestamp": "$timestamp",
  "level": "$level",
  "message": "$message",
  "hostname": "$(hostname)",
  "system": "oos-performance-monitor"
}
EOF

    echo -e "${RED}🚨 ALERT [$level]: $message${NC}"
}

collect_system_metrics() {
    local timestamp=$(date -Iseconds)

    # CPU metrics
    local cpu_usage=$(top -bn1 | grep "Cpu(s)" | awk '{print $2}' | sed 's/%us,//')
    log_metric "cpu_usage_percent" "$cpu_usage"

    # Memory metrics
    local mem_info=$(free -m | grep Mem)
    local total_mem=$(echo $mem_info | awk '{print $2}')
    local used_mem=$(echo $mem_info | awk '{print $3}')
    local free_mem=$(echo $mem_info | awk '{print $4}')
    local mem_usage=$(( (used_mem * 100) / total_mem ))

    log_metric "memory_total_mb" "$total_mem"
    log_metric "memory_used_mb" "$used_mem"
    log_metric "memory_free_mb" "$free_mem"
    log_metric "memory_usage_percent" "$mem_usage"

    # Disk metrics
    local disk_info=$(df / | awk 'NR==2 {print $2,$3,$4,$5}')
    local total_disk=$(echo $disk_info | awk '{print $1}')
    local used_disk=$(echo $disk_info | awk '{print $2}')
    local free_disk=$(echo $disk_info | awk '{print $3}')
    local disk_usage=$(echo $disk_info | awk '{print $4}' | sed 's/%//')

    log_metric "disk_total_kb" "$total_disk"
    log_metric "disk_used_kb" "$used_disk"
    log_metric "disk_free_kb" "$free_disk"
    log_metric "disk_usage_percent" "$disk_usage"

    # Load average
    local load_1m=$(uptime | awk -F'load average:' '{print $2}' | awk '{print $1}' | sed 's/,//')
    local load_5m=$(uptime | awk -F'load average:' '{print $2}' | awk '{print $2}' | sed 's/,//')
    local load_15m=$(uptime | awk -F'load average:' '{print $2}' | awk '{print $3}')

    log_metric "load_1m" "$load_1m"
    log_metric "load_5m" "$load_5m"
    log_metric "load_15m" "$load_15m"

    # Network metrics
    local network_rx=$(cat /proc/net/dev | grep eth0 | awk '{print $2}' || echo "0")
    local network_tx=$(cat /proc/net/dev | grep eth0 | awk '{print $10}' || echo "0")

    log_metric "network_rx_bytes" "$network_rx"
    log_metric "network_tx_bytes" "$network_tx"

    # Check for alerts
    check_performance_alerts "$cpu_usage" "$mem_usage" "$disk_usage" "$load_1m"
}

check_performance_alerts() {
    local cpu_usage="$1"
    local mem_usage="$2"
    local disk_usage="$3"
    local load_1m="$4"

    # CPU alerts
    if command -v bc > /dev/null; then
        if (( $(echo "$cpu_usage > $CPU_CRITICAL" | bc -l) )); then
            send_alert "CRITICAL" "Critical CPU usage: ${cpu_usage}%"
        elif (( $(echo "$cpu_usage > $CPU_WARNING" | bc -l) )); then
            send_alert "WARNING" "High CPU usage: ${cpu_usage}%"
        fi
    else
        if (( cpu_usage > CPU_CRITICAL )); then
            send_alert "CRITICAL" "Critical CPU usage: ${cpu_usage}%"
        elif (( cpu_usage > CPU_WARNING )); then
            send_alert "WARNING" "High CPU usage: ${cpu_usage}%"
        fi
    fi

    # Memory alerts
    if (( mem_usage > MEM_CRITICAL )); then
        send_alert "CRITICAL" "Critical memory usage: ${mem_usage}%"
    elif (( mem_usage > MEM_WARNING )); then
        send_alert "WARNING" "High memory usage: ${mem_usage}%"
    fi

    # Disk alerts
    if (( disk_usage > DISK_CRITICAL )); then
        send_alert "CRITICAL" "Critical disk usage: ${disk_usage}%"
    elif (( disk_usage > DISK_WARNING )); then
        send_alert "WARNING" "High disk usage: ${disk_usage}%"
    fi

    # Load alerts
    if command -v bc > /dev/null; then
        if (( $(echo "$load_1m > $LOAD_CRITICAL" | bc -l) )); then
            send_alert "CRITICAL" "Critical system load: $load_1m"
        elif (( $(echo "$load_1m > $LOAD_WARNING" | bc -l) )); then
            send_alert "WARNING" "High system load: $load_1m"
        fi
    else
        local load_int=${load_1m%.*}
        if (( load_int > 2 )); then
            send_alert "CRITICAL" "Critical system load: $load_1m"
        elif (( load_int > 1 )); then
            send_alert "WARNING" "High system load: $load_1m"
        fi
    fi
}

cleanup_old_metrics() {
    find "$METRICS_DIR" -name "*.csv" -mtime +$METRICS_RETENTION_DAYS -delete
    find "$ALERTS_DIR" -name "alert_*.json" -mtime +$METRICS_RETENTION_DAYS -delete
}

generate_performance_report() {
    local report_file="$METRICS_DIR/performance_report_$(date +%Y%m%d).txt"
    local today=$(date +%Y-%m-%d)

    cat << EOF > "$report_file"
OOS Performance Report - $today
==================================

System Information:
- Hostname: $(hostname)
- OS: $(uname -s -r)
- CPU Cores: $(nproc)
- Total Memory: $(free -h | grep Mem | awk '{print $2}')
- Disk Space: $(df -h / | awk 'NR==2 {print $2}')

Current Performance:
Metrics collected successfully

Recent Alerts:
$(find "$ALERTS_DIR" -name "alert_*.json" -mtime -1 -exec cat {} \; | jq -r '.timestamp + " [" + .level + "] " + .message' 2>/dev/null || echo "No recent alerts")

Performance Trends:
- Data available in: $METRICS_DIR/performance.csv
- Generated by: OOS Performance Monitor
EOF

    echo "Performance report generated: $report_file"
}

main() {
    case "${1:-collect}" in
        "collect")
            collect_system_metrics
            ;;
        "report")
            generate_performance_report
            ;;
        "cleanup")
            cleanup_old_metrics
            ;;
        "monitor")
            echo "Starting performance monitoring (Ctrl+C to stop)..."
            while true; do
                collect_system_metrics
                sleep 60
            done
            ;;
        *)
            echo "Usage: $0 {collect|report|cleanup|monitor}"
            exit 1
            ;;
    esac
}

main "$@"