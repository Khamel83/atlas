#!/bin/bash
# Real-time Downie Activity Monitor
# Run this BEFORE triggering a Downie failure

echo "🔍 REAL-TIME DOWNIE MONITORING"
echo "=============================="

# Create timestamp for new file detection
touch /tmp/before_downie_test

echo "⏰ Timestamp created. Now trigger a Downie failure..."
echo "📱 Send a URL through Hyperduck that will fail in Downie"
echo ""
echo "🔄 Monitoring for new files (Press Ctrl+C to stop)..."

# Monitor for new files in all Downie locations
while true; do
    # Check for new log files
    new_logs=$(find ~/Library/Containers/com.charliemonroe.Downie-4 -newer /tmp/before_downie_test -name "*.log" 2>/dev/null)

    # Check for any new files in Downie containers
    new_files=$(find ~/Library/Containers/com.charliemonroe.Downie-4 -newer /tmp/before_downie_test -type f 2>/dev/null)

    # Check for new database files (Downie might use SQLite)
    new_dbs=$(find ~/Library/Containers/com.charliemonroe.Downie-4 -newer /tmp/before_downie_test -name "*.db" -o -name "*.sqlite" 2>/dev/null)

    # Check for new plist files (preferences/state)
    new_plists=$(find ~/Library/Containers/com.charliemonroe.Downie-4 -newer /tmp/before_downie_test -name "*.plist" 2>/dev/null)

    # Check Console.app logs for Downie (macOS system logs)
    console_logs=$(log stream --predicate 'process == "Downie 4"' --last 5s 2>/dev/null | grep -i "error\|fail\|cannot\|unsupported" | tail -3)

    if [ -n "$new_logs" ]; then
        echo "🎯 NEW LOG FILES DETECTED:"
        echo "$new_logs"
        echo "Contents:"
        while read -r logfile; do
            echo "📄 $logfile:"
            cat "$logfile"
            echo "---"
        done <<< "$new_logs"
    fi

    if [ -n "$new_files" ]; then
        echo "📁 NEW FILES DETECTED:"
        echo "$new_files" | head -10
        echo "---"
    fi

    if [ -n "$new_dbs" ]; then
        echo "💾 NEW DATABASE FILES:"
        echo "$new_dbs"
        echo "---"
    fi

    if [ -n "$new_plists" ]; then
        echo "⚙️ NEW PREFERENCE FILES:"
        echo "$new_plists"
        echo "---"
    fi

    if [ -n "$console_logs" ]; then
        echo "🖥️ CONSOLE LOGS (System Logs):"
        echo "$console_logs"
        echo "---"
    fi

    sleep 2
done