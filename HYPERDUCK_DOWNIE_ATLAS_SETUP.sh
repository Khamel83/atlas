#!/bin/bash
# HYPERDUCK → DOWNIE → ATLAS COMPLETE SETUP
# Run this on your Mac Mini to connect everything
# Usage: bash HYPERDUCK_DOWNIE_ATLAS_SETUP.sh

echo "🔧 Setting up Hyperduck → Downie → Atlas pipeline..."
echo "📍 Atlas Server: atlas.khamel.com:35555"

# Step 1: Create Downie failure monitor
cat > ~/downie-atlas-bridge.sh << 'EOF'
#!/bin/bash
# Downie → Atlas Bridge Monitor
# Runs in background, sends failed URLs to Atlas

ATLAS_SERVER="http://atlas.khamel.com:35555"
LOG_FILE="$HOME/Library/Logs/Downie.log"
SENT_URLS_FILE="$HOME/.atlas_sent_urls.txt"

# Create sent URLs tracking file
touch "$SENT_URLS_FILE"

echo "🌉 Downie→Atlas bridge started"
echo "📊 Monitoring: $LOG_FILE"
echo "🎯 Target: $ATLAS_SERVER"

while true; do
    # Get recent failed URLs from Downie logs
    recent_failures=$(tail -n 50 "$LOG_FILE" 2>/dev/null | grep -i "failed\|error\|unsupported\|cannot" | grep -o 'https\?://[^") ]*' | sort -u)

    if [ -n "$recent_failures" ]; then
        echo "$recent_failures" | while read -r url; do
            # Skip if already sent
            if ! grep -q "$url" "$SENT_URLS_FILE" 2>/dev/null; then
                echo "📤 Sending to Atlas: $url"
                response=$(curl -s "$ATLAS_SERVER/ingest?url=$url")

                if echo "$response" | grep -q "success\|received"; then
                    echo "✅ Sent: $url"
                    echo "$url" >> "$SENT_URLS_FILE"
                else
                    echo "❌ Failed: $url"
                fi
            fi
        done
    fi

    sleep 5
done
EOF

# Step 2: Create manual URL sender (for testing)
cat > ~/send-to-atlas.sh << 'EOF'
#!/bin/bash
# Manual URL sender to Atlas
# Usage: ./send-to-atlas.sh "https://example.com"

ATLAS_SERVER="http://atlas.khamel.com:35555"
URL="$1"

if [ -z "$URL" ]; then
    echo "Usage: $0 \"URL\""
    exit 1
fi

echo "📤 Sending: $url"
response=$(curl -s "$ATLAS_SERVER/ingest?url=$URL")

if echo "$response" | grep -q "success\|received"; then
    echo "✅ Success: $URL sent to Atlas"
else
    echo "❌ Failed: $URL"
    echo "Response: $response"
fi
EOF

# Step 3: Create Atlas status checker
cat > ~/atlas-status.sh << 'EOF'
#!/bin/bash
# Check Atlas server status
ATLAS_SERVER="http://atlas.khamel.com:35555"

echo "🔍 Checking Atlas status..."
response=$(curl -s "$ATLAS_SERVER/status" 2>/dev/null)

if [ $? -eq 0 ]; then
    echo "✅ Atlas is online: $ATLAS_SERVER"
    echo "📊 Response: $response"
else
    echo "❌ Atlas is offline: $ATLAS_SERVER"
fi
EOF

# Step 4: Make everything executable
chmod +x ~/downie-atlas-bridge.sh
chmod +x ~/send-to-atlas.sh
chmod +x ~/atlas-status.sh

# Step 5: Test Atlas connection
echo ""
echo "🧪 Testing Atlas connection..."
~/atlas-status.sh

# Step 6: Start the bridge
echo ""
echo "🚀 Starting Downie→Atlas bridge..."
echo "💡 This will run in the background"
echo "📱 Send non-video URLs via Hyperduck to test"
echo ""

# Start in background
nohup ~/downie-atlas-bridge.sh > ~/downie-atlas-bridge.log 2>&1 &
BRIDGE_PID=$!

echo "✅ Bridge started (PID: $BRIDGE_PID)"
echo "📋 Commands:"
echo "  Check status: ~/atlas-status.sh"
echo "  Send URL manually: ~/send-to-atlas.sh \"URL\""
echo "  View logs: tail -f ~/downie-atlas-bridge.log"
echo "  Stop bridge: kill $BRIDGE_PID"
echo ""
echo "🎯 Ready! Hyperduck → Downie → Atlas is now active"
echo "📱 Any URL Downie can't handle will automatically go to Atlas"