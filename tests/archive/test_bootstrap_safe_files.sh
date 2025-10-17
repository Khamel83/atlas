#!/usr/bin/env bash
set -euo pipefail

# Test Suite for Bootstrap Safe File Creation
# Tests all permutations of file creation scenarios
# Incorporates usability validation principles:
# - User understanding of script behavior
# - Clear error communication
# - Predictable outcomes
# - Data safety validation

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
BOOTSTRAP_SCRIPT="$PROJECT_ROOT/scripts/bootstrap_enhanced.sh"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Test results tracking
TESTS_RUN=0
TESTS_PASSED=0
TESTS_FAILED=0

# Test utilities
log() { echo -e "${BLUE}[TEST]${NC} $*"; }
pass() { echo -e "${GREEN}[PASS]${NC} $*"; ((TESTS_PASSED++)); }
fail() { echo -e "${RED}[FAIL]${NC} $*"; ((TESTS_FAILED++)); }
warn() { echo -e "${YELLOW}[WARN]${NC} $*"; }

run_test() {
    local test_name="$1"
    shift
    log "Running: $test_name"
    ((TESTS_RUN++))

    if "$@"; then
        pass "$test_name"
    else
        fail "$test_name"
    fi
}

# Setup test environment
setup_test_env() {
    local test_dir="$1"
    rm -rf "$test_dir"
    mkdir -p "$test_dir"
    cd "$test_dir"

    # Create minimal .env for testing
    cat > .env <<'EOF'
OPENROUTER_KEYS=sk-test-key-123
CONTEXT7_API_KEY=test-context7-key
GITHUB_PAT=ghp_test-token
EOF
}

cleanup_test_env() {
    local test_dir="$1"
    cd "$PROJECT_ROOT"
    rm -rf "$test_dir"
}

# Test 1: New file creation (should work)
test_new_file_creation() {
    local test_dir="$PROJECT_ROOT/test_env_new"
    setup_test_env "$test_dir"

    # Run bootstrap in dry-run mode first
    if "$BOOTSTRAP_SCRIPT" --dry-run --no-git --no-github test_project "$test_dir" >/dev/null 2>&1; then
        # Run actual bootstrap
        if "$BOOTSTRAP_SCRIPT" --no-git --no-github --no-preflight test_project "$test_dir" >/dev/null 2>&1; then
            # Check if files were created
            if [[ -f "docs/CLAUDE.md" && -f "docs/GEMINI.md" && -f ".agents/agents.md" ]]; then
                cleanup_test_env "$test_dir"
                return 0
            fi
        fi
    fi

    cleanup_test_env "$test_dir"
    return 1
}

# Test 2: Existing file skip (should skip without --force)
test_existing_file_skip() {
    local test_dir="$PROJECT_ROOT/test_env_skip"
    setup_test_env "$test_dir"

    # Pre-create files with different content
    mkdir -p docs .agents
    echo "# Existing Claude content" > docs/CLAUDE.md
    echo "# Existing agents content" > .agents/agents.md

    # Run bootstrap without --force
    local output
    output=$("$BOOTSTRAP_SCRIPT" --no-git --no-github --no-preflight test_project "$test_dir" 2>&1 || true)

    # Check that original content is preserved
    if [[ "$(cat docs/CLAUDE.md)" == "# Existing Claude content" ]] &&
       [[ "$(cat .agents/agents.md)" == "# Existing agents content" ]] &&
       echo "$output" | grep -q "Skipping existing"; then
        cleanup_test_env "$test_dir"
        return 0
    fi

    cleanup_test_env "$test_dir"
    return 1
}

