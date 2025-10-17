#!/bin/bash
# One-command OOS update script
# Usage: curl -sSL https://raw.githubusercontent.com/your-repo/oos/main/update-oos.sh | bash
# Or: ./update-oos.sh

set -e

echo "🚀 OOS One-Command Update System"
echo "================================="
echo ""

# Check if we're in a valid project directory
if [ ! -f "package.json" ] && [ ! -f "pyproject.toml" ] && [ ! -f "requirements.txt" ] && [ ! -d "src" ]; then
    echo "❌ This doesn't look like a project directory."
    echo "   Expected to find: package.json, pyproject.toml, requirements.txt, or src/ directory"
    echo ""
    echo "💡 Run this command from your project root directory."
    exit 1
fi

echo "✅ Project directory detected"
echo "📁 Current directory: $(pwd)"
echo ""

# Download the smart updater if it doesn't exist
if [ ! -f "update_oos.py" ]; then
    echo "📥 Downloading OOS smart updater..."

    # Try to download from your OOS repo (replace with actual URL)
    if command -v curl >/dev/null 2>&1; then
        curl -sSL -o update_oos.py "https://raw.githubusercontent.com/your-oos-repo/main/update_oos.py" || {
            echo "❌ Failed to download updater from remote"
            echo "💡 Copying from local OOS installation..."

            # Try to find local OOS installation
            if [ -f "../Speech/update_oos.py" ]; then
                cp "../Speech/update_oos.py" .
            elif [ -f "../../Speech/update_oos.py" ]; then
                cp "../../Speech/update_oos.py" .
            else
                echo "❌ Could not find OOS updater"
                echo "💡 Please ensure OOS source is available"
                exit 1
            fi
        }
    else
        echo "❌ curl not found. Please install curl or download update_oos.py manually"
        exit 1
    fi

    echo "✅ Updater downloaded"
else
    echo "✅ Using existing updater"
fi

echo ""

# Make sure Python 3 is available
if ! command -v python3 >/dev/null 2>&1; then
    echo "❌ Python 3 is required but not found"
    echo "💡 Please install Python 3"
    exit 1
fi

echo "🔧 Running smart OOS update..."
echo ""

# Run the smart updater
python3 update_oos.py --project .

echo ""
echo "🎉 Update complete!"
echo ""
echo "🔄 **Next steps:**"
echo "1. Restart Claude Code"
echo "2. Try: /consultant \"How can we improve this project?\""
echo "3. Try: /consultant status"
echo ""
echo "✨ Your project now has strategic intelligence!"