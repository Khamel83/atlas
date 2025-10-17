#!/usr/bin/env bash
set -euo pipefail
IN="${1:-.env}"; OUT="${2:-.env.active}"
sed -e 's/\r$//' "$IN" | awk 'NF && $1 !~ /^#/' > .env.export
set -a; . ./.env.export; set +a
: "${OPENAI_API_BASE_URL:=https://openrouter.ai/api/v1}"
SEL=""
if [[ -n "${OPENROUTER_KEYS:-}" ]]; then
  IFS=',' read -ra KEYS <<< "$OPENROUTER_KEYS"; SEL="${KEYS[0]}"
elif [[ -n "${OPENROUTER_API_KEY:-}" ]]; then
  SEL="${OPENROUTER_API_KEY}"
elif [[ -n "${OPENAI_API_KEY:-}" ]]; then
  SEL="${OPENAI_API_KEY}"
fi
{
  echo "OPENAI_API_BASE_URL=${OPENAI_API_BASE_URL}"
  [[ -n "${SEL}" ]] && echo "OPENAI_API_KEY=${SEL}"
} > "${OUT}"