# Test 3: Existing file overwrite with --force (should overwrite)
test_existing_file_force_overwrite() {
    local test_dir="$PROJECT_ROOT/test_env_force"
    setup_test_env "$test_dir"

    # Pre-create files with different content
    mkdir -p docs .agents
    echo "# Existing Claude content" > docs/CLAUDE.md
    echo "# Existing agents content" > .agents/agents.md

    # Run bootstrap with --force
    if "$BOOTSTRAP_SCRIPT" --force --no-git --no-github --no-preflight test_project "$test_dir" >/dev/null 2>&1; then
        # Check that content was overwritten (should contain bootstrap-generated content)
        if [[ "$(cat docs/CLAUDE.md)" != "# Existing Claude content" ]] &&
           [[ "$(cat .agents/agents.md)" != "# Existing agents content" ]] &&
           grep -q "Claude Code Overlay" docs/CLAUDE.md &&
           grep -q "Agent Instructions" .agents/agents.md; then
            cleanup_test_env "$test_dir"
            return 0
        fi
    fi

    cleanup_test_env "$test_dir"
    return 1
}

# Test 4: Permission errors (should fail gracefully)
test_permission_errors() {
    local test_dir="$PROJECT_ROOT/test_env_perms"
    setup_test_env "$test_dir"

    # Create read-only directory
    mkdir -p docs
    chmod 444 docs

    # Run bootstrap (should handle permission error gracefully)
    local exit_code=0
    "$BOOTSTRAP_SCRIPT" --no-git --no-github --no-preflight test_project "$test_dir" >/dev/null 2>&1 || exit_code=$?

    # Restore permissions for cleanup
    chmod 755 docs
    cleanup_test_env "$test_dir"

    # Should have failed but not crashed
    [[ $exit_code -ne 0 ]]
}

# Test 5: Directory vs file conflict (should handle gracefully)
test_directory_vs_file_conflict() {
    local test_dir="$PROJECT_ROOT/test_env_conflict"
    setup_test_env "$test_dir"

    # Create directory where file should be
    mkdir -p docs/CLAUDE.md

    # Run bootstrap (should handle conflict)
    local exit_code=0
    "$BOOTSTRAP_SCRIPT" --no-git --no-github --no-preflight test_project "$test_dir" >/dev/null 2>&1 || exit_code=$?

    cleanup_test_env "$test_dir"

    # Should have failed gracefully
    [[ $exit_code -ne 0 ]]
}

# Test 6: Symlink handling
test_symlink_handling() {
    local test_dir="$PROJECT_ROOT/test_env_symlink"
    setup_test_env "$test_dir"

    # Create symlink where file should be
    mkdir -p docs
    echo "# Target content" > docs/target.md
    ln -s target.md docs/CLAUDE.md

    # Run bootstrap without --force (should skip symlink)
    local output
    output=$("$BOOTSTRAP_SCRIPT" --no-git --no-github --no-preflight test_project "$test_dir" 2>&1 || true)

    # Check that symlink is preserved
    if [[ -L "docs/CLAUDE.md" ]] && echo "$output" | grep -q "Skipping existing"; then
        cleanup_test_env "$test_dir"
        return 0
    fi

    cleanup_test_env "$test_dir"
    return 1
}

