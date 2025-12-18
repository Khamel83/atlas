#!/bin/bash
# Downie History Database Bridge
# Monitors Downie's actual database for failed URLs
# Based on real monitoring data showing History.db usage

ATLAS_SERVER="https://atlas.khamel.com"
HISTORY_DB="/Users/macmini/Library/Containers/com.charliemonroe.Downie-4/Data/Library/Application Support/com.charliemonroe.Downie-4/History.db"
SENT_URLS_FILE="$HOME/.atlas_sent_urls.txt"
LAST_CHECK_FILE="$HOME/.atlas_last_check.txt"

# Create tracking files
touch "$SENT_URLS_FILE"

# Get current timestamp
current_time=$(date +%s)
if [ ! -f "$LAST_CHECK_FILE" ]; then
    echo "$current_time" > "$LAST_CHECK_FILE"
fi

echo "🎯 DOWNIE HISTORY DATABASE BRIDGE"
echo "================================="
echo "📊 Database: $HISTORY_DB"
echo "🌐 Atlas: $ATLAS_SERVER"
echo "⏰ Started: $(date)"

# Function to send URL to Atlas
send_to_atlas() {
    local url="$1"
    local status="$2"

    # Skip if already sent
    if grep -q "$url" "$SENT_URLS_FILE" 2>/dev/null; then
        return 0
    fi

    echo "📤 Sending failed URL to Atlas: $url"
    response=$(curl -s "$ATLAS_SERVER/ingest?url=$url")

    if echo "$response" | grep -q "success"; then
        echo "✅ Success: $url → Atlas"
        echo "$url" >> "$SENT_URLS_FILE"
    else
        echo "❌ Failed to send: $url"
    fi
}

# Monitor database changes
echo "🔄 Monitoring Downie History database..."
while true; do
    if [ -f "$HISTORY_DB" ]; then
        # Get last check time
        last_check=$(cat "$LAST_CHECK_FILE" 2>/dev/null || echo "0")

        # Query database for recent failed entries
        # Common SQLite patterns for download status: 0=success, 1=failed, etc.
        failed_urls=$(sqlite3 "$HISTORY_DB" "
            SELECT url FROM downloads
            WHERE (status != 0 OR status IS NULL OR error IS NOT NULL)
            AND created_at > datetime($last_check, 'unixepoch')
            ORDER BY created_at DESC;" 2>/dev/null)

        # Alternative query patterns if above doesn't work
        if [ -z "$failed_urls" ]; then
            failed_urls=$(sqlite3 "$HISTORY_DB" "
                SELECT url FROM history
                WHERE (failed = 1 OR success = 0 OR error IS NOT NULL)
                AND timestamp > $last_check;" 2>/dev/null)
        fi

        # Another common pattern
        if [ -z "$failed_urls" ]; then
            failed_urls=$(sqlite3 "$HISTORY_DB" "
                SELECT source_url FROM entries
                WHERE (download_status = 'failed' OR download_status = 'error')
                AND date_added > datetime($last_check, 'unixepoch');" 2>/dev/null)
        fi

        # If we found failed URLs, process them
        if [ -n "$failed_urls" ]; then
            echo "🚨 Found failed downloads:"
            echo "$failed_urls" | while read -r url; do
                if [ -n "$url" ]; then
                    send_to_atlas "$url" "failed"
                fi
            done
        fi

        # Update last check time
        echo "$current_time" > "$LAST_CHECK_FILE"
        current_time=$(date +%s)
    else
        echo "⚠️  History database not found: $HISTORY_DB"
    fi

    sleep 10  # Check every 10 seconds
done