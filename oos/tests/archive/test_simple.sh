#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Simple test without the test lib for now
echo "Running simple validation tests..."

# Test 1: Check if essential files exist
echo "TEST 1: Essential files exist"
essential_files=(
  "bin/safe_source_env.sh"
  "bin/select_or_key.sh"
  "bin/diagnose.sh"
  "bin/health_monitor.sh"
  "bootstrap_enhanced.sh"
  "CLAUDE.md"
)

passed=0
total=${#essential_files[@]}

for file in "${essential_files[@]}"; do
  if [[ -f "$PROJECT_ROOT/$file" ]]; then
    echo "  ✓ $file exists"
    ((passed++))
  else
    echo "  ✗ $file missing"
  fi
done

echo "  Result: $passed/$total files found"

# Test 2: Scripts are executable
echo "TEST 2: Scripts are executable"
script_passed=0
script_total=0

for file in bin/*.sh bootstrap_enhanced.sh; do
  if [[ -f "$file" ]]; then
    ((script_total++))
    if [[ -x "$file" ]]; then
      echo "  ✓ $file is executable"
      ((script_passed++))
    else
      echo "  ✗ $file not executable"
    fi
  fi
done

echo "  Result: $script_passed/$script_total scripts executable"

# Test 3: Basic syntax check
echo "TEST 3: Script syntax validation"
syntax_passed=0
syntax_total=0

for script in bin/*.sh bootstrap_enhanced.sh; do
  if [[ -f "$script" ]]; then
    ((syntax_total++))
    if bash -n "$script" 2>/dev/null; then
      echo "  ✓ $script syntax OK"
      ((syntax_passed++))
    else
      echo "  ✗ $script syntax error"
    fi
  fi
done

echo "  Result: $syntax_passed/$syntax_total scripts have valid syntax"

# Summary
total_tests=3
passed_tests=0
[[ $passed -eq $total ]] && ((passed_tests++))
[[ $script_passed -eq $script_total ]] && ((passed_tests++))
[[ $syntax_passed -eq $syntax_total ]] && ((passed_tests++))

echo
echo "Summary: $passed_tests/$total_tests test groups passed"

if [[ $passed_tests -eq $total_tests ]]; then
  echo "✅ All tests passed!"
  exit 0
else
  echo "❌ Some tests failed"
  exit 1
fi