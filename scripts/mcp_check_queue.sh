#!/usr/bin/env bash
set -euo pipefail

echo "[mcp] running queue check (pytest tests/test_queue.py)"
python3 -m pytest tests/test_queue.py
