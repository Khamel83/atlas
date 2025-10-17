#!/bin/bash

# Atlas Quick Launch Script
# This script quickly starts Atlas services

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

print_error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

# Check if we're in the Atlas directory
if [ ! -f "run.py" ]; then
    print_error "This script must be run from the Atlas root directory"
    exit 1
fi

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    print_warning "Virtual environment not found. Creating one..."
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
else
    source venv/bin/activate
fi

# Check system health
print_status "Checking system health..."
if ! python helpers/resource_monitor.py; then
    print_error "System health check failed. Please check logs."
    exit 1
fi

# Start Atlas services
print_status "Starting Atlas services..."
if python atlas_service_manager.py start; then
    print_status "Atlas services started successfully!"
else
    print_error "Failed to start Atlas services"
    exit 1
fi

# Start web dashboard
print_status "Starting web dashboard..."
python web/app.py &

# Display status
print_status "Atlas Quick Launch Complete!"
echo ""
echo "Services running:"
echo "  - Atlas background services"
echo "  - Web dashboard (http://localhost:8000)"
echo ""
echo "To stop services, run: python atlas_service_manager.py stop"
echo "To check status, run: python atlas_service_manager.py status"
echo ""
echo "Access the web dashboard at: http://localhost:8000"
echo "Access the cognitive dashboard at: http://localhost:8000/ask/html"