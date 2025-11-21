#!/bin/bash

# Atlas Backup Script
# Creates comprehensive backups of Atlas data and configuration

set -euo pipefail

# Configuration
ATLAS_HOME="/opt/atlas"
BACKUP_DIR="/opt/atlas/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_NAME="atlas_backup_${TIMESTAMP}"
RETENTION_DAYS=30

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

warn() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING: $1${NC}"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR: $1${NC}"
    exit 1
}

info() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')] INFO: $1${NC}"
}

# Check if running as root or atlas user
check_permissions() {
    if [[ $EUID -eq 0 ]]; then
        # Running as root, ok
        return
    elif [[ $(id -un) == "atlas" ]]; then
        # Running as atlas user, ok
        return
    else
        error "This script must be run as root or atlas user"
    fi
}

# Create backup directory
create_backup_dir() {
    local backup_path="${BACKUP_DIR}/${BACKUP_NAME}"
    mkdir -p "$backup_path"
    echo "$backup_path"
}

# Backup database
backup_database() {
    local backup_path="$1"
    log "Backing up database..."

    local db_path="${ATLAS_HOME}/data/atlas.db"
    if [[ -f "$db_path" ]]; then
        # Use sqlite3 backup command for consistency
        sqlite3 "$db_path" ".backup ${backup_path}/atlas.db"
        log "Database backup completed"
    else
        warn "Database file not found: $db_path"
    fi
}

# Backup configuration
backup_config() {
    local backup_path="$1"
    log "Backing up configuration..."

    mkdir -p "${backup_path}/config"

    # Copy all config files
    if [[ -d "${ATLAS_HOME}/config" ]]; then
        cp -r "${ATLAS_HOME}/config/"* "${backup_path}/config/"
        log "Configuration backup completed"
    else
        warn "Configuration directory not found"
    fi

    # Backup environment file
    if [[ -f "${ATLAS_HOME}/.env" ]]; then
        cp "${ATLAS_HOME}/.env" "${backup_path}/.env"
        log "Environment file backup completed"
    fi
}

# Backup vault data
backup_vault() {
    local backup_path="$1"
    log "Backing up vault data..."

    if [[ -d "${ATLAS_HOME}/vault" ]]; then
        # Create tar.gz archive of vault
        tar -czf "${backup_path}/vault.tar.gz" -C "${ATLAS_HOME}" vault/
        log "Vault backup completed"
    else
        warn "Vault directory not found"
    fi
}

# Backup logs
backup_logs() {
    local backup_path="$1"
    log "Backing up recent logs..."

    if [[ -d "${ATLAS_HOME}/logs" ]]; then
        mkdir -p "${backup_path}/logs"
        # Only backup last 7 days of logs to save space
        find "${ATLAS_HOME}/logs" -name "*.log" -mtime -7 -exec cp {} "${backup_path}/logs/" \;
        log "Logs backup completed"
    else
        warn "Logs directory not found"
    fi
}

# Backup monitoring data
backup_monitoring() {
    local backup_path="$1"
    log "Backing up monitoring data..."

    if [[ -d "${ATLAS_HOME}/monitoring" ]]; then
        mkdir -p "${backup_path}/monitoring"
        cp -r "${ATLAS_HOME}/monitoring/"* "${backup_path}/monitoring/"
        log "Monitoring data backup completed"
    else
        warn "Monitoring directory not found"
    fi
}

# Create backup metadata
create_metadata() {
    local backup_path="$1"
    log "Creating backup metadata..."

    cat > "${backup_path}/metadata.json" << EOF
{
    "backup_name": "${BACKUP_NAME}",
    "timestamp": "$(date -Iseconds)",
    "atlas_version": "4.0",
    "hostname": "$(hostname)",
    "user": "$(id -un)",
    "backup_type": "full",
    "includes": {
        "database": true,
        "config": true,
        "vault": true,
        "logs": true,
        "monitoring": true
    },
    "sizes": {
        "database": "$(du -h "${backup_path}/atlas.db" 2>/dev/null | cut -f1 || echo "0B")",
        "config": "$(du -sh "${backup_path}/config" 2>/dev/null | cut -f1 || echo "0B")",
        "vault": "$(du -h "${backup_path}/vault.tar.gz" 2>/dev/null | cut -f1 || echo "0B")",
        "logs": "$(du -sh "${backup_path}/logs" 2>/dev/null | cut -f1 || echo "0B")",
        "monitoring": "$(du -sh "${backup_path}/monitoring" 2>/dev/null | cut -f1 || echo "0B")"
    }
}
EOF
}

