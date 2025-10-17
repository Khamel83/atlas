#!/bin/bash

# Atlas Disaster Recovery Script
# Comprehensive disaster recovery procedures for Atlas v4

set -euo pipefail

# Configuration
ATLAS_HOME="/opt/atlas"
BACKUP_DIR="/opt/atlas/backups"
DR_DIR="/opt/atlas/disaster_recovery"
LOG_FILE="/var/log/atlas_disaster_recovery.log"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1" >> "$LOG_FILE"
}

warn() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING: $1${NC}"
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] WARNING: $1" >> "$LOG_FILE"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR: $1${NC}"
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] ERROR: $1" >> "$LOG_FILE"
}

info() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')] INFO: $1${NC}"
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] INFO: $1" >> "$LOG_FILE"
}

# Check prerequisites
check_prerequisites() {
    log "Checking disaster recovery prerequisites..."

    # Check if running as root
    if [[ $EUID -ne 0 ]]; then
        error "This script must be run as root"
    fi

    # Check if Atlas directories exist
    if [[ ! -d "$ATLAS_HOME" ]]; then
        error "Atlas installation not found at $ATLAS_HOME"
    fi

    # Check if backup directory exists
    if [[ ! -d "$BACKUP_DIR" ]]; then
        error "Backup directory not found at $BACKUP_DIR"
    fi

    # Check available disk space
    available_space=$(df "$BACKUP_DIR" | awk 'NR==2 {print $4}')
    required_space=2097152  # 2GB in KB

    if [[ $available_space -lt $required_space ]]; then
        error "Insufficient disk space for disaster recovery operations"
    fi

    # Create disaster recovery directory
    mkdir -p "$DR_DIR"

    log "Prerequisites check passed"
}

# Create emergency backup
create_emergency_backup() {
    log "Creating emergency backup..."

    local emergency_backup_dir="${DR_DIR}/emergency_backup_$(date +%Y%m%d_%H%M%S)"
    mkdir -p "$emergency_backup_dir"

    info "Backing up critical system files..."

    # Backup database
    if [[ -f "${ATLAS_HOME}/data/atlas.db" ]]; then
        cp "${ATLAS_HOME}/data/atlas.db" "$emergency_backup_dir/"
        log "Database backed up"
    fi

    # Backup configuration
    if [[ -d "${ATLAS_HOME}/config" ]]; then
        cp -r "${ATLAS_HOME}/config" "$emergency_backup_dir/"
        log "Configuration backed up"
    fi

    # Backup environment file
    if [[ -f "${ATLAS_HOME}/.env" ]]; then
        cp "${ATLAS_HOME}/.env" "$emergency_backup_dir/"
        log "Environment file backed up"
    fi

    # Backup vault metadata (not content, just structure)
    if [[ -d "${ATLAS_HOME}/vault" ]]; then
        find "${ATLAS_HOME}/vault" -name "*.md" -type f | head -100 | xargs cp -t "$emergency_backup_dir/vault_sample/" 2>/dev/null || true
        log "Vault metadata sample backed up"
    fi

    # Create recovery manifest
    cat > "${emergency_backup_dir}/recovery_manifest.json" << EOF
{
    "backup_type": "emergency",
    "created_at": "$(date -Iseconds)",
    "atlas_version": "4.0",
    "hostname": "$(hostname)",
    "components": {
        "database": $( [[ -f "${ATLAS_HOME}/data/atlas.db" ]] && echo "true" || echo "false" ),
        "config": $( [[ -d "${ATLAS_HOME}/config" ]] && echo "true" || echo "false" ),
        "environment": $( [[ -f "${ATLAS_HOME}/.env" ]] && echo "true" || echo "false" ),
        "vault": $( [[ -d "${ATLAS_HOME}/vault" ]] && echo "true" || echo "false" )
    },
    "system_info": {
        "kernel": "$(uname -r)",
        "os": "$(lsb_release -d | cut -f2)",
        "memory_gb": "$(free -g | awk 'NR==2{print $2}')",
        "disk_space_gb": "$(df -h / | awk 'NR==2 {print $4}' | sed 's/G//')"
    }
}
EOF

    # Compress emergency backup
    tar -czf "${emergency_backup_dir}.tar.gz" -C "$(dirname "$emergency_backup_dir")" "$(basename "$emergency_backup_dir")"
    rm -rf "$emergency_backup_dir"

    log "Emergency backup created: ${emergency_backup_dir}.tar.gz"
    echo "${emergency_backup_dir}.tar.gz"
}

