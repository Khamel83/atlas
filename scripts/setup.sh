#!/usr/bin/env bash
# ONE_SHOT Standard: setup.sh
# First-time setup for Atlas

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

echo "=========================================="
echo "  Atlas Setup"
echo "=========================================="
echo ""

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python 3 is required but not installed."
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
echo "Python version: $PYTHON_VERSION"

# Create virtual environment if needed
if [ ! -d "venv" ]; then
    echo ""
    echo "Creating virtual environment..."
    python3 -m venv venv
    echo "Virtual environment created."
fi

# Activate and install dependencies
echo ""
echo "Installing dependencies..."
./venv/bin/pip install --upgrade pip -q
./venv/bin/pip install -r requirements.txt -q

# Create .env from template if needed
if [ -f ".env.template" ] && [ ! -f ".env" ]; then
    cp .env.template .env
    echo ""
    echo "Created .env from template - please edit with your configuration"
fi

# Create required directories
mkdir -p logs data/databases .oneshot

# Initialize database if needed
if [ ! -f "podcast_processing.db" ] && [ ! -f "data/databases/podcast_processing.db" ]; then
    echo ""
    echo "Note: Database will be created on first run"
fi

echo ""
echo "=========================================="
echo "  Setup Complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "  1. Edit .env with your configuration (if needed)"
echo "  2. Run: ./scripts/start.sh"
echo "  3. Check: ./scripts/status.sh"
echo ""
