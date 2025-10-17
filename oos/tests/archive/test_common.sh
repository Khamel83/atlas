#!/usr/bin/env bash
set -euo pipefail

# Common test utilities for OOS test suite

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Test counter (global)
TESTS_TOTAL=0
TESTS_PASSED=0
TESTS_FAILED=0

# Test reporting functions
test_start() {
    local test_name="$1"
    echo -e "${CYAN}[TEST] ${test_name}${NC}"
    ((TESTS_TOTAL++))
}

test_pass() {
    local message="${1:-Passed}"
    echo -e "${GREEN}[PASS] ${message}${NC}"
    ((TESTS_PASSED++))
}

test_fail() {
    local message="${1:-Failed}"
    echo -e "${RED}[FAIL] ${message}${NC}"
    ((TESTS_FAILED++))
}

test_skip() {
    local message="${1:-Skipped}"
    echo -e "${YELLOW}[SKIP] ${message}${NC}"
}

test_info() {
    local message="$1"
    echo -e "${BLUE}[INFO] ${message}${NC}"
}

# Test assertions
assert_equals() {
    local expected="$1"
    local actual="$2"
    local message="${3:-Assertion failed}"

    if [[ "$expected" == "$actual" ]]; then
        test_pass "$message"
    else
        test_fail "$message: expected '$expected', got '$actual'"
    fi
}

assert_not_equals() {
    local expected="$1"
    local actual="$2"
    local message="${3:-Assertion failed}"

    if [[ "$expected" != "$actual" ]]; then
        test_pass "$message"
    else
        test_fail "$message: values should not be equal"
    fi
}

assert_contains() {
    local haystack="$1"
    local needle="$2"
    local message="${3:-Assertion failed}"

    if echo "$haystack" | grep -q "$needle"; then
        test_pass "$message"
    else
        test_fail "$message: '$needle' not found in '$haystack'"
    fi
}

assert_not_contains() {
    local haystack="$1"
    local needle="$2"
    local message="${3:-Assertion failed}"

    if ! echo "$haystack" | grep -q "$needle"; then
        test_pass "$message"
    else
        test_fail "$message: '$needle' should not be in '$haystack'"
    fi
}

assert_file_exists() {
    local file_path="$1"
    local message="${2:-File should exist}"

    if [[ -f "$file_path" ]]; then
        test_pass "$message"
    else
        test_fail "$message: file '$file_path' does not exist"
    fi
}

assert_file_not_exists() {
    local file_path="$1"
    local message="${2:-File should not exist}"

    if [[ ! -f "$file_path" ]]; then
        test_pass "$message"
    else
        test_fail "$message: file '$file_path' exists"
    fi
}

assert_file_executable() {
    local file_path="$1"
    local message="${2:-File should be executable}"

    if [[ -x "$file_path" ]]; then
        test_pass "$message"
    else
        test_fail "$message: file '$file_path' is not executable"
    fi
}

assert_dir_exists() {
    local dir_path="$1"
    local message="${2:-Directory should exist}"

    if [[ -d "$dir_path" ]]; then
        test_pass "$message"
    else
        test_fail "$message: directory '$dir_path' does not exist"
    fi
}

# Environment setup
setup_test_env() {
    local test_name="$1"
    local test_dir="/tmp/oos_test_${test_name}_$$"

    # Create test directory
    mkdir -p "$test_dir"
    cd "$test_dir"

    echo "$test_dir"
}

cleanup_test_env() {
    local test_dir="$1"

    if [[ -n "$test_dir" && "$test_dir" == /tmp/oos_test_* ]]; then
        cd /tmp
        rm -rf "$test_dir"
    fi
}

# Mock functions for testing
mock_curl() {
    local url="$1"
    shift

    # Parse URL to determine mock response
    case "$url" in
        *"/v1/models"*)
            echo '{"data": [{"id": "glm-4.5", "object": "model"}]}'
            return 0
            ;;
        *"/v1/messages"*)
            echo '{"content": [{"type": "text", "text": "Mock response"}]}'
            return 0
            ;;
        *)
            echo '{"error": {"message": "Mock error"}}'
            return 1
            ;;
    esac
}

# Test helpers
run_with_timeout() {
    local timeout="$1"
    shift
    local cmd=("$@")

    # Use timeout command if available
    if command -v timeout >/dev/null 2>&1; then
        timeout "$timeout" "${cmd[@]}"
    else
        # Fallback for systems without timeout
        "${cmd[@]}"
    fi
}

retry_command() {
    local max_attempts="$1"
    local delay="$2"
    shift 2
    local cmd=("$@")

    local attempt=1
    while ((attempt <= max_attempts)); do
        if "${cmd[@]}"; then
            return 0
        fi

        if ((attempt < max_attempts)); then
            sleep "$delay"
        fi

        ((attempt++))
    done

    return 1
}

# Test suite summary
print_test_summary() {
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
        return 0
    else
        echo
        echo -e "${RED}$TESTS_FAILED test(s) failed!${NC}"
        return 1
    fi
}

# Export functions
export -f test_start test_pass test_fail test_skip test_info
export -f assert_equals assert_not_equals assert_contains assert_not_contains
export -f assert_file_exists assert_file_not_exists assert_file_executable assert_dir_exists
export -f setup_test_env cleanup_test_env mock_curl run_with_timeout retry_command print_test_summary