#!/bin/bash

# Build script for Atlas Browser Extension
# Creates a zip package for distribution

set -euo pipefail

echo "📦 Building Atlas Browser Extension..."

# Create dist directory
mkdir -p dist

# Create zip package
cd browser_extension
zip -r ../dist/atlas_browser_extension.zip . -x "*.DS_Store" "Thumbs.db"

echo "✅ Extension packaged successfully!"
echo "📁 Package location: dist/atlas_browser_extension.zip"