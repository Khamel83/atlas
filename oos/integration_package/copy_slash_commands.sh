#!/bin/bash
# Copy OOS slash commands to existing project
set -e

# Colors
BLUE='\033[0;34m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

TARGET_DIR=${1:-$(pwd)}
OOS_SOURCE="/home/ubuntu/dev/oos"

if [[ ! -d "$TARGET_DIR" ]]; then
    echo -e "${RED}Target directory doesn't exist: $TARGET_DIR${NC}"
    exit 1
fi

echo -e "${BLUE}🚀 Installing OOS slash commands to: $TARGET_DIR${NC}"

# Create necessary directories
echo -e "${YELLOW}Creating directory structure...${NC}"
mkdir -p "$TARGET_DIR/.claude/commands"
mkdir -p "$TARGET_DIR/.claude/constraints"
mkdir -p "$TARGET_DIR/bin"
mkdir -p "$TARGET_DIR/src"

# Copy slash command definitions
echo -e "${YELLOW}Copying slash command definitions...${NC}"
cp -r "$OOS_SOURCE/.claude/commands/"* "$TARGET_DIR/.claude/commands/"
cp -r "$OOS_SOURCE/.claude/constraints/"* "$TARGET_DIR/.claude/constraints/"

# Copy bin scripts
echo -e "${YELLOW}Copying executable scripts...${NC}"
cp "$OOS_SOURCE/bin/"claude-*.sh "$TARGET_DIR/bin/" 2>/dev/null || echo "Some scripts not found - that's OK"

# Make scripts executable
chmod +x "$TARGET_DIR/bin/"*.sh 2>/dev/null || true

# Copy required Python modules
echo -e "${YELLOW}Copying Python modules...${NC}"
cp "$OOS_SOURCE/src/simple_command_handler.py" "$TARGET_DIR/src/"
cp "$OOS_SOURCE/src/capability_router.py" "$TARGET_DIR/src/"
cp "$OOS_SOURCE/src/knowledge_resolver.py" "$TARGET_DIR/src/"
cp "$OOS_SOURCE/src/renderers.py" "$TARGET_DIR/src/"
cp "$OOS_SOURCE/src/clarification_workflow.py" "$TARGET_DIR/src/"
cp "$OOS_SOURCE/src/orchestrator.py" "$TARGET_DIR/src/"
cp "$OOS_SOURCE/src/auto_documentation.py" "$TARGET_DIR/src/"
cp "$OOS_SOURCE/src/token_optimization.py" "$TARGET_DIR/src/"

# Copy command modules
mkdir -p "$TARGET_DIR/src/commands"
cp -r "$OOS_SOURCE/src/commands/"* "$TARGET_DIR/src/commands/"

# Copy config files
echo -e "${YELLOW}Copying configuration...${NC}"
mkdir -p "$TARGET_DIR/config"
cp "$OOS_SOURCE/config/"*.yaml "$TARGET_DIR/config/" 2>/dev/null || true

# Copy search functionality (if not already present)
if [[ ! -f "$TARGET_DIR/src/free_search_alternatives.py" ]]; then
    echo -e "${YELLOW}Adding search functionality...${NC}"
    cp "$OOS_SOURCE/src/free_search_alternatives.py" "$TARGET_DIR/src/"
    cp "$OOS_SOURCE/src/perplexity_usage_manager.py" "$TARGET_DIR/src/"
    mkdir -p "$TARGET_DIR/data"
    cp -r "$OOS_SOURCE/data/"* "$TARGET_DIR/data/" 2>/dev/null || true
fi

# Create integration test script
cat > "$TARGET_DIR/test_slash_commands.py" << 'EOF'
#!/usr/bin/env python3
"""Test slash commands integration"""
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

async def test_slash_commands():
    try:
        from simple_command_handler import SimpleCommandHandler
        handler = SimpleCommandHandler()

        print("✅ Slash command handler imported successfully")

        # Test capabilities command
        result = await handler.execute_command("capabilities", ["test query"])
        print("✅ /capabilities command working")

        # Test actions command
        result = await handler.execute_command("actions", [])
        print("✅ /actions command working")

        print("\n🎉 All slash commands integrated successfully!")

    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("Some dependencies may be missing")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_slash_commands())
EOF

chmod +x "$TARGET_DIR/test_slash_commands.py"

# Create usage guide
cat > "$TARGET_DIR/SLASH_COMMANDS_USAGE.md" << 'EOF'
# 🚀 OOS Slash Commands - Usage Guide

Your project now has all OOS slash commands integrated!

## ✅ Available Slash Commands

- `/optimize` - Optimize current context for token efficiency
- `/auto-fix` - Automatically fix code consistency issues
- `/smart-commit` - Generate intelligent commit message for current changes
- `/help-me` - Smart context engineering help
- `/clarify` - Start clarification workflow to refine vague requests
- `/doc-check` - Check documentation completeness and code consistency
- `/workflow` - Start structured workflow for complex tasks
- `/meta-ai` - Generate prompt for external AI assistance
- `/context-stats` - Show current context size and optimization stats
- `/brain-dump` - Smart processing of rambling input

## 🧪 Test Integration

```bash
# Test that slash commands work:
python3 test_slash_commands.py

# Test a specific command:
./bin/claude-smart-commit.sh

# Test capability system:
python3 -c "from src.simple_command_handler import SimpleCommandHandler; print('✅ Working')"
```

## 🎯 Usage Examples

```bash
# In Claude Code, you can now use:
/smart-commit
/optimize
/help-me "how to deploy this project"
/clarify "I want to add authentication"
```

## 🔧 Integration with Your Code

```python
# In your Python code:
from src.simple_command_handler import SimpleCommandHandler

handler = SimpleCommandHandler()
result = await handler.execute_command("optimize", [])
```

## 📁 What Was Added

```
.claude/commands/       # Slash command definitions
.claude/constraints/    # Command constraints
bin/                   # Executable scripts
src/                   # Python modules
config/                # Configuration files
data/                  # Search data (if applicable)
```

## 🎉 You're Ready!

All slash commands from the main OOS development environment are now available in your project!
EOF

echo -e "${GREEN}✅ OOS slash commands installed successfully!${NC}"
echo ""
echo -e "${BLUE}📋 What was installed:${NC}"
echo "  • All slash command definitions (.claude/commands/)"
echo "  • Executable scripts (bin/)"
echo "  • Python modules (src/)"
echo "  • Configuration files (config/)"
echo "  • Integration test script"
echo ""
echo -e "${BLUE}🧪 Test the integration:${NC}"
echo "  cd $TARGET_DIR"
echo "  python3 test_slash_commands.py"
echo ""
echo -e "${BLUE}📖 Read the usage guide:${NC}"
echo "  cat $TARGET_DIR/SLASH_COMMANDS_USAGE.md"