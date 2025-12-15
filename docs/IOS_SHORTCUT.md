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

---

## iOS Shortcut: Save Selection as Note

This shortcut captures highlighted text from a webpage and saves it as a note in Atlas.

### What It Does

1. Captures the selected text from a webpage
2. Gets the page URL and title
3. Creates a note in Atlas with the selection
4. Optionally queues the URL for full article fetch

### Setup Instructions

#### 1. Create New Shortcut

Open Shortcuts app and tap **+** to create a new shortcut.

#### 2. Add Actions

##### Action 1: Get Safari Selection
- **Type:** "Get Details of Safari Web Page"
- **Get:** "Page Selection"
- **From:** Shortcut Input
- This captures the highlighted text

##### Action 2: Set Variable for Selection
- **Type:** "Set Variable"
- **Name:** "SelectedText"
- **Input:** Previous action output

##### Action 3: Get Page URL
- **Type:** "Get Details of Safari Web Page"
- **Get:** "URL"
- **From:** Shortcut Input

##### Action 4: Set Variable for URL
- **Type:** "Set Variable"
- **Name:** "PageURL"
- **Input:** Previous action output

##### Action 5: Get Page Title
- **Type:** "Get Details of Safari Web Page"
- **Get:** "Name"
- **From:** Shortcut Input

##### Action 6: Set Variable for Title
- **Type:** "Set Variable"
- **Name:** "PageTitle"
- **Input:** Previous action output

##### Action 7: POST to Atlas Notes API
- **Type:** "Get Contents of URL"
- **URL:** `https://YOUR-ATLAS-HOST:7444/api/notes/url`
- **Method:** POST
- **Headers:**
  - `Content-Type`: `application/json`
- **Request Body:** JSON
  ```json
  {
    "url": "[PageURL variable]",
    "selection": "[SelectedText variable]",
    "title": "[PageTitle variable]",
    "fetch_full_article": true
  }
  ```

##### Action 8: Show Notification
- **Type:** "Show Notification"
- **Title:** "Saved to Atlas Notes"
- **Body:** "Selection saved and article queued"

#### 3. Name and Configure

- Name it "Save to Atlas Notes"
- Enable "Show in Share Sheet"
- Set types to: Safari Web Pages

### Usage

1. Select/highlight text on a webpage in Safari
2. Tap **Share** button
3. Tap **"Save to Atlas Notes"**
4. Done! The selection is saved and the full article is queued

### API Endpoint Reference

**POST `/api/notes/url`**

```json
{
  "url": "https://example.com/article",
  "selection": "The highlighted text from the page",
  "title": "Optional custom title",
  "fetch_full_article": true
}
```

Response:
```json
{
  "status": "created",
  "content_id": "abc123def456",
  "title": "Your Note Title",
  "article_queued": true
}
```

### Alternative: Direct Text Notes

For notes without a source URL:

**POST `/api/notes/`**

```json
{
  "text": "Your note text here",
  "title": "Optional title",
  "source_url": "optional URL"
}
```
