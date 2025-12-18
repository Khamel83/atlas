#!/bin/bash
# MAC MINI BRIDGE V2 - Enhanced Downie failure detection
# More comprehensive patterns for detecting Downie failures

ATLAS_SERVER="https://atlas.khamel.com"
LOG_FILE="$HOME/Library/Logs/Downie.log"
SENT_URLS_FILE="$HOME/.atlas_sent_urls.txt"
DEBUG_LOG="$HOME/bridge_debug.log"

# Create tracking files
touch "$SENT_URLS_FILE"
touch "$DEBUG_LOG"

echo "🌉 Downie→Atlas bridge v2 started" | tee -a "$DEBUG_LOG"
echo "📊 Monitoring: $LOG_FILE" | tee -a "$DEBUG_LOG"
echo "🎯 Target: $ATLAS_SERVER" | tee -a "$DEBUG_LOG"

# More comprehensive failure patterns
FAILURE_PATTERNS=(
    "failed"
    "error"
    "unsupported"
    "cannot"
    "unable"
    "invalid"
    "not supported"
    "no media"
    "no video"
    "could not"
    "failed to"
    "error processing"
)

# Function to extract URLs from text
extract_urls() {
    echo "$1" | grep -oE 'https?://[^")[:space:]]+' | sort -u
}

# Function to check if URL should be sent
should_send_url() {
    local url="$1"

    # Skip if already sent
    if grep -q "$url" "$SENT_URLS_FILE" 2>/dev/null; then
        return 1
    fi

    # Skip common test URLs
    if [[ "$url" == *"example.com"* ]]; then
        return 1
    fi

    # Skip if no content
    if [ -z "$url" ]; then
        return 1
    fi

    return 0
}

# Function to send URL to Atlas
send_to_atlas() {
    local url="$1"

    echo "📤 Sending to Atlas: $url" | tee -a "$DEBUG_LOG"
    response=$(curl -s "$ATLAS_SERVER/ingest?url=$url")

    if echo "$response" | grep -q "success\|received"; then
        echo "✅ Sent: $url" | tee -a "$DEBUG_LOG"
        echo "$url" >> "$SENT_URLS_FILE"
        return 0
    else
        echo "❌ Failed: $url - Response: $response" | tee -a "$DEBUG_LOG"
        return 1
    fi
}

echo "🔍 Searching for Downie log files..." | tee -a "$DEBUG_LOG"

# Find all possible Downie log locations
LOG_LOCATIONS=(
    "$HOME/Library/Logs/Downie.log"
    "$HOME/Library/Containers/com.charliemonroe.downie/Data/Library/Logs/Downie.log"
    "$HOME/Library/Application Support/Downie/Logs/Downie.log"
    "$LOG_FILE"
)

# Check each log location
for log_path in "${LOG_LOCATIONS[@]}"; do
    if [ -f "$log_path" ]; then
        echo "📁 Found log: $log_path" | tee -a "$DEBUG_LOG"

        # Search for failures with multiple patterns
        for pattern in "${FAILURE_PATTERNS[@]}"; do
            echo "🔍 Searching for pattern: $pattern" | tee -a "$DEBUG_LOG"

            # Get recent log entries with this pattern
            recent_entries=$(tail -n 100 "$log_path" 2>/dev/null | grep -i "$pattern")

            if [ -n "$recent_entries" ]; then
                echo "🎯 Found entries with pattern: $pattern" | tee -a "$DEBUG_LOG"
                echo "$recent_entries" | tee -a "$DEBUG_LOG"

                # Extract URLs from these entries
                urls=$(extract_urls "$recent_entries")

                if [ -n "$urls" ]; then
                    echo "🔗 Found URLs: $urls" | tee -a "$DEBUG_LOG"
                    echo "$urls" | while read -r url; do
                        if should_send_url "$url"; then
                            send_to_atlas "$url"
                        fi
                    done
                fi
            fi
        done
    fi
done

echo "🔄 Starting continuous monitoring..." | tee -a "$DEBUG_LOG"

# Continuous monitoring loop
while true; do
    for log_path in "${LOG_LOCATIONS[@]}"; do
        if [ -f "$log_path" ]; then
            # Get the most recent log entries
            recent_entries=$(tail -n 50 "$log_path" 2>/dev/null)

            if [ -n "$recent_entries" ]; then
                # Check all failure patterns
                for pattern in "${FAILURE_PATTERNS[@]}"; do
                    matched_entries=$(echo "$recent_entries" | grep -i "$pattern")

                    if [ -n "$matched_entries" ]; then
                        urls=$(extract_urls "$matched_entries")

                        if [ -n "$urls" ]; then
                            echo "$urls" | while read -r url; do
                                if should_send_url "$url"; then
                                    send_to_atlas "$url"
                                fi
                            done
                        fi
                    fi
                done
            fi
        fi
    done

    sleep 3  # Check every 3 seconds for faster detection
done