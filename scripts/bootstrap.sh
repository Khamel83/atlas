#!/usr/bin/env bash
set -euo pipefail

# ---------- Inputs ----------
NAME="${1:-oos}"
PATH_ABS="${2:-/home/ubuntu/dev/oos}"
ORG="${ORG:-Khamel83}"         # GitHub user/org
VIS="${VIS:-public}"           # public|private

# 1Password location for the multiline .env
OP_VAULT="${OP_VAULT:-Personal}"
OP_ITEM="${OP_ITEM:-bootstrap-env}"
OP_FIELD="${OP_FIELD:-env}"    # set to 'dotenv' if that’s your field name

# ---------- Checks ----------
need(){ command -v "$1" >/dev/null || { echo "Missing $1"; exit 1; }; }
need git; need python3; need rsync; command -v npm >/dev/null || need node
command -v op >/dev/null || { echo "Install 1Password CLI (op) and run 'op signin'"; exit 1; }
command -v claude >/dev/null || npm i -g @anthropic-ai/claude-code >/dev/null 2>&1 || true
command -v gh >/dev/null || true

# ---------- Pull .env from 1Password ----------
TMP_ENV="$(mktemp)"
op item get "$OP_ITEM" --vault "$OP_VAULT" --fields "$OP_FIELD" > "$TMP_ENV"

mkdir -p "$(dirname "$PATH_ABS")"
cd "$(dirname "$PATH_ABS")"; mkdir -p "$PATH_ABS"; cd "$PATH_ABS"
cp "$TMP_ENV" .env; rm -f "$TMP_ENV"

