#!/bin/bash
# OOS Integration Script - Copy capabilities to parent project
# Solves the issue where updating OOS subdirectory doesn't make commands available

set -e

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OOS_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo -e "${BLUE}🔗 OOS Integration to Parent Project${NC}"
echo "====================================="

# Detect if we're in a subdirectory of a larger project
PARENT_DIR="$(dirname "$OOS_ROOT")"
PROJECT_NAME="$(basename "$OOS_ROOT")"

if [ "$PROJECT_NAME" = "oos" ] && [ -d "$PARENT_DIR/.git" ]; then
    echo -e "${YELLOW}📍 Detected OOS as subdirectory of larger project${NC}"
    echo "   OOS Location: $OOS_ROOT"
    echo "   Parent Project: $PARENT_DIR"

    # 1. Copy slash commands to parent .claude directory
    echo ""
    echo -e "${BLUE}📋 Step 1: Integrating Slash Commands${NC}"

    PARENT_CLAUDE_DIR="$PARENT_DIR/.claude"
    mkdir -p "$PARENT_CLAUDE_DIR/commands"

    # Merge OOS slash commands intelligently
    if [ -f "$OOS_ROOT/.claude/slash_commands.json" ]; then
        echo "  → Merging slash commands with existing ones"

        # Check if parent already has slash commands
        if [ -f "$PARENT_CLAUDE_DIR/slash_commands.json" ]; then
            # Add /consultant command if not already present
            if ! grep -q '"name": "consultant"' "$PARENT_CLAUDE_DIR/slash_commands.json"; then
                echo "  → Adding /consultant command"
                # Insert consultant command before the closing bracket
                sed -i '/^  ]$/i\    },\
    {\
      "name": "consultant",\
      "description": "Strategic AI consultant for project analysis and recommendations",\
      "script": "bin/claude-consultant.sh"' "$PARENT_CLAUDE_DIR/slash_commands.json"
            fi
        else
            # No existing file, copy OOS version
            cp "$OOS_ROOT/.claude/slash_commands.json" "$PARENT_CLAUDE_DIR/"
        fi

        # Create symlink for compatibility
        if [ ! -L "$PARENT_CLAUDE_DIR/slash-commands.json" ]; then
            ln -sf slash_commands.json "$PARENT_CLAUDE_DIR/slash-commands.json"
        fi
    fi

    # Copy command markdown files
    if [ -d "$OOS_ROOT/.claude/commands" ]; then
        echo "  → Copying command definitions"
        cp -r "$OOS_ROOT/.claude/commands/"* "$PARENT_CLAUDE_DIR/commands/" 2>/dev/null || true
    fi

    # 2. Copy executable scripts to parent bin
    echo ""
    echo -e "${BLUE}🔧 Step 2: Integrating Scripts${NC}"

    PARENT_BIN_DIR="$PARENT_DIR/bin"
    mkdir -p "$PARENT_BIN_DIR"

    # Copy OOS scripts
    if [ -d "$OOS_ROOT/bin" ]; then
        echo "  → Copying executable scripts"
        cp "$OOS_ROOT/bin/"*.sh "$PARENT_BIN_DIR/" 2>/dev/null || true
        chmod +x "$PARENT_BIN_DIR/"*.sh 2>/dev/null || true
    fi

    # 3. Create wrapper for OOS command system
    echo ""
    echo -e "${BLUE}⚡ Step 3: Creating OOS Command Bridge${NC}"

    cat > "$PARENT_BIN_DIR/oos-command.sh" << 'EOF'
#!/bin/bash
# Bridge to OOS command system from parent project
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PARENT_DIR="$(dirname "$SCRIPT_DIR")"
OOS_DIR="$PARENT_DIR/oos"

if [ ! -d "$OOS_DIR" ]; then
    echo "❌ OOS directory not found at $OOS_DIR"
    exit 1
fi

# Forward to OOS command system
cd "$OOS_DIR"
if [ -f "src/simple_command_handler.py" ]; then
    python3 -c "
import sys
sys.path.insert(0, 'src')
from simple_command_handler import SimpleCommandHandler
import asyncio

async def run_command():
    handler = SimpleCommandHandler()
    args = sys.argv[1:] if len(sys.argv) > 1 else ['help']
    command = args[0] if args else 'help'
    params = args[1:] if len(args) > 1 else []

    result = await handler.execute_command(command, ' '.join(params))
    print(result['output'])

asyncio.run(run_command())
" "$@"
else
    echo "❌ OOS command system not found"
    exit 1
fi
EOF
    chmod +x "$PARENT_BIN_DIR/oos-command.sh"

    # 4. Update parent project slash commands to include consultant
    echo ""
    echo -e "${BLUE}🎯 Step 4: Ensuring Consultant Command Available${NC}"

    # Create a direct consultant bridge if needed
    cat > "$PARENT_BIN_DIR/claude-consultant.sh" << 'EOF'
#!/bin/bash
# Direct bridge to OOS consultant command
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PARENT_DIR="$(dirname "$SCRIPT_DIR")"
"$PARENT_DIR/bin/oos-command.sh" consultant "$@"
EOF
    chmod +x "$PARENT_BIN_DIR/claude-consultant.sh"

    # 5. Create integration status file
    echo ""
    echo -e "${BLUE}📝 Step 5: Creating Integration Status${NC}"

    cat > "$PARENT_DIR/.oos_integration_status" << EOF
OOS Integration Status
=====================
Date: $(date)
OOS Version: $(cd "$OOS_ROOT" && git log --oneline -1 2>/dev/null || echo "Unknown")
Integration Components:
- ✅ Slash commands copied to .claude/
- ✅ Scripts copied to bin/
- ✅ OOS command bridge created
- ✅ Consultant command available

Usage:
- /consultant <query>    - Strategic AI consultant
- /archon-status         - Show Archon project status
- /archon-research       - Search Archon knowledge base
- oos-command.sh <cmd>   - Direct OOS command access

Next Steps:
1. Restart Claude Code to pick up new slash commands
2. Test: /consultant status
3. Verify: oos-command.sh help
EOF

    echo -e "${GREEN}✅ OOS Integration Complete!${NC}"
    echo ""
    echo -e "${YELLOW}📋 Next Steps:${NC}"
    echo "1. Restart Claude Code to pick up new slash commands"
    echo "2. Test the /consultant command"
    echo "3. Check integration status: cat .oos_integration_status"
    echo ""
    echo -e "${GREEN}🎉 The /consultant command should now be available!${NC}"

else
    echo -e "${YELLOW}ℹ️  OOS appears to be a standalone project, no parent integration needed${NC}"
    echo "   Current location: $OOS_ROOT"
fi