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
