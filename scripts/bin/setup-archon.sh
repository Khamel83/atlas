#!/bin/bash

# Archon Setup Script for OOS
# Configures Archon project connection for task management integration

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
ENV_FILE="$PROJECT_ROOT/.env"

info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_env_file() {
    if [[ ! -f "$ENV_FILE" ]]; then
        info "Creating .env file..."
        touch "$ENV_FILE"
        echo "# OOS Environment Configuration" > "$ENV_FILE"
        echo "# Created by OOS setup" >> "$ENV_FILE"
        echo "" >> "$ENV_FILE"
    fi
}

check_archon_config() {
    local project_id="${ARCHON_PROJECT_ID:-}"
    local archon_url="${ARCHON_URL:-}"

    if [[ -z "$project_id" ]]; then
        # Check if it's in .env file
        if [[ -f "$ENV_FILE" ]]; then
            project_id=$(grep "^ARCHON_PROJECT_ID=" "$ENV_FILE" | cut -d'=' -f2- | tr -d '"' | tr -d "'" || echo "")
        fi
    fi

    if [[ -z "$archon_url" ]]; then
        if [[ -f "$ENV_FILE" ]]; then
            archon_url=$(grep "^ARCHON_URL=" "$ENV_FILE" | cut -d'=' -f2- | tr -d '"' | tr -d "'" || echo "")
        fi
    fi

    if [[ -n "$project_id" && -n "$archon_url" ]]; then
        return 0
    else
        return 1
    fi
}

show_setup_instructions() {
    echo
    info "=== Archon Setup Instructions ==="
    echo
    echo "Archon provides project management and task tracking for OOS."
    echo "To enable Archon integration:"
    echo
    echo "1. Get your Archon project details:"
    echo "   • Create a new project in your Archon instance"
    echo "   • Or use an existing project"
    echo
    echo "2. Add these lines to your .env file:"
    echo "   ARCHON_URL=https://your-archon-instance.com"
    echo "   ARCHON_PROJECT_ID=your-project-id-here"
    echo
    echo "3. Example configuration:"
    echo "   ARCHON_URL=https://archon.yourcompany.com"
    echo "   ARCHON_PROJECT_ID=550e8400-e29b-41d4-a716-446655440000"
    echo
    echo "4. Test your setup:"
    echo "   $0 --test"
    echo
    echo "Benefits of Archon integration:"
    echo "  ✅ Task tracking and management"
    echo "  ✅ Project status visibility"
    echo "  ✅ Knowledge base search"
    echo "  ✅ Work coordination"
    echo
}

configure_archon() {
    echo
    info "Configuring Archon integration..."

    echo "Enter your Archon details (press Enter to skip if already configured):"
    echo

    read -p "Archon URL (e.g., https://archon.yourcompany.com): " archon_url
    read -p "Archon Project ID (UUID format): " project_id

    if [[ -n "$archon_url" ]]; then
        # Remove existing ARCHON_URL and add new one
        if grep -q "^ARCHON_URL=" "$ENV_FILE" 2>/dev/null; then
            sed -i.bak "/^ARCHON_URL=/d" "$ENV_FILE"
        fi
        echo "ARCHON_URL=$archon_url" >> "$ENV_FILE"
        success "Archon URL configured"
    fi

    if [[ -n "$project_id" ]]; then
        # Remove existing ARCHON_PROJECT_ID and add new one
        if grep -q "^ARCHON_PROJECT_ID=" "$ENV_FILE" 2>/dev/null; then
            sed -i.bak "/^ARCHON_PROJECT_ID=/d" "$ENV_FILE"
        fi
        echo "ARCHON_PROJECT_ID=$project_id" >> "$ENV_FILE"
        success "Archon Project ID configured"
    fi

    # Clean up backup files
    rm -f "$ENV_FILE.bak" 2>/dev/null || true

    # Export for current session
    if [[ -n "$archon_url" ]]; then
        export ARCHON_URL="$archon_url"
    fi
    if [[ -n "$project_id" ]]; then
        export ARCHON_PROJECT_ID="$project_id"
    fi
}

test_archon_connection() {
    info "Testing Archon connection..."

    if ! check_archon_config; then
        error "Archon not configured properly"
        return 1
    fi

    # Try to use the archon-status command to test connection
    if command -v claude &> /dev/null; then
        info "Testing with Claude Code..."
        # We can't easily test the MCP connection from bash, but we can validate the config
        success "Archon configuration appears valid"
        info "Run /archon-status in Claude Code to test the actual connection"
        return 0
    else
        # Just validate the format
        local project_id="${ARCHON_PROJECT_ID:-}"
        if [[ -f "$ENV_FILE" ]]; then
            project_id=$(grep "^ARCHON_PROJECT_ID=" "$ENV_FILE" | cut -d'=' -f2- | tr -d '"' | tr -d "'" || echo "")
        fi

        if [[ "$project_id" =~ ^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$ ]]; then
            success "Archon Project ID format is valid"
            return 0
        else
            error "Archon Project ID format is invalid (should be UUID)"
            return 1
        fi
    fi
}

show_status() {
    echo
    info "=== Archon Configuration Status ==="
    echo

    if check_archon_config; then
        local project_id="${ARCHON_PROJECT_ID:-}"
        local archon_url="${ARCHON_URL:-}"

        if [[ -f "$ENV_FILE" ]]; then
            project_id=$(grep "^ARCHON_PROJECT_ID=" "$ENV_FILE" | cut -d'=' -f2- | tr -d '"' | tr -d "'" || echo "")
            archon_url=$(grep "^ARCHON_URL=" "$ENV_FILE" | cut -d'=' -f2- | tr -d '"' | tr -d "'" || echo "")
        fi

        success "✅ Archon is configured"
        echo "  URL: $archon_url"
        echo "  Project ID: $project_id"
        echo
        echo "Available commands:"
        echo "  /archon-status     - Show project status and tasks"
        echo "  /archon-task-start - Start working on a task"
        echo "  /archon-complete   - Mark current work complete"
        echo "  /archon-research   - Search knowledge base"
    else
        warning "⚠️  Archon is not configured"
        echo "  Run: $0 --setup"
        echo "  Or manually add ARCHON_URL and ARCHON_PROJECT_ID to .env"
    fi
}

main() {
    local action="status"

    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --setup)
                action="setup"
                shift
                ;;
            --test)
                action="test"
                shift
                ;;
            --status)
                action="status"
                shift
                ;;
            -h|--help)
                echo "Usage: $0 [--setup|--test|--status|--help]"
                echo "  --setup  Configure Archon integration"
                echo "  --test   Test Archon connection"
                echo "  --status Show current configuration status"
                echo "  --help   Show this help message"
                exit 0
                ;;
            *)
                error "Unknown option: $1"
                exit 1
                ;;
        esac
    done

    check_env_file

    case $action in
        setup)
            show_setup_instructions
            configure_archon
            ;;
        test)
            test_archon_connection
            ;;
        status)
            show_status
            ;;
    esac
}

# Run main function
main "$@"