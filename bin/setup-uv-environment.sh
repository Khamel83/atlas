#!/usr/bin/env bash
set -euo pipefail

# Setup uv-based development environment for OOS projects
# This script is called during bootstrap to ensure uv is installed and configured

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log() {
    echo -e "${BLUE}[uv-setup]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[uv-setup]${NC} $1"
}

log_error() {
    echo -e "${RED}[uv-setup]${NC} $1" >&2
}

log_warning() {
    echo -e "${YELLOW}[uv-setup]${NC} $1"
}

# Check if uv is installed, install if needed
install_uv() {
    if command -v uv &> /dev/null; then
        log_success "uv is already installed ($(uv --version))"
        return 0
    fi

    log "Installing uv..."

    # Use the official installer
    if curl -LsSf https://astral.sh/uv/install.sh | sh; then
        log_success "uv installed successfully"

        # Source the environment to make uv available
        if [[ -f "$HOME/.cargo/env" ]]; then
            source "$HOME/.cargo/env"
        fi

        # Add to PATH for current session
        export PATH="$HOME/.cargo/bin:$PATH"

        return 0
    else
        log_error "Failed to install uv"
        return 1
    fi
}

# Initialize uv project if needed
setup_uv_project() {
    cd "$PROJECT_ROOT"

    # If pyproject.toml exists but no uv.lock, sync it
    if [[ -f "pyproject.toml" && ! -f "uv.lock" ]]; then
        log "Syncing uv environment..."
        if uv sync; then
            log_success "uv environment synced"
        else
            log_error "Failed to sync uv environment"
            return 1
        fi
    elif [[ ! -f "pyproject.toml" ]]; then
        log_warning "No pyproject.toml found - creating basic uv project"
        if uv init --name oos --no-readme; then
            log_success "uv project initialized"
        else
            log_error "Failed to initialize uv project"
            return 1
        fi
    else
        log_success "uv project already configured"
    fi
}

# Main setup function
main() {
    log "Setting up uv development environment..."

    install_uv || exit 1
    setup_uv_project || exit 1

    log_success "uv development environment ready!"

    # Show helpful information
    echo
    echo -e "${BLUE}uv Commands:${NC}"
    echo "  uv sync              # Sync dependencies"
    echo "  uv run python        # Run Python in project environment"
    echo "  uv add <package>     # Add dependency"
    echo "  uv run <command>     # Run command in project environment"
    echo
}

# Run if executed directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi