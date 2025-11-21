# Atlas Browser Bookmarklet

Save any web page to Atlas with one click.

## Quick Setup

1. **Open the installer:** `open browser_bookmarklet/install_bookmarklet.html`
2. **Drag the blue button** to your bookmarks bar
3. **Make sure Atlas is running:** `python atlas_service_manager.py start`
4. **Click the bookmark** on any page you want to save

## Features

- ✅ **One-click saving** from any website
- ✅ **Smart port detection** (prompts for Atlas URL)
- ✅ **Content extraction** (title, URL, text content)
- ✅ **Success confirmation** shows when saved
- ✅ **Error handling** for failed saves

## Usage

1. Navigate to any article, blog post, or web page
2. Click the "📖 Save to Atlas" bookmark
3. Confirm or change the Atlas URL (default: https://atlas.khamel.com)
4. Get instant confirmation when saved

## Technical Details

The bookmarklet:
- Extracts `document.title`, `window.location.href`, and `document.body.innerText`
- Limits content to first 10,000 characters (prevents browser hanging)
- Uses XMLHttpRequest to POST to `/api/content/save`
- Shows user-friendly success/error messages
- Asks for Atlas URL each time (allows port flexibility)

Perfect complement to Atlas voice capture and file dropping!