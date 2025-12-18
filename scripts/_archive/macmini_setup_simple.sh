#!/bin/bash
# MAC MINI BRIDGE SETUP - Simple version
# Run this on your Mac Mini to connect to Atlas

echo "🔧 Setting up Hyperduck → Downie → Atlas pipeline..."

# Atlas server domain
ATLAS_SERVER="https://atlas.khamel.com"

# Test connection with timeout
echo "🧪 Testing Atlas connection..."
response=$(timeout 10 curl -s "$ATLAS_SERVER/ingest?url=https://example.com" 2>/dev/null)

if echo "$response" | grep -q "success"; then
    echo "✅ Atlas is online: $ATLAS_SERVER"
else
    echo "❌ Atlas is offline: $ATLAS_SERVER"
    echo "💡 Try again in a moment - the server may be restarting"
    exit 1
fi

# Create Downie bridge using printf to avoid heredoc issues
printf '#!/bin/bash\n# Downie → Atlas Bridge Monitor\n\nATLAS_SERVER="%s"\nLOG_FILE="$HOME/Library/Logs/Downie.log"\nSENT_URLS_FILE="$HOME/.atlas_sent_urls.txt"\n\ntouch "$SENT_URLS_FILE"\n\necho "🌉 Downie→Atlas bridge started"\necho "🎯 Target: $ATLAS_SERVER"\n\nwhile true; do\n    recent_failures=$(tail -n 50 "$LOG_FILE" 2>/dev/null | grep -i "failed\\|error\\|unsupported\\|cannot" | grep -o '"'"'https\\?://[^") ]*'"'"' | sort -u)\n    \n    if [ -n "$recent_failures" ]; then\n        echo "$recent_failures" | while read -r url; do\n            if ! grep -q "$url" "$SENT_URLS_FILE" 2>/dev/null; then\n                echo "📤 Sending to Atlas: $url"\n                response=$(curl -s "$ATLAS_SERVER/ingest?url=$url")\n                \n                if echo "$response" | grep -q "success\\|received"; then\n                    echo "✅ Sent: $url"\n                    echo "$url" >> "$SENT_URLS_FILE"\n                else\n                    echo "❌ Failed: $url"\n                fi\n            fi\n        done\n    fi\n    \n    sleep 5\ndone\n' "$ATLAS_SERVER" > ~/downie-atlas-bridge.sh

# Create manual sender
printf '#!/bin/bash\n# Manual URL sender\n\nATLAS_SERVER="%s"\nURL="$1"\n\nif [ -z "$URL" ]; then\n    echo "Usage: $0 \\"URL\\"\n    exit 1\nfi\n\necho "📤 Sending: $URL"\nresponse=$(curl -s "$ATLAS_SERVER/ingest?url=$URL")\n\nif echo "$response" | grep -q "success\\|received"; then\n    echo "✅ Success: $URL sent to Atlas"\nelse\n    echo "❌ Failed: $URL"\nfi\n' "$ATLAS_SERVER" > ~/send-to-atlas.sh

# Create status checker
printf '#!/bin/bash\n# Atlas status checker\n\nATLAS_SERVER="%s"\n\necho "🔍 Checking Atlas status..."\nresponse=$(curl -s "$ATLAS_SERVER/ingest?url=https://example.com" 2>/dev/null)\n\nif echo "$response" | grep -q "success"; then\n    echo "✅ Atlas is online: $ATLAS_SERVER"\nelse\n    echo "❌ Atlas is offline: $ATLAS_SERVER"\nfi\n' "$ATLAS_SERVER" > ~/atlas-status.sh

# Make executable
chmod +x ~/downie-atlas-bridge.sh
chmod +x ~/send-to-atlas.sh
chmod +x ~/atlas-status.sh

echo ""
echo "🚀 Starting bridge..."
nohup ~/downie-atlas-bridge.sh > ~/bridge.log 2>&1 &
BRIDGE_PID=$!
echo "✅ Bridge started (PID: $BRIDGE_PID)"

echo ""
echo "🎯 Setup complete!"
echo ""
echo "📋 Commands:"
echo "  Check Atlas: ~/atlas-status.sh"
echo "  Send URL: ~/send-to-atlas.sh \"URL\""
echo "  View logs: tail -f ~/bridge.log"
echo "  Stop bridge: kill $BRIDGE_PID"
echo ""
echo "📱 Ready! Hyperduck → Downie → Atlas is active"
echo "🌐 Server: $ATLAS_SERVER"