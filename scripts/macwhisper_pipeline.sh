#!/bin/bash
#
# MacWhisper Pipeline - Push audio to Mac Mini, pull transcripts back
# Mac Mini runs MacWhisper Pro with folder watch
#

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ATLAS_DIR="$(dirname "$SCRIPT_DIR")"
QUEUE_DIR="$ATLAS_DIR/data/whisper_queue"
AUDIO_DIR="$QUEUE_DIR/audio"
TRANSCRIPT_DIR="$QUEUE_DIR/transcripts"

MAC_HOST="mac-mini"
MAC_QUEUE="~/atlas-whisper"

BATCH_SIZE="${BATCH_SIZE:-20}"
LOG_FILE="$QUEUE_DIR/macwhisper_pipeline.log"

log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "$LOG_FILE"
}

# Get audio files that don't have transcripts yet
get_pending_files() {
    for audio in "$AUDIO_DIR"/*.mp3; do
        [ -f "$audio" ] || continue
        base=$(basename "$audio" .mp3)
        # Check if transcript exists locally
        if [ ! -f "$TRANSCRIPT_DIR/${base}.txt" ] && [ ! -f "$TRANSCRIPT_DIR/${base}.json" ]; then
            echo "$audio"
        fi
    done
}

push_audio() {
    log "=== Pushing audio to Mac Mini ==="

    pending=$(get_pending_files | wc -l)
    log "Pending audio files: $pending"

    if [ "$pending" -eq 0 ]; then
        log "No pending files to push"
        return 0
    fi

    # Get batch
    files=$(get_pending_files | head -n "$BATCH_SIZE")
    count=$(echo "$files" | grep -c . || echo 0)
    log "Pushing batch of $count files"

    echo "$files" | while read -r file; do
        [ -f "$file" ] || continue
        name=$(basename "$file")
        # Check if already on Mac Mini
        if ! ssh "$MAC_HOST" "[ -f $MAC_QUEUE/audio/$name ] || [ -f $MAC_QUEUE/done/$name ]" 2>/dev/null; then
            log "  Pushing: $name"
            scp -q "$file" "$MAC_HOST:$MAC_QUEUE/audio/"
        else
            log "  Skip (exists): $name"
        fi
    done

    log "Push complete"
}

pull_transcripts() {
    log "=== Pulling transcripts from Mac Mini ==="

    # Pull any .txt files from transcripts folder
    count=$(ssh "$MAC_HOST" "ls $MAC_QUEUE/transcripts/*.txt 2>/dev/null | wc -l" | tr -d ' ')

    if [ "$count" -eq 0 ]; then
        log "No new transcripts to pull"
        return 0
    fi

    log "Pulling $count transcripts"
    scp -q "$MAC_HOST:$MAC_QUEUE/transcripts/*.txt" "$TRANSCRIPT_DIR/" 2>/dev/null || true

    # Clear pulled transcripts from Mac Mini
    ssh "$MAC_HOST" "rm -f $MAC_QUEUE/transcripts/*.txt" 2>/dev/null || true

    log "Pull complete"
}

import_transcripts() {
    log "=== Importing transcripts to Atlas ==="
    cd "$ATLAS_DIR"
    ./venv/bin/python scripts/import_whisper_transcripts.py 2>&1 | tail -10
}

status() {
    local_pending=$(get_pending_files | wc -l)
    mac_audio=$(ssh "$MAC_HOST" "ls $MAC_QUEUE/audio/*.mp3 2>/dev/null | wc -l" | tr -d ' ')
    mac_transcripts=$(ssh "$MAC_HOST" "ls $MAC_QUEUE/transcripts/*.txt 2>/dev/null | wc -l" | tr -d ' ')
    mac_done=$(ssh "$MAC_HOST" "ls $MAC_QUEUE/done/*.mp3 2>/dev/null | wc -l" | tr -d ' ')

    echo "=== MacWhisper Pipeline Status ==="
    echo "Local pending:     $local_pending"
    echo "Mac processing:    $mac_audio"
    echo "Mac ready:         $mac_transcripts"
    echo "Mac done:          $mac_done"
}

case "${1:-run}" in
    push)
        push_audio
        ;;
    pull)
        pull_transcripts
        ;;
    import)
        import_transcripts
        ;;
    status)
        status
        ;;
    run|*)
        push_audio
        pull_transcripts
        import_transcripts
        status
        ;;
esac
