#!/bin/bash
# Show current context size and optimization stats
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Colors
BLUE='\033[0;34m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${BLUE}📊 Context Statistics${NC}"
echo "===================="

# Basic project stats
echo -e "${GREEN}📁 Project Overview:${NC}"
echo "  • Working directory: $(pwd)"
echo "  • Git repository: $(git rev-parse --is-inside-work-tree 2>/dev/null || echo 'Not a git repo')"

if [[ -d ".git" ]]; then
    BRANCH=$(git branch --show-current 2>/dev/null || echo "unknown")
    echo "  • Current branch: $BRANCH"

    COMMITS=$(git rev-list --count HEAD 2>/dev/null || echo "0")
    echo "  • Total commits: $COMMITS"
fi

echo ""

# File statistics
echo -e "${GREEN}📄 File Statistics:${NC}"
TOTAL_FILES=$(find . -type f | wc -l)
CODE_FILES=$(find . -name "*.py" -o -name "*.js" -o -name "*.sh" -o -name "*.md" | wc -l)
echo "  • Total files: $TOTAL_FILES"
echo "  • Code/doc files: $CODE_FILES"

# Get file sizes and estimate tokens
TOTAL_SIZE=$(find . -type f -exec wc -c {} + 2>/dev/null | tail -1 | awk '{print $1}' || echo "0")
CODE_SIZE=$(find . -name "*.py" -o -name "*.js" -o -name "*.sh" -o -name "*.md" -exec wc -c {} + 2>/dev/null | tail -1 | awk '{print $1}' || echo "0")

echo "  • Total size: $(numfmt --to=iec $TOTAL_SIZE 2>/dev/null || echo "${TOTAL_SIZE} bytes")"
echo "  • Code size: $(numfmt --to=iec $CODE_SIZE 2>/dev/null || echo "${CODE_SIZE} bytes")"

# Estimate tokens (rough: 1 token ≈ 4 characters for English text)
ESTIMATED_TOKENS=$((CODE_SIZE / 4))
echo "  • Estimated tokens: ~$ESTIMATED_TOKENS"

echo ""

# Context optimization stats
echo -e "${GREEN}🔧 Optimization Potential:${NC}"

if [[ $ESTIMATED_TOKENS -lt 1000 ]]; then
    echo "  • Context size: ✅ Small ($ESTIMATED_TOKENS tokens)"
    echo "  • Optimization: Not needed"
elif [[ $ESTIMATED_TOKENS -lt 4000 ]]; then
    echo "  • Context size: 🟡 Medium ($ESTIMATED_TOKENS tokens)"
    echo "  • Optimization: Beneficial for complex requests"
else
    echo "  • Context size: 🔴 Large ($ESTIMATED_TOKENS tokens)"
    echo "  • Optimization: Strongly recommended"
fi

# Recent activity
echo ""
echo -e "${GREEN}📈 Recent Activity:${NC}"

if [[ -d ".git" ]]; then
    RECENT_COMMITS=$(git log --oneline --since="24 hours ago" | wc -l)
    echo "  • Commits today: $RECENT_COMMITS"

    if [[ $RECENT_COMMITS -gt 0 ]]; then
        echo "  • Latest commit: $(git log -1 --pretty=format:'%h %s' 2>/dev/null)"
    fi
fi

# Check for optimization history
if [[ -f "$HOME/.oos/optimization_history.json" ]]; then
    echo "  • Optimization history: Available"
    OPTIMIZATIONS=$(jq length "$HOME/.oos/optimization_history.json" 2>/dev/null || echo "0")
    echo "  • Previous optimizations: $OPTIMIZATIONS"
else
    echo "  • Optimization history: None"
fi

echo ""

# Context recommendations
echo -e "${GREEN}💡 Recommendations:${NC}"

if [[ $ESTIMATED_TOKENS -gt 4000 ]]; then
    echo "  • Use /optimize to reduce token usage"
    echo "  • Focus on specific files/functions"
    echo "  • Break large tasks into smaller steps"
fi

if [[ $CODE_FILES -gt 50 ]]; then
    echo "  • Consider using specific file patterns"
    echo "  • Use /clarify for better scope definition"
fi

echo "  • Use /meta-ai for complex clarification needs"
echo "  • Use /smart-commit for consistent git messages"

echo ""
echo -e "${BLUE}💾 Token budget guidelines:${NC}"
echo "  • Light usage: < 2,000 tokens"
echo "  • Moderate usage: 2,000 - 8,000 tokens"
echo "  • Heavy usage: > 8,000 tokens"
echo "  • Optimization threshold: > 4,000 tokens"