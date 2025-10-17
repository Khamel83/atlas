#!/bin/bash
set -e

echo "🚀 Atlas Quick Install Script"
echo "============================"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Check macOS
if [[ "$OSTYPE" != "darwin"* ]]; then
    echo -e "${RED}❌ This installer is for macOS only${NC}"
    echo "For Linux/Windows setup, see docs/user-guides/SETUP_GUIDE.md"
    exit 1
fi

echo -e "${BLUE}📋 Pre-flight checks...${NC}"

# Check Python version
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Python 3 not found${NC}"
    echo "Install Python 3.9+ from https://python.org"
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
echo -e "${GREEN}✅ Python ${PYTHON_VERSION} found${NC}"

# Check disk space
AVAILABLE_GB=$(df -g . | awk 'NR==2 {print $4}')
if [ "$AVAILABLE_GB" -lt 2 ]; then
    echo -e "${YELLOW}⚠️  Low disk space: ${AVAILABLE_GB}GB available (2GB recommended)${NC}"
fi

echo -e "${BLUE}🔧 Setting up virtual environment...${NC}"

# Create virtual environment
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo -e "${GREEN}✅ Virtual environment created${NC}"
fi

# Activate virtual environment
source venv/bin/activate
echo -e "${GREEN}✅ Virtual environment activated${NC}"

echo -e "${BLUE}📦 Installing dependencies...${NC}"

# Install requirements
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt > /dev/null 2>&1
    echo -e "${GREEN}✅ Dependencies installed${NC}"
else
    echo -e "${YELLOW}⚠️  requirements.txt not found, installing basic dependencies${NC}"
    pip install fastapi uvicorn python-multipart > /dev/null 2>&1
fi

echo -e "${BLUE}⚙️  Configuring Atlas...${NC}"

# Setup configuration
if [ ! -f ".env" ]; then
    if [ -f ".env.template" ]; then
        cp .env.template .env
        echo -e "${GREEN}✅ Configuration file created (.env)${NC}"
    else
        echo -e "${BLUE}Creating basic .env configuration...${NC}"
        cat > .env << 'EOF'
ATLAS_PORT=8000
ATLAS_HOST=localhost
ATLAS_DEBUG=false
ATLAS_DATA_DIR=data
ATLAS_LOGS_DIR=logs
EOF
        echo -e "${GREEN}✅ Basic configuration created${NC}"
    fi
else
    echo -e "${GREEN}✅ Configuration file exists${NC}"
fi

# Create necessary directories
mkdir -p data logs ~/Documents/Atlas/{inbox,articles,audio,images,archives}
echo -e "${GREEN}✅ Directory structure created${NC}"

echo -e "${BLUE}🧪 Testing Atlas...${NC}"

# Test basic functionality
if python3 -c "import sys; sys.path.append('.'); from atlas_status import main; main()" > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Atlas core modules working${NC}"
else
    echo -e "${YELLOW}⚠️  Some Atlas modules may need attention${NC}"
fi

echo -e "${BLUE}🎯 Starting Atlas service...${NC}"

# Start Atlas service
if [ -f "atlas_service_manager.py" ]; then
    python3 atlas_service_manager.py start > /dev/null 2>&1 &
    sleep 3

    # Check if service started
    if curl -s http://localhost:8000 > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Atlas service started successfully${NC}"
        SERVICE_STARTED=true
    else
        echo -e "${YELLOW}⚠️  Atlas service may need manual start${NC}"
        SERVICE_STARTED=false
    fi
else
    echo -e "${YELLOW}⚠️  Atlas service manager not found${NC}"
    SERVICE_STARTED=false
fi

echo ""
echo -e "${GREEN}🎉 Atlas Installation Complete!${NC}"
echo ""

if [ "$SERVICE_STARTED" = true ]; then
    echo -e "${BLUE}📱 Next Steps:${NC}"
    echo "1. Install Apple Shortcuts: ./install_shortcuts.sh"
    echo "2. Test voice capture: 'Hey Siri, save to Atlas'"
    echo "3. Visit dashboard: http://localhost:8000/ask/html"
    echo ""
    echo -e "${BLUE}📖 Documentation:${NC}"
    echo "• Quick Start: quick_start_package/QUICK_START.md"
    echo "• Mac Guide: docs/user-guides/MAC_USER_GUIDE.md"
    echo "• All Guides: docs/user-guides/"
else
    echo -e "${BLUE}🔧 Manual start needed:${NC}"
    echo "python3 atlas_service_manager.py start"
    echo ""
    echo -e "${BLUE}📖 Troubleshooting:${NC}"
    echo "• Check status: python3 atlas_status.py"
    echo "• View logs: tail -f logs/atlas_service.log"
    echo "• Setup guide: docs/user-guides/SETUP_GUIDE.md"
fi

echo ""
echo -e "${GREEN}Welcome to Atlas - Your Personal AI Knowledge System! 🧠${NC}"