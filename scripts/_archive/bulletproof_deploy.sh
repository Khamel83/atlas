#!/bin/bash
set -euo pipefail

echo "🚀 Atlas Bulletproof Deployment Script"
echo "======================================"

# Pre-deployment checks
echo "📋 Pre-deployment checks..."
cd /home/ubuntu/dev/atlas

# Verify environment
./venv/bin/python --version
./venv/bin/python -c "import psutil; print(f'psutil {psutil.__version__}')"

# Run tests
echo "🧪 Running tests..."
./venv/bin/python -m pytest tests/test_memory_leaks.py -v
./venv/bin/python -m pytest tests/test_process_management.py -v

# System health check
./venv/bin/python helpers/resource_monitor.py

# Stop existing services
echo "⏹️ Stopping existing services..."
sudo systemctl stop atlas.service || echo "Service not running"
pkill -f "atlas_" || echo "No atlas processes found"

# Deploy new configuration
echo "📦 Deploying bulletproof configuration..."
sudo systemctl daemon-reload
sudo systemctl enable atlas.service

# Start services
echo "▶️ Starting services..."
sudo systemctl start atlas.service

# Verification
echo "✅ Deployment verification..."
sleep 10
sudo systemctl status atlas.service
./venv/bin/python atlas_status.py

echo "🎉 Bulletproof deployment completed successfully!"
