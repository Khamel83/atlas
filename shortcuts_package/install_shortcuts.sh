#!/bin/bash

# Atlas Apple Shortcuts Installer
# This script opens all shortcuts for easy installation

echo "🍎 Atlas Apple Shortcuts Installer"
echo "=================================="
echo ""

# Check if we're on macOS
if [[ "$OSTYPE" == "darwin"* ]]; then
    echo "✅ macOS detected - shortcuts can be installed"
    echo ""

    # Count shortcuts
    SHORTCUT_COUNT=$(ls shortcuts/*.shortcut 2>/dev/null | wc -l)

    if [ "$SHORTCUT_COUNT" -eq 0 ]; then
        echo "❌ No shortcuts found in shortcuts/ directory"
        exit 1
    fi

    echo "📱 Found $SHORTCUT_COUNT shortcuts to install:"
    ls shortcuts/*.shortcut | sed 's/shortcuts\///g' | sed 's/\.shortcut//g' | sed 's/^/  - /'
    echo ""

    echo "🔄 Opening shortcuts for installation..."
    echo "   (Tap 'Add Shortcut' for each one)"
    echo ""

    # Open each shortcut file
    for shortcut in shortcuts/*.shortcut; do
        echo "Opening $(basename "$shortcut" .shortcut)..."
        open "$shortcut"
        sleep 2  # Give time for each to open
    done

    echo ""
    echo "✅ All shortcuts opened!"
    echo "📋 Next steps:"
    echo "   1. Tap 'Add Shortcut' for each opened shortcut"
    echo "   2. Grant permissions when asked"
    echo "   3. Test with: 'Hey Siri, Capture Thought'"
    echo ""
    echo "📖 See INSTALLATION_GUIDE.md for detailed setup instructions"

else
    echo "⚠️  This installer works on macOS only"
    echo "📱 For iOS: Download .shortcut files and open them directly"
    echo "📖 See INSTALLATION_GUIDE.md for manual installation steps"
fi