#!/bin/bash
# MAC MINI BRIDGE SETUP - Updated for IP-based connection
# Run this on your Mac Mini to connect to Atlas via IP

echo "🔧 Setting up Hyperduck → Downie → Atlas pipeline..."
echo ""

# Get Atlas server IP (replace with your actual server IP)
ATLAS_SERVER="http://54.210.133.145:35555"  # Update this IP if needed

# Test connection first
echo "🧪 Testing Atlas connection..."
response=$(curl -s "$ATLAS_SERVER/status" 2>/dev/null)

if [ $? -eq 0 ]; then
    echo "✅ Atlas is online: $ATLAS_SERVER"
else
    echo "❌ Atlas is offline: $ATLAS_SERVER"
    echo "💡 Make sure the Atlas server is running and accessible"
    echo "💡 Update the ATLAS_SERVER IP in this script if needed"
    exit 1
fi

# Create Downie failure monitor
cat > ~/downie-atlas-bridge.sh << EOF
#!/bin/bash
# Downie → Atlas Bridge Monitor
# Runs in background, sends failed URLs to Atlas

ATLAS_SERVER="$ATLAS_SERVER"
LOG_FILE="\$HOME/Library/Logs/Downie.log"
SENT_URLS_FILE="\$HOME/.atlas_sent_urls.txt"

# Create sent URLs tracking file
touch "\$SENT_URLS_FILE"

echo "🌉 Downie→Atlas bridge started"
echo "📊 Monitoring: \$LOG_FILE"
echo "🎯 Target: \$ATLAS_SERVER"

while true; do
    # Get recent failed URLs from Downie logs
    recent_failures=\$(tail -n 50 "\$LOG_FILE" 2>/dev/null | grep -i "failed\|error\|unsupported\|cannot" | grep -o 'https\?://[^") ]*' | sort -u)

    if [ -n "\$recent_failures" ]; then
        echo "\$recent_failures" | while read -r url; do
            # Skip if already sent
            if ! grep -q "\$url" "\$SENT_URLS_FILE" 2>/dev/null; then
                echo "📤 Sending to Atlas: \$url"
                response=\$(curl -s "\$ATLAS_SERVER/ingest?url=\$url")

                if echo "\$response" | grep -q "success\|received"; then
                    echo "✅ Sent: \$url"
                    echo "\$url" >> "\$SENT_URLS_FILE"
                else
                    echo "❌ Failed: \$url"
                fi
            fi
        done
    fi

    sleep 5
done
EOF

# Create manual URL sender
cat > ~/send-to-atlas.sh << EOF
#!/bin/bash
# Manual URL sender to Atlas
# Usage: ./send-to-atlas.sh "https://example.com"

ATLAS_SERVER="$ATLAS_SERVER"
URL="\$1"

if [ -z "\$URL" ]; then
    echo "Usage: \$0 \"URL\""
    exit 1
fi

echo "📤 Sending: \$url"
response=\$(curl -s "\$ATLAS_SERVER/ingest?url=\$URL")

if echo "\$response" | grep -q "success\|received"; then
    echo "✅ Success: \$URL sent to Atlas"
else
    echo "❌ Failed: \$URL"
    echo "Response: \$response"
fi
EOF

# Create Atlas status checker
cat > ~/atlas-status.sh << EOF
#!/bin/bash
# Check Atlas server status
ATLAS_SERVER="$ATLAS_SERVER"

echo "🔍 Checking Atlas status..."
response=\$(curl -s "\$ATLAS_SERVER/status" 2>/dev/null)

if [ \$? -eq 0 ]; then
    echo "✅ Atlas is online: \$ATLAS_SERVER"
    echo "📊 Response: \$response"
else
    echo "❌ Atlas is offline: \$ATLAS_SERVER"
fi
EOF

# Create auto-restart script for the bridge
cat > ~/bridge-service.sh << EOF
#!/bin/bash
# Bridge service manager - ensures bridge runs 100% of the time
BRIDGE_SCRIPT="\$HOME/downie-atlas-bridge.sh"
PID_FILE="\$HOME/.bridge.pid"
LOG_FILE="\$HOME/bridge-service.log"

start_bridge() {
    if [ -f "\$PID_FILE" ] && kill -0 \$(cat \$PID_FILE) 2>/dev/null; then
        echo "✅ Bridge is already running (PID: \$(cat \$PID_FILE))"
        return 0
    fi

    echo "🚀 Starting bridge..."
    nohup "\$BRIDGE_SCRIPT" > "\$LOG_FILE" 2>&1 &
    BRIDGE_PID=\$!
    echo "\$BRIDGE_PID" > "\$PID_FILE"
    echo "✅ Bridge started (PID: \$BRIDGE_PID)"
}

stop_bridge() {
    if [ -f "\$PID_FILE" ]; then
        PID=\$(cat \$PID_FILE)
        if kill -0 "\$PID" 2>/dev/null; then
            echo "🛑 Stopping bridge (PID: \$PID)..."
            kill "\$PID"
            sleep 2
            if kill -0 "\$PID" 2>/dev/null; then
                kill -9 "\$PID"
            fi
        fi
        rm -f "\$PID_FILE"
    fi
}

monitor_bridge() {
    echo "👁️  Starting bridge monitor..."
    while true; do
        if ! [ -f "\$PID_FILE" ] || ! kill -0 \$(cat \$PID_FILE) 2>/dev/null; then
            echo "⚠️  Bridge died, restarting..."
            start_bridge
        fi
        sleep 30
    done
}

case "\$1" in
    start)
        start_bridge
        ;;
    stop)
        stop_bridge
        ;;
    restart)
        stop_bridge
        sleep 1
        start_bridge
        ;;
    monitor)
        monitor_bridge
        ;;
    *)
        echo "Usage: \$0 {start|stop|restart|monitor}"
        exit 1
        ;;
esac
EOF

# Make everything executable
chmod +x ~/downie-atlas-bridge.sh
chmod +x ~/send-to-atlas.sh
chmod +x ~/atlas-status.sh
chmod +x ~/bridge-service.sh

echo ""
echo "🚀 Starting bridge service..."
~/bridge-service.sh start

echo ""
echo "🎯 Setup complete!"
echo ""
echo "📋 Commands:"
echo "  Check Atlas: ~/atlas-status.sh"
echo "  Send URL: ~/send-to-atlas.sh \"URL\""
echo "  Bridge control: ~/bridge-service.sh {start|stop|restart|monitor}"
echo "  View logs: tail -f ~/bridge-service.log"
echo ""
echo "🔧 For 100% uptime, run: ~/bridge-service.sh monitor &"
echo ""
echo "📱 Ready! Hyperduck → Downie → Atlas is now active"
echo "🌐 Server: $ATLAS_SERVER"