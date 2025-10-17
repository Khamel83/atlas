#!/bin/bash
# OOS Production Test Suite v1.0.0
# Tests core functionality to ensure production readiness

set -e

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

PASSED=0
FAILED=0

test_result() {
    if [ $1 -eq 0 ]; then
        echo -e "${GREEN}✅ PASS${NC}: $2"
        ((PASSED++))
    else
        echo -e "${RED}❌ FAIL${NC}: $2"
        ((FAILED++))
    fi
}

echo -e "${BLUE}
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║   🧪 OOS Production Test Suite v1.0.0                       ║
║   Testing core functionality for production readiness       ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
${NC}"

echo -e "${YELLOW}📋 Running production tests...${NC}"
echo ""

# Test 1: Core directories exist
echo "1️⃣ Testing core directory structure..."
if test -d ".claude/commands"; then
    test_result 0 "Claude commands directory exists"
else
    test_result 1 "Claude commands directory missing"
fi

if test -d "src"; then
    test_result 0 "Source directory exists"
else
    test_result 1 "Source directory missing"
fi

if test -d "bin"; then
    test_result 0 "Binary directory exists"
else
    test_result 1 "Binary directory missing"
fi

# Test 2: Essential files exist
echo ""
echo "2️⃣ Testing essential files..."
test -f "install.sh" && test_result 0 "Installer exists" || test_result 1 "Installer missing"
test -f "VERSION" && test_result 0 "Version file exists" || test_result 1 "Version file missing"
test -f "LICENSE" && test_result 0 "License file exists" || test_result 1 "License file missing"
test -f "README.md" && test_result 0 "README exists" || test_result 1 "README missing"

# Test 3: Core Python modules
echo ""
echo "3️⃣ Testing core Python modules..."
test -f "src/free_search_alternatives.py" && test_result 0 "Free search module exists" || test_result 1 "Free search module missing"
test -f "src/perplexity_usage_manager.py" && test_result 0 "Perplexity manager exists" || test_result 1 "Perplexity manager missing"
test -f "src/oos_cli.py" && test_result 0 "OOS CLI exists" || test_result 1 "OOS CLI missing"

# Test 4: Slash commands
echo ""
echo "4️⃣ Testing slash commands..."
COMMAND_COUNT=$(find .claude/commands -name "*.md" 2>/dev/null | wc -l)
if [ "$COMMAND_COUNT" -ge 5 ]; then
    test_result 0 "Found $COMMAND_COUNT slash commands"
else
    test_result 1 "Only found $COMMAND_COUNT slash commands (expected 5+)"
fi

# Test 5: Python syntax check
echo ""
echo "5️⃣ Testing Python syntax..."
if command -v python3 &> /dev/null; then
    if python3 -m py_compile src/free_search_alternatives.py 2>/dev/null; then
        test_result 0 "Free search module syntax valid"
    else
        test_result 1 "Free search module syntax error"
    fi

    if python3 -m py_compile src/perplexity_usage_manager.py 2>/dev/null; then
        test_result 0 "Perplexity manager syntax valid"
    else
        test_result 1 "Perplexity manager syntax error"
    fi
else
    test_result 1 "Python3 not available for syntax testing"
fi

# Test 6: Bash script syntax
echo ""
echo "6️⃣ Testing bash script syntax..."
if bash -n install.sh 2>/dev/null; then
    test_result 0 "Installer script syntax valid"
else
    test_result 1 "Installer script syntax error"
fi

# Test 7: Version consistency
echo ""
echo "7️⃣ Testing version consistency..."
if [ -f "VERSION" ]; then
    VERSION_FILE=$(cat VERSION)
    INSTALLER_VERSION=$(grep "OOS_VERSION=" install.sh | cut -d'"' -f2)
    if [ "$VERSION_FILE" = "$INSTALLER_VERSION" ]; then
        test_result 0 "Version consistency: $VERSION_FILE"
    else
        test_result 1 "Version mismatch: VERSION=$VERSION_FILE, installer=$INSTALLER_VERSION"
    fi
else
    test_result 1 "VERSION file not found"
fi

# Test 8: Git repository status
echo ""
echo "8️⃣ Testing Git repository..."
if git status &>/dev/null; then
    test_result 0 "Git repository valid"

    # Check for uncommitted changes in production files
    if git diff --quiet HEAD -- install.sh VERSION README.md CHANGELOG.md 2>/dev/null; then
        test_result 0 "Production files committed"
    else
        test_result 1 "Production files have uncommitted changes"
    fi
else
    test_result 1 "Not a valid Git repository"
fi

# Summary
echo ""
echo -e "${BLUE}📊 Test Results Summary:${NC}"
echo -e "   ✅ Passed: $PASSED"
echo -e "   ❌ Failed: $FAILED"
echo -e "   📊 Total:  $((PASSED + FAILED))"

if [ $FAILED -eq 0 ]; then
    echo ""
    echo -e "${GREEN}🎉 ALL TESTS PASSED - OOS IS PRODUCTION READY!${NC}"
    echo -e "${GREEN}✅ Ready for public release${NC}"
    exit 0
else
    echo ""
    echo -e "${RED}🚨 $FAILED TESTS FAILED - PRODUCTION NOT READY${NC}"
    echo -e "${YELLOW}Please fix failing tests before release${NC}"
    exit 1
fi