# System health assessment
assess_system_health() {
    log "Assessing system health..."

    local health_report="${DR_DIR}/system_health_$(date +%Y%m%d_%H%M%S).json"

    # Check system services
    local services_status=""
    for service in atlas-ingest atlas-bot atlas-monitor; do
        if systemctl is-active --quiet "$service" 2>/dev/null; then
            services_status+="$service:running;"
        else
            services_status+="$service:stopped;"
        fi
    done

    # Check database integrity
    local db_status="unknown"
    if [[ -f "${ATLAS_HOME}/data/atlas.db" ]]; then
        if sqlite3 "${ATLAS_HOME}/data/atlas.db" "PRAGMA integrity_check;" >/dev/null 2>&1; then
            db_status="healthy"
        else
            db_status="corrupted"
        fi
    else
        db_status="missing"
    fi

    # Check disk space
    local disk_usage=$(df / | awk 'NR==2 {print $5}' | sed 's/%//')
    local disk_status="healthy"
    if [[ $disk_usage -gt 90 ]]; then
        disk_status="critical"
    elif [[ $disk_usage -gt 80 ]]; then
        disk_status="warning"
    fi

    # Check memory usage
    local memory_usage=$(free | awk 'NR==2{printf "%.0f", $3*100/$2}')
    local memory_status="healthy"
    if [[ $memory_usage -gt 90 ]]; then
        memory_status="critical"
    elif [[ $memory_usage -gt 80 ]]; then
        memory_status="warning"
    fi

    # Check network connectivity
    local network_status="healthy"
    if ! ping -c 1 8.8.8.8 >/dev/null 2>&1; then
        network_status="critical"
    fi

    # Create health report
    cat > "$health_report" << EOF
{
    "assessment_timestamp": "$(date -Iseconds)",
    "hostname": "$(hostname)",
    "overall_status": "$([ "$db_status" = "healthy" ] && [ "$disk_status" = "healthy" ] && [ "$memory_status" = "healthy" ] && echo "healthy" || echo "degraded")",
    "services": {
        "status": "$services_status",
        "count": $(echo "$services_status" | tr ';' '\n' | grep -c "running")
    },
    "database": {
        "status": "$db_status",
        "path": "${ATLAS_HOME}/data/atlas.db"
    },
    "disk": {
        "status": "$disk_status",
        "usage_percent": $disk_usage,
        "available_gb": "$(df -h / | awk 'NR==2 {print $4}' | sed 's/G//')"
    },
    "memory": {
        "status": "$memory_status",
        "usage_percent": $memory_usage,
        "available_gb": "$(free -h | awk 'NR==2 {print $7}' | sed 's/G//')"
    },
    "network": {
        "status": "$network_status"
    },
    "recommendations": [
        $([ "$db_status" != "healthy" ] && echo "\"Restore database from backup\",")
        $([ "$disk_status" = "critical" ] && echo "\"Free up disk space immediately\",")
        $([ "$memory_status" = "critical" ] && echo "\"Free up memory or restart services\",")
        $([ "$network_status" = "critical" ] && echo "\"Check network configuration\",")
        "Review service logs for errors"
    ]
}
EOF

    log "System health assessment completed: $health_report"
    echo "$health_report"
}

