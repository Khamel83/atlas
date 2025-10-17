#!/bin/bash
set -e

echo "🍎 Atlas Apple Shortcuts Installer"
echo "=================================="

# Check if running on macOS
if [[ "$OSTYPE" != "darwin"* ]]; then
    echo "❌ This installer is for macOS only"
    exit 1
fi

# Check if Shortcuts app exists
if ! command -v shortcuts &> /dev/null; then
    echo "❌ Shortcuts app not found. Please install it from the App Store."
    exit 1
fi

# Create shortcuts directory if it doesn't exist
SHORTCUTS_DIR="$HOME/Downloads/Atlas_Shortcuts"
mkdir -p "$SHORTCUTS_DIR"

echo "📁 Copying shortcuts to $SHORTCUTS_DIR..."
cp shortcuts/*.shortcut "$SHORTCUTS_DIR/"

echo "✅ Shortcuts copied successfully!"
echo ""
echo "Next steps:"
echo "1. Open Finder and navigate to $SHORTCUTS_DIR"
echo "2. Double-click each .shortcut file to import"
echo "3. Grant permissions when prompted"
echo "4. Test with: 'Hey Siri, save to Atlas'"
echo ""
echo "📖 For detailed setup instructions, see:"
echo "   docs/user-guides/MAC_USER_GUIDE.md"

# Optionally open the directory
read -p "Open shortcuts folder now? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    open "$SHORTCUTS_DIR"
fi

echo "🎉 Installation complete!"