# ---------- OpenRouter key select/rotate helpers ----------
mkdir -p bin .agents/runners .claude
cat > bin/select_or_key.sh <<'SH'
#!/usr/bin/env bash
set -euo pipefail
ENV_FILE="${1:-.env}"; ACTIVE_FILE="${2:-.env.active}"
mapfile -t KEYS < <(grep -E '^OPENROUTER_KEYS=' "$ENV_FILE" | sed 's/^OPENROUTER_KEYS=//' | tr -d '"' | tr ',' '\n' | sed '/^\s*$/d')
[[ ${#KEYS[@]} -gt 0 ]] || { echo "No OPENROUTER_KEYS"; exit 1; }
for k in "${KEYS[@]}"; do
  code=$(curl -sS -o /dev/null -w "%{http_code}" -H "Authorization: Bearer $k" https://openrouter.ai/api/v1/models || echo "000")
  if [[ "$code" == "200" ]]; then printf "OPENAI_API_KEY=%s\n" "$k" > "$ACTIVE_FILE"; exit 0; fi
done
echo "No working OpenRouter key"; exit 2
SH
cat > bin/rotate_or_key.sh <<'SH'
#!/usr/bin/env bash
set -euo pipefail
ENV_FILE="${1:-.env}"; ACTIVE_FILE="${2:-.env.active}"
current="$(grep -E '^OPENAI_API_KEY=' "$ACTIVE_FILE" 2>/dev/null | cut -d= -f2- || true)"
keys=$(grep -E '^OPENROUTER_KEYS=' "$ENV_FILE" | sed 's/^OPENROUTER_KEYS=//' | tr -d '"' | tr ',' '\n' | sed '/^\s*$/d')
[[ -n "$keys" ]] || { echo "No OPENROUTER_KEYS"; exit 1; }
mapfile -t arr <<< "$keys"; idx=-1
for i in "${!arr[@]}"; do [[ "${arr[$i]}" == "$current" ]] && idx=$i; done
next_index=$(( (idx + 1) % ${#arr[@]} )); printf "OPENAI_API_KEY=%s\n" "${arr[$next_index]}" > "$ACTIVE_FILE"
SH
chmod +x bin/*.sh

# ---------- Runners (Claude / Gemini / Qwen) ----------
cat > .agents/runners/run_claude.sh <<'SH'
#!/usr/bin/env bash
set -euo pipefail
set -a; source .env; set +a
[[ -f .env.active ]] || bin/select_or_key.sh .env .env.active
set -a; source .env.active; set +a
exec claude --mcp-debug
SH
chmod +x .agents/runners/run_claude.sh

cat > .agents/runners/run_gemini.sh <<'SH'
#!/usr/bin/env bash
set -euo pipefail
set -a; source .env; [[ -f .env.active ]] || bin/select_or_key.sh .env .env.active; source .env.active; set +a
exec gemini chat
SH
chmod +x .agents/runners/run_gemini.sh

cat > .agents/runners/run_qwen.sh <<'SH'
#!/usr/bin/env bash
set -euo pipefail
set -a; source .env; [[ -f .env.active ]] || bin/select_or_key.sh .env .env.active; source .env.active; set +a
exec qwen chat
SH
chmod +x .agents/runners/run_qwen.sh

# ---------- Doctrine + basics ----------
mkdir -p .claude/commands .agents/prompts
printf "# dev log\n" > dev.md
cat > .agents/agents.md <<'MD'
- Use Archon + MCPs for context/tasks; keep diffs small; log decisions in dev.md
- Never print secrets; reference by name; short, test-first plans
MD
echo "- Plan: Goal / Constraints / Steps (3–7) / Risks" > .claude/commands/plan.md
printf "# Claude Code Overlay\n- Read .agents/agents.md\n" > docs/CLAUDE.md
printf "# Gemini CLI Overlay\n- Read .agents/agents.md\n" > docs/GEMINI.md
printf "# Qwen Code Overlay\n- Read .agents/agents.md\n" > docs/qwen.md

# ---------- MCP registry (active) ----------
mkdir -p "$HOME/.mcp"
cat > "$HOME/.mcp/registry.json" <<'JSON'
{
  "servers": {
    "archon":     { "transport": "http", "url": "https://archon.khamel.com:8051/mcp" },
    "context7":   { "transport": "http", "url": "https://context7.liam.sh/mcp", "headers": { "CONTEXT7_API_KEY": "${CONTEXT7_API_KEY}" } },
    "filesystem": { "command": "npx", "args": ["-y", "@modelcontextprotocol/server-filesystem", "/home/ubuntu"] },
    "github":     { "command": "npx", "args": ["-y", "@modelcontextprotocol/server-github"], "env": { "GITHUB_PERSONAL_ACCESS_TOKEN": "${GITHUB_PAT}" } },
    "sequential": { "command": "npx", "args": ["-y", "@modelcontextprotocol/server-sequential-thinking"] }
  }
}
JSON

# ---------- Sync registry into Gemini/Qwen ----------
python3 - "$HOME/.mcp/registry.json" "$HOME/.gemini/settings.json" "$HOME/.qwen/settings.json" <<'PY'
import json, os, sys
reg=json.load(open(sys.argv[1]))["servers"]
for out in sys.argv[2:]:
    os.makedirs(os.path.dirname(out), exist_ok=True)
    cur={}
    if os.path.exists(out):
        try: cur=json.load(open(out))
        except: cur={}
    cur["mcpServers"]=reg
    json.dump(cur, open(out,"w"), indent=2)
print("Synced MCP into Gemini/Qwen.")
PY

# ---------- Ensure Claude knows Archon (+Context7 if key set) ----------
claude mcp add --transport http archon "https://archon.khamel.com:8051/mcp" || true
if grep -q '^CONTEXT7_API_KEY=' .env; then
  KEY=$(grep '^CONTEXT7_API_KEY=' .env | cut -d= -f2-)
  [[ -n "$KEY" ]] && claude mcp add --transport http context7 "https://context7.liam.sh/mcp" --header "CONTEXT7_API_KEY: $KEY" || true
fi

# ---------- Repo init + create on GitHub (no secrets mirrored) ----------
git init -q; git add -A; git commit -m "chore: bootstrap ${NAME}" >/dev/null 2>&1 || true
if command -v gh >/dev/null; then
  if ! git remote get-url origin >/dev/null 2>&1; then
    gh repo create "${ORG}/${NAME}" --${VIS} --source "." --remote origin --push
  else
    git push -u origin HEAD || true
  fi
fi

echo "✅ ${NAME} ready at ${PATH_ABS}"
echo "Next:"
echo "  cd ${PATH_ABS}"
echo "  .agents/runners/run_claude.sh   # /mcp lists archon + others"
echo "  .agents/runners/run_gemini.sh"
echo "  .agents/runners/run_qwen.sh"
