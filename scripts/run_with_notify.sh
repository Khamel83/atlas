#!/bin/bash
# Run Atlas commands with notifications on failure
#
# Usage: ./run_with_notify.sh <component_name> <command> [args...]
# Example: ./run_with_notify.sh gmail python -m modules.ingest.gmail_ingester

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
SECRETS_FILE="$PROJECT_DIR/secrets.env.encrypted"

COMPONENT="$1"
shift

if [ -z "$COMPONENT" ]; then
    echo "Usage: $0 <component_name> <command> [args...]"
    exit 1
fi

# Decrypt and export secrets
if [ -f "$SECRETS_FILE" ]; then
    eval "$(sops --decrypt --input-type dotenv --output-type dotenv "$SECRETS_FILE" 2>/dev/null | grep -v '^#' | grep '=' | sed 's/^/export /')"
fi

cd "$PROJECT_DIR"
if [ -f ".venv/bin/activate" ]; then
    source .venv/bin/activate
fi

# Run the command and capture exit code
set +e
OUTPUT=$("$@" 2>&1)
EXIT_CODE=$?
set -e

if [ $EXIT_CODE -ne 0 ]; then
    # Send failure notification
    python -c "
from modules.notifications import notify_error
notify_error(
    '$COMPONENT',
    '''Exit code: $EXIT_CODE''',
    '''$OUTPUT'''[:500] if '''$OUTPUT''' else None
)
" 2>/dev/null || true

    echo "Command failed with exit code $EXIT_CODE"
    echo "$OUTPUT"
    exit $EXIT_CODE
fi

echo "$OUTPUT"
exit 0
