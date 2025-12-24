#!/bin/bash
#
# whisper_local.sh - MacWhisper pipeline using local Mac Mini storage
#
# Flow:
#   1. rsync 10 audio files TO Mac Mini ~/atlas-whisper/audio/
#   2. MacWhisper Pro transcribes locally (fast)
#   3. rsync transcripts BACK to homelab
#   4. Move processed files, repeat
#
# Failure handling:
#   - Files in audio/ for >30 min without .txt → moved to failed/
#   - Failed files get re-added to end of staging after 1 hour
#

set -e

QUEUE="/home/khamel83/github/atlas/data/whisper_queue"
MAC="mac-mini"
MAC_DIR="~/atlas-whisper"

BATCH=10
TIMEOUT_MIN=30
LOG="$QUEUE/local_pipeline.log"

log() { echo "$(date '+%H:%M:%S') - $1" | tee -a "$LOG"; }

mkdir -p "$QUEUE/failed"

# Ensure Mac Mini folders exist
ssh $MAC "mkdir -p $MAC_DIR/{audio,transcripts,done}" 2>/dev/null

# Count current state
mac_audio=$(ssh $MAC "ls $MAC_DIR/audio/*.mp3 2>/dev/null | wc -l" | tr -d ' ')
mac_txt=$(ssh $MAC "ls $MAC_DIR/audio/*.txt 2>/dev/null | wc -l" | tr -d ' ')
staging=$(ls "$QUEUE/staging/"*.mp3 2>/dev/null | wc -l)

log "=== Status: Mac audio=$mac_audio, txt=$mac_txt, staging=$staging ==="

# 1. Pull any completed transcripts back
if [ "$mac_txt" -gt 0 ]; then
    log "Pulling $mac_txt transcripts..."
    scp -q "$MAC:$MAC_DIR/audio/*.txt" "$QUEUE/transcripts/"

    # Delete processed files on Mac (save space)
    ssh $MAC "cd $MAC_DIR/audio && for t in *.txt; do [ -f \"\$t\" ] || continue; b=\"\${t%.txt}\"; rm -f \"\$t\" \"\${b}.mp3\"; done"

    # Import to Atlas
    log "Importing to Atlas..."
    cd /home/khamel83/github/atlas
    ./venv/bin/python scripts/import_whisper_transcripts.py 2>&1 | grep -E "Imported|complete" | tail -3
fi

# 2. Refill Mac if needed
mac_audio=$(ssh $MAC "ls $MAC_DIR/audio/*.mp3 2>/dev/null | wc -l" | tr -d ' ')
if [ "$mac_audio" -lt 3 ] && [ "$staging" -gt 0 ]; then
    need=$((BATCH - mac_audio))
    log "Pushing $need files to Mac..."

    ls "$QUEUE/staging/"*.mp3 2>/dev/null | head -n "$need" | while read f; do
        scp -q "$f" "$MAC:$MAC_DIR/audio/"
        mv "$f" "$QUEUE/audio/"  # Track what we sent
        log "  $(basename "$f")"
    done
fi

# 3. Check for stuck files on Mac (no .txt after TIMEOUT_MIN)
log "Checking for stuck files..."
ssh $MAC "cd $MAC_DIR/audio && for f in *.mp3; do [ -f \"\$f\" ] || continue; t=\"\${f%.mp3}.txt\"; if [ ! -f \"\$t\" ]; then age=\$(( (\$(date +%s) - \$(stat -f %m \"\$f\")) / 60 )); if [ \$age -gt $TIMEOUT_MIN ]; then echo \"STUCK:\$f\"; fi; fi; done" 2>/dev/null | while read line; do
    if [[ "$line" == STUCK:* ]]; then
        file="${line#STUCK:}"
        log "  Stuck file (>${TIMEOUT_MIN}m): $file → failed/"
        scp -q "$MAC:$MAC_DIR/audio/$file" "$QUEUE/failed/"
        ssh $MAC "rm $MAC_DIR/audio/$file"
    fi
done

# 4. Re-queue old failed files (>1 hour old)
find "$QUEUE/failed" -name "*.mp3" -mmin +60 2>/dev/null | while read f; do
    log "  Re-queuing failed: $(basename "$f")"
    mv "$f" "$QUEUE/staging/"
done

# 5. Final status
mac_audio=$(ssh $MAC "ls $MAC_DIR/audio/*.mp3 2>/dev/null | wc -l" | tr -d ' ')
mac_done=$(ssh $MAC "ls $MAC_DIR/done/*.mp3 2>/dev/null | wc -l" | tr -d ' ')
staging=$(ls "$QUEUE/staging/"*.mp3 2>/dev/null | wc -l)
failed=$(ls "$QUEUE/failed/"*.mp3 2>/dev/null | wc -l)

log "=== Done: processing=$mac_audio, done=$mac_done, waiting=$staging, failed=$failed ==="
