#!/bin/bash
# Rollback script for codebase rationalization
# Usage: ./scripts/rollback_rationalization.sh

set -e

echo "Rolling back codebase rationalization..."

git checkout codebase-rationalization-backup -- modules/
git checkout codebase-rationalization-backup -- scripts/

echo "Restarting systemd timers..."
sudo systemctl restart atlas-*.timer 2>/dev/null || true

echo "Rollback complete. Run ./venv/bin/pytest tests/ to verify."
