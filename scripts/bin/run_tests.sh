#!/usr/bin/env bash
set -euo pipefail

# Run the PYTHONPATH=$PROJECT_ROOT pytest test suite

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$PROJECT_ROOT"

echo "Running tests..."
PYTHONPATH=$PROJECT_ROOT pytest
