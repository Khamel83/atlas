#!/bin/bash
# Single KPI metric for Atlas health and progress

ATLAS_DIR="/home/ubuntu/dev/atlas"
DB_FILE="$ATLAS_DIR/data/atlas.db"

cd "$ATLAS_DIR"

# Get current metrics
TOTAL_EPISODES=$(sqlite3 "$DB_FILE" "SELECT COUNT(*) FROM episode_queue")
PENDING_EPISODES=$(sqlite3 "$DB_FILE" "SELECT COUNT(*) FROM episode_queue WHERE status = 'pending'")
FOUND_EPISODES=$(sqlite3 "$DB_FILE" "SELECT COUNT(*) FROM episode_queue WHERE status = 'found'")
NOT_FOUND_EPISODES=$(sqlite3 "$DB_FILE" "SELECT COUNT(*) FROM episode_queue WHERE status = 'not_found'")
TRANSCRIPTS=$(sqlite3 "$DB_FILE" "SELECT COUNT(*) FROM content WHERE content_type = 'podcast_transcript'")

# Calculate REAL-TIME ACTIVITY SCORE
# This measures what Atlas is doing RIGHT NOW, not historical success

# Recent Activity Component (0-50 points)
# Check if Atlas has been active in the last 10 minutes
LOG_FILE="$ATLAS_DIR/logs/atlas_output.log"
if [ -f "$LOG_FILE" ]; then
    RECENT_ACTIVITY=$(tail -n 50 "$LOG_FILE" | grep -c "$(date '+%Y-%m-%d %H:%M')" | awk '{print $1}')
    if [ "$RECENT_ACTIVITY" -gt 10 ]; then
        ACTIVITY_SCORE=50
    elif [ "$RECENT_ACTIVITY" -gt 5 ]; then
        ACTIVITY_SCORE=30
    elif [ "$RECENT_ACTIVITY" -gt 0 ]; then
        ACTIVITY_SCORE=15
    else
        ACTIVITY_SCORE=0
    fi
else
    ACTIVITY_SCORE=0
fi

# System Health Component (0-50 points)
# Check if Atlas is running RIGHT NOW
ATLAS_RUNNING=$(ps aux | grep "python3 atlas_manager.py" | grep -v grep | wc -l)
MONITORING_RUNNING=$(ps aux | grep "monitoring_service.py" | grep -v grep | wc -l)
ENHANCED_MONITOR_RUNNING=$(ps aux | grep "enhanced_monitor_atlas_fixed" | grep -v grep | wc -l)

SYSTEM_HEALTH=0
if [ "$ATLAS_RUNNING" -gt 0 ]; then
    SYSTEM_HEALTH=$(($SYSTEM_HEALTH + 30))  # Atlas is most important
fi
if [ "$MONITORING_RUNNING" -gt 0 ]; then
    SYSTEM_HEALTH=$(($SYSTEM_HEALTH + 10))
fi
if [ "$ENHANCED_MONITOR_RUNNING" -gt 0 ]; then
    SYSTEM_HEALTH=$(($SYSTEM_HEALTH + 10))
fi

# Processing Activity (are we working through the queue?)
# Check if queue is being reduced
if [ "$PENDING_EPISODES" -gt 0 ]; then
    QUEUE_PRESSURE=10  # Bonus points for having work to do
else
    QUEUE_PRESSURE=0
fi

# Final KPI: What's happening RIGHT NOW
HEALTH_SCORE=$(echo "scale=1; $ACTIVITY_SCORE + $SYSTEM_HEALTH + $QUEUE_PRESSURE" | bc -l 2>/dev/null || echo "0")

# Processing Activity Score (are we making progress?)
if [ "$PENDING_EPISODES" -gt 0 ]; then
    ACTIVITY_SCORE=$(echo "scale=1; $PROCESSED_COUNT * 100 / $TOTAL_EPISODES" | bc -l 2>/dev/null || echo "0")
else
    ACTIVITY_SCORE="100"
fi

# Overall system status
if [ "$ATLAS_RUNNING" -gt 0 ] && [ "$MONITORING_RUNNING" -gt 0 ] && [ "$ENHANCED_MONITOR_RUNNING" -gt 0 ]; then
    SYSTEM_STATUS="RUNNING"
else
    SYSTEM_STATUS="DEGRADED"
fi

# Determine health category for REAL-TIME activity
if (( $(echo "$HEALTH_SCORE >= 80" | bc -l) )); then
    HEALTH_CATEGORY="ACTIVE"
elif (( $(echo "$HEALTH_SCORE >= 60" | bc -l) )); then
    HEALTH_CATEGORY="RUNNING"
elif (( $(echo "$HEALTH_SCORE >= 40" | bc -l) )); then
    HEALTH_CATEGORY="IDLE"
elif (( $(echo "$HEALTH_SCORE >= 20" | bc -l) )); then
    HEALTH_CATEGORY="DEGRADED"
else
    HEALTH_CATEGORY="STOPPED"
fi

# Output REAL-TIME KPI metric
echo "🎯 ATLAS REAL-TIME STATUS: $HEALTH_SCORE% ($HEALTH_CATEGORY)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📊 Right Now: $(date)"
echo "🏃 Recent Activity: $RECENT_ACTIVITY log entries (current hour)"
echo "📋 Queue: $PENDING_EPISODES pending | $FOUND_EPISODES found | $NOT_FOUND_EPISODES not found"
echo "🏃 Services: Atlas($ATLAS_RUNNING) Monitor($MONITORING_RUNNING) Enhanced($ENHANCED_MONITOR_RUNNING)"
echo "💾 Historical: $TRANSCRIPTS transcripts total"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Status explanations
case $HEALTH_CATEGORY in
    "ACTIVE")
        echo "🟢 Atlas is actively processing and making progress"
        ;;
    "RUNNING")
        echo "🟡 Atlas is running but could be more active"
        ;;
    "IDLE")
        echo "🟠 Atlas is running but not very active right now"
        ;;
    "DEGRADED")
        echo "🔴 Atlas has issues - services missing or not responding"
        ;;
    "STOPPED")
        echo "⚫ Atlas is not working - needs immediate attention"
        ;;
esac
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Simple single number output for quick checks
echo "$HEALTH_SCORE"