# Emergency service restart
emergency_restart_services() {
    log "Performing emergency service restart..."

    local services_restart_log="${DR_DIR}/emergency_restart_$(date +%Y%m%d_%H%M%S).log"

    # Stop all Atlas services
    info "Stopping Atlas services..."
    systemctl stop atlas-ingest atlas-bot atlas-monitor 2>&1 | tee -a "$services_restart_log"

    # Wait for services to stop
    sleep 10

    # Check if any services are still running
    local running_services=$(systemctl list-units --state=running | grep atlas | wc -l)
    if [[ $running_services -gt 0 ]]; then
        warn "Some services are still running, forcing stop..."
        systemctl kill atlas-ingest atlas-bot atlas-monitor 2>&1 | tee -a "$services_restart_log"
        sleep 5
    fi

    # Start services in order
    info "Starting atlas-ingest service..."
    systemctl start atlas-ingest 2>&1 | tee -a "$services_restart_log"
    sleep 5

    info "Starting atlas-bot service..."
    systemctl start atlas-bot 2>&1 | tee -a "$services_restart_log"
    sleep 5

    info "Starting atlas-monitor service..."
    systemctl start atlas-monitor 2>&1 | tee -a "$services_restart_log"
    sleep 5

    # Verify services are running
    local restarted_services=0
    for service in atlas-ingest atlas-bot atlas-monitor; do
        if systemctl is-active --quiet "$service"; then
            log "$service is running"
            ((restarted_services++))
        else
            error "$service failed to start"
        fi
    done

    log "Emergency service restart completed: $restarted_services/3 services running"
    echo "$services_restart_log"
}

# Database repair
repair_database() {
    log "Attempting database repair..."

    local db_path="${ATLAS_HOME}/data/atlas.db"
    local repaired_db="${ATLAS_HOME}/data/atlas_repaired.db"
    local repair_log="${DR_DIR}/database_repair_$(date +%Y%m%d_%H%M%S).log"

    if [[ ! -f "$db_path" ]]; then
        error "Database file not found: $db_path"
    fi

    # Create backup before repair
    cp "$db_path" "${db_path}.repair_backup_$(date +%Y%m%d_%H%M%S)"

    info "Running database integrity check..."
    if sqlite3 "$db_path" "PRAGMA integrity_check;" 2>&1 | tee -a "$repair_log"; then
        log "Database integrity check passed"
        return 0
    fi

    warn "Database integrity check failed, attempting repair..."

    # Attempt to repair using .recover
    info "Attempting database recovery..."
    if sqlite3 "$db_path" ".recover" | sqlite3 "$repaired_db" 2>&1 | tee -a "$repair_log"; then
        # Verify repaired database
        if sqlite3 "$repaired_db" "PRAGMA integrity_check;" >/dev/null 2>&1; then
            # Replace original with repaired
            mv "$db_path" "${db_path}.corrupted_$(date +%Y%m%d_%H%M%S)"
            mv "$repaired_db" "$db_path"
            chown atlas:atlas "$db_path"
            log "Database repair successful"
            return 0
        fi
    fi

    error "Database repair failed"
    return 1
}

