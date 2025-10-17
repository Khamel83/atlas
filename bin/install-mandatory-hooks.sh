#!/usr/bin/env bash
set -euo pipefail

# Install Mandatory Git Hooks - Makes Development Gate Absolutely Required
# This script installs git hooks that BLOCK commits/pushes without proper environment

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
HOOKS_DIR="$PROJECT_ROOT/.git/hooks"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m'

log() {
    echo -e "${BLUE}[hooks]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[hooks]${NC} $1"
}

log_error() {
    echo -e "${RED}[hooks]${NC} $1" >&2
}

log_warning() {
    echo -e "${YELLOW}[hooks]${NC} $1"
}

# Check if we're in a git repository
check_git_repo() {
    if [[ ! -d "$PROJECT_ROOT/.git" ]]; then
        log_error "Not in a git repository. Cannot install hooks."
        exit 1
    fi
    log_success "Git repository detected"
}

# Install pre-commit hook
install_pre_commit_hook() {
    local hook_file="$HOOKS_DIR/pre-commit"

    log "Installing pre-commit hook..."

    cat > "$hook_file" << 'EOF'
#!/usr/bin/env bash
set -euo pipefail

# Mandatory Development Gate - Pre-Commit Hook
# This hook BLOCKS commits unless development environment is properly set up

echo "🚪 Running mandatory development gate before commit..."

# Run the development gate
if ./bin/dev-gate.sh; then
    echo "✅ Development gate passed - commit allowed"
    exit 0
else
    echo
    echo "❌ COMMIT BLOCKED: Development environment not ready"
    echo
    echo "Fix the issues above, then try committing again."
    echo "Emergency bypass: DEV_GATE_BYPASS=true git commit"
    exit 1
fi
EOF

    chmod +x "$hook_file"
    log_success "Pre-commit hook installed"
}

# Install pre-push hook
install_pre_push_hook() {
    local hook_file="$HOOKS_DIR/pre-push"

    log "Installing pre-push hook..."

    cat > "$hook_file" << 'EOF'
#!/usr/bin/env bash
set -euo pipefail

# Mandatory Development Gate - Pre-Push Hook
# Extra safety: ensure environment is still valid before pushing

echo "🚪 Validating development environment before push..."

# Run the development gate
if ./bin/dev-gate.sh; then
    echo "✅ Development environment validated - push allowed"
    exit 0
else
    echo
    echo "❌ PUSH BLOCKED: Development environment not ready"
    echo
    echo "Your environment has become invalid since your last commit."
    echo "Fix the issues above, then try pushing again."
    echo "Emergency bypass: DEV_GATE_BYPASS=true git push"
    exit 1
fi
EOF

    chmod +x "$hook_file"
    log_success "Pre-push hook installed"
}

# Install post-checkout hook
install_post_checkout_hook() {
    local hook_file="$HOOKS_DIR/post-checkout"

    log "Installing post-checkout hook..."

    cat > "$hook_file" << 'EOF'
#!/usr/bin/env bash
set -euo pipefail

# Mandatory Development Gate - Post-Checkout Hook
# Automatically validate environment after branch changes

echo "🚪 Validating development environment after checkout..."

# Clear any existing gate status
rm -f .dev-gate-passed

# Run the development gate (but don't block checkout)
if ./bin/dev-gate.sh; then
    echo "✅ Development environment ready for new branch"
else
    echo
    echo "⚠️  WARNING: Development environment needs attention"
    echo "Run './bin/dev-gate.sh' to fix issues before developing"
fi
EOF

    chmod +x "$hook_file"
    log_success "Post-checkout hook installed"
}

# Install commit-msg hook for safety
install_commit_msg_hook() {
    local hook_file="$HOOKS_DIR/commit-msg"

    log "Installing commit-msg hook..."

    cat > "$hook_file" << 'EOF'
#!/usr/bin/env bash
set -euo pipefail

# Mandatory Development Gate - Commit Message Hook
# Final safety check before commit is finalized

# If gate file doesn't exist, something is wrong
if [[ ! -f .dev-gate-passed ]]; then
    echo "❌ CRITICAL ERROR: Development gate was bypassed improperly"
    echo "Run './bin/dev-gate.sh' to validate your environment"
    exit 1
fi

# Check if gate file is recent (within last hour)
if [[ -f .dev-gate-passed ]]; then
    local gate_time=$(stat -f %m .dev-gate-passed 2>/dev/null || stat -c %Y .dev-gate-passed 2>/dev/null)
    local current_time=$(date +%s)
    local age=$((current_time - gate_time))

    # If gate is older than 1 hour, re-validate
    if [[ $age -gt 3600 ]]; then
        echo "⚠️  Development gate is stale (older than 1 hour)"
        echo "Re-validating environment..."
        if ./bin/dev-gate.sh; then
            echo "✅ Environment re-validated"
        else
            echo "❌ Environment validation failed"
            exit 1
        fi
    fi
fi
EOF

    chmod +x "$hook_file"
    log_success "Commit-msg hook installed"
}

# Main installation function
main() {
    echo -e "\n${BOLD}${BLUE}🔒 Installing Mandatory Development Gate Hooks${NC}"
    echo "=============================================="

    check_git_repo

    # Create hooks directory if it doesn't exist
    mkdir -p "$HOOKS_DIR"

    # Install all hooks
    install_pre_commit_hook
    install_pre_push_hook
    install_post_checkout_hook
    install_commit_msg_hook

    echo
    log_success "All mandatory hooks installed successfully!"

    echo
    echo -e "${YELLOW}What this means:${NC}"
    echo "  ❌ Cannot commit without passing development gate"
    echo "  ❌ Cannot push without valid environment"
    echo "  🔄 Environment auto-checked after branch changes"
    echo "  ⏰ Gate status expires after 1 hour"
    echo
    echo -e "${BLUE}Emergency bypasses:${NC}"
    echo "  DEV_GATE_BYPASS=true git commit"
    echo "  DEV_GATE_BYPASS=true git push"
    echo
    echo -e "${GREEN}Result: 100% enforcement for all developers${NC}"
}

# Run if executed directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi