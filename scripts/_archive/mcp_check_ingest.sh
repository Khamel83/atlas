#!/usr/bin/env bash
set -euo pipefail

python3 - <<'PY'
from os import getenv
from vos.ingestion.rss import poll_rss
from vos.ingestion.gmail import poll_gmail

rss_count = poll_rss()
print(f"[mcp] RSS poll created {rss_count} jobs")
username = getenv('GMAIL_USERNAME')
password = getenv('GMAIL_APP_PASSWORD')
if username and password:
    gmail_count = poll_gmail()
    print(f"[mcp] Gmail poll created {gmail_count} jobs")
else:
    print("[mcp] Gmail credentials missing; skipping Gmail poll")
PY
