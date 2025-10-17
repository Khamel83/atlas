#!/usr/bin/env bash
set -euo pipefail
ENV_FILE="${1:-.env}"
# Normalize CRLF, strip UTF-8 BOM, drop surrounding file quotes (if any), drop blank + comment lines
tr -d '\r' < "$ENV_FILE" \
| sed '1s/^\xEF\xBB\xBF//' \
| sed '1s/^"//;$s/"$//' \
| awk 'NF && $1 !~ /^#/' > .env.export
set -a
. ./.env.export
set +a
