#!/bin/bash
# Monitor 18-hour processing progress and provide real-time status

echo "🚀 Atlas 18-Hour Processing Monitor"
echo "===================================="
echo "Started: $(date)"
echo "Target: 1000+ items processed in 18 hours"
echo ""

# Initial status
initial_completed=$(sqlite3 atlas_v2/data/atlas_v2.db "SELECT COUNT(*) FROM processing_queue WHERE status = 'completed';")
echo "📊 Initial Status: $initial_completed items completed"

# Continuous monitoring
while true; do
    current_time=$(date)
    completed=$(sqlite3 atlas_v2/data/atlas_v2.db "SELECT COUNT(*) FROM processing_queue WHERE status = 'completed';")
    pending=$(sqlite3 atlas_v2/data/atlas_v2.db "SELECT COUNT(*) FROM processing_queue WHERE status = 'pending';")
    failed=$(sqlite3 atlas_v2/data/atlas_v2.db "SELECT COUNT(*) FROM processing_queue WHERE status = 'failed';")

    processed_since_start=$((completed - initial_completed))
    hours_running=$(echo "($(date +%s) - $(date -d '16:24' +%s)) / 3600" | bc -l 2>/dev/null || echo "0.1")
    rate_per_hour=$(echo "scale=1; $processed_since_start / $hours_running" | bc -l 2>/dev/null || echo "0")

    # Calculate projection
    remaining_hours=$(echo "18 - $hours_running" | bc -l 2>/dev/null || echo "18")
    projected_total=$(echo "scale=0; $completed + ($rate_per_hour * $remaining_hours)" | bc -l 2>/dev/null || echo "$completed")

    clear
    echo "🚀 Atlas 18-Hour Processing Monitor"
    echo "===================================="
    echo "Current Time: $current_time"
    echo "Hours Running: $hours_running"
    echo ""
    echo "📊 Queue Status:"
    echo "  ✅ Completed: $completed"
    echo "  ⏳ Pending: $pending"
    echo "  ❌ Failed: $failed"
    echo "  📈 Processed this run: $processed_since_start"
    echo ""
    echo "📈 Performance:"
    echo "  Rate: $rate_per_hour items/hour"
    echo "  Projected 18h total: $projected_total"
    echo ""

    if [ "$projected_total" -ge 1000 ]; then
        echo "🟢 ON TRACK: Projected to meet 1000+ target!"
    elif [ "$projected_total" -ge 500 ]; then
        echo "🟡 BEHIND: Need to increase processing rate"
    else
        echo "🔴 CRITICAL: Processing rate too low"
    fi

    echo ""
    echo "Process Status:"
    if pgrep -f "create_frequent_scheduler.py" > /dev/null; then
        echo "  ✅ Continuous processor running (PID: $(pgrep -f create_frequent_scheduler.py))"
    else
        echo "  ❌ Continuous processor STOPPED"
    fi

    echo ""
    echo "Press Ctrl+C to stop monitoring"

    sleep 60
done