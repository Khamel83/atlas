#!/bin/bash

# Atlas Status Dashboard - Quick progress check
# Usage: ./atlas_status.sh

echo "🎯 ATLAS PODCAST PROCESSING STATUS"
echo "=================================="
echo "📅 $(date '+%Y-%m-%d %H:%M:%S')"
echo ""

# Check if Atlas is running
echo "🔥 PROCESS STATUS:"
if pgrep -f "python3.*atlas_manager" > /dev/null; then
    PID=$(pgrep -f "python3.*atlas_manager")
    UPTIME=$(ps -o etime= -p $PID | tr -d ' ')
    echo "  ✅ Atlas Manager: RUNNING (PID: $PID, Uptime: $UPTIME)"
else
    echo "  ❌ Atlas Manager: NOT RUNNING"
fi

echo ""

# Database status - main database
DB_PATH="data/databases/atlas_content_before_reorg.db"
if [ -f "$DB_PATH" ]; then
    echo "📊 TRANSCRIPT DISCOVERY:"

    TOTAL=$(sqlite3 "$DB_PATH" "SELECT COUNT(*) FROM episodes;" 2>/dev/null || echo "0")
    COMPLETED=$(sqlite3 "$DB_PATH" "SELECT COUNT(*) FROM episodes WHERE processing_status = 'completed';" 2>/dev/null || echo "0")
    TRANSCRIPTS=$(sqlite3 "$DB_PATH" "SELECT COUNT(*) FROM episodes WHERE transcript_found = 1;" 2>/dev/null || echo "0")
    PENDING=$(sqlite3 "$DB_PATH" "SELECT COUNT(*) FROM episodes WHERE processing_status = 'pending';" 2>/dev/null || echo "0")
    PROCESSING=$(sqlite3 "$DB_PATH" "SELECT COUNT(*) FROM episodes WHERE processing_status = 'processing';" 2>/dev/null || echo "0")
    FAILED=$(sqlite3 "$DB_PATH" "SELECT COUNT(*) FROM episodes WHERE processing_status = 'failed';" 2>/dev/null || echo "0")

    echo "  📈 Total Episodes: $TOTAL"
    echo "  ✅ Completed: $COMPLETED"
    echo "  🎯 Transcripts Found: $TRANSCRIPTS"
    echo "  ⏳ Pending: $PENDING"
    echo "  🔄 Processing: $PROCESSING"
    echo "  ❌ Failed: $FAILED"

    # Progress calculation
    if [ "$TOTAL" -gt 0 ]; then
        PROGRESS=$((TRANSCRIPTS * 100 / TOTAL))
        echo "  📊 Progress: $PROGRESS% (transcripts found)"
    fi
else
    echo "  ❌ Database not found at $DB_PATH"
fi

echo ""

# Recent activity (last 5 minutes)
echo "⚡ RECENT ACTIVITY (5 min):"
RECENT_TRANSCRIPTS=$(sqlite3 "$DB_PATH" "SELECT COUNT(*) FROM episodes WHERE transcript_found = 1 AND id IN (SELECT episode_id FROM module_execution_log WHERE start_time > datetime('now', '-5 minutes'));" 2>/dev/null || echo "0")
echo "  🎯 New transcripts (5 min): $RECENT_TRANSCRIPTS"

if [ -f "logs/atlas_manager.log" ]; then
    SUCCESSES=$(tail -100 logs/atlas_manager.log | grep -c "✅" 2>/dev/null || echo "0")
    FAILURES=$(tail -100 logs/atlas_manager.log | grep -c "❌" 2>/dev/null || echo "0")
    echo "  ✅ Recent successes: $SUCCESSES"
    echo "  ❌ Recent failures: $FAILURES"
fi

echo ""

# External API issues
echo "🌐 EXTERNAL API STATUS:"
if [ -f "logs/atlas_manager.log" ]; then
    DUCK_ERRORS=$(tail -50 logs/atlas_manager.log | grep -c "DuckDuckGo" 2>/dev/null || echo "0")
    TIMEOUTS=$(tail -50 logs/atlas_manager.log | grep -c "timeout\|Timeout\|TIMEOUT" 2>/dev/null || echo "0")

    if [ "$DUCK_ERRORS" -gt 0 ]; then
        echo "  ⚠️  DuckDuckGo errors: $DUCK_ERRORS (external dependency)"
    else
        echo "  ✅ No DuckDuckGo errors"
    fi

    if [ "$TIMEOUTS" -gt 0 ]; then
        echo "  ⚠️  Timeouts: $TIMEOUTS (possible rate limiting)"
    else
        echo "  ✅ No timeout issues"
    fi
fi

echo ""
echo "🚀 QUICK START: ./start_atlas.sh"
echo "📋 FULL LOGS: tail -f logs/atlas_manager.log"
echo "=================================="