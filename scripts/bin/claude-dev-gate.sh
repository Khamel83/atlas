#!/usr/bin/env bash
set -euo pipefail

# Claude Code Development Gate Command
# Usage: /dev-gate [check|pass|status]

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Colors for Claude Code output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m'

ACTION="${1:-check}"

case "$ACTION" in
    "check"|"")
        echo -e "${BLUE}🚪 Development Gate Status Check${NC}"
        echo "=================================="

        if [[ -f "$PROJECT_ROOT/.dev-gate-passed" ]]; then
            gate_time=$(stat -c %Y "$PROJECT_ROOT/.dev-gate-passed" 2>/dev/null || echo "0")
            current_time=$(date +%s)
            age=$((current_time - gate_time))

            if [[ $age -lt 3600 ]]; then
                echo -e "${GREEN}✅ Development environment is ready${NC}"
                echo "Gate passed $(( (3600 - age) / 60 )) minutes ago"
                echo "Valid for another $(( (3600 - age) / 60 )) minutes"
                exit 0
            else
                echo -e "${YELLOW}⚠️  Development gate has expired${NC}"
                echo "Last validated $(( age / 60 )) minutes ago"
                echo "Run: /dev-gate pass"
                exit 1
            fi
        else
            echo -e "${RED}❌ Development gate not passed${NC}"
            echo "Run: /dev-gate pass"
            exit 1
        fi
        ;;

    "pass")
        echo -e "${BLUE}🚪 Running Development Gate...${NC}"

        # Run the actual gate validation
        if "$PROJECT_ROOT/bin/dev-gate.sh"; then
            echo -e "${GREEN}✅ Development environment ready!${NC}"
            echo "You can now use development commands in Claude Code"
            exit 0
        else
            echo -e "${RED}❌ Development gate failed${NC}"
            echo "Fix the issues above before continuing development"
            exit 1
        fi
        ;;

    "status")
        # Silent status check for other scripts
        if [[ -f "$PROJECT_ROOT/.dev-gate-passed" ]]; then
            gate_time=$(stat -c %Y "$PROJECT_ROOT/.dev-gate-passed" 2>/dev/null || echo "0")
            current_time=$(date +%s)
            age=$((current_time - gate_time))

            if [[ $age -lt 3600 ]]; then
                exit 0  # Gate is valid
            fi
        fi
        exit 1  # Gate not valid
        ;;

    "bypass")
        echo -e "${YELLOW}⚠️  Emergency bypass activated${NC}"
        touch "$PROJECT_ROOT/.dev-gate-passed"
        echo "$(date)" > "$PROJECT_ROOT/.dev-gate-passed"
        echo "Development commands temporarily enabled"
        exit 0
        ;;

    *)
        echo "Usage: /dev-gate [check|pass|status|bypass]"
        echo ""
        echo "Commands:"
        echo "  check  - Check current gate status (default)"
        echo "  pass   - Run development environment validation"
        echo "  status - Silent status check (for automation)"
        echo "  bypass - Emergency bypass (use sparingly)"
        exit 1
        ;;
esac