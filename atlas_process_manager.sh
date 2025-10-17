#!/bin/bash
# ATLAS PROCESS MANAGER - SYSTEMD BASED, BULLETPROOF
# Single script that manages all Atlas services with systemd integration

ATLAS_DIR="/home/ubuntu/dev/atlas"
LOG_DIR="$ATLAS_DIR/logs"
SYSTEMD_DIR="/etc/systemd/system"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log() {
    echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1"
}

warn() {
    echo -e "${YELLOW}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1"
}

error() {
    echo -e "${RED}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1"
}

# Ensure directories exist
setup_directories() {
    mkdir -p "$LOG_DIR"
    mkdir -p "$ATLAS_DIR/data"
    chmod +x "$ATLAS_DIR"/*.py
    chmod +x "$ATLAS_DIR"/*.sh
}

# Create systemd service files
create_systemd_services() {
    log "Creating systemd service files..."

    # Atlas Manager Service
    cat > "$SYSTEMD_DIR/atlas-manager.service" << 'EOF'
[Unit]
Description=Atlas Manager - Podcast Processing Engine
After=network.target
Wants=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/dev/atlas
ExecStart=/usr/bin/python3 /home/ubuntu/dev/atlas/atlas_manager.py
Restart=always
RestartSec=10
StandardOutput=file:/home/ubuntu/dev/atlas/logs/atlas_output.log
StandardError=file:/home/ubuntu/dev/atlas/logs/atlas_error.log
TimeoutStopSec=30
KillSignal=SIGTERM
KillMode=mixed
Environment=PYTHONPATH=/home/ubuntu/dev/atlas

[Install]
WantedBy=multi-user.target
EOF

    # Atlas Monitor Service
    cat > "$SYSTEMD_DIR/atlas-monitor.service" << 'EOF'
[Unit]
Description=Atlas Monitor - Health Monitoring Service
After=network.target atlas-manager.service
Requires=atlas-manager.service

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/dev/atlas
ExecStart=/usr/bin/python3 /home/ubuntu/dev/atlas/monitoring_service.py
Restart=always
RestartSec=10
StandardOutput=file:/home/ubuntu/dev/atlas/logs/monitoring_output.log
StandardError=file:/home/ubuntu/dev/atlas/logs/monitoring_error.log
TimeoutStopSec=30
KillSignal=SIGTERM
KillMode=mixed
Environment=PYTHONPATH=/home/ubuntu/dev/atlas

[Install]
WantedBy=multi-user.target
EOF

    # Atlas Guardian Service (main supervisor)
    cat > "$SYSTEMD_DIR/atlas-guardian.service" << 'EOF'
[Unit]
Description=Atlas Guardian - Process Supervisor
After=network.target atlas-manager.service atlas-monitor.service

[Service]
Type=simple
User=root
WorkingDirectory=/home/ubuntu/dev/atlas
ExecStart=/home/ubuntu/dev/atlas/atlas_guardian.sh
Restart=always
RestartSec=30
StandardOutput=file:/home/ubuntu/dev/atlas/logs/guardian_output.log
StandardError=file:/home/ubuntu/dev/atlas/logs/guardian_error.log

[Install]
WantedBy=multi-user.target
EOF

    log "Systemd services created"
}

# Create guardian script
create_guardian() {
    cat > "$ATLAS_DIR/atlas_guardian.sh" << 'EOF'
#!/bin/bash
# Atlas Guardian - Simple, robust process supervisor

ATLAS_DIR="/home/ubuntu/dev/atlas"
LOG_FILE="$ATLAS_DIR/logs/guardian.log"

log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "$LOG_FILE"
}

check_health() {
    # Check if all required services are running
    if systemctl is-active --quiet atlas-manager.service; then
        log "Atlas Manager: RUNNING"
    else
        log "Atlas Manager: DOWN - restarting..."
        systemctl restart atlas-manager.service
        sleep 5
    fi

    if systemctl is-active --quiet atlas-monitor.service; then
        log "Atlas Monitor: RUNNING"
    else
        log "Atlas Monitor: DOWN - restarting..."
        systemctl restart atlas-monitor.service
        sleep 5
    fi

    # Check processing activity
    if [ -f "$ATLAS_DIR/data/atlas.db" ]; then
        PENDING=$(sqlite3 "$ATLAS_DIR/data/atlas.db" "SELECT COUNT(*) FROM episode_queue WHERE status = 'pending'")
        log "Queue Status: $PENDING episodes pending"
    fi
}

# Main loop
while true; do
    check_health
    sleep 60  # Check every minute
done
EOF

    chmod +x "$ATLAS_DIR/atlas_guardian.sh"
    log "Guardian script created"
}

# Install and enable services
install_services() {
    log "Installing and enabling systemd services..."

    systemctl daemon-reload
    systemctl enable atlas-manager.service
    systemctl enable atlas-monitor.service
    systemctl enable atlas-guardian.service

    log "Services installed and enabled"
}

# Start all services
start_services() {
    log "Starting all Atlas services..."

    systemctl start atlas-manager.service
    sleep 5
    systemctl start atlas-monitor.service
    sleep 5
    systemctl start atlas-guardian.service

    log "All services started"
}

# Status check
check_status() {
    echo "=== Atlas Service Status ==="
    echo "Atlas Manager: $(systemctl is-active atlas-manager.service)"
    echo "Atlas Monitor: $(systemctl is-active atlas-monitor.service)"
    echo "Atlas Guardian: $(systemctl is-active atlas-guardian.service)"

    if systemctl is-active --quiet atlas-guardian.service; then
        echo ""
        echo "Recent Guardian Activity:"
        tail -10 "$LOG_DIR/guardian.log"
    fi
}

# Stop all services
stop_services() {
    log "Stopping all Atlas services..."

    systemctl stop atlas-guardian.service
    systemctl stop atlas-monitor.service
    systemctl stop atlas-manager.service

    log "All services stopped"
}

# Restart all services
restart_services() {
    stop_services
    sleep 5
    start_services
}

# Show logs
show_logs() {
    case "$1" in
        manager)
            tail -f "$LOG_DIR/atlas_output.log"
            ;;
        monitor)
            tail -f "$LOG_DIR/monitoring_output.log"
            ;;
        guardian)
            tail -f "$LOG_DIR/guardian_output.log"
            ;;
        *)
            echo "Usage: $0 logs [manager|monitor|guardian]"
            ;;
    esac
}

# Main script logic
case "$1" in
    setup)
        setup_directories
        create_systemd_services
        create_guardian
        install_services
        log "Atlas process management setup complete"
        ;;
    start)
        start_services
        ;;
    stop)
        stop_services
        ;;
    restart)
        restart_services
        ;;
    status)
        check_status
        ;;
    logs)
        show_logs "$2"
        ;;
    health)
        if systemctl is-active --quiet atlas-guardian.service; then
            echo "🟢 Atlas is healthy and monitored"
        else
            echo "🔴 Atlas needs attention"
            systemctl status atlas-guardian.service
        fi
        ;;
    *)
        echo "Atlas Process Manager v1.0"
        echo ""
        echo "Usage: $0 {setup|start|stop|restart|status|health|logs}"
        echo ""
        echo "  setup    - Install systemd services and guardian"
        echo "  start    - Start all Atlas services"
        echo "  stop     - Stop all Atlas services"
        echo "  restart  - Restart all Atlas services"
        echo "  status   - Check service status"
        echo "  health   - Quick health check"
        echo "  logs     - View service logs"
        echo ""
        echo "After setup, services will auto-start on boot and auto-restart on failure"
        exit 1
        ;;
esac