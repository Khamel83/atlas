#!/bin/bash
# Atlas SystemD Service Installation Script
#
# This script installs all Atlas systemd services with proper dependency ordering
# and bulletproof auto-restart policies.

set -e

ATLAS_DIR="/home/ubuntu/dev/atlas"
SYSTEMD_DIR="$ATLAS_DIR/systemd"
SYSTEM_SYSTEMD_DIR="/etc/systemd/system"

echo "🚀 Installing Atlas SystemD Services..."

# Check if running as root for system service installation
if [[ $EUID -ne 0 ]]; then
   echo "❌ This script must be run as root (use sudo)"
   echo "Usage: sudo bash scripts/install-systemd-services.sh"
   exit 1
fi

# Create necessary directories
echo "📁 Creating directories..."
mkdir -p /var/log/atlas
mkdir -p /var/lib/atlas
chown -R ubuntu:ubuntu /var/log/atlas /var/lib/atlas

# Copy service files to systemd directory
echo "📋 Installing service files..."
services=(
    "atlas-api.service"
    "atlas-google-search.service"
    "atlas-manager.service"
    "atlas-web.service"
    "atlas-health-monitor.service"
    "atlas-watchdog.service"
    "atlas.target"
)

for service in "${services[@]}"; do
    if [[ -f "$SYSTEMD_DIR/$service" ]]; then
        echo "  Installing $service..."
        cp "$SYSTEMD_DIR/$service" "$SYSTEM_SYSTEMD_DIR/"
        chmod 644 "$SYSTEM_SYSTEMD_DIR/$service"
    else
        echo "  ⚠️  Warning: $service not found, skipping..."
    fi
done

# Copy timer files if they exist
timers=(
    "atlas-discovery.timer"
    "atlas-watchdog.timer"
)

for timer in "${timers[@]}"; do
    if [[ -f "$SYSTEMD_DIR/$timer" ]]; then
        echo "  Installing $timer..."
        cp "$SYSTEMD_DIR/$timer" "$SYSTEM_SYSTEMD_DIR/"
        chmod 644 "$SYSTEM_SYSTEMD_DIR/$timer"
    fi
done

# Reload systemd daemon
echo "🔄 Reloading systemd daemon..."
systemctl daemon-reload

# Enable services (but don't start yet)
echo "✅ Enabling Atlas services..."
systemctl enable atlas.target
systemctl enable atlas-api.service
systemctl enable atlas-manager.service
systemctl enable atlas-google-search.service
systemctl enable atlas-web.service
systemctl enable atlas-health-monitor.service
systemctl enable atlas-watchdog.service

# Enable timers if they exist
for timer in "${timers[@]}"; do
    if [[ -f "$SYSTEM_SYSTEMD_DIR/$timer" ]]; then
        echo "  Enabling $timer..."
        systemctl enable "$timer"
    fi
done

echo ""
echo "🎉 Atlas SystemD Services Installed Successfully!"
echo ""
echo "📋 Available commands:"
echo "  Start all services:    sudo systemctl start atlas.target"
echo "  Stop all services:     sudo systemctl stop atlas.target"
echo "  Restart all services:  sudo systemctl restart atlas.target"
echo "  Check status:          sudo systemctl status atlas.target"
echo "  View logs:             journalctl -u atlas-api.service -f"
echo ""
echo "🔧 Individual service management:"
echo "  sudo systemctl [start|stop|restart|status] atlas-[api|manager|google-search|web|health-monitor].service"
echo ""
echo "⚡ Auto-restart is enabled for all services with 5-second delays"
echo "🛡️  Resource limits and health monitoring are configured"
echo "📊 All logs go to journald - use 'journalctl -u [service-name] -f' to view"
echo ""
echo "To start Atlas now: sudo systemctl start atlas.target"