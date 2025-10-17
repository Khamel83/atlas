#!/usr/bin/env bash
set -euo pipefail

# Claude Code Development Command Guard
# This script should be called before any development command to ensure gate is passed

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

COMMAND_NAME="${1:-command}"

# Check if gate is passed and recent
if [[ -f "$PROJECT_ROOT/.dev-gate-passed" ]]; then
    gate_time=$(stat -c %Y "$PROJECT_ROOT/.dev-gate-passed" 2>/dev/null || echo "0")
    current_time=$(date +%s)
    age=$((current_time - gate_time))

    if [[ $age -lt 3600 ]]; then
        # Gate is valid, allow command
        exit 0
    fi
fi

# Gate not passed or expired
echo -e "${RED}🚫 Development Command Blocked${NC}"
echo "============================="
echo
echo -e "${YELLOW}The command '$COMMAND_NAME' requires a valid development environment.${NC}"
echo
echo -e "${BLUE}To proceed:${NC}"
echo "  1. Run: /dev-gate pass"
echo "  2. Or run: /dev-gate bypass (emergency only)"
echo
echo -e "${YELLOW}Why this matters:${NC}"
echo "  • Ensures uv environment is synced"
echo "  • Validates 1Password authentication"
echo "  • Confirms all development tools are ready"
echo "  • Prevents environment drift and errors"

exit 1