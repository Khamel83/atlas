#!/bin/bash
# Check documentation completeness and code consistency
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Colors
BLUE='\033[0;34m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}📋 Checking documentation and consistency...${NC}"

# Check README exists and is substantial
if [[ -f "README.md" ]]; then
    README_LINES=$(wc -l < README.md)
    if [[ $README_LINES -gt 50 ]]; then
        echo -e "${GREEN}✅ README.md exists and is comprehensive ($README_LINES lines)${NC}"
    else
        echo -e "${YELLOW}⚠️  README.md exists but might need more content ($README_LINES lines)${NC}"
    fi
else
    echo -e "${RED}❌ README.md missing${NC}"
fi

# Check for package.json/requirements.txt
if [[ -f "package.json" ]]; then
    echo -e "${GREEN}✅ package.json found${NC}"
elif [[ -f "requirements.txt" ]]; then
    echo -e "${GREEN}✅ requirements.txt found${NC}"
elif [[ -f "pyproject.toml" ]]; then
    echo -e "${GREEN}✅ pyproject.toml found${NC}"
else
    echo -e "${YELLOW}⚠️  No dependency file found (package.json, requirements.txt, pyproject.toml)${NC}"
fi

# Check for license
if [[ -f "LICENSE" || -f "LICENSE.txt" || -f "LICENSE.md" ]]; then
    echo -e "${GREEN}✅ License file found${NC}"
else
    echo -e "${YELLOW}⚠️  No license file found${NC}"
fi

# Check for .gitignore
if [[ -f ".gitignore" ]]; then
    echo -e "${GREEN}✅ .gitignore exists${NC}"
else
    echo -e "${YELLOW}⚠️  .gitignore missing${NC}"
fi

# Check for tests directory
if [[ -d "tests" || -d "test" ]]; then
    TEST_COUNT=$(find tests test -name "*.py" -o -name "*.js" -o -name "*.sh" 2>/dev/null | wc -l)
    if [[ $TEST_COUNT -gt 0 ]]; then
        echo -e "${GREEN}✅ Tests directory found with $TEST_COUNT test files${NC}"
    else
        echo -e "${YELLOW}⚠️  Tests directory exists but no test files found${NC}"
    fi
else
    echo -e "${YELLOW}⚠️  No tests directory found${NC}"
fi

# Check for basic documentation structure
echo ""
echo -e "${BLUE}📁 Documentation structure:${NC}"

DOC_DIRS=("docs" "documentation" "doc")
DOC_FOUND=false

for dir in "${DOC_DIRS[@]}"; do
    if [[ -d "$dir" ]]; then
        DOC_COUNT=$(find "$dir" -name "*.md" -o -name "*.rst" -o -name "*.txt" | wc -l)
        echo -e "${GREEN}✅ $dir/ directory with $DOC_COUNT documentation files${NC}"
        DOC_FOUND=true
        break
    fi
done

if [[ "$DOC_FOUND" == false ]]; then
    echo -e "${YELLOW}⚠️  No dedicated documentation directory found${NC}"
fi

# Check code consistency
echo ""
echo -e "${BLUE}🔍 Code consistency checks:${NC}"

# Check for mixed line endings (basic check)
if command -v dos2unix >/dev/null 2>&1; then
    MIXED_ENDINGS=$(find . -name "*.py" -o -name "*.js" -o -name "*.sh" | head -20 | xargs file | grep -c "CRLF" || true)
    if [[ $MIXED_ENDINGS -eq 0 ]]; then
        echo -e "${GREEN}✅ Consistent line endings${NC}"
    else
        echo -e "${YELLOW}⚠️  Found $MIXED_ENDINGS files with CRLF line endings${NC}"
    fi
fi

# Check for trailing whitespace
TRAILING_WS=$(grep -r "[[:space:]]$" --include="*.py" --include="*.js" --include="*.sh" . | wc -l || true)
if [[ $TRAILING_WS -eq 0 ]]; then
    echo -e "${GREEN}✅ No trailing whitespace found${NC}"
else
    echo -e "${YELLOW}⚠️  Found $TRAILING_WS lines with trailing whitespace${NC}"
fi

echo ""
echo -e "${BLUE}📊 Summary complete. Use /auto-fix to address consistency issues.${NC}"