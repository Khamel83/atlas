#!/bin/bash
# Automatically fix code consistency issues
set -e

# Colors
BLUE='\033[0;34m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}🔧 Auto-fixing code consistency issues...${NC}"

FIXES_APPLIED=0

# Fix trailing whitespace
echo -e "${YELLOW}Removing trailing whitespace...${NC}"
if command -v sed >/dev/null 2>&1; then
    find . -name "*.py" -o -name "*.js" -o -name "*.sh" -o -name "*.md" | while read -r file; do
        if [[ -f "$file" ]]; then
            sed -i 's/[[:space:]]*$//' "$file" 2>/dev/null || true
        fi
    done
    echo -e "${GREEN}✅ Trailing whitespace removed${NC}"
    ((FIXES_APPLIED++))
fi

# Fix line endings (convert CRLF to LF)
echo -e "${YELLOW}Normalizing line endings...${NC}"
if command -v dos2unix >/dev/null 2>&1; then
    find . -name "*.py" -o -name "*.js" -o -name "*.sh" -o -name "*.md" | xargs dos2unix >/dev/null 2>&1 || true
    echo -e "${GREEN}✅ Line endings normalized${NC}"
    ((FIXES_APPLIED++))
elif command -v sed >/dev/null 2>&1; then
    find . -name "*.py" -o -name "*.js" -o -name "*.sh" -o -name "*.md" | while read -r file; do
        if [[ -f "$file" ]]; then
            sed -i 's/\r$//' "$file" 2>/dev/null || true
        fi
    done
    echo -e "${GREEN}✅ Line endings normalized (sed)${NC}"
    ((FIXES_APPLIED++))
fi

# Ensure files end with newline
echo -e "${YELLOW}Ensuring files end with newline...${NC}"
find . -name "*.py" -o -name "*.js" -o -name "*.sh" -o -name "*.md" | while read -r file; do
    if [[ -f "$file" && -s "$file" ]]; then
        # Check if file ends with newline
        if [[ $(tail -c1 "$file" | wc -l) -eq 0 ]]; then
            echo "" >> "$file"
        fi
    fi
done
echo -e "${GREEN}✅ Files now end with newline${NC}"
((FIXES_APPLIED++))

# Fix executable permissions for shell scripts
echo -e "${YELLOW}Fixing shell script permissions...${NC}"
find . -name "*.sh" | while read -r script; do
    if [[ -f "$script" ]]; then
        chmod +x "$script"
    fi
done
echo -e "${GREEN}✅ Shell script permissions fixed${NC}"
((FIXES_APPLIED++))

# Create basic .gitignore if missing
if [[ ! -f ".gitignore" ]]; then
    echo -e "${YELLOW}Creating basic .gitignore...${NC}"
    cat > .gitignore << 'EOF'
# Dependencies
node_modules/
venv/
env/
__pycache__/
*.pyc

# Environment variables
.env
.env.local

# IDE
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db

# Logs
*.log
logs/

# Temporary files
*.tmp
*.temp
*~

# API keys and secrets
*_key
*_secret
*_token
EOF
    echo -e "${GREEN}✅ Basic .gitignore created${NC}"
    ((FIXES_APPLIED++))
fi

# Python-specific fixes
if find . -name "*.py" | head -1 | grep -q ".py"; then
    echo -e "${YELLOW}Applying Python-specific fixes...${NC}"

    # Fix common Python formatting issues
    find . -name "*.py" | while read -r file; do
        if [[ -f "$file" ]]; then
            # Remove extra blank lines (more than 2 consecutive)
            sed -i '/^$/N;/^\n$/d' "$file" 2>/dev/null || true
        fi
    done
    echo -e "${GREEN}✅ Python formatting improved${NC}"
    ((FIXES_APPLIED++))
fi

echo ""
echo -e "${GREEN}🎉 Auto-fix complete! Applied $FIXES_APPLIED fixes.${NC}"

# Show git status if in a git repo
if git rev-parse --git-dir >/dev/null 2>&1; then
    echo ""
    echo -e "${BLUE}📊 Git status after fixes:${NC}"
    git status --short

    if ! git diff --quiet; then
        echo ""
        echo -e "${YELLOW}💡 Run /smart-commit to commit these consistency fixes${NC}"
    fi
fi