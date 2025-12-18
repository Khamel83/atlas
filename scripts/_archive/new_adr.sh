#!/usr/bin/env bash
set -euo pipefail
TITLE="${1:-decision-record}"
SLUG="$(echo "$TITLE" | tr '[:upper:]' '[:lower:]' | tr -cs 'a-z0-9' '-' | sed 's/^-//;s/-$//')"
DATE="$(date +%Y%m%d)"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FILE="$ROOT/docs/adr/${DATE}-${SLUG}.md"
mkdir -p "$ROOT/docs/adr"
cat > "$FILE" <<'EOF'
# Title: REPLACE
**Date:** YYYY-MM-DD
**Status:** proposed | accepted | superseded
**Context**
- Problem and constraints.

**Decision**
- What we chose and why.

**Alternatives Considered**
- Option A …
- Option B …

**Consequences**
- Positive / negative / risks.

**Alignment**
- How this advances Atlas mission/vision.
EOF
sed -i.bak "s/REPLACE/$TITLE/; s/YYYY-MM-DD/$(date +%F)/" "$FILE" && rm -f "$FILE.bak"
echo "Created $FILE"
