#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# 1) .env presence
if [[ ! -f "$ROOT/.env" ]]; then
  echo "[preflight] .env missing. Copy .env.template -> .env and fill values." >&2
  exit 10
fi

# 2) required keys from .env.template must be non-empty in .env
REQ_KEYS=$(grep -E '^[A-Z0-9_]+=' "$ROOT/.env.template" | grep -v '# optional' | cut -d= -f1 || true)
if [[ -n "$REQ_KEYS" ]]; then
  # shellcheck disable=SC2046
  set -a; source "$ROOT/.env"; set +a
  while IFS= read -r key; do
    [[ -z "$key" ]] && continue
    val="${!key-}"
    if [[ -z "${val:-}" ]]; then
      echo "[preflight] required env key empty: $key" >&2
      exit 11
    fi
done <<< "$REQ_KEYS"
fi

# 3) python venv
if [[ ! -d "$ROOT/.venv" ]]; then
  echo "[preflight] creating venv..."
  python3 -m venv "$ROOT/.venv"
fi
# shellcheck disable=SC1091
source "$ROOT/.venv/bin/activate"

# 4) install deps if present
if [[ -f "$ROOT/requirements.txt" ]]; then
  pip install -q -r "$ROOT/requirements.txt"
elif [[ -f "$ROOT/pyproject.toml" ]]; then
  pip install -q -U pip
  pip install -q .
fi

# 5) git cleanliness on main
cd "$ROOT"
CURRENT_BRANCH="$(git rev-parse --abbrev-ref HEAD)"
if [[ "$CURRENT_BRANCH" != "main" ]]; then
  echo "[preflight] not on main (on $CURRENT_BRANCH). Please checkout main." >&2
  exit 12
fi
if [[ -n "$(git status --porcelain)" ]]; then
  echo "[preflight] working tree not clean. Commit or stash changes." >&2
  exit 13
fi

echo "[preflight] OK"
