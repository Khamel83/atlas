#!/bin/bash
# Run Atlas commands with decrypted secrets
#
# Usage: ./run_with_secrets.sh <command>
# Example: ./run_with_secrets.sh python -m modules.ingest.gmail_ingester

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
SECRETS_FILE="$PROJECT_DIR/secrets.env.encrypted"

# Check if secrets file exists
if [ ! -f "$SECRETS_FILE" ]; then
    echo "Error: Secrets file not found at $SECRETS_FILE"
    exit 1
fi

# Decrypt and export secrets as environment variables
eval "$(sops --decrypt --input-type dotenv --output-type dotenv "$SECRETS_FILE" | grep -v '^#' | grep '=' | sed 's/^/export /')"

# Change to project directory and activate venv
cd "$PROJECT_DIR"
if [ -f ".venv/bin/activate" ]; then
    source .venv/bin/activate
fi

# Run the command
exec "$@"