# Verify backup integrity
verify_backup() {
    local backup_path="$1"
    log "Verifying backup integrity..."

    local verification_failed=false

    # Check if essential files exist
    if [[ ! -f "${backup_path}/atlas.db" ]]; then
        warn "Database backup missing or corrupted"
        verification_failed=true
    fi

    if [[ ! -f "${backup_path}/metadata.json" ]]; then
        error "Metadata file missing"
        verification_failed=true
    fi

    # Verify database integrity
    if [[ -f "${backup_path}/atlas.db" ]]; then
        if ! sqlite3 "${backup_path}/atlas.db" "PRAGMA integrity_check;" >/dev/null 2>&1; then
            error "Database integrity check failed"
            verification_failed=true
        fi
    fi

    if [[ "$verification_failed" == true ]]; then
        error "Backup verification failed"
    fi

    log "Backup verification completed successfully"
}

# Compress backup
compress_backup() {
    local backup_path="$1"
    log "Compressing backup..."

    # Create compressed archive
    tar -czf "${backup_path}.tar.gz" -C "$(dirname "$backup_path")" "$(basename "$backup_path")"

    # Remove uncompressed backup directory
    rm -rf "$backup_path"

    # Update backup path to compressed file
    echo "${backup_path}.tar.gz"
}

# Cleanup old backups
cleanup_old_backups() {
    log "Cleaning up old backups (retaining ${RETENTION_DAYS} days)..."

    if [[ -d "$BACKUP_DIR" ]]; then
        # Remove backups older than retention period
        find "$BACKUP_DIR" -name "atlas_backup_*.tar.gz" -mtime +$RETENTION_DAYS -delete
        log "Old backups cleanup completed"
    else
        warn "Backup directory not found"
    fi
}

# Send notification (optional)
send_notification() {
    local backup_path="$1"
    local status="$2"

    # Check if notification script exists
    local notify_script="${ATLAS_HOME}/scripts/notify.sh"
    if [[ -x "$notify_script" ]]; then
        "$notify_script" "Atlas Backup" "Backup ${status}: $(basename "$backup_path")"
    fi
}

# List available backups
list_backups() {
    info "Available backups:"

    if [[ -d "$BACKUP_DIR" ]]; then
        find "$BACKUP_DIR" -name "atlas_backup_*.tar.gz" -exec ls -lh {} \; | sort -k9
    else
        warn "No backups directory found"
    fi
}