# Test 7: Backup functionality validation
test_backup_functionality() {
    local test_dir="$PROJECT_ROOT/test_env_backup"
    setup_test_env "$test_dir"

    # Create some existing files
    mkdir -p docs .agents bin
    echo "# Existing content" > docs/CLAUDE.md
    echo "#!/bin/bash" > bin/test.sh

    # Run bootstrap (should create backup)
    if "$BOOTSTRAP_SCRIPT" --no-git --no-github --no-preflight test_project "$test_dir" >/dev/null 2>&1; then
        # Check if backup was created
        local backup_dirs=(*.backup.*)
        if [[ ${#backup_dirs[@]} -gt 0 ]] && [[ -d "${backup_dirs[0]}" ]]; then
            cleanup_test_env "$test_dir"
            return 0
        fi
    fi

    cleanup_test_env "$test_dir"
    return 1
}

# Test 8: User understanding validation (measures communication clarity)
test_user_understanding() {
    local test_dir="$PROJECT_ROOT/test_env_understanding"
    setup_test_env "$test_dir"

    # Create existing file with important user content
    mkdir -p docs
    echo "# Important user customizations - DO NOT DELETE" > docs/CLAUDE.md

    # Run bootstrap and capture output
    local output
    output=$("$BOOTSTRAP_SCRIPT" --verbose --no-git --no-github --no-preflight test_project "$test_dir" 2>&1 || true)

    # Validate communication clarity (what users need to understand)
    local understanding_checks=0

    # Check 1: User knows files were skipped
    if echo "$output" | grep -q "Skipping existing"; then
        ((understanding_checks++))
    fi

    # Check 2: User knows how to override if desired
    if echo "$output" | grep -q "use --force to overwrite"; then
        ((understanding_checks++))
    fi

    # Check 3: User knows backup will be created if forcing
    if echo "$output" | grep -q "backup will be created"; then
        ((understanding_checks++))
    fi

    # Check 4: Original content is preserved (most important)
    if [[ "$(cat docs/CLAUDE.md)" == "# Important user customizations - DO NOT DELETE" ]]; then
        ((understanding_checks++))
    fi

    cleanup_test_env "$test_dir"

    # Success if all understanding indicators are present
    [[ $understanding_checks -eq 4 ]]
}

# Test 9: Error communication clarity
test_error_communication() {
    local test_dir="$PROJECT_ROOT/test_env_errors"
    setup_test_env "$test_dir"

    # Create problematic scenarios
    mkdir -p docs/CLAUDE.md  # Directory where file should be

    # Run bootstrap and capture error output
    local output
    output=$("$BOOTSTRAP_SCRIPT" --verbose --no-git --no-github --no-preflight test_project "$test_dir" 2>&1 || true)

    # Validate error communication
    if echo "$output" | grep -q "Cannot create.*is a directory"; then
        cleanup_test_env "$test_dir"
        return 0
    fi

    cleanup_test_env "$test_dir"
    return 1
}

# Test 10: Predictable behavior validation
test_predictable_behavior() {
    local test_dir="$PROJECT_ROOT/test_env_predictable"
    setup_test_env "$test_dir"

    # Run 1: Clean slate
    local output1
    output1=$("$BOOTSTRAP_SCRIPT" --dry-run --verbose --no-git --no-github --no-preflight test_project "$test_dir" 2>&1 || true)

    # Run 2: Same command again (should have identical output)
    local output2
    output2=$("$BOOTSTRAP_SCRIPT" --dry-run --verbose --no-git --no-github --no-preflight test_project "$test_dir" 2>&1 || true)

    cleanup_test_env "$test_dir"

    # Behavior should be identical between runs
    [[ "$output1" == "$output2" ]]
}

# Main test runner
main() {
    echo "🧪 Bootstrap Safe File Creation Test Suite"
    echo "=========================================="
    echo

    # Check if bootstrap script exists
    if [[ ! -f "$BOOTSTRAP_SCRIPT" ]]; then
        fail "Bootstrap script not found: $BOOTSTRAP_SCRIPT"
        exit 1
    fi

    # Run all tests
    run_test "New file creation" test_new_file_creation
    run_test "Existing file skip (no --force)" test_existing_file_skip
    run_test "Existing file overwrite (with --force)" test_existing_file_force_overwrite
    run_test "Permission error handling" test_permission_errors
    run_test "Directory vs file conflict" test_directory_vs_file_conflict
    run_test "Symlink handling" test_symlink_handling
    run_test "Backup functionality" test_backup_functionality
    run_test "User understanding validation" test_user_understanding
    run_test "Error communication clarity" test_error_communication
    run_test "Predictable behavior" test_predictable_behavior

    # Results summary
    echo
    echo "=========================================="
    echo "Test Results:"
    echo "  Total: $TESTS_RUN"
    echo "  Passed: $TESTS_PASSED"
    echo "  Failed: $TESTS_FAILED"

    if [[ $TESTS_FAILED -eq 0 ]]; then
        echo -e "${GREEN}✅ All tests passed!${NC}"
        exit 0
    else
        echo -e "${RED}❌ $TESTS_FAILED test(s) failed${NC}"
        exit 1
    fi
}

# Run tests
main "$@"