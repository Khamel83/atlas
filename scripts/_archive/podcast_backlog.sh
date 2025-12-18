#!/bin/bash
# Atlas Podcast Backlog Processor
#
# This script processes the podcast transcript backlog to 100% coverage.
# It handles both Podscripts (89% of episodes) and YouTube (11% of episodes).
#
# For YouTube, it can rotate NordVPN IPs when blocked.
#
# Usage:
#   ./scripts/podcast_backlog.sh              # Full run (Podscripts + YouTube retry)
#   ./scripts/podcast_backlog.sh --status     # Just show status
#   ./scripts/podcast_backlog.sh --youtube    # Only retry YouTube failures

set -e

ATLAS_DIR="/home/khamel83/github/atlas"
LOG_DIR="/var/log/atlas"
VENV="$ATLAS_DIR/venv/bin/python"
CLI="$VENV -m modules.podcasts.cli"

# NordVPN proxy (on Tailscale network)
PROXY_HOST="100.112.130.100"
PROXY_PORT="8118"
export YOUTUBE_PROXY_URL="http://${PROXY_HOST}:${PROXY_PORT}"
export YOUTUBE_RATE_LIMIT_SECONDS=30
export PODSCRIPTS_RATE_LIMIT_SECONDS=4

cd "$ATLAS_DIR"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log() {
    echo -e "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

show_status() {
    $CLI status
}

check_proxy() {
    if curl -s --proxy "http://${PROXY_HOST}:${PROXY_PORT}" --max-time 5 https://www.youtube.com > /dev/null 2>&1; then
        echo -e "${GREEN}Proxy OK${NC}"
        return 0
    else
        echo -e "${RED}Proxy unavailable${NC}"
        return 1
    fi
}

rotate_nordvpn() {
    log "${YELLOW}Rotating NordVPN IP...${NC}"
    # SSH to the proxy host and rotate (assumes SSH key auth)
    if ssh -o ConnectTimeout=5 khamel83@${PROXY_HOST} "nordvpn disconnect && sleep 2 && nordvpn connect us" 2>/dev/null; then
        log "${GREEN}NordVPN rotated successfully${NC}"
        sleep 5  # Wait for connection to stabilize
        return 0
    else
        log "${RED}Failed to rotate NordVPN (SSH may not be configured)${NC}"
        return 1
    fi
}

process_backlog() {
    log "Starting backlog processing..."
    log "Proxy: $YOUTUBE_PROXY_URL"
    log "Rate limit: ${YOUTUBE_RATE_LIMIT_SECONDS}s between YouTube requests"

    # Run the fetch - Podscripts/NPR will succeed, YouTube may fail
    $CLI fetch-transcripts --all 2>&1 | tee -a "$LOG_DIR/backlog-$(date +%Y%m%d).log"

    log "Backlog processing complete"
}

retry_youtube() {
    log "Retrying YouTube-only failures..."

    # Check proxy first
    if ! check_proxy; then
        log "Proxy not available, attempting rotation..."
        rotate_nordvpn || true
    fi

    # Retry failed episodes (will try YouTube again)
    $CLI fetch-transcripts --all --status failed 2>&1 | tee -a "$LOG_DIR/youtube-retry-$(date +%Y%m%d).log"
}

# Main
case "${1:-}" in
    --status)
        show_status
        ;;
    --youtube)
        retry_youtube
        ;;
    --rotate)
        rotate_nordvpn
        ;;
    --check-proxy)
        check_proxy
        ;;
    *)
        log "═══════════════════════════════════════════════════════════"
        log "ATLAS PODCAST BACKLOG PROCESSOR"
        log "═══════════════════════════════════════════════════════════"
        echo
        show_status
        echo
        log "Phase 1: Processing all podcasts (Podscripts + NPR + YouTube)"
        process_backlog
        echo
        log "Phase 1 complete. Checking status..."
        show_status
        echo
        # If there are still failures, try rotating and retrying
        FAILED=$($VENV -c "
import sqlite3
conn = sqlite3.connect('data/podcasts/atlas_podcasts.db')
print(conn.execute('SELECT COUNT(*) FROM episodes WHERE transcript_status = \"failed\"').fetchone()[0])
")
        if [ "$FAILED" -gt 0 ]; then
            log "Phase 2: Retrying $FAILED failed episodes with fresh proxy..."
            rotate_nordvpn || log "Could not rotate, continuing anyway..."
            retry_youtube
        fi
        echo
        log "═══════════════════════════════════════════════════════════"
        log "FINAL STATUS"
        log "═══════════════════════════════════════════════════════════"
        show_status
        ;;
esac
