#!/bin/bash

# Downie → Atlas Automation Script for Mac
# This script monitors Downie failures and sends URLs to Atlas

# Configuration
ATLAS_SERVER="http://atlas.khamel.com:35555"
DOWNIE_LOG="$HOME/Library/Logs/Downie.log"
MONITOR_INTERVAL=5  # Check every 5 seconds

echo "🍎 Downie → Atlas Bridge Starting..."
echo "📥 Atlas Server: $ATLAS_SERVER"
echo "📋 Monitoring Downie failures..."

# Function to send URL to Atlas
send_to_atlas() {
    local url="$1"
    echo "📤 Sending to Atlas: $url"

    response=$(curl -s --connect-timeout 10 "$ATLAS_SERVER/ingest?url=$(echo "$url" | sed 's/+/%2B/g' | sed 's/&/%26/g')")

    if echo "$response" | grep -q '"status":"success"'; then
        echo "✅ Success: $url sent to Atlas"
    else
        echo "❌ Failed: Could not send $url to Atlas"
    fi
}

# Function to process Downie failures
process_downie_failures() {
    # Check Downie's recent log entries for failures
    local recent_failures=$(tail -n 20 "$DOWNIE_LOG" 2>/dev/null | grep -i "failed\|error\|unsupported" | grep -o 'https\?://[^"]*' | sort -u)

    if [ -n "$recent_failures" ]; then
        echo "🔍 Found Downie failures:"
        echo "$recent_failures"

        # Send each failed URL to Atlas
        while IFS= read -r url; do
            if [ -n "$url" ]; then
                send_to_atlas "$url"
            fi
        done <<< "$recent_failures"
    fi
}

# Alternative: Monitor Downie's database or preferences for failed URLs
monitor_downie_database() {
    local downie_db="$HOME/Library/Application Support/Downie/Downie.db"

    if [ -f "$downie_db" ]; then
        # Look for URLs that have failed status
        echo "🗂️  Monitoring Downie database..."

        # This would require specific knowledge of Downie's database structure
        # For now, we'll use the log-based approach
        process_downie_failures
    fi
}

# Main monitoring loop
echo "🔄 Starting monitoring loop..."
while true; do
    process_downie_failures
    sleep $MONITOR_INTERVAL
done