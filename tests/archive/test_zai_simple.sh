#!/usr/bin/env bash
set -euo pipefail

# Simple ZAI integration test suite
# Tests the core functionality without complex dependencies

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BIN_DIR="$(cd "${SCRIPT_DIR}/../bin" && pwd)"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

PASSED=0
FAILED=0

pass() {
    echo -e "${GREEN}[PASS] $1${NC}"
    ((PASSED++))
}

fail() {
    echo -e "${RED}[FAIL] $1${NC}"
    ((FAILED++))
}

info() {
    echo -e "${BLUE}[INFO] $1${NC}"
}

echo "ZAI Integration Simple Test Suite"
echo "================================="

# Test 1: Secrets management
info "Testing secrets management..."

# Test storing a key
TEST_KEY="zai-test-key-12345"
if "${BIN_DIR}/secrets.sh" store "$TEST_KEY" >/dev/null 2>&1; then
    pass "Key storage works"
else
    fail "Key storage failed"
fi

# Test key retrieval
RETRIEVED_KEY=$("${BIN_DIR}/secrets.sh" get 2>/dev/null || echo "")
if [[ "$RETRIEVED_KEY" == "$TEST_KEY" ]]; then
    pass "Key retrieval works"
else
    fail "Key retrieval failed"
fi

# Test key exists check
if "${BIN_DIR}/secrets.sh" has >/dev/null 2>&1; then
    pass "Key existence check works"
else
    fail "Key existence check failed"
fi

# Test key removal
if "${BIN_DIR}/secrets.sh" remove >/dev/null 2>&1; then
    pass "Key removal works"
else
    fail "Key removal failed"
fi

# Verify key is gone
if "${BIN_DIR}/secrets.sh" has >/dev/null 2>&1; then
    fail "Key should be removed"
else
    pass "Key properly removed"
fi

# Test 2: Script permissions and syntax
info "Testing script permissions..."

for script in secrets.sh claude-zai oos-doctor generate-runner.sh; do
    if [[ -x "${BIN_DIR}/${script}" ]]; then
        pass "${script} is executable"
    else
        fail "${script} is not executable"
    fi
done

# Test script syntax
for script in secrets.sh claude-zai oos-doctor generate-runner.sh; do
    if bash -n "${BIN_DIR}/${script}" 2>/dev/null; then
        pass "${script} syntax is valid"
    else
        fail "${script} has syntax errors"
    fi
done

# Test 3: Runner generation
info "Testing runner generation..."

TEST_DIR="/tmp/test_runner_$$"
mkdir -p "$TEST_DIR"
cd "$TEST_DIR"

if "${BIN_DIR}/generate-runner.sh" --no-global >/dev/null 2>&1; then
    pass "Runner generation succeeded"
else
    fail "Runner generation failed"
fi

if [[ -f ".oosrc" ]]; then
    pass ".oosrc created"
else
    fail ".oosrc not created"
fi

if [[ -f ".agents/runners/run_zai.sh" ]]; then
    pass "Runner script created"
else
    fail "Runner script not created"
fi

if [[ -x ".agents/runners/run_zai.sh" ]]; then
    pass "Runner script is executable"
else
    fail "Runner script is not executable"
fi

# Test 4: Environment isolation
info "Testing environment isolation..."

# Test that scripts work with clean environment
if env -i HOME="$HOME" USER="$USER" SHELL="$SHELL" PATH="$PATH" TERM="$TERM" "${BIN_DIR}/secrets.sh" has >/dev/null 2>&1; then
    pass "Scripts work with clean environment"
else
    fail "Scripts fail with clean environment"
fi

# Test 5: API connectivity (if key available)
info "Testing API connectivity..."

# Check if we have a real ZAI key
if "${BIN_DIR}/secrets.sh" has >/dev/null 2>&1; then
    # Test models endpoint
    response=$(curl -s -w "%{http_code}" \
        -H "Authorization: Bearer $("${BIN_DIR}/secrets.sh" get)" \
        "https://api.z.ai/api/anthropic/v1/models" 2>/dev/null || echo "000")

    code=$(echo "$response" | tail -n1)
    if [[ "$code" == "200" ]] || [[ "$code" == "401" ]]; then
        pass "API connectivity test ($code)"
    else
        fail "API connectivity failed ($code)"
    fi
else
    pass "API test skipped (no key)"
fi

# Cleanup
cd /tmp
rm -rf "$TEST_DIR"

# Summary
echo ""
echo "Test Summary"
echo "============"
echo "Passed: $PASSED"
echo "Failed: $FAILED"
echo "Total: $((PASSED + FAILED))"

if [[ $FAILED -eq 0 ]]; then
    echo -e "${GREEN}All tests passed!${NC}"
    exit 0
else
    echo -e "${RED}$FAILED test(s) failed!${NC}"
    exit 1
fi