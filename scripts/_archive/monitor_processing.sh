#!/bin/bash
# Simple monitoring script for the trusted processor

echo "🎯 ATLAS TRUSTED PROCESSING MONITOR"
echo "=================================="

# Check if processor is running
if pgrep -f "python3 trusted_queue_processor.py" > /dev/null; then
    echo "🟢 STATUS: PROCESSOR IS RUNNING"
    echo "   PID: $(pgrep -f 'python3 trusted_queue_processor.py')"
else
    echo "🔴 STATUS: PROCESSOR NOT RUNNING"
    echo "   Start with: python3 trusted_queue_processor.py"
fi

echo ""

# Check queue status
echo "📋 QUEUE STATUS:"
sqlite3 data/atlas.db "SELECT status, COUNT(*) as count FROM episode_queue GROUP BY status ORDER BY count DESC;"

echo ""

# Check total transcripts
echo "🗄️  DATABASE STATUS:"
total_transcripts=$(sqlite3 data/atlas.db "SELECT COUNT(*) FROM content WHERE content_type = 'podcast_transcript';")
echo "   Total transcripts: $total_transcripts"

echo ""

# Check progress file if it exists
if [ -f "logs/processing_progress.json" ]; then
    echo "📊 PROCESSING PROGRESS:"
    python3 -c "
import json
with open('logs/processing_progress.json', 'r') as f:
    progress = json.load(f)
print(f'   Processed: {progress.get(\"processed_count\", 0):,}')
print(f'   Success: {progress.get(\"success_count\", 0):,}')
print(f'   Failed: {progress.get(\"failed_count\", 0):,}')
if progress.get('start_time'):
    from datetime import datetime
    start = datetime.fromisoformat(progress['start_time'])
    runtime = datetime.now() - start
    hours = runtime.total_seconds() // 3600
    print(f'   Runtime: {int(hours)} hours')
"
fi

echo ""

# Show recent logs
echo "📝 RECENT LOGS:"
if [ -f "logs/trusted_processor.log" ]; then
    tail -10 logs/trusted_processor.log
else
    echo "   No logs found"
fi