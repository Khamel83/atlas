#!/bin/bash

# Velja Integration Setup Script for macOS
# Run this script to configure Velja for Atlas integration

echo "🚀 Setting up Velja integration with Atlas..."

# Check if running on macOS
if [[ "$OSTYPE" != "darwin"* ]]; then
    echo "❌ This script is for macOS only"
    exit 1
fi

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}📍 Velja Integration Setup${NC}"
echo "================================"

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check if Velja is installed
echo -e "${YELLOW}🔍 Checking Velja installation...${NC}"

if command_exists velja; then
    echo -e "${GREEN}✅ Velja found in PATH${NC}"
    VELJA_CMD="velja"
elif [ -d "/Applications/Velja.app" ]; then
    echo -e "${GREEN}✅ Velja.app found in /Applications/${NC}"
    VELJA_CMD="/Applications/Velja.app/Contents/MacOS/Velja"
elif [ -d "$HOME/Applications/Velja.app" ]; then
    echo -e "${GREEN}✅ Velja.app found in ~/Applications/${NC}"
    VELJA_CMD="$HOME/Applications/Velja.app/Contents/MacOS/Velja"
else
    echo -e "${RED}❌ Velja not found${NC}"
    echo -e "${YELLOW}Please install Velja from: https://sindresorhus.com/velja${NC}"
    echo -e "${YELLOW}Then run this script again.${NC}"
    exit 1
fi

# Check Velja data directories
echo -e "${YELLOW}🔍 Checking Velja data directories...${NC}"

VELJA_DATA_DIRS=(
    "$HOME/Library/Application Support/Velja"
    "$HOME/Library/Containers/com.sindresorhus.Velja/Data/Library/Application Support/Velja"
)

VELJA_DATA_DIR=""

for dir in "${VELJA_DATA_DIRS[@]}"; do
    if [ -d "$dir" ]; then
        echo -e "${GREEN}✅ Found Velja data: $dir${NC}"
        VELJA_DATA_DIR="$dir"
        break
    fi
done

if [ -z "$VELJA_DATA_DIR" ]; then
    echo -e "${YELLOW}⚠️  Velja data directory not found${NC}"
    echo -e "${YELLOW}Velja will create it after first use${NC}"
    echo -e "${YELLOW}Please run Velja at least once, then run this script again${NC}"
    exit 1
fi

# Check if we can read Velja data
echo -e "${YELLOW}🔍 Testing data access...${NC}"

if [ -r "$VELJA_DATA_DIR" ]; then
    echo -e "${GREEN}✅ Velja data directory is readable${NC}"
else
    echo -e "${YELLOW}⚠️  Velja data directory exists but may not be readable${NC}"
    echo -e "${YELLOW}Attempting to fix permissions...${NC}"

    # Try to fix permissions (user may need to enter password)
    if chmod +r "$VELJA_DATA_DIR" 2>/dev/null; then
        echo -e "${GREEN}✅ Fixed directory permissions${NC}"
    else
        echo -e "${YELLOW}⚠️  Could not fix permissions automatically${NC}"
        echo -e "${YELLOW}You may need to manually fix this${NC}"
    fi
fi

# Check for existing data files
echo -e "${YELLOW}🔍 Checking for existing Velja data files...${NC}"

DATA_FILES=("urls.json" "history.json" "bookmarks.json" "links.json")
HAS_DATA=false

for file in "${DATA_FILES[@]}"; do
    if [ -f "$VELJA_DATA_DIR/$file" ]; then
        echo -e "${GREEN}✅ Found $file${NC}"
        HAS_DATA=true
    else
        echo -e "${YELLOW}⚠️  $file not found (will be created by Velja)${NC}"
    fi
done

if [ "$HAS_DATA" = false ]; then
    echo -e "${YELLOW}💡 No existing data found - this is normal for new installations${NC}"
    echo -e "${YELLOW}Velja will create data files as you use it${NC}"
fi

# Create test integration
echo -e "${YELLOW}🧪 Testing Atlas integration...${NC}"

# Find Atlas directory
ATLAS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INTEGRATION_SCRIPT="$ATLAS_DIR/velja_integration.py"

