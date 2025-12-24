#!/bin/bash
#
# whisper_sweep.sh - Manages MacWhisper Pro transcription queue
#
# Runs on homelab. Maintains ~10 files in audio/ for MacWhisper to process.
# Pulls completed transcripts and imports them to Atlas.
#
# Folder structure (data/whisper_queue/):
#   staging/     - Files waiting to be processed
#   audio/       - Active queue (SMB shared, MacWhisper watches this)
#   transcripts/ - Completed .txt files (cleanup.sh moves them here)
#   done/        - Processed .mp3 files
#

set -e

QUEUE_DIR="/home/khamel83/github/atlas/data/whisper_queue"
STAGING="$QUEUE_DIR/staging"
AUDIO="$QUEUE_DIR/audio"
TRANSCRIPTS="$QUEUE_DIR/transcripts"
DONE="$QUEUE_DIR/done"

BATCH_SIZE=10
MIN_QUEUE=3

LOG="/home/khamel83/github/atlas/data/whisper_queue/sweep.log"

log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "$LOG"
}

# Ensure directories exist
mkdir -p "$STAGING" "$AUDIO" "$TRANSCRIPTS" "$DONE"

# Count files
audio_count=$(ls "$AUDIO"/*.mp3 2>/dev/null | wc -l || echo 0)
transcript_count=$(ls "$TRANSCRIPTS"/*.txt 2>/dev/null | wc -l || echo 0)
staging_count=$(ls "$STAGING"/*.mp3 2>/dev/null | wc -l || echo 0)
done_count=$(ls "$DONE"/*.mp3 2>/dev/null | wc -l || echo 0)

log "Status: audio=$audio_count, transcripts=$transcript_count, staging=$staging_count, done=$done_count"

# 1. Import any completed transcripts
if [ "$transcript_count" -gt 0 ]; then
    log "Importing $transcript_count transcripts..."
    cd /home/khamel83/github/atlas
    ./venv/bin/python scripts/import_whisper_transcripts.py 2>&1 | tail -5 | while read line; do log "  $line"; done
fi

# 2. Refill audio queue if below minimum
if [ "$audio_count" -lt "$MIN_QUEUE" ] && [ "$staging_count" -gt 0 ]; then
    need=$((BATCH_SIZE - audio_count))
    log "Refilling queue: adding $need files"

    ls "$STAGING"/*.mp3 2>/dev/null | head -n "$need" | while read f; do
        mv "$f" "$AUDIO/"
        log "  Added: $(basename "$f")"
    done
fi

# 3. Status summary
audio_count=$(ls "$AUDIO"/*.mp3 2>/dev/null | wc -l || echo 0)
staging_count=$(ls "$STAGING"/*.mp3 2>/dev/null | wc -l || echo 0)
done_count=$(ls "$DONE"/*.mp3 2>/dev/null | wc -l || echo 0)

log "Queue: $audio_count active, $staging_count waiting, $done_count complete"

# 4. Check if we're done
if [ "$staging_count" -eq 0 ] && [ "$audio_count" -eq 0 ]; then
    log "🎉 All files processed! Total done: $done_count"
fi
