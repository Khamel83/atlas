#!/bin/bash
# OOS One-Command Installer
# Usage: curl -sSL install.oos.dev | bash

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
WHITE='\033[0;37m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# Print banner
echo -e "${CYAN}${BOLD}"
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║                                                              ║"
echo "   🚀 OOS One-Command Installer                                 ║"
echo "   Build AI projects without coding • Zero configuration        ║"
echo "                                                              ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Functions for output
print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    print_error "Python 3 is required but not installed"
    print_info "Please install Python 3.8+ and try again"
    exit 1
fi

# Check Python version
python_version=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
if [[ "$python_version" < "3.8" ]]; then
    print_error "Python 3.8+ is required (found $python_version)"
    exit 1
fi

print_success "Python $python_version detected"

# Create temporary directory
temp_dir=$(mktemp -d)
cd "$temp_dir"

print_info "Downloading OOS installer..."

# Download the setup script (in production, this would be from a real URL)
# For now, we'll copy from the current directory if this is being run locally
if [[ -f "/home/ubuntu/dev/oos/scripts/oos-setup.py" ]]; then
    cp "/home/ubuntu/dev/oos/scripts/oos-setup.py" "oos-setup.py"
else
    # Fallback: download from GitHub (this URL would be real in production)
    curl -sSL "https://raw.githubusercontent.com/yourusername/oos/main/scripts/oos-setup.py" -o "oos-setup.py" || {
        print_error "Failed to download OOS installer"
        print_info "Please check your internet connection and try again"
        exit 1
    }
fi

print_success "Download complete"

# Make it executable
chmod +x "oos-setup.py"

print_info "Starting OOS setup..."
print_info "This will only ask for your OpenRouter API key"
print_info "Everything else will be configured automatically"

# Run the setup script
python3 "oos-setup.py"

# Cleanup
cd - > /dev/null
rm -rf "$temp_dir"

echo
echo -e "${GREEN}${BOLD}🎉 OOS Installation Complete!${NC}"
echo
echo -e "${CYAN}What's next?${NC}"
echo -e "${WHITE}  1. Restart your terminal or run: source ~/.bashrc${NC}"
echo -e "${WHITE}  2. Try your first command: oos help${NC}"
echo -e "${WHITE}  3. Create something: oos create chatbot${NC}"
echo
echo -e "${YELLOW}Need help?${NC}"
echo -e "${WHITE}  • Type: oos help me <anything>${NC}"
echo -e "${WHITE}  • All commands explain what they're doing${NC}"
echo -e "${WHITE}  • Safe by default - can't break anything${NC}"
echo
echo -e "${GREEN}Welcome to OOS! 🚀${NC}"