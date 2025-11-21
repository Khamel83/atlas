#!/bin/bash
# Simple service installer for Atlas Manager

set -e

SERVICE_FILE="atlas-manager.service"
SERVICE_PATH="$HOME/.config/systemd/user/$SERVICE_FILE"

echo "🔧 Installing Atlas Manager service..."

# Create systemd user directory if it doesn't exist
mkdir -p "$HOME/.config/systemd/user"

# Copy service file
cp "$SERVICE_FILE" "$SERVICE_PATH"

# Reload systemd
systemctl --user daemon-reload

# Enable service
systemctl --user enable "$SERVICE_FILE"

echo "✅ Service installed successfully!"
echo ""
echo "Service management commands:"
echo "  Start:    systemctl --user start atlas-manager.service"
echo "  Stop:     systemctl --user stop atlas-manager.service"
echo "  Status:   systemctl --user status atlas-manager.service"
echo "  Logs:     journalctl --user -u atlas-manager.service -f"
echo ""
echo "Starting service now..."

# Start the service
systemctl --user start "$SERVICE_FILE"

# Show status
sleep 2
systemctl --user status "$SERVICE_FILE"