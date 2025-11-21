#!/bin/bash

# Atlas Services Verification Script
# Part of Atlas Reliability Closeout - Task 1: Systemd Services

set -euo pipefail

# Configuration
API_URL="http://localhost:7444"
HEALTH_URL="${API_URL}/health"
SERVICES=("atlas-api.service" "atlas-worker.service" "atlas-scheduler.timer" "atlas-backup.timer")

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')] ✓ $1${NC}"
}

warn() {
    echo -e "${YELLOW}[$(date '+%Y-%m-%d %H:%M:%S')] ⚠ $1${NC}"
}

error() {
    echo -e "${RED}[$(date '+%Y-%m-%d %H:%M:%S')] ✗ $1${NC}"
    exit 1
}

info() {
    echo -e "${BLUE}[$(date '+%Y-%m-%d %H:%M:%S')] ℹ $1${NC}"
}

# Function to check if a service is active
check_service_active() {
    local service="$1"
    if systemctl is-active --quiet "$service"; then
        log "$service is active"
        return 0
    else
        error "$service is not active"
    fi
}

# Function to check if a service is enabled
check_service_enabled() {
    local service="$1"
    if systemctl is-enabled --quiet "$service"; then
        log "$service is enabled"
        return 0
    else
        error "$service is not enabled"
    fi
}

# Function to check service restart policy
check_restart_policy() {
    local service="$1"
    local restart_policy
    restart_policy=$(systemctl show "$service" -p Restart | cut -d= -f2)

    if [[ "$restart_policy" == "always" ]] || [[ "$restart_policy" == "on-failure" ]]; then
        log "$service has restart policy: $restart_policy"
        return 0
    else
        warn "$service has restart policy: $restart_policy"
        return 1
    fi
}

# Function to check service resource limits
check_resource_limits() {
    local service="$1"
    local memory_limit
    memory_limit=$(systemctl show "$service" -p MemoryMax | cut -d= -f2)

    if [[ -n "$memory_limit" ]]; then
        log "$service has memory limit: $memory_limit"
        return 0
    else
        warn "$service has no memory limit configured"
        return 1
    fi
}

# Function to check API health
check_api_health() {
    info "Checking API health endpoint..."

    # Wait up to 30 seconds for API to respond
    for i in {1..30}; do
        if curl -s -f "$HEALTH_URL" >/dev/null 2>&1; then
            log "API health check passed"
            return 0
        fi

        if [[ $i -eq 30 ]]; then
            error "API health check failed after 30 seconds"
        fi

        sleep 1
        info "Waiting for API to respond... ($i/30)"
    done
}

# Function to check service logs for errors
check_service_logs() {
    local service="$1"
    local recent_errors

    # Check for errors in the last 10 minutes
    recent_errors=$(journalctl -u "$service" --since "10 minutes ago" --priority=err --no-pager | wc -l)

    if [[ "$recent_errors" -eq 0 ]]; then
        log "$service has no recent errors"
        return 0
    else
        warn "$service has $recent_errors recent errors"
        return 1
    fi
}

# Function to check timer scheduling
check_timer_scheduling() {
    local timer="$1"

    if systemctl is-active --quiet "$timer"; then
        log "$timer is active and scheduled"

        # Show next run time
        local next_run
        next_run=$(systemctl list-timers "$timer" --no-pager | awk 'NR==2 {print $4}')
        if [[ -n "$next_run" ]]; then
            info "$timer next run: $next_run"
        fi
        return 0
    else
        error "$timer is not active"
    fi
}

# Function to check worker processing
check_worker_processing() {
    info "Checking worker processing status..."

    # Check if worker process is running
    if pgrep -f "python3 worker.py" >/dev/null; then
        log "Worker process is running"
        return 0
    else
        warn "Worker process not found"
        return 1
    fi
}

# Function to check backup system
check_backup_system() {
    info "Checking backup system..."

    local backup_dir="/home/ubuntu/dev/atlas/backups"
    if [[ -d "$backup_dir" ]]; then
        local backup_count
        backup_count=$(find "$backup_dir" -name "atlas_backup_*.tar.gz" | wc -l)

        if [[ "$backup_count" -gt 0 ]]; then
            log "Found $backup_count backup files"
            return 0
        else
            warn "No backup files found (expected for new installation)"
            return 0
        fi
    else
        warn "Backup directory not found"
        return 1
    fi
}

# Function to check database access
check_database_access() {
    info "Checking database access..."

    local db_path="/home/ubuntu/dev/atlas/data/atlas.db"
    if [[ -f "$db_path" ]]; then
        log "Database file exists"

        # Try to read from database
        if python3 -c "
import sqlite3
import sys
try:
    conn = sqlite3.connect('$db_path')
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM content')
    count = cursor.fetchone()[0]
    print(f'Database contains {count} records')
    conn.close()
except Exception as e:
    print(f'Database error: {e}')
    sys.exit(1)
" 2>/dev/null; then
            log "Database is accessible"
            return 0
        else
            warn "Database access failed"
            return 1
        fi
    else
        warn "Database file not found (expected for new installation)"
        return 0
    fi
}

# Function to check system resources
check_system_resources() {
    info "Checking system resources..."

    # Check disk space
    local disk_usage
    disk_usage=$(df /home/ubuntu/dev/atlas | awk 'NR==2 {print $5}' | sed 's/%//')

    if [[ "$disk_usage" -lt 80 ]]; then
        log "Disk space usage: ${disk_usage}% (OK)"
        return 0
    else
        warn "Disk space usage: ${disk_usage}% (High)"
        return 1
    fi
}

# Function to check timer status
check_timer_status() {
    info "Checking timer status..."

    systemctl list-timers atlas-* --no-pager

    log "Timer status check completed"
}

# Main verification function
verify_all() {
    info "Starting comprehensive Atlas services verification..."
    echo ""

    # Check each service
    for service in "${SERVICES[@]}"; do
        info "Verifying $service..."
        check_service_active "$service"
        check_service_enabled "$service"

        if [[ "$service" == *.service ]]; then
            check_restart_policy "$service"
            check_resource_limits "$service"
            check_service_logs "$service"
        elif [[ "$service" == *.timer ]]; then
            check_timer_scheduling "$service"
        fi

        echo ""
    done

    # Check API health
    check_api_health
    echo ""

    # Check worker processing
    check_worker_processing
    echo ""

    # Check backup system
    check_backup_system
    echo ""

    # Check database access
    check_database_access
    echo ""

    # Check system resources
    check_system_resources
    echo ""

    # Check timer status
    check_timer_status
    echo ""

    log "Verification completed!"
    info "Next steps:"
    info "- Monitor logs: journalctl -u atlas-api.service -f"
    info "- Check API: curl $HEALTH_URL"
    info "- View all timers: systemctl list-timers"
    info "- Restart services: systemctl restart atlas-api.service"
}

# Parse command line arguments
case "${1:-all}" in
    all)
        verify_all
        ;;
    api)
        check_api_health
        ;;
    worker)
        check_worker_processing
        ;;
    backup)
        check_backup_system
        ;;
    database)
        check_database_access
        ;;
    resources)
        check_system_resources
        ;;
    timers)
        check_timer_status
        ;;
    *)
        echo "Usage: $0 {all|api|worker|backup|database|resources|timers}"
        exit 1
        ;;
esac