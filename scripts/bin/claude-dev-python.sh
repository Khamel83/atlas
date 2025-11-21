#!/usr/bin/env bash
set -euo pipefail

# Claude Code Python Command with Development Gate
# Usage: /dev-python [python arguments]

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Require development gate before running Python
if ! "$SCRIPT_DIR/claude-require-gate.sh" "python"; then
    exit 1
fi

# Gate passed, run Python with uv
echo "🐍 Running Python in validated environment..."
exec uv run python "$@"