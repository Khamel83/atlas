#!/bin/bash

# Atlas Systemd Services Deployment Script
# Part of Atlas Reliability Closeout - Task 1: Systemd Services

set -euo pipefail

# Configuration
ATLAS_DIR="/home/ubuntu/dev/atlas"
SERVICE_DIR="/etc/systemd/system"
LOG_DIR="/var/log/atlas"
BACKUP_DIR="/home/ubuntu/dev/atlas/backups"
DATA_DIR="/home/ubuntu/dev/atlas/data"
USER="ubuntu"
GROUP="ubuntu"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')] $1${NC}"
}

warn() {
    echo -e "${YELLOW}[$(date '+%Y-%m-%d %H:%M:%S')] WARNING: $1${NC}"
}

error() {
    echo -e "${RED}[$(date '+%Y-%m-%d %H:%M:%S')] ERROR: $1${NC}"
    exit 1
}

# Check if running as root
if [[ $EUID -ne 0 ]]; then
   error "This script must be run as root. Use sudo."
fi

# Function to create directories
setup_directories() {
    log "Creating necessary directories..."

    mkdir -p "$LOG_DIR" || error "Failed to create log directory"
    chown "$USER:$GROUP" "$LOG_DIR" || error "Failed to set log directory ownership"
    chmod 755 "$LOG_DIR" || error "Failed to set log directory permissions"

    mkdir -p "$BACKUP_DIR" || error "Failed to create backup directory"
    chown "$USER:$GROUP" "$BACKUP_DIR" || error "Failed to set backup directory ownership"
    chmod 755 "$BACKUP_DIR" || error "Failed to set backup directory permissions"

    mkdir -p "$DATA_DIR" || error "Failed to create data directory"
    chown "$USER:$GROUP" "$DATA_DIR" || error "Failed to set data directory ownership"
    chmod 755 "$DATA_DIR" || error "Failed to set data directory permissions"

    log "Directories created successfully"
}

# Function to install services
install_services() {
    log "Installing systemd services..."

    # Service files to install
    services=(
        "atlas-api.service"
        "atlas-worker.service"
        "atlas-scheduler.service"
        "atlas-backup.service"
        "atlas-scheduler.timer"
        "atlas-backup.timer"
    )

    for service in "${services[@]}"; do
        src_file="$ATLAS_DIR/systemd/$service"
        dest_file="$SERVICE_DIR/$service"

        if [[ ! -f "$src_file" ]]; then
            error "Service file not found: $src_file"
        fi

        log "Installing $service..."
        cp "$src_file" "$dest_file" || error "Failed to copy $service"
        chown root:root "$dest_file" || error "Failed to set ownership for $service"
        chmod 644 "$dest_file" || error "Failed to set permissions for $service"

        log "Installed $service"
    done

    log "All services installed successfully"
}

# Function to reload systemd
reload_systemd() {
    log "Reloading systemd daemon..."
    systemctl daemon-reload || error "Failed to reload systemd daemon"
    log "Systemd daemon reloaded"
}

# Function to enable and start services
start_services() {
    log "Enabling and starting Atlas services..."

    # Enable timer units
    systemctl enable atlas-scheduler.timer || error "Failed to enable scheduler timer"
    systemctl enable atlas-backup.timer || error "Failed to enable backup timer"

    # Enable services
    systemctl enable atlas-api.service || error "Failed to enable API service"
    systemctl enable atlas-worker.service || error "Failed to enable worker service"
    systemctl enable atlas-scheduler.service || error "Failed to enable scheduler service"
    systemctl enable atlas-backup.service || error "Failed to enable backup service"

    # Start services
    systemctl start atlas-api.service || error "Failed to start API service"
    systemctl start atlas-worker.service || error "Failed to start worker service"
    systemctl start atlas-scheduler.timer || error "Failed to start scheduler timer"
    systemctl start atlas-backup.timer || error "Failed to start backup timer"

    log "All services enabled and started"
}

# Function to verify services
verify_services() {
    log "Verifying service status..."

    services=(
        "atlas-api.service"
        "atlas-worker.service"
        "atlas-scheduler.timer"
        "atlas-backup.timer"
    )

    all_healthy=true

    for service in "${services[@]}"; do
        if systemctl is-active --quiet "$service"; then
            log "✅ $service is active"
        else
            warn "❌ $service is not active"
            all_healthy=false
        fi

        if systemctl is-enabled --quiet "$service"; then
            log "✅ $service is enabled"
        else
            warn "❌ $service is not enabled"
            all_healthy=false
        fi
    done

    if [[ "$all_healthy" == "true" ]]; then
        log "All services are healthy and enabled"
    else
        warn "Some services are not healthy or enabled"
    fi
}

# Function to show service status
show_status() {
    log "Current service status:"
    echo ""
    systemctl status atlas-api.service atlas-worker.service atlas-scheduler.timer atlas-backup.timer --no-pager
    echo ""
}

# Main deployment function
deploy() {
    log "Starting Atlas systemd services deployment..."
    log "Atlas directory: $ATLAS_DIR"
    log "Service directory: $SERVICE_DIR"

    setup_directories
    install_services
    reload_systemd
    start_services
    verify_services
    show_status

    log "Deployment completed successfully!"
    log ""
    log "Next steps:"
    log "1. Check service logs: journalctl -u atlas-api.service -f"
    log "2. Verify API health: curl http://localhost:7444/health"
    log "3. Monitor worker: systemctl status atlas-worker.service"
    log "4. Check timers: systemctl list-timers atlas-*"
}

# Function to uninstall services
uninstall() {
    log "Uninstalling Atlas systemd services..."

    # Stop and disable services
    systemctl stop atlas-api.service 2>/dev/null || true
    systemctl stop atlas-worker.service 2>/dev/null || true
    systemctl stop atlas-scheduler.timer 2>/dev/null || true
    systemctl stop atlas-backup.timer 2>/dev/null || true

    systemctl disable atlas-api.service 2>/dev/null || true
    systemctl disable atlas-worker.service 2>/dev/null || true
    systemctl disable atlas-scheduler.service 2>/dev/null || true
    systemctl disable atlas-backup.service 2>/dev/null || true
    systemctl disable atlas-scheduler.timer 2>/dev/null || true
    systemctl disable atlas-backup.timer 2>/dev/null || true

    # Remove service files
    rm -f "$SERVICE_DIR"/atlas-*.service
    rm -f "$SERVICE_DIR"/atlas-*.timer

    # Reload systemd
    systemctl daemon-reload

    log "Atlas services uninstalled"
}

# Parse command line arguments
case "${1:-deploy}" in
    deploy)
        deploy
        ;;
    uninstall)
        uninstall
        ;;
    status)
        show_status
        ;;
    verify)
        verify_services
        ;;
    *)
        echo "Usage: $0 {deploy|uninstall|status|verify}"
        exit 1
        ;;
esac