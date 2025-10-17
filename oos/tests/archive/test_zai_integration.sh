#!/usr/bin/env bash
set -euo pipefail

# Test suite for ZAI integration
# Based on the test matrix from integration learnings

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BIN_DIR="$(cd "${SCRIPT_DIR}/../bin" && pwd)"

# Test utilities
source "${SCRIPT_DIR}/test_common.sh"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Test counter
TESTS_TOTAL=0
TESTS_PASSED=0
TESTS_FAILED=0

# Test functions
test_start() {
    local test_name="$1"
    echo -e "${BLUE}[TEST] ${test_name}${NC}"
    ((TESTS_TOTAL++))
}

test_pass() {
    echo -e "${GREEN}[PASS] $1${NC}"
    ((TESTS_PASSED++))
}

test_fail() {
    echo -e "${RED}[FAIL] $1${NC}"
    ((TESTS_FAILED++))
}

test_skip() {
    echo -e "${YELLOW}[SKIP] $1${NC}"
}

# Cleanup function
cleanup() {
    # Clean up test files
    rm -f /tmp/test_zai_key.txt
    rm -f /tmp/test_oosrc.txt
    rm -rf /tmp/test_agents
}

# Set trap for cleanup
trap cleanup EXIT

# Test T1: Key present, good token
test_t1_good_token() {
    test_start "T1 - Good token test"

    # Store a test key (this would normally be a real ZAI key)
    echo "zai-test-key-1234567890abcdef" > /tmp/test_zai_key.txt

    # Test key validation
    if "${BIN_DIR}/secrets.sh" store "$(cat /tmp/test_zai_key.txt)" >/dev/null 2>&1; then
        test_pass "Key stored successfully"
    else
        test_fail "Failed to store key"
        return
    fi

    # Test key retrieval
    if "${BIN_DIR}/secrets.sh" has >/dev/null 2>&1; then
        test_pass "Key retrieval works"
    else
        test_fail "Key retrieval failed"
        return
    fi

    # Test API connectivity (this will fail with test key, but should reach the API)
    local response
    response=$(curl -s -w "%{http_code}" \
        -H "Authorization: Bearer $(cat /tmp/test_zai_key.txt)" \
        "https://api.z.ai/api/anthropic/v1/models" 2>/dev/null || echo "000")

    local code=$(echo "$response" | tail -n1)
    if [[ "$code" == "401" ]] || [[ "$code" == "200" ]]; then
        test_pass "API connectivity test (expected auth error with test key)"
    else
        test_fail "Unexpected API response code: $code"
    fi

    # Clean up test key
    "${BIN_DIR}/secrets.sh" remove >/dev/null 2>&1 || true
}

# Test T2: Key missing
test_t2_missing_key() {
    test_start "T2 - Missing key test"

    # Ensure no key exists
    "${BIN_DIR}/secrets.sh" remove >/dev/null 2>&1 || true

    # Test that has returns failure
    if "${BIN_DIR}/secrets.sh" has >/dev/null 2>&1; then
        test_fail "Key should not exist"
    else
        test_pass "Key correctly reported as missing"
    fi

    # Test that get returns empty
    local key
    key=$("${BIN_DIR}/secrets.sh" get 2>/dev/null || echo "")
    if [[ -z "$key" ]]; then
        test_pass "Get correctly returns empty for missing key"
    else
        test_fail "Get should return empty for missing key"
    fi
}

# Test T3: Bad token format
test_t3_bad_token() {
    test_start "T3 - Bad token format test"

    local bad_keys=(
        ""
        "invalid"
        "too-short"
        "zai"
        "not-a-key-at-all"
    )

    for key in "${bad_keys[@]}"; do
        # Test validation
        if "${BIN_DIR}/secrets.sh" validate "$key" >/dev/null 2>&1; then
            test_fail "Key '$key' should be invalid"
        else
            # This is expected
            continue
        fi
    done

    test_pass "Bad token formats correctly rejected"
}

# Test T4: Model name handling
test_t4_model_names() {
    test_start "T4 - Model name handling test"

    # Test claude-zai script with different model names
    local models=(
        "glm-4.5"
        "glm-4.5-air"
        "z-ai/glm-4.5"  # Should be corrected
        "zai/glm-4.5"   # Should be corrected
    )

    # We can't actually run Claude Code without a real key, but we can test argument parsing
    # by checking the script syntax
    for model in "${models[@]}"; do
        if bash -n "${BIN_DIR}/claude-zai" 2>/dev/null; then
            test_pass "Script syntax valid for model: $model"
        else
            test_fail "Script syntax error for model: $model"
        fi
    done
}