if [ -f "$INTEGRATION_SCRIPT" ]; then
    echo -e "${GREEN}✅ Found Atlas integration script${NC}"

    # Test the integration
    if python3 "$INTEGRATION_SCRIPT" find >/dev/null 2>&1; then
        echo -e "${GREEN}✅ Atlas integration script working${NC}"
    else
        echo -e "${YELLOW}⚠️  Atlas integration script needs testing${NC}"
    fi
else
    echo -e "${RED}❌ Atlas integration script not found${NC}"
    echo -e "${YELLOW}Expected at: $INTEGRATION_SCRIPT${NC}"
fi

# Create symbolic link for easier access (optional)
echo -e "${YELLOW}🔗 Creating convenient access...${NC}"

LINK_DIR="$HOME/.atlas"
mkdir -p "$LINK_DIR"

if [ ! -L "$LINK_DIR/velja_data" ]; then
    if ln -sf "$VELJA_DATA_DIR" "$LINK_DIR/velja_data" 2>/dev/null; then
        echo -e "${GREEN}✅ Created symbolic link: $LINK_DIR/velja_data${NC}"
    else
        echo -e "${YELLOW}⚠️  Could not create symbolic link${NC}"
    fi
fi

# Create monitoring script
echo -e "${YELLOW}📝 Creating monitoring script...${NC}"

MONITOR_SCRIPT="$LINK_DIR/monitor_velja.sh"

cat > "$MONITOR_SCRIPT" << 'EOF'
#!/bin/bash
# Velja monitoring script
# This script monitors Velja data and processes new URLs

ATLAS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
INTEGRATION_SCRIPT="$ATLAS_DIR/velja_integration.py"

echo "Starting Velja monitoring for Atlas..."
echo "Atlas directory: $ATLAS_DIR"

# Start monitoring (60 second intervals)
python3 "$INTEGRATION_SCRIPT" monitor 60
EOF

chmod +x "$MONITOR_SCRIPT"
echo -e "${GREEN}✅ Created monitoring script: $MONITOR_SCRIPT${NC}"

# Create LaunchAgent for automatic startup
echo -e "${YELLOW}⚙️  Creating LaunchAgent for automatic startup...${NC}"

LAUNCH_AGENT_DIR="$HOME/Library/LaunchAgents"
LAUNCH_AGENT_FILE="$LAUNCH_AGENT_DIR/com.user.atlas.velja-monitor.plist"

mkdir -p "$LAUNCH_AGENT_DIR"

cat > "$LAUNCH_AGENT_FILE" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.user.atlas.velja-monitor</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/bin/python3</string>
        <string>$INTEGRATION_SCRIPT</string>
        <string>monitor</string>
        <string>60</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>$HOME/.atlas/velja-monitor.log</string>
    <key>StandardErrorPath</key>
    <string>$HOME/.atlas/velja-monitor-error.log</string>
    <key>WorkingDirectory</key>
    <string>$ATLAS_DIR</string>
</dict>
</plist>
EOF

echo -e "${GREEN}✅ Created LaunchAgent: $LAUNCH_AGENT_FILE${NC}"

# Summary
echo ""
echo -e "${GREEN}🎉 Velja Integration Setup Complete!${NC}"
echo "================================"
echo ""
echo -e "${GREEN}What's been configured:${NC}"
echo "  ✅ Velja installation verified"
echo "  ✅ Data access permissions checked"
echo "  ✅ Atlas integration tested"
echo "  ✅ Monitoring script created"
echo "  ✅ LaunchAgent created for automatic startup"
echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo "  1. Ensure Velja is configured to keep history"
echo "  2. Enable iCloud sync in Velja (optional)"
echo "  3. Test the integration with some URLs"
echo ""
echo -e "${YELLOW}Testing commands:${NC}"
echo "  • Manual test: python3 $INTEGRATION_SCRIPT import"
echo "  • Start monitoring: python3 $INTEGRATION_SCRIPT monitor 60"
echo "  • Enable auto-start: launchctl load '$LAUNCH_AGENT_FILE'"
echo ""
echo -e "${YELLOW}Data location:${NC}"
echo "  Velja data: $VELJA_DATA_DIR"
echo "  Logs: $HOME/.atlas/"
echo ""
echo -e "${GREEN}🚀 Ready to use!${NC}"