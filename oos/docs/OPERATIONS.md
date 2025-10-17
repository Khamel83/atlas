# Operations

## New project
```bash
mkdir -p /home/ubuntu/dev/<Name>
eval "$(op signin)"
OP_VAULT="Private" OP_ITEM="bootstrap-env" OP_FIELD="env" \
ORG="Khamel83" VIS="public" \
/home/ubuntu/dev/oos/scripts/bootstrap.sh "<Name>" "/home/ubuntu/dev/<Name>"
```

## Daily use
```bash
eval "$(op signin)"                 # each shell
cd /home/ubuntu/dev/<Name>
.agents/runners/run_claude.sh       # or run_gemini.sh / run_qwen.sh
```

## Rotate keys
- Update 1Password item `bootstrap-env` → `env`.
- Re-pull into project:
```bash
eval "$(op signin)"
op item get "bootstrap-env" --vault "Private" --fields env > .env
sed -i 's/\r$//' .env
```
- Rerun a runner (selector will pick the first working key).

## Upgrade OOS
- Pull latest from GitHub.
- Rerun `scripts/bootstrap.sh` in existing projects (idempotent).

## Health checks
```bash
# 1Password access
eval "$(op signin)" && op whoami

# Archon MCP
curl -4 -I http://localhost:8051/mcp

# MCPs in Claude
claude mcp list

# Environment normalization
bin/safe_source_env.sh .env && echo "✅ .env valid"

# Key selection
bin/select_or_key.sh .env .env.active && echo "✅ API key selected"
```

## Project cleanup
```bash
# Remove project (keeps 1Password intact)
rm -rf /home/ubuntu/dev/<Name>

# Reset Claude MCP config for project
cd /home/ubuntu/dev/<Name>
claude mcp remove archon || true
claude mcp remove context7 || true
```