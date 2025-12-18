#!/usr/bin/env bash
set -euo pipefail

echo "[mcp] running worker check (process 5 jobs)"
python3 -m vos.cli worker --max-iterations 5
