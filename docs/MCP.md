# MCP wiring

## Archon
- URL from `.env`: `ARCHON_URL` (e.g., `http://localhost:8051/mcp`).
- Health: `curl -4 -I $ARCHON_URL` should return 200/405 quickly.

## Project-scoped registration
`scripts/bootstrap.sh` ensures your project config (`~/.claude.json` scoped to the project) contains:
- `archon` (HTTP transport → `ARCHON_URL`)
- `context7` (if `CONTEXT7_API_KEY` present)

Verify at project root:
```bash
claude mcp list
```

## Runners
- All run the same prelude:
  1. `bin/safe_source_env.sh .env`
  2. `bin/select_or_key.sh .env .env.active` (if missing)
  3. `bin/safe_source_env.sh .env.active`
- Then exec the CLI:
  - Claude: `claude --mcp-debug`
  - Gemini: `gemini chat`
  - Qwen: `qwen chat`