#!/bin/bash
# Direct bridge to OOS consultant command
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
"$SCRIPT_DIR/oos-command.sh" consultant "$@"