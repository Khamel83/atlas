#!/usr/bin/env bash
set -euo pipefail

# Claude Code UV Command with Development Gate
# Usage: /dev-uv [uv arguments]

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Require development gate before running uv
if ! "$SCRIPT_DIR/claude-require-gate.sh" "uv"; then
    exit 1
fi

# Gate passed, run uv
echo "📦 Running uv in validated environment..."
exec uv "$@"