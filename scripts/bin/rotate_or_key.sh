#!/usr/bin/env bash
set -euo pipefail
ENV_FILE="${1:-.env}"; ACTIVE_FILE="${2:-.env.active}"
current="$(grep -E '^OPENAI_API_KEY=' "$ACTIVE_FILE" 2>/dev/null | cut -d= -f2- || true)"
keys=$(grep -E '^OPENROUTER_KEYS=' "$ENV_FILE" | sed 's/^OPENROUTER_KEYS=//' | tr -d '"' | tr ',' '\n' | sed '/^\s*$/d')
[[ -n "$keys" ]] || { echo "No OPENROUTER_KEYS"; exit 1; }
mapfile -t arr <<< "$keys"; idx=-1
for i in "${!arr[@]}"; do [[ "${arr[$i]}" == "$current" ]] && idx=$i; done
next_index=$(( (idx + 1) % ${#arr[@]} )); printf "OPENAI_API_KEY=%s\n" "${arr[$next_index]}" > "$ACTIVE_FILE"
