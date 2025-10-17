#!/bin/bash
# Install Atlas as a systemd service (like PiHole)
# Runs 24/7 and auto-starts on boot

set -e

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${BLUE}🛠️  Installing Atlas as System Service${NC}"
echo "=========================================="

# Get current directory and user
ATLAS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ATLAS_USER="$(whoami)"

# Check if we're root (we need sudo for systemd)
if [[ $EUID -eq 0 ]]; then
   echo -e "${RED}❌ Don't run this as root. Run as regular user with sudo access.${NC}"
   exit 1
fi

# Check sudo access
if ! sudo -n true 2>/dev/null; then
    echo -e "${YELLOW}🔐 This script needs sudo access to install system service${NC}"
    sudo -v
fi

# Create systemd service file
echo -e "${BLUE}📝 Creating systemd service file...${NC}"

sudo tee /etc/systemd/system/atlas.service > /dev/null <<EOF
[Unit]
Description=Atlas Content Intelligence Platform
After=network-online.target
Wants=network-online.target
StartLimitIntervalSec=300
StartLimitBurst=5

[Service]
Type=forking
User=${ATLAS_USER}
Group=${ATLAS_USER}
WorkingDirectory=${ATLAS_DIR}
Environment=PATH=${ATLAS_DIR}/venv/bin:/usr/local/bin:/usr/bin:/bin
ExecStartPre=/bin/bash -c 'cd ${ATLAS_DIR} && source venv/bin/activate && python3 -c "print(\\"Atlas environment ready\\")"'
ExecStart=/bin/bash -c 'cd ${ATLAS_DIR} && source venv/bin/activate && python3 atlas_service_manager.py start --daemon'
ExecStop=/bin/bash -c 'cd ${ATLAS_DIR} && source venv/bin/activate && python3 atlas_service_manager.py stop'
ExecReload=/bin/bash -c 'cd ${ATLAS_DIR} && source venv/bin/activate && python3 atlas_service_manager.py restart'
Restart=always
RestartSec=10
TimeoutStartSec=60
TimeoutStopSec=30
StandardOutput=journal
StandardError=journal
SyslogIdentifier=atlas

# Resource limits
LimitNOFILE=65536
MemoryMax=2G

# Security settings
NoNewPrivileges=true
PrivateTmp=true
ProtectKernelTunables=true
ProtectControlGroups=true
RestrictRealtime=true

[Install]
WantedBy=multi-user.target
EOF

# Set correct permissions
sudo chmod 644 /etc/systemd/system/atlas.service

# Reload systemd to recognize new service
echo -e "${BLUE}🔄 Reloading systemd daemon...${NC}"
sudo systemctl daemon-reload

# Enable service to start on boot
echo -e "${BLUE}🚀 Enabling Atlas service to start on boot...${NC}"
sudo systemctl enable atlas.service

# Make sure virtual environment and dependencies are set up
echo -e "${BLUE}🐍 Ensuring virtual environment is ready...${NC}"
cd "$ATLAS_DIR"
if [ ! -d "venv" ]; then
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
else
    source venv/bin/activate
fi

# Make sure configuration exists
if [ ! -f ".env" ]; then
    if [ -f "env.template" ]; then
        cp env.template .env
        echo -e "${YELLOW}⚠️  Created .env from template. Please edit with your API keys:${NC}"
        echo -e "${YELLOW}    nano ${ATLAS_DIR}/.env${NC}"
    fi
fi

# Stop any existing Atlas processes first
echo -e "${BLUE}🛑 Stopping any existing Atlas processes...${NC}"
python3 atlas_service_manager.py stop >/dev/null 2>&1 || true
sudo pkill -f atlas_service_manager >/dev/null 2>&1 || true

# Start the service
echo -e "${BLUE}▶️  Starting Atlas service...${NC}"
sudo systemctl start atlas.service

# Wait a moment and check status
sleep 5
if sudo systemctl is-active --quiet atlas.service; then
    echo -e "${GREEN}✅ Atlas service is running!${NC}"
else
    echo -e "${RED}❌ Service failed to start. Checking logs...${NC}"
    sudo journalctl -u atlas.service --no-pager -n 20
    exit 1
fi

# Show status
echo ""
echo -e "${GREEN}🎉 Atlas Installation Complete!${NC}"
echo ""
echo -e "${BLUE}📋 Service Status:${NC}"
sudo systemctl status atlas.service --no-pager -l

echo ""
echo -e "${BLUE}🎯 Atlas is now installed like PiHole:${NC}"
echo "  ✅ Runs 24/7 automatically"
echo "  ✅ Starts on boot/reboot"
echo "  ✅ Auto-restarts if it crashes"
echo "  ✅ Resource limits and security hardening"
echo ""
echo -e "${BLUE}🔧 Service Management:${NC}"
echo "  sudo systemctl status atlas     # Check status"
echo "  sudo systemctl restart atlas    # Restart service"
echo "  sudo systemctl stop atlas       # Stop service"
echo "  sudo systemctl disable atlas    # Disable auto-start"
echo "  sudo journalctl -u atlas -f     # View live logs"
echo ""
echo -e "${BLUE}📊 Monitor Atlas:${NC}"
echo "  python3 ${ATLAS_DIR}/atlas_monitor.py    # System health dashboard"
echo ""
echo -e "${GREEN}Atlas will now survive reboots and run continuously!${NC}"
EOF