#!/usr/bin/env bash
set -euo pipefail

# Claude Code "Start Coding" Command
# One command to validate environment and get ready for development

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

echo -e "${BOLD}${CYAN}🚀 Starting Development Session${NC}"
echo "==============================="

# Step 0: ALWAYS update OOS from GitHub first (ensures slash commands are current)
echo -e "${BLUE}Step 0: Updating OOS subfolder operating system...${NC}"
if [[ -f "$PROJECT_ROOT/bin/oos-update-from-github.sh" ]]; then
    bash "$PROJECT_ROOT/bin/oos-update-from-github.sh"
else
    echo -e "${YELLOW}⚠️  OOS update script not found - you may have outdated commands${NC}"
fi

# Step 1: Run development gate
echo -e "${BLUE}Step 1: Validating development environment...${NC}"
if DEV_GATE_BYPASS=true "$PROJECT_ROOT/bin/dev-gate.sh"; then
    echo -e "${GREEN}✅ Development environment ready${NC}"
else
    echo -e "${RED}❌ Development environment validation failed${NC}"
    echo "Please fix the issues above before coding"
    exit 1
fi

# Step 2: Show environment status
echo -e "\n${BLUE}Step 2: Environment Status${NC}"
echo "• uv: $(uv --version)"
echo "• Python: $(uv run python --version)"
echo "• 1Password: $(if op whoami >/dev/null 2>&1; then echo "✅ Authenticated"; else echo "⚠️  Not authenticated"; fi)"

# Step 3: Quick project health check
echo -e "\n${BLUE}Step 3: Project Health Check${NC}"
if [[ -f "$PROJECT_ROOT/pyproject.toml" ]]; then
    echo "• pyproject.toml: ✅ Found"
    if [[ -f "$PROJECT_ROOT/uv.lock" ]]; then
        echo "• uv.lock: ✅ Found (dependencies locked)"
    else
        echo "• uv.lock: ⚠️  Missing (run: uv sync)"
    fi
else
    echo "• pyproject.toml: ⚠️  Missing"
fi

if [[ -d "$PROJECT_ROOT/.git" ]]; then
    echo "• Git repository: ✅ Found"
    echo "• Branch: $(git branch --show-current 2>/dev/null || echo 'unknown')"

    # Check for uncommitted changes
    if ! git diff-index --quiet HEAD -- 2>/dev/null; then
        echo "• Working directory: ⚠️  Has uncommitted changes"
    else
        echo "• Working directory: ✅ Clean"
    fi
else
    echo "• Git repository: ⚠️  Not initialized"
fi

# Step 4: Available commands
echo -e "\n${PURPLE}🛠️  Available Development Commands:${NC}"
echo "• /dev-python [args]    - Run Python scripts"
echo "• /dev-test [args]      - Run tests with pytest"
echo "• /dev-uv [args]        - Run uv package manager"
echo "• /smart-commit         - AI-generated commit messages"
echo "• /auto-fix             - Auto-fix code issues"

# Step 5: Quick tips
echo -e "\n${YELLOW}💡 Quick Tips:${NC}"
echo "• Environment valid for 1 hour"
echo "• Re-run /start-coding if commands get blocked"
echo "• Use /dev-gate bypass for emergencies"

echo -e "\n${BOLD}${GREEN}🎉 Ready to code! Happy developing!${NC}"