#!/bin/bash
# Check Downie Container Logs - Based on diagnostic results

echo "🔍 CHECKING DOWNIE CONTAINERS"
echo "============================="

# From the diagnostic, we found these Downie containers:
CONTAINERS=(
    "$HOME/Library/Containers/com.charliemonroe.Downie-4"
    "$HOME/Library/Containers/com.charliemonroe.Downie-4-Downie-Extension"
    "$HOME/Library/Containers/com.charliemonroe.Downie-4.Downie-Extension-New"
    "$HOME/Library/Containers/com.charliemonroe.Downie-4.Share-Extension"
)

for container in "${CONTAINERS[@]}"; do
    if [ -d "$container" ]; then
        echo ""
        echo "📦 Checking: $container"
        echo "----------------------------------------"

        # Check for logs in Data/Library/Logs
        log_dir="$container/Data/Library/Logs"
        if [ -d "$log_dir" ]; then
            echo "📊 Found logs directory: $log_dir"
            ls -la "$log_dir/"

            # Check each log file
            find "$log_dir" -name "*.log" -type f | while read -r logfile; do
                echo ""
                echo "📄 Log file: $logfile"
                echo "Size: $(wc -l "$logfile" 2>/dev/null || echo "0") lines"
                echo "Recent entries:"
                tail -5 "$logfile" 2>/dev/null || echo "Cannot read file"
            done
        else
            echo "❌ No logs directory in this container"
        fi

        # Check for other interesting directories
        data_dir="$container/Data"
        if [ -d "$data_dir" ]; then
            echo ""
            echo "📁 Other data directories:"
            find "$data_dir" -maxdepth 2 -type d | grep -E "(Log|Cache|Crash|Support)" | head -10
        fi
    fi
done

echo ""
echo "🎯 MANUAL TESTING STEPS:"
echo "========================"
echo "1. Create timestamp: touch /tmp/before_test"
echo "2. Send a URL through Hyperduck that you know will fail in Downie"
echo "3. Wait for failure to appear in Downie UI"
echo "4. Run: find ~/Library/Containers/com.charliemonroe.Downie-4 -newer /tmp/before_test -name '*.log'"
echo "5. Check those files for the failure message"
echo ""
echo "💡 Also try:"
echo "   tail -f ~/Library/Containers/com.charliemonroe.Downie-4/Data/Library/Logs/*.log"