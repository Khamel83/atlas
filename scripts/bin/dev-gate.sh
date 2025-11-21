#!/usr/bin/env bash
set -euo pipefail

# Mandatory Development Gate - NO DEVELOPMENT WITHOUT PROPER SETUP
# This script MUST pass before any development work can begin
# Version: 1.0.0

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
GATE_LOCKFILE="$PROJECT_ROOT/.dev-gate-passed"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color
BOLD='\033[1m'

# Gate status tracking
GATE_FAILED=false
ISSUES=()

log_error() {
    echo -e "${RED}❌ GATE FAILURE:${NC} $1" >&2
    ISSUES+=("$1")
    GATE_FAILED=true
}

log_warning() {
    echo -e "${YELLOW}⚠️  WARNING:${NC} $1" >&2
}

log_success() {
    echo -e "${GREEN}✅${NC} $1"
}

log_info() {
    echo -e "${BLUE}ℹ️${NC} $1"
}

log_header() {
    echo -e "\n${BOLD}${BLUE}🚪 DEVELOPMENT GATE - MANDATORY CHECKS${NC}"
    echo "========================================"
}

# Check 1: uv installation and setup
check_uv_environment() {
    log_info "Checking uv environment..."

    # Check if uv is installed
    if ! command -v uv &> /dev/null; then
        log_error "uv is not installed. Install with: curl -LsSf https://astral.sh/uv/install.sh | sh"
        return 1
    fi

    log_success "uv is installed ($(uv --version))"

    # Check if pyproject.toml exists
    if [[ ! -f "$PROJECT_ROOT/pyproject.toml" ]]; then
        log_error "pyproject.toml missing. Run: uv init"
        return 1
    fi

    # Ensure virtual environment exists and is synced
    if ! uv sync --check &> /dev/null; then
        log_info "Syncing uv environment..."
        if ! uv sync; then
            log_error "Failed to sync uv environment"
            return 1
        fi
    fi

    log_success "uv environment is synced and ready"
    return 0
}

# Check 2: Environment variables from centralized source
check_environment_variables() {
    log_info "Checking environment variable setup..."

    # Check if 1Password CLI is available and signed in
    if ! command -v op &> /dev/null; then
        log_error "1Password CLI (op) is not installed"
        return 1
    fi

    if ! op whoami &> /dev/null; then
        log_error "Not signed into 1Password CLI. Run: op signin"
        return 1
    fi

    log_success "1Password CLI is available and signed in"

    # Check if we can access the environment configuration
    local vault="${OP_VAULT:-Personal}"
    local item="${OP_ITEM:-bootstrap-env}"

    if ! op item get "$item" --vault "$vault" &> /dev/null; then
        log_error "Cannot access environment item '$item' in vault '$vault'"
        return 1
    fi

    log_success "Environment variables are accessible from 1Password"
    return 0
}

# Check 3: Python version and virtual environment
check_python_environment() {
    log_info "Checking Python environment..."

    # Check if we're in a virtual environment (uv should handle this)
    if [[ -z "${VIRTUAL_ENV:-}" ]] && [[ -z "${UV_PROJECT_ENVIRONMENT:-}" ]]; then
        log_warning "No virtual environment detected, but uv may manage this automatically"
    fi

    # Check Python version
    local python_version
    python_version=$(uv run python --version 2>/dev/null || echo "Unknown")
    log_success "Python environment ready: $python_version"

    return 0
}

# Check 4: Git repository status
check_git_status() {
    log_info "Checking git repository status..."

    if [[ ! -d "$PROJECT_ROOT/.git" ]]; then
        log_error "Not in a git repository"
        return 1
    fi

    # Check if there are any staged changes that shouldn't be committed
    if git diff --cached --quiet; then
        log_success "No staged changes"
    else
        log_warning "There are staged changes - review before committing"
    fi

    return 0
}

# Check 5: Required tools and dependencies
check_required_tools() {
    log_info "Checking required development tools..."

    local required_tools=("git" "curl" "rsync")
    local missing_tools=()

    for tool in "${required_tools[@]}"; do
        if ! command -v "$tool" &> /dev/null; then
            missing_tools+=("$tool")
        fi
    done

    if [[ ${#missing_tools[@]} -gt 0 ]]; then
        log_error "Missing required tools: ${missing_tools[*]}"
        return 1
    fi

    log_success "All required tools are available"
    return 0
}

# Main gate validation
run_development_gate() {
    log_header

    # Run all checks
    check_required_tools
    check_uv_environment
    check_environment_variables
    check_python_environment
    check_git_status

    # Final gate decision
    if [[ "$GATE_FAILED" == "true" ]]; then
        echo -e "\n${RED}${BOLD}🚫 DEVELOPMENT GATE FAILED${NC}"
        echo -e "${RED}Issues that must be resolved:${NC}"
        for issue in "${ISSUES[@]}"; do
            echo -e "  ${RED}•${NC} $issue"
        done
        echo -e "\n${YELLOW}Fix these issues before development can continue.${NC}"
        exit 1
    else
        echo -e "\n${GREEN}${BOLD}🎉 DEVELOPMENT GATE PASSED${NC}"
        echo -e "${GREEN}Environment is ready for development!${NC}"

        # Create lockfile to indicate gate passed
        touch "$GATE_LOCKFILE"
        echo "$(date)" > "$GATE_LOCKFILE"

        exit 0
    fi
}

# Allow bypassing gate for emergencies (but log it)
if [[ "${DEV_GATE_BYPASS:-}" == "true" ]]; then
    log_warning "Development gate bypassed via DEV_GATE_BYPASS=true"
    # Still create lockfile for tools to work
    touch "$GATE_LOCKFILE"
    echo "$(date)" > "$GATE_LOCKFILE"
    exit 0
fi

# Run the gate
run_development_gate