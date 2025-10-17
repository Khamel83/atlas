#!/bin/bash
# Archon Telegram Ingest - Complete OCI Deployment Script
# ========================================================
# This script deploys the entire Telegram → Atlas pipeline on OCI

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PROJECT_DIR="/opt/archon-telegram-ingest"
SERVICE_NAME="archon-telegram-ingest"
SERVICE_PORT="8081"

echo -e "${BLUE}🚀 Archon Telegram Ingest Deployment${NC}"
echo "===================================="

# Check if running as root
if [[ $EUID -eq 0 ]]; then
   echo -e "${RED}❌ Do not run this script as root. Use sudo for individual commands.${NC}"
   exit 1
fi

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

echo -e "${YELLOW}📋 Pre-flight checks...${NC}"

# Check required commands
for cmd in python3 pip curl systemctl; do
    if ! command_exists "$cmd"; then
        echo -e "${RED}❌ Required command not found: $cmd${NC}"
        exit 1
    fi
done

echo -e "${GREEN}✅ All required commands available${NC}"

# Create project directory
echo -e "${YELLOW}📁 Creating project directory...${NC}"
sudo mkdir -p "$PROJECT_DIR"
sudo chown "$USER:$USER" "$PROJECT_DIR"

# Copy files to project directory
echo -e "${YELLOW}📦 Copying project files...${NC}"
cp telegram_webhook.py "$PROJECT_DIR/"
cp .env.example "$PROJECT_DIR/.env"
cp requirements.txt "$PROJECT_DIR/" 2>/dev/null || echo "fastapi==0.104.1
uvicorn[standard]==0.24.0
requests==2.31.0
python-dotenv==1.0.0" > "$PROJECT_DIR/requirements.txt"

# Create Python virtual environment
echo -e "${YELLOW}🐍 Setting up Python environment...${NC}"
cd "$PROJECT_DIR"
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

echo -e "${GREEN}✅ Python environment ready${NC}"

# Create systemd service
echo -e "${YELLOW}⚙️  Creating systemd service...${NC}"
sudo tee "/etc/systemd/system/${SERVICE_NAME}.service" > /dev/null << EOF
[Unit]
Description=Archon Telegram Ingest Service
Documentation=https://github.com/your-org/archon-telegram-ingest
After=network-online.target
Wants=network-online.target

[Service]
Type=exec
User=$USER
Group=$USER
WorkingDirectory=$PROJECT_DIR
Environment=PATH=$PROJECT_DIR/venv/bin
EnvironmentFile=$PROJECT_DIR/.env
ExecStart=$PROJECT_DIR/venv/bin/uvicorn telegram_webhook:app --host 127.0.0.1 --port $SERVICE_PORT
ExecReload=/bin/kill -HUP \$MAINPID
Restart=always
RestartSec=5
StartLimitInterval=0

# Security settings
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=$PROJECT_DIR
PrivateTmp=true
ProtectKernelTunables=true
ProtectKernelModules=true
ProtectControlGroups=true

[Install]
WantedBy=multi-user.target
EOF

# Reload systemd and enable service
sudo systemctl daemon-reload
sudo systemctl enable "$SERVICE_NAME"

echo -e "${GREEN}✅ Systemd service created and enabled${NC}"

# Install and configure Caddy (if not already installed)
if ! command_exists caddy; then
    echo -e "${YELLOW}📡 Installing Caddy...${NC}"
    sudo apt-get update
    sudo apt-get install -y debian-keyring debian-archive-keyring apt-transport-https
    curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | sudo gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
    curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | sudo tee /etc/apt/sources.list.d/caddy-stable.list
    sudo apt-get update
    sudo apt-get install -y caddy
    echo -e "${GREEN}✅ Caddy installed${NC}"
fi

# Create Caddy configuration example
echo -e "${YELLOW}📡 Creating Caddy configuration example...${NC}"
sudo tee "/etc/caddy/Caddyfile.telegram-example" > /dev/null << 'EOF'
# Add this to your main Caddyfile:

your-domain.com {
    encode zstd gzip

    # Telegram webhook endpoint
    @telegram path /telegram/*
    handle @telegram {
        reverse_proxy 127.0.0.1:8081
    }

    # Your other services...
}
EOF

echo -e "${YELLOW}⚠️  Manual step required: Update your Caddy configuration${NC}"
echo -e "   1. Edit ${BLUE}/etc/caddy/Caddyfile${NC}"
echo -e "   2. Add the telegram webhook proxy configuration"
echo -e "   3. Run: ${BLUE}sudo systemctl reload caddy${NC}"

# Configuration reminder
echo ""
echo -e "${YELLOW}📝 Configuration required:${NC}"
echo -e "   1. Edit ${BLUE}$PROJECT_DIR/.env${NC} with your credentials:"
echo -e "      - TELEGRAM_BOT_TOKEN"
echo -e "      - WEBHOOK_SECRET (generate a long random string)"
echo -e "      - ATLAS_URL"
echo -e "      - DOMAIN"
echo ""
echo -e "   2. Start the service: ${BLUE}sudo systemctl start $SERVICE_NAME${NC}"
echo ""
echo -e "   3. Set Telegram webhook:"
echo -e "      ${BLUE}curl -X POST \"https://api.telegram.org/bot\$TELEGRAM_BOT_TOKEN/setWebhook\" \\${NC}"
echo -e "      ${BLUE}  -d \"url=https://\$DOMAIN/telegram/\$WEBHOOK_SECRET\"${NC}"
echo ""

# Final instructions
echo -e "${GREEN}🎉 Deployment complete!${NC}"
echo ""
echo -e "${BLUE}Next steps:${NC}"
echo -e "   1. Configure .env file"
echo -e "   2. Update Caddy configuration"
echo -e "   3. Start service: ${BLUE}sudo systemctl start $SERVICE_NAME${NC}"
echo -e "   4. Check status: ${BLUE}sudo systemctl status $SERVICE_NAME${NC}"
echo -e "   5. View logs: ${BLUE}sudo journalctl -u $SERVICE_NAME -f${NC}"
echo ""
echo -e "${BLUE}Service will be available at:${NC}"
echo -e "   Local: http://127.0.0.1:$SERVICE_PORT"
echo -e "   Public: https://your-domain.com/telegram/your-webhook-secret"