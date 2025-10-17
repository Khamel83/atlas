#!/bin/bash
# OOS Command Handler - Bridge to Python command system
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OOS_DIR="$(dirname "$SCRIPT_DIR")"
python3 "$OOS_DIR/src/simple_command_handler.py" "$@"