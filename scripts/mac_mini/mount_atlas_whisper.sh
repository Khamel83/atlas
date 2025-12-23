#!/bin/bash
#
# Ensure atlas-whisper SMB share is mounted
# Run this at login or periodically to keep mount alive
#

MOUNT_POINT="/Volumes/atlas-whisper"
SMB_URL="smb://khamel83@HOMELAB._smb._tcp.local/atlas-whisper"
LOG_FILE="$HOME/logs/mount_atlas.log"

log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" >> "$LOG_FILE"
}

# Check if already mounted and accessible
if mount | grep -q "atlas-whisper" && ls "$MOUNT_POINT/audio" >/dev/null 2>&1; then
    log "Mount OK - accessible"
    exit 0
fi

log "Mount not available, attempting to mount..."

# Clean up stale mount point
if [ -d "$MOUNT_POINT" ]; then
    log "Removing stale mount point"
    diskutil unmount force "$MOUNT_POINT" 2>/dev/null || true
    rmdir "$MOUNT_POINT" 2>/dev/null || true
fi

# Mount via Finder (uses saved Keychain credentials)
open "$SMB_URL"

# Wait for mount to appear
for i in {1..30}; do
    if mount | grep -q "atlas-whisper" && ls "$MOUNT_POINT/audio" >/dev/null 2>&1; then
        log "Mount successful after ${i}s"
        exit 0
    fi
    sleep 1
done

log "ERROR: Mount failed after 30s"
exit 1
