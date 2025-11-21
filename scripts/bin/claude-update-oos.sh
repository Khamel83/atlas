#!/usr/bin/env bash
set -euo pipefail

# Claude Code OOS Update Command
# Updates existing projects with latest OOS development gate system

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

echo -e "${BOLD}${CYAN}🔄 Updating Project with Latest OOS${NC}"
echo "===================================="

# Check if we're in OOS repo itself
if [[ -f "$PROJECT_ROOT/scripts/bootstrap_enhanced.sh" ]]; then
    echo -e "${YELLOW}📍 Detected: You're in the OOS repository itself${NC}"
    echo "This command is for updating OTHER projects with OOS features"
    echo "Use this command from your project directories instead"
    exit 0
fi

# Check if OOS is available
OOS_PATH=""
if [[ -d "oos" ]]; then
    OOS_PATH="$(pwd)/oos"
elif [[ -d "../oos" ]]; then
    OOS_PATH="$(cd ../oos && pwd)"
elif [[ -d "$HOME/dev/oos" ]]; then
    OOS_PATH="$HOME/dev/oos"
else
    echo -e "${RED}❌ Cannot find OOS repository${NC}"
    echo "Please ensure OOS is available at:"
    echo "  • ./oos (in current directory)"
    echo "  • ../oos (parent directory)"
    echo "  • ~/dev/oos (standard location)"
    exit 1
fi

echo -e "${GREEN}✅ Found OOS at: $OOS_PATH${NC}"

# Step 1: Copy essential development scripts
echo -e "\n${BLUE}Step 1: Installing development gate system...${NC}"

mkdir -p bin/.claude

# Copy development gate scripts
cp "$OOS_PATH/bin/dev-gate.sh" bin/
cp "$OOS_PATH/bin/claude-dev-gate.sh" bin/
cp "$OOS_PATH/bin/claude-require-gate.sh" bin/
cp "$OOS_PATH/bin/claude-start-coding.sh" bin/
cp "$OOS_PATH/bin/claude-dev-python.sh" bin/
cp "$OOS_PATH/bin/claude-dev-test.sh" bin/
cp "$OOS_PATH/bin/claude-dev-uv.sh" bin/
cp "$OOS_PATH/bin/setup-uv-environment.sh" bin/

# Make them executable
chmod +x bin/dev-gate.sh
chmod +x bin/claude-*.sh
chmod +x bin/setup-uv-environment.sh

echo "✅ Development scripts installed"

# Step 2: Setup Claude Code configuration
echo -e "\n${BLUE}Step 2: Configuring Claude Code integration...${NC}"

mkdir -p .claude

# Copy slash commands (merge with existing)
if [[ -f ".claude/slash_commands.json" ]]; then
    echo "⚠️  Existing Claude Code configuration found"
    echo "You may need to manually merge slash commands"
    cp "$OOS_PATH/.claude/slash_commands.json" .claude/slash_commands_oos.json
    echo "✅ OOS slash commands saved as .claude/slash_commands_oos.json"
else
    cp "$OOS_PATH/.claude/slash_commands.json" .claude/
    echo "✅ Claude Code slash commands installed"
fi

# Copy auto patterns (merge with existing)
if [[ -f ".claude/auto_patterns.json" ]]; then
    echo "⚠️  Existing auto patterns found"
    cp "$OOS_PATH/.claude/auto_patterns.json" .claude/auto_patterns_oos.json
    echo "✅ OOS auto patterns saved as .claude/auto_patterns_oos.json"
else
    cp "$OOS_PATH/.claude/auto_patterns.json" .claude/
    echo "✅ Auto patterns installed"
fi

# Step 3: Setup modern Python environment
echo -e "\n${BLUE}Step 3: Setting up modern Python environment...${NC}"

if [[ -f "pyproject.toml" ]]; then
    echo "⚠️  Existing pyproject.toml found"
    echo "Consider updating it with OOS structure from: $OOS_PATH/pyproject.toml"
else
    cp "$OOS_PATH/pyproject.toml" .
    echo "✅ Modern pyproject.toml installed"
fi

# Step 4: Install git hooks
echo -e "\n${BLUE}Step 4: Installing mandatory git hooks...${NC}"

if [[ -d ".git" ]]; then
    cp "$OOS_PATH/bin/install-mandatory-hooks.sh" bin/
    chmod +x bin/install-mandatory-hooks.sh
    ./bin/install-mandatory-hooks.sh
    echo "✅ Git hooks installed"
else
    echo "⚠️  No git repository found - skipping git hooks"
fi

# Step 5: Setup uv environment
echo -e "\n${BLUE}Step 5: Setting up uv environment...${NC}"

if command -v uv >/dev/null 2>&1; then
    echo "✅ uv already installed"
    if [[ -f "pyproject.toml" ]]; then
        echo "Running uv sync..."
        uv sync 2>/dev/null && echo "✅ uv environment synced" || echo "⚠️  uv sync failed - run manually later"
    fi
else
    echo "⚠️  uv not installed - run: curl -LsSf https://astral.sh/uv/install.sh | sh"
fi

# Step 6: Summary
echo -e "\n${PURPLE}📋 Update Summary:${NC}"
echo "✅ Development gate system installed"
echo "✅ Claude Code slash commands available"
echo "✅ Git hooks for mandatory validation"
echo "✅ Modern Python/uv configuration"

echo -e "\n${YELLOW}Next Steps:${NC}"
echo "1. Restart Claude Code to load new slash commands"
echo "2. Run: /start-coding (to validate everything works)"
echo "3. Use /dev-python, /dev-test, /dev-uv for development"

echo -e "\n${YELLOW}Manual Steps (if needed):${NC}"
if [[ -f ".claude/slash_commands_oos.json" ]]; then
    echo "• Merge .claude/slash_commands_oos.json into .claude/slash_commands.json"
fi
if [[ -f ".claude/auto_patterns_oos.json" ]]; then
    echo "• Merge .claude/auto_patterns_oos.json into .claude/auto_patterns.json"
fi

echo -e "\n${BOLD}${GREEN}🎉 Project updated with OOS development gate system!${NC}"