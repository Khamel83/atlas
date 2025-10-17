#!/bin/bash
# Quick slash commands setup for existing OOS projects
set -e

TARGET_DIR=${1:-$(pwd)}
OOS_SOURCE="/home/ubuntu/dev/oos"

echo "🚀 Quick slash commands setup for: $TARGET_DIR"

# Essential directories
mkdir -p "$TARGET_DIR/.claude/commands"
mkdir -p "$TARGET_DIR/bin"

# Copy the most important slash commands
echo "📋 Copying essential slash commands..."
cp "$OOS_SOURCE/.claude/commands/smart-commit.md" "$TARGET_DIR/.claude/commands/"
cp "$OOS_SOURCE/.claude/commands/optimize.md" "$TARGET_DIR/.claude/commands/"
cp "$OOS_SOURCE/.claude/commands/auto-fix.md" "$TARGET_DIR/.claude/commands/"
cp "$OOS_SOURCE/.claude/commands/help-me.md" "$TARGET_DIR/.claude/commands/"

# Copy essential scripts
echo "🔧 Copying executable scripts..."
cp "$OOS_SOURCE/bin/claude-smart-commit.sh" "$TARGET_DIR/bin/" 2>/dev/null || echo "smart-commit script not found"
cp "$OOS_SOURCE/bin/claude-optimize.sh" "$TARGET_DIR/bin/" 2>/dev/null || echo "optimize script not found"
cp "$OOS_SOURCE/bin/claude-auto-fix.sh" "$TARGET_DIR/bin/" 2>/dev/null || echo "auto-fix script not found"

# Make scripts executable
chmod +x "$TARGET_DIR/bin/"*.sh 2>/dev/null || true

# Create minimal test
cat > "$TARGET_DIR/test_basic_slash.py" << 'EOF'
#!/usr/bin/env python3
import os
from pathlib import Path

def test_slash_commands():
    print("🧪 Testing basic slash command setup...")

    # Check if .claude directory exists
    claude_dir = Path('.claude/commands')
    if claude_dir.exists():
        commands = list(claude_dir.glob('*.md'))
        print(f"✅ Found {len(commands)} slash commands:")
        for cmd in commands:
            print(f"   • /{cmd.stem}")
    else:
        print("❌ .claude/commands directory not found")
        return False

    # Check if bin scripts exist
    bin_dir = Path('bin')
    if bin_dir.exists():
        scripts = list(bin_dir.glob('claude-*.sh'))
        print(f"✅ Found {len(scripts)} executable scripts:")
        for script in scripts:
            print(f"   • {script.name}")
    else:
        print("❌ bin directory not found")
        return False

    print("\n🎉 Basic slash commands setup complete!")
    print("\nTo use in Claude Code:")
    print("  /smart-commit")
    print("  /optimize")
    print("  /auto-fix")
    print("  /help-me")

    return True

if __name__ == "__main__":
    test_slash_commands()
EOF

chmod +x "$TARGET_DIR/test_basic_slash.py"

echo "✅ Quick setup complete!"
echo ""
echo "🧪 Test it:"
echo "  cd $TARGET_DIR"
echo "  python3 test_basic_slash.py"
echo ""
echo "🎯 Essential slash commands now available:"
echo "  /smart-commit - Generate intelligent commit messages"
echo "  /optimize    - Optimize context for token efficiency"
echo "  /auto-fix    - Fix code consistency issues"
echo "  /help-me     - Smart context engineering help"