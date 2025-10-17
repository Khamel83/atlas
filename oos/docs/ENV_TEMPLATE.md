# .env.template (copy these keys to 1Password → bootstrap-env → field "env")

```bash
# ==== OOS bootstrap env ====

## Archon (MCP endpoint is /mcp)
ARCHON_URL=http://localhost:8051/mcp
ARCHON_UI_PORT=3737
ARCHON_SERVER_PORT=8181
ARCHON_MCP_PORT=8051

## OpenRouter model routing (rotation supported)
OPENAI_API_BASE_URL=https://openrouter.ai/api/v1
# EITHER a single key:
# OPENROUTER_API_KEY=sk-or-...
# OR a rotation list (first wins):
# OPENROUTER_KEYS=sk-or-...,sk-or-...,sk-or-...

## Other API keys (optional)
FIRECRAWL_API_KEY=

## Supabase (if used by Archon/other tools)
SUPABASE_URL=
SUPABASE_SERVICE_KEY=

## Site credentials (optional; avoid if possible)
NYTIMES_USERNAME=
NYTIMES_PASSWORD=
WSJ_USERNAME=
WSJ_PASSWORD=

## Default model preference
MODEL=google/gemini-2.0-flash-001

## Feature toggles
YOUTUBE_INGESTOR_ENABLED=false
INSTAPAPER_INGESTOR_ENABLED=false

## Local server config
HOST=0.0.0.0
API_HOST=localhost
API_PORT=7444
DATABASE_URL=sqlite:///atlas.db

## Security & session
SECRET_KEY=change_me
SESSION_TIMEOUT=3600
LOG_LEVEL=INFO

## Optional (Context7 & GitHub)
CONTEXT7_API_KEY=
GITHUB_PAT=

# ==== LLM Gateway (Bifrost) ====
# When using the gateway directly (outside Bifrost UI virtual keys)
ZAI_API_KEY=replace_me
ANTHROPIC_API_KEY=replace_me
# Optional other Anthropic-compatible providers you may add later:
DEEPSEEK_API_KEY=
KIMI_API_KEY=
```