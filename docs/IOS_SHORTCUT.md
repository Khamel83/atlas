# iOS Shortcut: Save to Atlas Reader

This shortcut allows you to save articles from the iOS Share Sheet directly to Atlas Reader.

## Setup Instructions

### 1. Open Shortcuts App

Open the Shortcuts app on your iPhone or iPad.

### 2. Create New Shortcut

Tap the **+** button to create a new shortcut.

### 3. Configure Shortcut

Add the following actions in order:

#### Action 1: Receive Input
- **Type:** "Receive what's on screen" or "Get URLs from Input"
- **Input:** Safari Pages, URLs, Articles
- This captures the URL you're sharing

#### Action 2: Get Contents of URL (for text)
- **Type:** "Get Contents of URL"
- **URL:** Shortcut Input
- This extracts the URL from the share

#### Action 3: Get URLs from Input
- **Type:** "Get URLs from Input"
- **Input:** Shortcut Input
- Extracts just the URL

#### Action 4: POST to Atlas API
- **Type:** "Get Contents of URL"
- **URL:** `https://read.khamel.com/api/bookmarks`
- **Method:** POST
- **Headers:**
  - `Content-Type`: `application/json`
  - `X-Session-Id`: `YOUR_SESSION_ID` (get from login)
- **Request Body:** JSON
  ```json
  {
    "url": "[URL from step 3]",
    "createArchive": true
  }
  ```

#### Action 5: Show Notification
- **Type:** "Show Notification"
- **Title:** "Saved to Atlas"
- **Body:** "Article saved for later reading"

### 4. Name Your Shortcut

Name it "Save to Atlas" or "Read Later".

### 5. Enable Share Sheet

- Tap the settings icon (top right)
- Enable "Show in Share Sheet"
- Set "Share Sheet Types" to: URLs, Safari Web Pages, Articles

## Getting Your Session ID

Since iOS Shortcuts can't easily handle dynamic login, you'll need a long-lived session:

### Option A: Store Session in Shortcut
1. Visit `https://read.khamel.com` in Safari
2. Login with username: `atlas`, password: `atlas`
3. Open browser dev tools (or use Safari Web Inspector)
4. Find the session ID from the login response
5. Paste it into your shortcut's X-Session-Id header

### Option B: Use API Key (Future Enhancement)
A future update will add API key authentication so you don't need session management.

## Usage

1. Open an article in Safari (or any app)
2. Tap the **Share** button
3. Scroll down and tap **"Save to Atlas"**
4. Wait for the "Saved to Atlas" notification

## Troubleshooting

### "Invalid session" error
- Your session may have expired
- Re-login at `https://read.khamel.com` and update the session ID in your shortcut

### Article not appearing
- Check `https://read.khamel.com` to see if it's processing
- Some paywalled articles may fail to fetch

### Shortcut not appearing in Share Sheet
- Go to Shortcuts app → Your shortcut → Settings
- Ensure "Show in Share Sheet" is enabled
- Make sure Safari is selected as an input type

## Alternative: Bookmarklet

If the Shortcut doesn't work well, you can use a bookmarklet:

1. Create a new bookmark in Safari
2. Set the URL to:
```javascript
javascript:(function(){var url=encodeURIComponent(window.location.href);window.location='https://read.khamel.com/api/bookmarks?url='+url;})();
```
3. Name it "Save to Atlas"
4. Tap it on any page to save

Note: The bookmarklet requires you to be logged in already.