# Full system restore
full_system_restore() {
    local backup_file="$1"

    log "Starting full system restore from: $backup_file"

    if [[ ! -f "$backup_file" ]]; then
        error "Backup file not found: $backup_file"
    fi

    local restore_log="${DR_DIR}/full_restore_$(date +%Y%m%d_%H%M%S).log"
    local temp_restore_dir="/tmp/atlas_restore_$$"

    # Extract backup
    info "Extracting backup..."
    mkdir -p "$temp_restore_dir"
    tar -xzf "$backup_file" -C "$temp_restore_dir" 2>&1 | tee -a "$restore_log"

    # Find backup directory
    local backup_dir=$(find "$temp_restore_dir" -name "atlas_backup_*" -type d | head -1)
    if [[ -z "$backup_dir" ]]; then
        error "Invalid backup file format"
    fi

    # Stop all services
    info "Stopping Atlas services..."
    systemctl stop atlas-ingest atlas-bot atlas-monitor 2>&1 | tee -a "$restore_log"

    # Create pre-restore backup
    info "Creating pre-restore backup..."
    "${ATLAS_HOME}/scripts/backup.sh" backup 2>&1 | tee -a "$restore_log"

    # Restore database
    if [[ -f "${backup_dir}/atlas.db" ]]; then
        info "Restoring database..."
        cp "${backup_dir}/atlas.db" "${ATLAS_HOME}/data/"
        chown atlas:atlas "${ATLAS_HOME}/data/atlas.db"
        log "Database restored"
    fi

    # Restore configuration
    if [[ -d "${backup_dir}/config" ]]; then
        info "Restoring configuration..."
        cp -r "${backup_dir}/config/"* "${ATLAS_HOME}/config/"
        chown -R atlas:atlas "${ATLAS_HOME}/config"
        log "Configuration restored"
    fi

    # Restore environment file
    if [[ -f "${backup_dir}/.env" ]]; then
        info "Restoring environment file..."
        cp "${backup_dir}/.env" "${ATLAS_HOME}/"
        chown atlas:atlas "${ATLAS_HOME}/.env"
        chmod 600 "${ATLAS_HOME}/.env"
        log "Environment file restored"
    fi

    # Restore vault (optional and dangerous)
    if [[ -f "${backup_dir}/vault.tar.gz" ]]; then
        warn "Vault restore requires manual intervention"
        warn "Run: tar -xzf ${backup_dir}/vault.tar.gz -C ${ATLAS_HOME}/"
        warn "This will overwrite existing vault content!"
    fi

    # Cleanup
    rm -rf "$temp_restore_dir"

    # Restart services
    info "Restarting services..."
    systemctl start atlas-ingest atlas-bot atlas-monitor 2>&1 | tee -a "$restore_log"

    # Verify restore
    sleep 10
    local running_services=0
    for service in atlas-ingest atlas-bot atlas-monitor; do
        if systemctl is-active --quiet "$service"; then
            ((running_services++))
        fi
    done

    log "Full system restore completed: $running_services/3 services running"
    log "Restore log: $restore_log"
}

