#!/usr/bin/env bash
set -euo pipefail

# Claude Code Test Command with Development Gate
# Usage: /dev-test [pytest arguments]

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Require development gate before running tests
if ! "$SCRIPT_DIR/claude-require-gate.sh" "pytest"; then
    exit 1
fi

# Gate passed, run tests with uv
echo "🧪 Running tests in validated environment..."
exec uv run pytest "$@"