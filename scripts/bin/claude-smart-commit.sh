#!/bin/bash
# Generate intelligent commit message for current changes
set -e

# Colors
BLUE='\033[0;34m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}🧠 Generating smart commit message...${NC}"

# Check if we're in a git repository
if ! git rev-parse --git-dir > /dev/null 2>&1; then
    echo -e "${RED}Not in a git repository. Please run from a git repository.${NC}"
    exit 1
fi

# Check if there are staged changes (compatible with older git versions)
if git diff --name-only --cached 2>/dev/null | grep -q .; then
    echo -e "${GREEN}Found staged changes. Analyzing...${NC}"
elif git diff --name-only 2>/dev/null | grep -q .; then
    echo -e "${YELLOW}Found unstaged changes. Staging them first...${NC}"
    git add .
else
    echo -e "${RED}No changes detected. Nothing to commit.${NC}"
    exit 1
fi

# Get git diff for analysis (compatible approach)
echo -e "${BLUE}📊 Analyzing changes...${NC}"
DIFF_OUTPUT=$(git diff --stat --cached 2>/dev/null || git diff --stat)
DETAILED_DIFF=$(git diff --name-only --cached 2>/dev/null || git diff --name-only)

echo "Files changed:"
echo "$DETAILED_DIFF" | sed 's/^/  • /'
echo ""

# Generate commit message based on changes
echo -e "${BLUE}🎯 Generating commit message...${NC}"

# Simple analysis of changes
COMMIT_TYPE="feat"
if echo "$DETAILED_DIFF" | grep -q "test"; then
    COMMIT_TYPE="test"
elif echo "$DETAILED_DIFF" | grep -qE "\.(md|txt|rst)$"; then
    COMMIT_TYPE="docs"
elif echo "$DETAILED_DIFF" | grep -qE "fix|bug"; then
    COMMIT_TYPE="fix"
elif echo "$DETAILED_DIFF" | grep -qE "refactor"; then
    COMMIT_TYPE="refactor"
fi

# Count files and generate summary
FILE_COUNT=$(echo "$DETAILED_DIFF" | wc -l)
if [[ $FILE_COUNT -eq 1 ]]; then
    MAIN_FILE=$(echo "$DETAILED_DIFF" | head -1)
    SUMMARY="update $(basename "$MAIN_FILE")"
elif [[ $FILE_COUNT -le 3 ]]; then
    SUMMARY="update $(echo "$DETAILED_DIFF" | tr '\n' ', ' | sed 's/, $//' | sed 's/.*\///')"
else
    SUMMARY="update $FILE_COUNT files for enhanced functionality"
fi

# Generate the commit message
COMMIT_MSG="$COMMIT_TYPE: $SUMMARY

🤖 Generated with [Claude Code](https://claude.ai/code)

Co-Authored-By: Claude <noreply@anthropic.com>"

echo -e "${GREEN}Generated commit message:${NC}"
echo "----------------------------------------"
echo "$COMMIT_MSG"
echo "----------------------------------------"
echo ""

read -p "Commit with this message? (y/n): " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Yy]$ ]]; then
    git commit -m "$COMMIT_MSG"
    echo -e "${GREEN}✅ Changes committed successfully!${NC}"
else
    echo -e "${YELLOW}Commit cancelled. Changes remain staged.${NC}"
fi