# Hyperduck → Safari → Atlas Solution

## 🎯 Understanding the Flow

**You're right - I had it backwards!**

```
Links → Hyperduck (Mac Mini) → Safari Opens URLs → Atlas Receives
```

## 🧪 Solution 1: Safari Bookmarklet

**Step 1**: Create this bookmarklet in Safari:
```javascript
javascript:(function(){
    var url = window.location.href;
    var atlasUrl = 'http://atlas.khamel.com:35555/ingest?url=' + encodeURIComponent(url);

    var iframe = document.createElement('iframe');
    iframe.style.display = 'none';
    iframe.src = atlasUrl;
    document.body.appendChild(iframe);

    setTimeout(function(){
        document.body.removeChild(iframe);
        alert('Sent to Atlas!');
    }, 2000);
})();
```

**Step 2**: When Hyperduck opens a URL in Safari, click the bookmarklet

**Step 3**: URL is sent to Atlas automatically

## 🍎 Solution 2: Safari Extension (Advanced)

Create a simple Safari extension that:
1. Detects when URLs are opened from Hyperduck
2. Automatically sends them to Atlas
3. Runs in background

## 🎮 Solution 3: AppleScript Automation

```applescript
-- This script could be triggered by Hyperduck
tell application "Safari"
    set currentURL to URL of front document
    set atlasURL to "http://atlas.khamel.com:35555/ingest?url=" & currentURL
    do shell script "curl '" & atlasURL & "'"
end tell
```

## 🧪 Downie Research Findings

Based on Downie documentation:
- Downie supports AppleScript automation
- Can be triggered via URL schemes
- Has command-line interface through macOS scripting
- Can extract video metadata

**Potential Downie Integration**:
1. Hyperduck opens URL in Safari
2. Safari page triggers Downie download
3. Downie metadata gets sent to Atlas
4. Both systems get the content

## 🎯 Recommended Approach

**Simple Path**: Safari Bookmarklet
- Hyperduck opens URL → Click bookmarklet → URL sent to Atlas

**Automated Path**: Safari Extension + Downie
- Hyperduck opens URL → Extension auto-sends to Atlas → Downie downloads video

**Bottom Line**: The key is having Safari automatically send URLs to Atlas when they're opened from Hyperduck.