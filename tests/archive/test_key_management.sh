#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
source "$SCRIPT_DIR/test_lib.sh"

# Setup test environment
TEST_KEY_DIR=$(mktemp -d)
TEST_ENV_FILE="$TEST_KEY_DIR/.env"
TEST_ACTIVE_FILE="$TEST_KEY_DIR/.env.active"
trap "rm -rf $TEST_KEY_DIR" EXIT

start_test "select_or_key with no keys"
cat > "$TEST_ENV_FILE" <<'TESTENV'
OTHER_VAR=value
TESTENV

assert_command_fails "VERBOSE=true '$PROJECT_ROOT/bin/select_or_key.sh' '$TEST_ENV_FILE' '$TEST_ACTIVE_FILE'" "Should fail with no keys"

start_test "select_or_key with empty keys"
cat > "$TEST_ENV_FILE" <<'TESTENV'
OPENROUTER_KEYS=
TESTENV

assert_command_fails "VERBOSE=true '$PROJECT_ROOT/bin/select_or_key.sh' '$TEST_ENV_FILE' '$TEST_ACTIVE_FILE'" "Should fail with empty keys"

start_test "select_or_key with test keys (will fail API check)"
cat > "$TEST_ENV_FILE" <<'TESTENV'
OPENROUTER_KEYS=test-key-1,test-key-2
TESTENV

# This should fail because test keys won't work with OpenRouter API
assert_command_fails "VERBOSE=true '$PROJECT_ROOT/bin/select_or_key.sh' '$TEST_ENV_FILE' '$TEST_ACTIVE_FILE'" "Should fail with invalid test keys"

start_test "rotate_or_key with valid setup"
# Create a mock active file
echo "OPENAI_API_KEY=test-key-1" > "$TEST_ACTIVE_FILE"

VERBOSE=true "$PROJECT_ROOT/bin/rotate_or_key.sh" "$TEST_ENV_FILE" "$TEST_ACTIVE_FILE"
current_key=$(grep -E '^OPENAI_API_KEY=' "$TEST_ACTIVE_FILE" | cut -d= -f2-)
assert_equals "test-key-2" "$current_key" "Should rotate to next key"

# Rotate again
VERBOSE=true "$PROJECT_ROOT/bin/rotate_or_key.sh" "$TEST_ENV_FILE" "$TEST_ACTIVE_FILE"
current_key=$(grep -E '^OPENAI_API_KEY=' "$TEST_ACTIVE_FILE" | cut -d= -f2-)
assert_equals "test-key-1" "$current_key" "Should rotate back to first key"

finish_tests
