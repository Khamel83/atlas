#!/usr/bin/env bash
set -euo pipefail

# Shell Environment Setup for Mandatory Development Gate
# Adds interceptors to PATH and sets up environment

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Add interceptors to PATH (prepend so they take precedence)
export PATH="$PROJECT_ROOT/bin/interceptors:$PATH"

# Set up gate environment check function
dev_gate_check() {
    if [[ ! -f "$PROJECT_ROOT/.dev-gate-passed" ]]; then
        echo "⚠️  Development gate not passed. Run: ./bin/dev-gate.sh"
        return 1
    fi

    # Check if gate is recent (within last hour)
    local gate_time=$(stat -f %m "$PROJECT_ROOT/.dev-gate-passed" 2>/dev/null || stat -c %Y "$PROJECT_ROOT/.dev-gate-passed" 2>/dev/null)
    local current_time=$(date +%s)
    local age=$((current_time - gate_time))

    if [[ $age -gt 3600 ]]; then
        echo "⚠️  Development gate is stale. Run: ./bin/dev-gate.sh"
        return 1
    fi

    return 0
}

# Add helpful aliases
alias gate='./bin/dev-gate.sh'
alias check-env='dev_gate_check'

# Show status when sourcing
if dev_gate_check 2>/dev/null; then
    echo "✅ Development environment ready"
else
    echo "⚠️  Development environment needs validation"
    echo "Run: ./bin/dev-gate.sh"
fi