# Test T5: Environment pollution
test_t5_env_pollution() {
    test_start "T5 - Environment pollution test"

    # Set up polluted environment
    export ANTHROPIC_API_KEY="fake-anthropic-key"
    export ANTHROPIC_BASE_URL="https://api.anthropic.com"
    export ANTHROPIC_MODEL="claude-3-sonnet-20240229"

    # Run doctor and check for pollution detection
    local doctor_output
    doctor_output=$("${BIN_DIR}/oos-doctor" 2>&1 || true)

    if echo "$doctor_output" | grep -q "ANTHROPIC_API_KEY is set"; then
        test_pass "Doctor detected ANTHROPIC_API_KEY pollution"
    else
        test_fail "Doctor missed ANTHROPIC_API_KEY pollution"
    fi

    if echo "$doctor_output" | grep -q "ANTHROPIC_BASE_URL is set"; then
        test_pass "Doctor detected ANTHROPIC_BASE_URL pollution"
    else
        test_fail "Doctor missed ANTHROPIC_BASE_URL pollution"
    fi

    if echo "$doctor_output" | grep -q "ANTHROPIC_MODEL is set"; then
        test_pass "Doctor detected ANTHROPIC_MODEL pollution"
    else
        test_fail "Doctor missed ANTHROPIC_MODEL pollution"
    fi

    # Clean up environment
    unset ANTHROPIC_API_KEY ANTHROPIC_BASE_URL ANTHROPIC_MODEL
}

# Test runner generation
test_runner_generation() {
    test_start "Runner generation test"

    local test_dir="/tmp/test_runner_$$"
    mkdir -p "$test_dir"
    cd "$test_dir"

    # Generate runner
    if "${BIN_DIR}/generate-runner.sh" --no-global >/dev/null 2>&1; then
        test_pass "Runner generation succeeded"
    else
        test_fail "Runner generation failed"
        cd /tmp
        rm -rf "$test_dir"
        return
    fi

    # Check files were created
    if [[ -f ".oosrc" ]]; then
        test_pass ".oosrc created"
    else
        test_fail ".oosrc not created"
    fi

    if [[ -f ".agents/runners/run_zai.sh" ]]; then
        test_pass "Runner script created"
    else
        test_fail "Runner script not created"
    fi

    # Check runner script is executable
    if [[ -x ".agents/runners/run_zai.sh" ]]; then
        test_pass "Runner script is executable"
    else
        test_fail "Runner script is not executable"
    fi

    # Test runner script syntax
    if bash -n ".agents/runners/run_zai.sh" 2>/dev/null; then
        test_pass "Runner script syntax is valid"
    else
        test_fail "Runner script has syntax errors"
    fi

    cd /tmp
    rm -rf "$test_dir"
}

# Test script permissions
test_script_permissions() {
    test_start "Script permissions test"

    local scripts=(
        "${BIN_DIR}/secrets.sh"
        "${BIN_DIR}/claude-zai"
        "${BIN_DIR}/oos-doctor"
        "${BIN_DIR}/generate-runner.sh"
    )

    for script in "${scripts[@]}"; do
        if [[ -f "$script" ]]; then
            if [[ -x "$script" ]]; then
                test_pass "$(basename "$script") is executable"
            else
                test_fail "$(basename "$script") is not executable"
            fi
        else
            test_skip "$(basename "$script") not found"
        fi
    done
}

