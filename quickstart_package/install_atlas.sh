#!/bin/bash

# Atlas Automated Installation Script
# This script installs Atlas with minimal user interaction

set -euo pipefail

echo "🚀 Atlas Automated Installation"
echo "================================="

# Check system requirements
echo "🔍 Checking system requirements..."

# Check OS
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    echo "✅ Linux detected"
    OS="linux"
elif [[ "$OSTYPE" == "darwin"* ]]; then
    echo "✅ macOS detected"
    OS="macos"
else
    echo "❌ Unsupported operating system"
    exit 1
fi

# Check Python version
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
    echo "✅ Python $PYTHON_VERSION found"
else
    echo "❌ Python 3 not found. Please install Python 3.9 or higher."
    exit 1
fi

# Check git
if command -v git &> /dev/null; then
    echo "✅ Git found"
else
    echo "❌ Git not found. Please install Git."
    exit 1
fi

# Create installation directory
INSTALL_DIR="$HOME/atlas"
echo "📂 Creating installation directory: $INSTALL_DIR"
mkdir -p "$INSTALL_DIR"

# Clone repository
echo "📥 Cloning Atlas repository..."
cd "$INSTALL_DIR"
if [ ! -d ".git" ]; then
    git clone https://github.com/your-username/atlas.git .
else
    echo "🔄 Updating existing repository..."
    git pull
fi

# Create virtual environment
echo "🐍 Creating virtual environment..."
python3 -m venv venv
source venv/bin/activate

# Install dependencies
echo "📦 Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Run setup wizard
echo "⚙️  Running setup wizard..."
python scripts/setup_wizard.py --automated

# Create sample configuration
echo "📝 Creating sample configuration..."
cp .env.template .env
echo "# Sample configuration created by quick start installer" >> .env
echo "# Please update with your actual API keys and preferences" >> .env

# Create sample input files
echo "📄 Creating sample input files..."
mkdir -p inputs
echo "https://example.com/sample-article1" > inputs/articles.txt
echo "https://example.com/sample-article2" >> inputs/articles.txt

# Create systemd service (Linux only)
if [ "$OS" = "linux" ]; then
    echo "サービ Creating systemd service..."
    sudo tee /etc/systemd/system/atlas.service > /dev/null << 'EOF'
[Unit]
Description=Atlas Content Intelligence Platform
After=network-online.target

[Service]
Type=simple
User=%i
WorkingDirectory=/home/%i/atlas
Environment=PATH=/home/%i/atlas/venv/bin
ExecStart=/home/%i/atlas/venv/bin/python atlas_service_manager.py start
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

    sudo systemctl daemon-reload
    echo "✅ Systemd service created. Enable with: sudo systemctl enable atlas.service"
fi

# Display completion message
echo ""
echo "🎉 Atlas Installation Complete!"
echo "================================"
echo ""
echo "Next steps:"
echo "1. Activate virtual environment: source $INSTALL_DIR/venv/bin/activate"
echo "2. Update configuration: nano $INSTALL_DIR/.env"
echo "3. Start services: python $INSTALL_DIR/atlas_service_manager.py start"
echo "4. Process content: python $INSTALL_DIR/run.py --articles"
echo "5. Access web dashboard: python $INSTALL_DIR/web/app.py"
echo ""
echo "📖 Read the full documentation: $INSTALL_DIR/docs/user-guides/SETUP_GUIDE.md"
echo ""
echo "Enjoy Atlas! 🚀🧠"