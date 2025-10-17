#!/bin/bash
# Atlas v4 Installation Script

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check Python
check_python() {
    print_status "Checking Python installation..."
    if command -v python3 &> /dev/null; then
        PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
        print_status "Found Python $PYTHON_VERSION ✓"
        PYTHON_CMD="python3"
    else
        print_error "Python 3 is not installed"
        exit 1
    fi
}

# Create virtual environment
create_venv() {
    print_status "Creating virtual environment..."
    VENV_DIR="$HOME/.atlas-venv"

    if [ -d "$VENV_DIR" ]; then
        print_warning "Virtual environment already exists"
        return
    fi

    $PYTHON_CMD -m venv "$VENV_DIR"
    print_status "Virtual environment created at $VENV_DIR"
}

# Install Atlas
install_atlas() {
    print_status "Installing Atlas v4..."
    source "$VENV_DIR/bin/activate"
    pip install --upgrade pip

    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

    cd "$PROJECT_DIR"
    pip install -e .
    print_status "Atlas v4 installed successfully!"
}

# Create configuration
create_config() {
    print_status "Creating default configuration..."
    CONFIG_DIR="$HOME/.atlas"
    CONFIG_FILE="$CONFIG_DIR/config.yaml"

    mkdir -p "$CONFIG_DIR"

    if [ ! -f "$CONFIG_FILE" ]; then
        cat > "$CONFIG_FILE" << 'EOF'
# Atlas v4 Configuration
vault:
  root: ~/Documents/Atlas
  auto_create: true

logging:
  level: INFO
  file: ~/.atlas/atlas.log

validation:
  min_content_length: 100
  required_fields:
    - title
    - content
    - date
EOF
        print_status "Configuration created at $CONFIG_FILE"
    fi
}

# Main installation
main() {
    print_status "Starting Atlas v4 installation..."
    check_python
    create_venv
    install_atlas
    create_config

    print_status "Installation complete! 🎉"
    echo
    echo "To use Atlas:"
    echo "  source ~/.atlas-venv/bin/activate"
    echo "  atlas --help"
}

case "${1:-}" in
    --help|-h)
        echo "Atlas v4 Installation Script"
        echo "Usage: $0"
        exit 0
        ;;
    "")
        main
        ;;
    *)
        print_error "Unknown option: $1"
        exit 1
        ;;
esac