#!/bin/bash
# Deploy Mac Mini Worker Script
# Copies worker script to Mac Mini and sets up the service

set -e

echo "🚀 Deploying Mac Mini worker..."

# Check if SSH connection works
if ! ssh macmini "echo 'Connection test successful'" >/dev/null 2>&1; then
    echo "❌ Cannot connect to Mac Mini via SSH"
    echo "Please run: ./scripts/setup_mac_mini_ssh.sh first"
    exit 1
fi

# Copy worker script to Mac Mini
echo "📤 Copying worker script to Mac Mini..."
scp scripts/mac_mini_worker.py macmini:~/atlas_worker/

# Copy additional setup files
ssh macmini "chmod +x ~/atlas_worker/mac_mini_worker.py"

# Create service script on Mac Mini
echo "🔧 Setting up Mac Mini worker service..."
ssh macmini 'cat > ~/atlas_worker/start_worker.sh << '"'"'EOF'"'"'
#!/bin/bash
cd ~/atlas_worker
source venv/bin/activate
python3 mac_mini_worker.py --poll-interval 30
EOF'

ssh macmini "chmod +x ~/atlas_worker/start_worker.sh"

# Create launchd plist for automatic startup (optional)
ssh macmini 'cat > ~/Library/LaunchAgents/com.atlas.macmini.worker.plist << '"'"'EOF'"'"'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.atlas.macmini.worker</string>
    <key>ProgramArguments</key>
    <array>
        <string>/bin/bash</string>
        <string>-c</string>
        <string>cd ~/atlas_worker && source venv/bin/activate && python3 mac_mini_worker.py</string>
    </array>
    <key>WorkingDirectory</key>
    <string>/Users/$(whoami)/atlas_worker</string>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>/Users/$(whoami)/atlas_worker/logs/worker.out</string>
    <key>StandardErrorPath</key>
    <string>/Users/$(whoami)/atlas_worker/logs/worker.err</string>
</dict>
</plist>
EOF'

# Test worker setup
echo "🧪 Testing Mac Mini worker..."
if ssh macmini "cd ~/atlas_worker && source venv/bin/activate && python3 mac_mini_worker.py --test"; then
    echo "✅ Mac Mini worker test successful"
else
    echo "❌ Mac Mini worker test failed"
    exit 1
fi

echo ""
echo "🎉 Mac Mini worker deployed successfully!"
echo ""
echo "To start the worker:"
echo "  ssh macmini '~/atlas_worker/start_worker.sh'"
echo ""
echo "To enable automatic startup:"
echo "  ssh macmini 'launchctl load ~/Library/LaunchAgents/com.atlas.macmini.worker.plist'"
echo ""
echo "To test from Atlas:"
echo "  python3 helpers/mac_mini_client.py test"