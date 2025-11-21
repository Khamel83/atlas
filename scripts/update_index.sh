#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export CURRENT_TASK_ID="${CURRENT_TASK_ID:-}"
python3 "$ROOT/scripts/build_index.py" >/dev/null
echo "[index] updated"