# Generate disaster recovery report
generate_dr_report() {
    log "Generating disaster recovery report..."

    local report_file="${DR_DIR}/dr_report_$(date +%Y%m%d_%H%M%S).html"

    # Get latest health assessment
    local health_file=$(ls -t "${DR_DIR}"/system_health_*.json 2>/dev/null | head -1)
    local health_data="{}"
    if [[ -f "$health_file" ]]; then
        health_data=$(cat "$health_file")
    fi

    # Get available backups
    local backup_count=$(ls -1 "$BACKUP_DIR"/atlas_backup_*.tar.gz 2>/dev/null | wc -l)
    local latest_backup=$(ls -t "$BACKUP_DIR"/atlas_backup_*.tar.gz 2>/dev/null | head -1 | xargs basename 2>/dev/null || echo "None")

    # Create HTML report
    cat > "$report_file" << EOF
<!DOCTYPE html>
<html>
<head>
    <title>Atlas Disaster Recovery Report</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        .header { background: #f5f5f5; padding: 20px; border-radius: 5px; }
        .section { margin: 20px 0; padding: 15px; border: 1px solid #ddd; border-radius: 5px; }
        .status-healthy { color: green; font-weight: bold; }
        .status-warning { color: orange; font-weight: bold; }
        .status-critical { color: red; font-weight: bold; }
        .status-degraded { color: orange; font-weight: bold; }
        table { width: 100%; border-collapse: collapse; margin: 10px 0; }
        th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
        th { background-color: #f2f2f2; }
        .timestamp { color: #666; font-size: 0.9em; }
    </style>
</head>
<body>
    <div class="header">
        <h1>Atlas Disaster Recovery Report</h1>
        <p class="timestamp">Generated: $(date)</p>
        <p>Hostname: $(hostname)</p>
    </div>

    <div class="section">
        <h2>System Status</h2>
        <pre>$health_data</pre>
    </div>

    <div class="section">
        <h2>Backup Status</h2>
        <table>
            <tr><th>Metric</th><th>Value</th></tr>
            <tr><td>Available Backups</td><td>$backup_count</td></tr>
            <tr><td>Latest Backup</td><td>$latest_backup</td></tr>
            <tr><td>Backup Directory</td><td>$BACKUP_DIR</td></tr>
            <tr><td>DR Directory</td><td>$DR_DIR</td></tr>
        </table>
    </div>

    <div class="section">
        <h2>Service Status</h2>
        <table>
            <tr><th>Service</th><th>Status</th></tr>
EOF

    # Add service status
    for service in atlas-ingest atlas-bot atlas-monitor; do
        local status="Stopped"
        local css_class="status-critical"
        if systemctl is-active --quiet "$service" 2>/dev/null; then
            status="Running"
            css_class="status-healthy"
        fi
        echo "            <tr><td>$service</td><td class=\"$css_class\">$status</td></tr>" >> "$report_file"
    done

    cat >> "$report_file" << EOF
        </table>
    </div>

    <div class="section">
        <h2>Recovery Procedures</h2>
        <h3>Emergency Backup</h3>
        <p>Run: $0 emergency-backup</p>

        <h3>System Health Assessment</h3>
        <p>Run: $0 health-assessment</p>

        <h3>Emergency Service Restart</h3>
        <p>Run: $0 emergency-restart</p>

        <h3>Database Repair</h3>
        <p>Run: $0 repair-database</p>

        <h3>Full System Restore</h3>
        <p>Run: $0 full-restore &lt;backup_file&gt;</p>
    </div>

    <div class="section">
        <h2>Recovery History</h2>
        <table>
            <tr><th>Operation</th><th>Timestamp</th><th>Log File</th></tr>
EOF

    # Add recent recovery operations
    for log_file in "$DR_DIR"/*.log; do
        if [[ -f "$log_file" ]]; then
            local operation=$(basename "$log_file" .log)
            local timestamp=$(stat -c %y "$log_file" | cut -d' ' -f1,2 | cut -d'.' -f1)
            echo "            <tr><td>$operation</td><td>$timestamp</td><td>$log_file</td></tr>" >> "$report_file"
        fi
    done

    cat >> "$report_file" << EOF
        </table>
    </div>
</body>
</html>
EOF

    log "Disaster recovery report generated: $report_file"
    echo "$report_file"
}

# Show usage
show_usage() {
    cat << EOF
Atlas Disaster Recovery Script

Usage: $0 <command> [options]

Commands:
    emergency-backup        Create emergency backup of critical components
    health-assessment       Assess system health and generate report
    emergency-restart       Emergency restart of all Atlas services
    repair-database         Attempt to repair corrupted database
    full-restore <file>     Full system restore from backup
    dr-report              Generate disaster recovery report
    check-prereqs         Check disaster recovery prerequisites

Examples:
    $0 emergency-backup
    $0 health-assessment
    $0 emergency-restart
    $0 repair-database
    $0 full-restore /opt/atlas/backups/atlas_backup_20251016_120000.tar.gz
    $0 dr-report

EOF
}

# Main function
main() {
    local command="${1:-}"

    case $command in
        "check-prereqs")
            check_prerequisites
            ;;
        "emergency-backup")
            check_prerequisites
            create_emergency_backup
            ;;
        "health-assessment")
            check_prerequisites
            assess_system_health
            ;;
        "emergency-restart")
            check_prerequisites
            emergency_restart_services
            ;;
        "repair-database")
            check_prerequisites
            repair_database
            ;;
        "full-restore")
            if [[ -z "${2:-}" ]]; then
                error "Full restore requires backup file path"
                show_usage
                exit 1
            fi
            check_prerequisites
            full_system_restore "$2"
            ;;
        "dr-report")
            check_prerequisites
            generate_dr_report
            ;;
        "help"|"-h"|"--help")
            show_usage
            ;;
        *)
            error "Unknown command: $command"
            show_usage
            exit 1
            ;;
    esac
}

# Run main function
main "$@"