#!/bin/bash

# Install Atlas macOS Service for right-click file context menu

echo "🍎 Installing Atlas macOS Service..."

# Copy workflow to user's Services directory
SERVICES_DIR="$HOME/Library/Services"
WORKFLOW_PATH="$SERVICES_DIR/Send to Atlas.workflow"

# Create Services directory if it doesn't exist
mkdir -p "$SERVICES_DIR"

# Copy the workflow
echo "📁 Copying workflow to $SERVICES_DIR"
cp -R "Send to Atlas.workflow" "$SERVICES_DIR/"

# Set proper permissions
chmod -R 755 "$WORKFLOW_PATH"

# Refresh Services menu
echo "🔄 Refreshing Services menu..."
/System/Library/CoreServices/pbs -flush

echo "✅ Installation complete!"
echo ""
echo "🎯 How to use:"
echo "1. Right-click any file in Finder"
echo "2. Go to Services → Send to Atlas"
echo "3. File will be saved to your Atlas database"
echo ""
echo "📄 Supported files:"
echo "- Text files (.txt, .md, .py, .js, .html)"
echo "- PDF documents"
echo "- Any other file (filename saved with basic metadata)"
echo ""
echo "⚡ Make sure Atlas is running on port 7444"
echo "   python atlas_service_manager.py start"