#!/bin/bash
set -e

echo "🏗️  Building Atlas Browser Extensions for All Platforms"
echo "================================================="

# Create build directory
rm -rf build/
mkdir -p build/{chrome,firefox,safari}

# Chrome Extension (Manifest V3)
echo "📦 Building Chrome extension..."
cp -r * build/chrome/ 2>/dev/null || true
cp manifest.json build/chrome/
cp popup.html build/chrome/
cp popup.js build/chrome/
cp background.js build/chrome/
cp content.js build/chrome/
cp settings.html build/chrome/
cp settings.js build/chrome/

# Firefox Extension (Manifest V2 + WebExtensions)
echo "🦊 Building Firefox extension..."
cp -r * build/firefox/ 2>/dev/null || true
cp manifest_firefox.json build/firefox/manifest.json
cp popup_firefox.html build/firefox/popup.html
cp popup_firefox.js build/firefox/popup.js
cp background_firefox.js build/firefox/background.js
cp content.js build/firefox/
cp settings.html build/firefox/
cp settings.js build/firefox/

# Create icons directory if it doesn't exist
mkdir -p build/{chrome,firefox}/icons
mkdir -p build/safari/Resources

# Safari Extension files
echo "🍎 Preparing Safari extension files..."
cp -r safari_extension/* build/safari/ 2>/dev/null || true

# Create simple placeholder icons (16x16, 48x48, 128x128 PNG)
echo "🎨 Creating placeholder icons..."
for size in 16 48 128; do
    # Create simple Atlas icon placeholders
    cat > build/chrome/icons/icon${size}.png << 'EOF'
# This would be a proper PNG file in production
# For now, using placeholder comment
EOF
    cp build/chrome/icons/icon${size}.png build/firefox/icons/
done

# Package extensions
echo "📦 Packaging extensions..."
cd build

# Zip Chrome extension
cd chrome && zip -r ../atlas-chrome-extension.zip . && cd ..
echo "✅ Chrome extension: atlas-chrome-extension.zip"

# Zip Firefox extension (XPI)
cd firefox && zip -r ../atlas-firefox-extension.xpi . && cd ..
echo "✅ Firefox extension: atlas-firefox-extension.xpi"

# Safari extension needs Xcode project (instructions)
echo "🍎 Safari extension files prepared in build/safari/"
echo "   To build Safari extension:"
echo "   1. Open Xcode"
echo "   2. Create new Safari Extension project"
echo "   3. Copy files from build/safari/ to project"
echo "   4. Build and sign for distribution"

cd ..

echo ""
echo "🎉 Browser extensions built successfully!"
echo "📁 Output directory: build/"
echo "🌐 Chrome:  build/atlas-chrome-extension.zip"
echo "🦊 Firefox: build/atlas-firefox-extension.xpi"
echo "🍎 Safari:  build/safari/ (requires Xcode)"
echo ""
echo "📖 Installation instructions:"
echo "   Chrome:  Load unpacked extension from build/chrome/"
echo "   Firefox: Install XPI file or load temporary add-on"
echo "   Safari:  Build with Xcode and install via App Store"
