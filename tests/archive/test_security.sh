#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
source "$SCRIPT_DIR/test_lib.sh"

start_test "Environment file permissions"
if [[ -f "$PROJECT_ROOT/.env" ]]; then
  perms=$(stat -c "%a" "$PROJECT_ROOT/.env" 2>/dev/null || stat -f "%Lp" "$PROJECT_ROOT/.env" 2>/dev/null || echo "000")
  if [[ "$perms" =~ ^[67][0-7][0-7]$ ]]; then
    echo -e "  ${T_GREEN}✓${T_NC} Environment file has secure permissions ($perms)"
    ((PASS_COUNT++))
  else
    echo -e "  ${T_RED}✗${T_NC} Environment file has insecure permissions ($perms)"
    ((FAIL_COUNT++))
    FAILED_TESTS+=("$CURRENT_TEST")
  fi
else
  echo "  Skipped: .env file not found"
fi

start_test "Script executable permissions"
scripts=(
  "bin/safe_source_env.sh"
  "bin/select_or_key.sh"
  "bin/diagnose.sh"
  "bin/health_monitor.sh"
  "bootstrap_enhanced.sh"
)

all_executable=true
for script in "${scripts[@]}"; do
  if [[ -f "$PROJECT_ROOT/$script" ]]; then
    if [[ ! -x "$PROJECT_ROOT/$script" ]]; then
      echo -e "  ${T_RED}✗${T_NC} Script not executable: $script"
      all_executable=false
    fi
  fi
done

if [[ "$all_executable" == "true" ]]; then
  echo -e "  ${T_GREEN}✓${T_NC} All scripts are executable"
  ((PASS_COUNT++))
else
  echo -e "  ${T_RED}✗${T_NC} Some scripts are not executable"
  ((FAIL_COUNT++))
  FAILED_TESTS+=("$CURRENT_TEST")
fi

start_test "No hardcoded secrets in scripts"
secret_patterns=(
  "sk-[a-zA-Z0-9-_]{43,}"  # OpenAI/OpenRouter keys
  "ghp_[a-zA-Z0-9]{36}"    # GitHub PAT
  "[a-zA-Z0-9]{32,}"       # Generic long strings
)

found_secrets=false
for script in bin/*.sh bootstrap*.sh; do
  if [[ -f "$script" ]]; then
    for pattern in "${secret_patterns[@]}"; do
      if grep -E "$pattern" "$script" >/dev/null 2>&1; then
        # Allow test patterns and placeholder values
        if ! grep -E "(test-key|your_.*_key_here|placeholder|example)" "$script" >/dev/null 2>&1; then
          echo -e "  ${T_RED}✗${T_NC} Potential secret found in $script"
          found_secrets=true
        fi
      fi
    done
  fi
done

if [[ "$found_secrets" == "false" ]]; then
  echo -e "  ${T_GREEN}✓${T_NC} No hardcoded secrets found"
  ((PASS_COUNT++))
else
  echo -e "  ${T_RED}✗${T_NC} Potential hardcoded secrets found"
  ((FAIL_COUNT++))
  FAILED_TESTS+=("$CURRENT_TEST")
fi

start_test "Git ignore patterns"
if [[ -f "$PROJECT_ROOT/.gitignore" ]]; then
  required_patterns=(
    ".env"
    "*.log"
    ".venv"
  )

  all_patterns_found=true
  for pattern in "${required_patterns[@]}"; do
    if ! grep -q "$pattern" "$PROJECT_ROOT/.gitignore"; then
      echo -e "  ${T_RED}✗${T_NC} Missing gitignore pattern: $pattern"
      all_patterns_found=false
    fi
  done

  if [[ "$all_patterns_found" == "true" ]]; then
    echo -e "  ${T_GREEN}✓${T_NC} All required gitignore patterns present"
    ((PASS_COUNT++))
  else
    echo -e "  ${T_RED}✗${T_NC} Some gitignore patterns missing"
    ((FAIL_COUNT++))
    FAILED_TESTS+=("$CURRENT_TEST")
  fi
else
  echo -e "  ${T_YELLOW}⚠${T_NC} .gitignore file not found"
  ((PASS_COUNT++))  # Warning, not failure
fi

finish_tests
