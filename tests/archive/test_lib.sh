#!/usr/bin/env bash

# Simple test assertion library for Bash
TEST_COUNT=0
PASS_COUNT=0
FAIL_COUNT=0
CURRENT_TEST=""

# Test result tracking
declare -a FAILED_TESTS=()
declare -a PASSED_TESTS=()

# Colors for test output
T_RED='\033[0;31m'
T_GREEN='\033[0;32m'
T_YELLOW='\033[1;33m'
T_BLUE='\033[0;34m'
T_NC='\033[0m'

# Test functions
start_test() {
  CURRENT_TEST="$1"
  ((TEST_COUNT++))
  echo -e "${T_BLUE}TEST ${TEST_COUNT}:${T_NC} $CURRENT_TEST"
}

assert_equals() {
  local expected="$1"
  local actual="$2"
  local message="${3:-}"

  if [[ "$expected" == "$actual" ]]; then
    echo -e "  ${T_GREEN}✓${T_NC} ${message:-Values match}"
    ((PASS_COUNT++))
    return 0
  else
    echo -e "  ${T_RED}✗${T_NC} ${message:-Values don't match}"
    echo -e "    Expected: $expected"
    echo -e "    Actual:   $actual"
    FAILED_TESTS+=("$CURRENT_TEST")
    ((FAIL_COUNT++))
    return 1
  fi
}

assert_not_equals() {
  local unexpected="$1"
  local actual="$2"
  local message="${3:-}"

  if [[ "$unexpected" != "$actual" ]]; then
    echo -e "  ${T_GREEN}✓${T_NC} ${message:-Values are different}"
    ((PASS_COUNT++))
    return 0
  else
    echo -e "  ${T_RED}✗${T_NC} ${message:-Values should be different}"
    echo -e "    Unexpected: $unexpected"
    echo -e "    Actual:     $actual"
    FAILED_TESTS+=("$CURRENT_TEST")
    ((FAIL_COUNT++))
    return 1
  fi
}

assert_true() {
  local condition="$1"
  local message="${2:-}"

  if [[ "$condition" == "true" ]] || [[ "$condition" == "0" ]]; then
    echo -e "  ${T_GREEN}✓${T_NC} ${message:-Condition is true}"
    ((PASS_COUNT++))
    return 0
  else
    echo -e "  ${T_RED}✗${T_NC} ${message:-Condition should be true}"
    echo -e "    Value: $condition"
    FAILED_TESTS+=("$CURRENT_TEST")
    ((FAIL_COUNT++))
    return 1
  fi
}

assert_false() {
  local condition="$1"
  local message="${2:-}"

  if [[ "$condition" == "false" ]] || [[ "$condition" == "1" ]]; then
    echo -e "  ${T_GREEN}✓${T_NC} ${message:-Condition is false}"
    ((PASS_COUNT++))
    return 0
  else
    echo -e "  ${T_RED}✗${T_NC} ${message:-Condition should be false}"
    echo -e "    Value: $condition"
    FAILED_TESTS+=("$CURRENT_TEST")
    ((FAIL_COUNT++))
    return 1
  fi
}

assert_file_exists() {
  local file="$1"
  local message="${2:-}"

  if [[ -f "$file" ]]; then
    echo -e "  ${T_GREEN}✓${T_NC} ${message:-File exists: $file}"
    ((PASS_COUNT++))
    return 0
  else
    echo -e "  ${T_RED}✗${T_NC} ${message:-File should exist: $file}"
    FAILED_TESTS+=("$CURRENT_TEST")
    ((FAIL_COUNT++))
    return 1
  fi
}

assert_command_success() {
  local command="$1"
  local message="${2:-}"

  if eval "$command" >/dev/null 2>&1; then
    echo -e "  ${T_GREEN}✓${T_NC} ${message:-Command succeeded: $command}"
    ((PASS_COUNT++))
    return 0
  else
    echo -e "  ${T_RED}✗${T_NC} ${message:-Command should succeed: $command}"
    FAILED_TESTS+=("$CURRENT_TEST")
    ((FAIL_COUNT++))
    return 1
  fi
}

assert_command_fails() {
  local command="$1"
  local message="${2:-}"

  if ! eval "$command" >/dev/null 2>&1; then
    echo -e "  ${T_GREEN}✓${T_NC} ${message:-Command failed as expected: $command}"
    ((PASS_COUNT++))
    return 0
  else
    echo -e "  ${T_RED}✗${T_NC} ${message:-Command should fail: $command}"
    FAILED_TESTS+=("$CURRENT_TEST")
    ((FAIL_COUNT++))
    return 1
  fi
}

finish_tests() {
  echo
  echo "Test Results:"
  echo "============="
  echo -e "Tests run: ${TEST_COUNT}"
  echo -e "${T_GREEN}Passed: ${PASS_COUNT}${T_NC}"
  echo -e "${T_RED}Failed: ${FAIL_COUNT}${T_NC}"

  if [[ ${#FAILED_TESTS[@]} -gt 0 ]]; then
    echo
    echo "Failed Tests:"
    for test in "${FAILED_TESTS[@]}"; do
      echo -e "  ${T_RED}✗${T_NC} $test"
    done
  fi

  if [[ $FAIL_COUNT -eq 0 ]]; then
    echo -e "\n${T_GREEN}All tests passed!${T_NC}"
    return 0
  else
    echo -e "\n${T_RED}Some tests failed.${T_NC}"
    return 1
  fi
}
