#!/bin/bash

# Downie → Atlas Setup Script
# Run this ONCE on your Mac Mini
# Usage: ./setup_downie_to_atlas.sh

echo "🍎 Setting up Downie → Atlas bridge..."

# Configuration
ATLAS_SERVER="http://atlas.khamel.com:35555"
SCRIPT_PATH="$HOME/downie-atlas-monitor.sh"
LAUNCH_AGENT_PLIST="$HOME/Library/LaunchAgents/com.downie.atlas.monitor.plist"

echo "📝 Creating monitor script at: $SCRIPT_PATH"

# Create the monitor script
cat > "$SCRIPT_PATH" << 'EOF'
#!/bin/bash
ATLAS_SERVER="http://atlas.khamel.com:35555"
DOWNIE_LOG="$HOME/Library/Logs/Downie.log"

send_to_atlas() {
    local url="$1"
    echo "📤 Sending to Atlas: $url"
    response=$(curl -s --connect-timeout 10 "$ATLAS_SERVER/ingest?url=$(echo "$url" | sed 's/+/%2B/g' | sed 's/&/%26/g')")
    if echo "$response" | grep -q '"status":"success"'; then
        echo "✅ Success: $url sent to Atlas"
    else
        echo "❌ Failed: $url not sent to Atlas"
    fi
}

while true; do
    recent_failures=$(tail -n 20 "$DOWNIE_LOG" 2>/dev/null | grep -i "failed\|error\|unsupported" | grep -o 'https\?://[^"]*' | sort -u)
    if [ -n "$recent_failures" ]; then
        echo "$recent_failures" | while read -r url; do
            if [ -n "$url" ]; then
                send_to_atlas "$url"
            fi
        done
    fi
    sleep 10
done
EOF

# Make script executable
chmod +x "$SCRIPT_PATH"
echo "✅ Script made executable"

# Test Atlas connection
echo "🧪 Testing connection to Atlas server..."
test_response=$(curl -s --connect-timeout 10 "$ATLAS_SERVER/ingest?url=https://example.com")

if echo "$test_response" | grep -q '"status":"success"'; then
    echo "✅ Atlas server is reachable!"
else
    echo "❌ Cannot reach Atlas server at $ATLAS_SERVER"
    echo "Please make sure Atlas v3 is running on atlas.khamel.com:35555"
    exit 1
fi

# Create Launch Agent for auto-start
echo "🚀 Setting up auto-start..."
cat > "$LAUNCH_AGENT_PLIST" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.downie.atlas.monitor</string>
    <key>ProgramArguments</key>
    <array>
        <string>$SCRIPT_PATH</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>$HOME/Library/Logs/downie-atlas-monitor.log</string>
    <key>StandardErrorPath</key>
    <string>$HOME/Library/Logs/downie-atlas-monitor.log</string>
</dict>
</plist>
EOF

# Load the Launch Agent
launchctl load "$LAUNCH_AGENT_PLIST"
echo "✅ Auto-start configured"

echo ""
echo "🎉 Setup complete!"
echo ""
echo "📋 What's happening now:"
echo "  • Downie → Atlas monitor script: $SCRIPT_PATH"
echo "  • Auto-start: Yes (runs automatically when you log in)"
echo "  • Log file: $HOME/Library/Logs/downie-atlas-monitor.log"
echo "  • Atlas server: $ATLAS_SERVER"
echo ""
echo "🧪 To test: Send a non-video URL through Hyperduck"
echo "📊 To check logs: tail -f ~/Library/Logs/downie-atlas-monitor.log"
echo "🛑 To stop: launchctl unload $LAUNCH_AGENT_PLIST"
echo ""
echo "✨ Downie failures will now automatically go to Atlas!"