#!/bin/bash
# Runs the Gemini agent with a secure environment

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Use the secure wrapper to execute the agent
"$PROJECT_ROOT/bin/secure_exec" gemini chat