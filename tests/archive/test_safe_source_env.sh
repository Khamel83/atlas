#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
source "$SCRIPT_DIR/test_lib.sh"

# Setup test environment
TEST_ENV_DIR=$(mktemp -d)
TEST_ENV_FILE="$TEST_ENV_DIR/.env"
TEST_EXPORT_FILE="$TEST_ENV_DIR/.env.export"
trap "rm -rf $TEST_ENV_DIR" EXIT

start_test "safe_source_env with valid environment"
cat > "$TEST_ENV_FILE" <<'TESTENV'
# Test environment
TEST_VAR_1=value1
TEST_VAR_2=value2
OPENROUTER_KEYS=key1,key2
TESTENV

VERBOSE=true "$PROJECT_ROOT/bin/safe_source_env.sh" "$TEST_ENV_FILE" "$TEST_EXPORT_FILE"
assert_file_exists "$TEST_EXPORT_FILE" "Export file should be created"
assert_command_success "grep -q 'TEST_VAR_1=value1' '$TEST_EXPORT_FILE'" "TEST_VAR_1 should be exported"
assert_command_success "grep -q 'TEST_VAR_2=value2' '$TEST_EXPORT_FILE'" "TEST_VAR_2 should be exported"

start_test "safe_source_env with invalid lines"
cat > "$TEST_ENV_FILE" <<'TESTENV'
# Valid comment
VALID_VAR=valid_value
invalid line without equals
=invalid_start
123INVALID_NAME=value
TESTENV

VERBOSE=true "$PROJECT_ROOT/bin/safe_source_env.sh" "$TEST_ENV_FILE" "$TEST_EXPORT_FILE"
assert_command_success "grep -q 'VALID_VAR=valid_value' '$TEST_EXPORT_FILE'" "Valid variable should be exported"
assert_command_fails "grep -q 'invalid line' '$TEST_EXPORT_FILE'" "Invalid line should not be exported"

start_test "safe_source_env with missing file"
assert_command_fails "$PROJECT_ROOT/bin/safe_source_env.sh /nonexistent/file" "Should fail with missing file"

finish_tests
