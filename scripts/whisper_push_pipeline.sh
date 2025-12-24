#!/bin/bash
#
# WhisperX Push Pipeline - Pushes audio to Mac Mini, processes, pulls transcripts back
# Works around one-way Tailscale connectivity (homelab → mac-mini only)
#

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ATLAS_DIR="$(dirname "$SCRIPT_DIR")"
QUEUE_DIR="$ATLAS_DIR/data/whisper_queue"
AUDIO_DIR="$QUEUE_DIR/audio"
TRANSCRIPT_DIR="$QUEUE_DIR/transcripts"

MAC_HOST="mac-mini"
MAC_AUDIO="~/whisper_queue/audio"
MAC_TRANSCRIPTS="~/whisper_queue/transcripts"

BATCH_SIZE="${BATCH_SIZE:-5}"
LOG_FILE="$QUEUE_DIR/push_pipeline.log"

log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "$LOG_FILE"
}

# Get list of unprocessed audio files
get_pending_files() {
    # Get files that don't have corresponding transcripts
    for audio in "$AUDIO_DIR"/*.mp3; do
        [ -f "$audio" ] || continue
        base=$(basename "$audio" .mp3)
        if [ ! -f "$TRANSCRIPT_DIR/${base}.json" ]; then
            echo "$audio"
        fi
    done
}

# Main pipeline
main() {
    log "=== WhisperX Push Pipeline Starting ==="

    # Count pending
    pending=$(get_pending_files | wc -l)
    log "Pending audio files: $pending"

    if [ "$pending" -eq 0 ]; then
        log "No pending files to process"
        exit 0
    fi

    # Get batch of files
    files=$(get_pending_files | head -n "$BATCH_SIZE")
    count=$(echo "$files" | wc -l)
    log "Processing batch of $count files"

    # Clear Mac Mini queue
    log "Clearing Mac Mini audio queue..."
    ssh "$MAC_HOST" "rm -f $MAC_AUDIO/*.mp3" 2>/dev/null || true

    # Push audio files
    log "Pushing audio files to Mac Mini..."
    echo "$files" | while read -r file; do
        [ -f "$file" ] || continue
        log "  Copying: $(basename "$file")"
        scp -q "$file" "$MAC_HOST:$MAC_AUDIO/"
    done

    # Process on Mac Mini (medium model, no diarization - fast)
    log "Running WhisperX on Mac Mini (medium model)..."
    ssh "$MAC_HOST" "export PATH=/opt/homebrew/bin:\$PATH && source ~/whisperx-env/bin/activate && cd ~/whisper_queue && for f in audio/*.mp3; do [ -f \"\$f\" ] || continue; echo \"Processing: \$f\"; whisperx \"\$f\" --model medium --language en --compute_type int8 --output_dir transcripts/ --output_format json 2>&1 | tail -5; done"

    # Pull transcripts back
    log "Pulling transcripts from Mac Mini..."
    scp -q "$MAC_HOST:$MAC_TRANSCRIPTS/*.json" "$TRANSCRIPT_DIR/" 2>/dev/null || true

    # Count results
    new_transcripts=$(ssh "$MAC_HOST" "ls $MAC_TRANSCRIPTS/*.json 2>/dev/null | wc -l" | tr -d ' ')
    log "Completed: $new_transcripts transcripts"

    # Cleanup Mac Mini
    ssh "$MAC_HOST" "rm -f $MAC_AUDIO/*.mp3 $MAC_TRANSCRIPTS/*.json" 2>/dev/null || true

    log "=== Batch complete ==="
}

main "$@"
