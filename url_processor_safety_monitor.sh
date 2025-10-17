#!/bin/bash
# URL Processor Safety Monitor - Aggressive restart
# Checks every 30 seconds and restarts if needed

echo "🛡️ Starting URL Processor Safety Monitor..."

while true; do
    # Check if universal_url_processor.py is running
    if ! pgrep -f "universal_url_processor.py" > /dev/null; then
        echo "🔄 $(date): URL Processor not running - restarting..."
        cd /home/ubuntu/dev/atlas
        nohup python3 universal_url_processor.py > logs/url_processor.log 2>&1 &
        echo "✅ URL Processor restarted at $(date)"
    fi

    # Also check if process is hung (not processing for 5+ minutes)
    if pgrep -f "universal_url_processor.py" > /dev/null; then
        # Check if the log file has recent activity
        LOG_FILE="logs/url_processor.log"
        if [ -f "$LOG_FILE" ]; then
            LAST_ACTIVITY=$(stat -c %Y "$LOG_FILE" 2>/dev/null || echo 0)
            CURRENT_TIME=$(date +%s)
            AGE=$((CURRENT_TIME - LAST_ACTIVITY))

            # If no activity for 5 minutes, restart it
            if [ $AGE -gt 300 ]; then
                echo "⏰ $(date): URL Processor appears hung (no activity for 5+ min) - restarting..."
                pkill -f "universal_url_processor.py"
                sleep 2
                cd /home/ubuntu/dev/atlas
                nohup python3 universal_url_processor.py > logs/url_processor.log 2>&1 &
                echo "✅ URL Processor force-restarted at $(date)"
            fi
        fi
    fi

    sleep 30
done