# Atlas Bookmarklet - atlas.khamel.com

## 📱 Mobile Installation

### iOS Safari:
1. Bookmark this page
2. Edit the bookmark
3. Replace the URL with the JavaScript code below
4. Save to home screen for easy access

### Desktop Chrome/Safari:
1. Bookmark this page
2. Edit the bookmark
3. Replace URL with JavaScript code
4. Add to bookmarks bar

## 🔗 Atlas Link Capture Bookmarklet

**Standard Version:**
```javascript
javascript:void(function(){window.open('https://atlas.khamel.com/add?content='+encodeURIComponent(location.href)+'&title='+encodeURIComponent(document.title)+'&source=Browser+Bookmarklet');})();
```

**Background Tab Version (doesn't navigate away):**
```javascript
javascript:void(function(){fetch('https://atlas.khamel.com/api/content',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({url:location.href,title:document.title,content_type:'article'})}).then(r=>r.json()).then(d=>alert('✅ '+d.message)).catch(e=>alert('❌ Error: '+e.message));})();
```

## 📱 iOS Share Sheet Alternative

### Method 1: Safari Share → Copy Link → Atlas
1. In Safari, tap share button
2. "Copy Link"
3. Go to `https://atlas.khamel.com/add`
4. Paste link

### Method 2: Create iOS Shortcut
1. Open Shortcuts app
2. Create new shortcut
3. Add "Get URL from Input"
4. Add "Open URL" with: `https://atlas.khamel.com/add?content=[URL]&title=[title]`
5. Add to Share Sheet

## 🚀 Usage

1. Navigate to any webpage
2. Click the bookmarklet
3. Link automatically opens in Atlas with title pre-filled
4. Click "Add Content" to save

## ✅ Tested and Working

- **Domain**: atlas.khamel.com
- **Add endpoint**: ✅ Working
- **API endpoint**: ✅ Working
- **Mobile responsive**: ✅ Working