# Restore from backup
restore_backup() {
    local backup_file="$1"

    if [[ ! -f "$backup_file" ]]; then
        error "Backup file not found: $backup_file"
    fi

    log "Restoring from backup: $(basename "$backup_file")"

    # Extract backup
    local temp_dir="/tmp/atlas_restore_$$"
    mkdir -p "$temp_dir"
    tar -xzf "$backup_file" -C "$temp_dir"

    # Find backup directory
    local backup_dir=$(find "$temp_dir" -name "atlas_backup_*" -type d | head -1)

    if [[ -z "$backup_dir" ]]; then
        error "Invalid backup file format"
    fi

    # Stop Atlas services
    log "Stopping Atlas services..."
    if command -v systemctl &>/dev/null; then
        systemctl stop atlas-ingest atlas-bot atlas-monitor || true
    fi

    # Backup current state before restore
    log "Creating pre-restore backup..."
    local pre_restore_backup="${BACKUP_DIR}/pre_restore_$(date +%Y%m%d_%H%M%S)"
    mkdir -p "$pre_restore_backup"

    if [[ -f "${ATLAS_HOME}/data/atlas.db" ]]; then
        cp "${ATLAS_HOME}/data/atlas.db" "$pre_restore_backup/"
    fi

    if [[ -d "${ATLAS_HOME}/config" ]]; then
        cp -r "${ATLAS_HOME}/config" "$pre_restore_backup/"
    fi

    # Restore database
    if [[ -f "${backup_dir}/atlas.db" ]]; then
        cp "${backup_dir}/atlas.db" "${ATLAS_HOME}/data/"
        chown atlas:atlas "${ATLAS_HOME}/data/atlas.db"
        log "Database restored"
    fi

    # Restore configuration
    if [[ -d "${backup_dir}/config" ]]; then
        cp -r "${backup_dir}/config/"* "${ATLAS_HOME}/config/"
        chown -R atlas:atlas "${ATLAS_HOME}/config"
        log "Configuration restored"
    fi

    # Restore environment file
    if [[ -f "${backup_dir}/.env" ]]; then
        cp "${backup_dir}/.env" "${ATLAS_HOME}/"
        chown atlas:atlas "${ATLAS_HOME}/.env"
        chmod 600 "${ATLAS_HOME}/.env"
        log "Environment file restored"
    fi

    # Restore vault (optional - requires confirmation)
    if [[ -f "${backup_dir}/vault.tar.gz" ]]; then
        warn "Vault restore skipped for safety. Manual restore required:"
        echo "  tar -xzf ${backup_dir}/vault.tar.gz -C ${ATLAS_HOME}/"
    fi

    # Cleanup
    rm -rf "$temp_dir"

    # Start services
    log "Starting Atlas services..."
    if command -v systemctl &>/dev/null; then
        systemctl start atlas-ingest atlas-bot atlas-monitor
    fi

    log "Restore completed successfully"
    log "Pre-restore backup saved to: $pre_restore_backup"
}

# Main backup function
create_backup() {
    log "Starting Atlas backup..."

    check_permissions

    local backup_path
    backup_path=$(create_backup_dir)

    backup_database "$backup_path"
    backup_config "$backup_path"
    backup_vault "$backup_path"
    backup_logs "$backup_path"
    backup_monitoring "$backup_path"
    create_metadata "$backup_path"
    verify_backup "$backup_path"

    local compressed_path
    compressed_path=$(compress_backup "$backup_path")

    cleanup_old_backups
    send_notification "$compressed_path" "completed"

    local backup_size=$(du -h "$compressed_path" | cut -f1)
    log "Backup completed successfully: $(basename "$compressed_path") ($backup_size)"

    echo "$compressed_path"
}

# Show usage
show_usage() {
    cat << EOF
Atlas Backup Script

Usage: $0 [OPTIONS]

Commands:
    backup              Create a full backup (default)
    restore <file>      Restore from backup file
    list                List available backups
    cleanup             Clean up old backups

Options:
    -h, --help          Show this help message
    -r, --retention N   Set retention days (default: 30)

Examples:
    $0 backup                          # Create backup
    $0 restore /path/to/backup.tar.gz  # Restore from backup
    $0 list                            # List backups
    $0 cleanup                         # Clean old backups
    $0 --retention 7 backup            # Create backup with 7-day retention

EOF
}

# Parse command line arguments
main() {
    local command="backup"
    local backup_file=""

    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                show_usage
                exit 0
                ;;
            -r|--retention)
                RETENTION_DAYS="$2"
                shift 2
                ;;
            backup)
                command="backup"
                shift
                ;;
            restore)
                command="restore"
                backup_file="$2"
                shift 2
                ;;
            list)
                command="list"
                shift
                ;;
            cleanup)
                command="cleanup"
                shift
                ;;
            *)
                error "Unknown option: $1. Use -h for help."
                ;;
        esac
    done

    # Execute command
    case $command in
        backup)
            create_backup
            ;;
        restore)
            if [[ -z "$backup_file" ]]; then
                error "Restore requires backup file path"
            fi
            restore_backup "$backup_file"
            ;;
        list)
            list_backups
            ;;
        cleanup)
            cleanup_old_backups
            ;;
        *)
            error "Unknown command: $command"
            ;;
    esac
}

# Run main function with all arguments
main "$@"