# Source this (e.g., `source scripts/cc-launchers.sh`) in your shell.

# 1) Regular Claude (Pro/Max), unchanged flow
cc-pro () {
  claude   # Use /login once; pick Sonnet/Opus with /model
}

# 2) Claude Code via Bifrost Anthropic shim (single base URL; models switchable via /model)
cc-gw () {
  ANTHROPIC_BASE_URL="http://127.0.0.1:8080/anthropic" \
  ANTHROPIC_AUTH_TOKEN="dummy" \
  claude ${1:+--model "$1"}
}

# Convenience: overflow to Z.AI GLM-4.5 behind Bifrost
cc-zai () { cc-gw "zai/glm-4.5"; }

# Convenience: back to Anthropic Sonnet behind Bifrost
cc-sona () { cc-gw "anthropic/claude-4-sonnet"; }