# Atlas Browser Extensions - Multi-Platform Support

Capture web content directly to your Atlas system from Chrome, Firefox, Chromium, and Safari.

## 🎯 Features

- **📝 One-click capture**: Save entire pages, article content, or selected text
- **🖱️ Context menu integration**: Right-click to save content
- **🧠 Smart article detection**: Automatically extracts main content from articles
- **⚙️ Configurable server**: Point to your Atlas instance
- **🌐 Cross-platform**: Chrome, Firefox, Chromium, and Safari support
- **🔒 Privacy-focused**: All data stays between your browser and your Atlas server

## 📦 Quick Installation

### Automated Build (Recommended)
```bash
./build_extensions.sh
```
This creates all platform versions in the `build/` directory.

### Manual Installation by Platform

#### 🟢 Chrome/Chromium
1. Open Chrome/Chromium → `chrome://extensions/`
2. Enable "Developer mode" (top right)
3. Click "Load unpacked" → Select `build/chrome/` folder
4. Extension appears in toolbar ✓

#### 🦊 Firefox
1. Open Firefox → `about:debugging`
2. Click "This Firefox" → "Load Temporary Add-on"
3. Select `build/firefox/manifest.json`
4. Extension appears in toolbar ✓

#### 🍎 Safari (macOS/iOS)
1. Safari extension files ready in `build/safari/`
2. Requires Xcode for building:
   - Open Xcode → New Safari Extension project
   - Copy files from `build/safari/` to project
   - Build & sign for distribution
3. Install via Mac App Store or Developer Certificate

## Configuration

1. Click the Atlas icon in your browser toolbar
2. Click the extension icon again to open the popup
3. Click the settings icon (gear) to configure your Atlas server URL
4. Enter your Atlas server address (default: `http://localhost:8000`)
5. Click "Save Settings"

## Usage

### Toolbar Button

Click the Atlas icon in your browser toolbar to open the popup menu with these options:
- **Save Current Page** - Saves the entire current page
- **Save Selection** - Saves any selected text
- **Save Article Content** - Saves just the main article content

### Context Menu

Right-click on any page, selection, or link to access Atlas capture options:
- **Save Page to Atlas** - Saves the current page
- **Save Selection to Atlas** - Saves the selected text
- **Save Link to Atlas** - Saves the clicked link

## Requirements

- Atlas running and accessible from your browser
- Web browser (Chrome, Chromium, or Firefox)
- Network connectivity to your Atlas server

## Troubleshooting

### Extension not appearing
- Ensure Developer Mode is enabled in Chrome extensions page
- Try refreshing the extensions page
- Check that the extension is enabled

### Content not saving
- Verify that your Atlas server is running
- Check that the server URL is correctly configured in extension settings
- Ensure your Atlas API is accessible from your browser (no CORS issues)
- Check the Atlas logs for error messages

### Article content extraction not working
- Some websites may have complex layouts that prevent accurate content detection
- Try using "Save Selection" instead and manually select the content
- The extension uses simple heuristics to detect content - it may not work perfectly on all sites

## Support

For issues with the browser extension:
- Check the Atlas documentation: `/docs/user-guides/`
- Visit GitHub Discussions: https://github.com/your-username/atlas/discussions
- Join the community Discord: https://discord.gg/atlas

For bug reports:
- File an issue on GitHub: https://github.com/your-username/atlas/issues
- Include screenshots and error messages when possible
- Describe steps to reproduce the issue