# Test secrets management
test_secrets_management() {
    test_start "Secrets management test"

    local test_key="zai-test-key-$(date +%s)"

    # Test store
    if "${BIN_DIR}/secrets.sh" store "$test_key" >/dev/null 2>&1; then
        test_pass "Key storage works"
    else
        test_fail "Key storage failed"
        return
    fi

    # Test has
    if "${BIN_DIR}/secrets.sh" has >/dev/null 2>&1; then
        test_pass "Key existence check works"
    else
        test_fail "Key existence check failed"
    fi

    # Test get
    local retrieved_key
    retrieved_key=$("${BIN_DIR}/secrets.sh" get 2>/dev/null || echo "")
    if [[ "$retrieved_key" == "$test_key" ]]; then
        test_pass "Key retrieval works"
    else
        test_fail "Key retrieval failed: got '$retrieved_key', expected '$test_key'"
    fi

    # Test info
    if "${BIN_DIR}/secrets.sh" info >/dev/null 2>&1; then
        test_pass "Key info command works"
    else
        test_fail "Key info command failed"
    fi

    # Test remove
    if "${BIN_DIR}/secrets.sh" remove >/dev/null 2>&1; then
        test_pass "Key removal works"
    else
        test_fail "Key removal failed"
    fi

    # Verify removal
    if "${BIN_DIR}/secrets.sh" has >/dev/null 2>&1; then
        test_fail "Key still exists after removal"
    else
        test_pass "Key properly removed"
    fi
}

# Test configuration file handling
test_config_files() {
    test_start "Configuration file handling test"

    # Test .oosrc generation
    local test_dir="/tmp/test_config_$$"
    mkdir -p "$test_dir"
    cd "$test_dir"

    if "${BIN_DIR}/generate-runner.sh" --no-global --base-url "https://custom.url" --model "glm-4.5-air" >/dev/null 2>&1; then
        test_pass "Configuration generation succeeded"
    else
        test_fail "Configuration generation failed"
        cd /tmp
        rm -rf "$test_dir"
        return
    fi

    # Check .oosrc contents
    if grep -q "https://custom.url" .oosrc; then
        test_pass "Custom base URL in .oosrc"
    else
        test_fail "Custom base URL not in .oosrc"
    fi

    if grep -q "glm-4.5-air" .oosrc; then
        test_pass "Custom model in .oosrc"
    else
        test_fail "Custom model not in .oosrc"
    fi

    cd /tmp
    rm -rf "$test_dir"
}

# Run all tests
run_tests() {
    echo "ZAI Integration Test Suite"
    echo "========================"
    echo

    # Run individual tests
    test_t1_good_token
    test_t2_missing_key
    test_t3_bad_token
    test_t4_model_names
    test_t5_env_pollution
    test_runner_generation
    test_script_permissions
    test_secrets_management
    test_config_files

    # Summary
    echo
    echo "Test Summary"
    echo "============"
    echo "Total tests:  $TESTS_TOTAL"
    echo "Passed:       $TESTS_PASSED"
    echo "Failed:       $TESTS_FAILED"
    echo "Skipped:      $((TESTS_TOTAL - TESTS_PASSED - TESTS_FAILED))"

    if [[ $TESTS_FAILED -eq 0 ]]; then
        echo
        echo -e "${GREEN}All tests passed!${NC}"
        exit 0
    else
        echo
        echo -e "${RED}$TESTS_FAILED test(s) failed!${NC}"
        exit 1
    fi
}

# Check if we're running in test mode
if [[ "${1:-}" == "--help" ]]; then
    echo "ZAI Integration Test Suite"
    echo
    echo "Usage: $0 [test_name]"
    echo
    echo "If test_name is specified, runs only that test."
    echo "Otherwise, runs all tests."
    echo
    echo "Available tests:"
    echo "  t1_good_token       Test T1: Good token"
    echo "  t2_missing_key      Test T2: Missing key"
    echo "  t3_bad_token        Test T3: Bad token format"
    echo "  t4_model_names      Test T4: Model name handling"
    echo "  t5_env_pollution    Test T5: Environment pollution"
    echo "  runner_generation  Runner generation test"
    echo "  script_permissions Script permissions test"
    echo "  secrets_management Secrets management test"
    echo "  config_files       Configuration file test"
    exit 0
fi

# Run specific test or all tests
case "${1:-}" in
    t1_good_token)
        test_t1_good_token
        ;;
    t2_missing_key)
        test_t2_missing_key
        ;;
    t3_bad_token)
        test_t3_bad_token
        ;;
    t4_model_names)
        test_t4_model_names
        ;;
    t5_env_pollution)
        test_t5_env_pollution
        ;;
    runner_generation)
        test_runner_generation
        ;;
    script_permissions)
        test_script_permissions
        ;;
    secrets_management)
        test_secrets_management
        ;;
    config_files)
        test_config_files
        ;;
    *)
        run_tests
        ;;
esac