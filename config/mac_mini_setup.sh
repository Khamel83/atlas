#!/bin/bash
# Mac Mini Transcription Client Setup Script for Atlas

set -e

echo "🎯 Atlas Mac Mini Transcription Client Setup"
echo "============================================"

# Check if we're on macOS
if [[ "$OSTYPE" != "darwin"* ]]; then
    echo "❌ This script is designed for macOS (Mac Mini)"
    echo "   Current OS: $OSTYPE"
    exit 1
fi

# Create directories
ATLAS_HOME="$HOME/atlas_transcription"
QUEUE_DIR="$ATLAS_HOME/transcription_queue"
echo "📁 Creating directories..."
mkdir -p "$QUEUE_DIR/incoming"
mkdir -p "$QUEUE_DIR/processed"
mkdir -p "$QUEUE_DIR/failed"

# Install Homebrew if not present
if ! command -v brew &> /dev/null; then
    echo "🍺 Installing Homebrew..."
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
fi

# Install whisper.cpp
if ! command -v whisper &> /dev/null; then
    echo "🎙️ Installing whisper.cpp..."
    brew install whisper-cpp
fi

# Install Python dependencies
echo "🐍 Setting up Python environment..."
if ! command -v python3 &> /dev/null; then
    echo "Installing Python..."
    brew install python
fi

# Install required Python packages
pip3 install requests watchdog

# Copy transcription client
echo "📥 Installing transcription client..."
cp mac_mini_transcription_client.py "$ATLAS_HOME/"
chmod +x "$ATLAS_HOME/mac_mini_transcription_client.py"

# Create configuration file
echo "⚙️ Creating configuration..."
cat > "$ATLAS_HOME/.env" << EOF
# Atlas Server Configuration
ATLAS_URL=http://192.168.1.100:8000
# ATLAS_API_KEY=your_api_key_here

# Transcription Settings
WHISPER_MODEL=base
WHISPER_LANGUAGE=en
EOF

# Create launcher script
cat > "$ATLAS_HOME/start_transcription.sh" << 'EOF'
#!/bin/bash
cd "$(dirname "$0")"
source .env 2>/dev/null || true
export ATLAS_URL=${ATLAS_URL:-"http://localhost:8000"}
export ATLAS_API_KEY=${ATLAS_API_KEY:-""}
echo "🚀 Starting Atlas Transcription Client..."
echo "🌐 Atlas URL: $ATLAS_URL"
python3 mac_mini_transcription_client.py
EOF
chmod +x "$ATLAS_HOME/start_transcription.sh"

# Create desktop launcher
cat > "$HOME/Desktop/Atlas Transcription.command" << EOF
#!/bin/bash
cd "$ATLAS_HOME"
./start_transcription.sh
EOF
chmod +x "$HOME/Desktop/Atlas Transcription.command"

# Create launchd service for auto-start
PLIST_PATH="$HOME/Library/LaunchAgents/com.atlas.transcription.plist"
cat > "$PLIST_PATH" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.atlas.transcription</string>
    <key>ProgramArguments</key>
    <array>
        <string>$ATLAS_HOME/start_transcription.sh</string>
    </array>
    <key>WorkingDirectory</key>
    <string>$ATLAS_HOME</string>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>$ATLAS_HOME/transcription.log</string>
    <key>StandardErrorPath</key>
    <string>$ATLAS_HOME/transcription_error.log</string>
</dict>
</plist>
EOF

echo "✅ Setup Complete!"
echo ""
echo "📋 Next Steps:"
echo "1. Edit $ATLAS_HOME/.env to set your Atlas server URL"
echo "2. Start transcription client:"
echo "   cd $ATLAS_HOME && ./start_transcription.sh"
echo ""
echo "📁 Usage:"
echo "   Drop audio files into: $QUEUE_DIR/incoming/"
echo "   Processed files go to: $QUEUE_DIR/processed/"
echo "   Failed files go to: $QUEUE_DIR/failed/"
echo ""
echo "🚀 Auto-start on login:"
echo "   launchctl load $PLIST_PATH"
echo "   launchctl start com.atlas.transcription"
echo ""
echo "🎯 Desktop launcher created: ~/Desktop/Atlas Transcription.command"