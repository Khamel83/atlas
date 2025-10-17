#!/bin/bash
# Simple Atlas Auto-Start Installation (PiHole-like reliability)
# Adds Atlas to crontab for reboot persistence

set -e

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${BLUE}🎯 Installing Atlas Auto-Start${NC}"
echo "=================================="

# Get current directory
ATLAS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ATLAS_USER="$(whoami)"

echo -e "${BLUE}📝 Creating startup script...${NC}"

# Create the autostart script
cat > "${ATLAS_DIR}/atlas_autostart.sh" <<EOF
#!/bin/bash
# Atlas Auto-Start Script - runs on boot
cd "${ATLAS_DIR}"
export PATH="${ATLAS_DIR}/venv/bin:/usr/local/bin:/usr/bin:/bin"
source venv/bin/activate
python3 atlas_service_manager.py start --daemon >> logs/autostart.log 2>&1
EOF

chmod +x "${ATLAS_DIR}/atlas_autostart.sh"

echo -e "${BLUE}📅 Adding to crontab for boot startup...${NC}"

# Create crontab entry (remove existing first to avoid duplicates)
(crontab -l 2>/dev/null | grep -v "atlas_autostart.sh") | crontab -
(crontab -l 2>/dev/null; echo "@reboot sleep 30 && ${ATLAS_DIR}/atlas_autostart.sh") | crontab -

# Also add a health check every 5 minutes
(crontab -l 2>/dev/null | grep -v "atlas_monitor.py") | crontab -
(crontab -l 2>/dev/null; echo "*/5 * * * * cd ${ATLAS_DIR} && source venv/bin/activate && python3 atlas_service_manager.py status >/dev/null 2>&1 || ${ATLAS_DIR}/atlas_autostart.sh") | crontab -

echo -e "${BLUE}🔍 Verifying crontab installation...${NC}"
crontab -l | grep atlas

echo ""
echo -e "${GREEN}✅ Atlas Auto-Start Installed!${NC}"
echo ""
echo -e "${BLUE}🎯 Atlas will now:${NC}"
echo "  ✅ Start automatically on boot (after 30 second delay)"
echo "  ✅ Auto-restart if it fails (checked every 5 minutes)"
echo "  ✅ Run continuously like PiHole"
echo "  ✅ Survive reboots and system updates"
echo ""
echo -e "${BLUE}🔧 Management Commands:${NC}"
echo "  ./start_atlas.sh                   # Manual start"
echo "  python3 atlas_service_manager.py status  # Check status"
echo "  python3 atlas_monitor.py          # Full health check"
echo "  crontab -l | grep atlas           # View autostart entries"
echo ""
echo -e "${BLUE}📊 Logs:${NC}"
echo "  tail -f logs/autostart.log        # Boot startup logs"
echo "  tail -f logs/atlas_manager.log    # Service manager logs"
echo ""
echo -e "${GREEN}Atlas is now PiHole-reliable! 🎉${NC}"