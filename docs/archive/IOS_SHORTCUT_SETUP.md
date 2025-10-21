# iOS Shortcut Setup for Atlas Gmail Integration

Setup iOS shortcuts to automatically send content to your Atlas knowledge base via Gmail.

## 🍎 Atlas Bookmark Shortcut

### Method 1: Simple Share Shortcut

1. **Open Shortcuts App**
2. **Tap "+" to create new shortcut**
3. **Add Actions:**

   **Share Intent** (Automatically added)
   ↓
   **Send Email**
   - Recipients: `khamel83+atlas@gmail.com`
   - Subject: `Atlas Bookmark: {Input from Share}`
   - Body: `{Input from Share}`

4. **Name**: "Atlas Bookmark"
5. **Save**

### Method 2: Advanced Shortcut with Options

1. **Create new shortcut**
2. **Add Actions:**

   **Share Intent** (Automatically added)
   ↓
   **Ask for Input** (Type: Text, Prompt: "Add any notes:")
   ↓
   **Text**
   ```
   Atlas Bookmark: {ShortcutInput}

   Notes: {ProvidedInput}

   Sent from iOS Shortcut
   ```
   ↓
   **Send Email**
   - Recipients: `khamel83+atlas@gmail.com`
   - Subject: `Atlas Bookmark`
   - Body: {Text output}

3. **Name**: "Atlas with Notes"
4. **Save**

## 📰 Newsletter Bookmark Shortcut

For newsletters and articles you want to save with "Newsletter" label:

1. **Create new shortcut**
2. **Add Actions:**

   **Share Intent** (Automatically added)
   ↓
   **Send Email**
   - Recipients: `khamel83+atlas@gmail.com`
   - Subject: `Newsletter: {Title from Share}`
   - Body: `{URL from Share}`

3. **Name**: "Save Newsletter"
4. **Save**

## 🔧 Gmail Filter Setup

### Create Filters in Gmail Web:

**Filter 1: Atlas Shortcuts**
- From: (your iOS device email)
- To: `khamel83+atlas@gmail.com`
- Subject contains: "Atlas Bookmark"
- **Action**: Apply label "Atlas", Mark as read, Skip inbox

**Filter 2: Newsletters**
- From: (newsletter sources)
- To: `khamel83+atlas@gmail.com`
- Subject contains: "Newsletter"
- **Action**: Apply label "Newsletter"

## 🚀 Usage Examples

### Saving a URL:
1. In Safari, find article to save
2. Tap Share → "Atlas Bookmark"
3. Email automatically sent
4. Content appears in Atlas within 5 seconds

### Saving with Notes:
1. Find content to save
2. Tap Share → "Atlas with Notes"
3. Add your thoughts/notes
4. Save to Atlas with context

### Saving Newsletter:
1. In email app or newsletter
2. Tap Share → "Save Newsletter"
3. Automatically labeled as newsletter
4. Processed by Atlas

## 📱 Shortcut Sharing

### Export Shortcuts:
1. In Shortcuts app, find your shortcut
2. Tap "..." (more options)
3. Tap "Share"
4. Send to yourself or others

### Import Shortcuts:
1. Receive shortcut link
2. Tap to open in Shortcuts app
3. Tap "Add Shortcut"

## 🔍 Testing Your Setup

### Test Basic Functionality:
1. Create a simple text note
2. Share using "Atlas Bookmark"
3. Check Gmail: email should arrive with "Atlas" label
4. Check Atlas: content should appear within 5 seconds

### Test URL Processing:
1. Share a webpage using shortcut
2. Verify URL is extracted and stored correctly
3. Check Atlas for new content with proper URL

### Test Attachment Support:
1. Email a PDF/document to `khamel83+atlas@gmail.com`
2. Check Atlas for attachment download
3. Verify document is stored in `data/documents/`

## ⚡ Pro Tips

### Multiple Shortcuts:
- **"Quick Atlas"**: Basic URL saving
- **"Atlas with Thoughts"**: Add your analysis
- **"Research Atlas"**: Save with research notes
- **"Newsletter Atlas"**: Categorize as newsletter

### Keyboard Integration:
1. Settings → General → Keyboard → Text Replacement
2. Add shortcut: `atlas` → `khamel83+atlas@gmail.com`
3. Use in any app for quick email addressing

### Siri Integration:
1. Add to shortcuts: "Hey Siri, Atlas bookmark this"
2. Voice activate your bookmarking workflow

### Widget Support:
1. Add shortcuts widget to home screen
2. One-tap access to Atlas shortcuts

## 🐛 Troubleshooting

### Shortcut Not Working:
- Check recipient email address
- Verify internet connection
- Ensure Gmail account is added to iOS Mail

### Content Not Appearing in Atlas:
- Check Gmail filters are applied correctly
- Verify Atlas Gmail integration is running
- Check Atlas logs for processing errors

### Labels Not Applied:
- Manually create "Atlas" and "Newsletter" labels in Gmail
- Test filter conditions with test emails
- Check filter precedence in Gmail settings

## 📊 Monitoring Your Workflow

### Track Incoming Content:
- Visit `http://localhost:7444/gmail/stats`
- See real-time statistics for Gmail processing
- Monitor both Atlas and Newsletter content

### Atlas Search:
- Search `content_type:gmail_atlas` for shortcut content
- Search `content_type:gmail_newsletter` for newsletters
- Use Atlas web interface for browsing

## 🎯 Best Practices

### Email Subject Lines:
- Use consistent prefixes: "Atlas:", "Newsletter:"
- Include source information for context
- Keep subjects descriptive but concise

### Content Organization:
- Use different shortcuts for different content types
- Add tags and notes for better searchability
- Regular review and cleanup of imported content

### Privacy Considerations:
- Be mindful of sensitive content shared via email
- Use secure connections for Atlas API
- Regular backup of Atlas database

## 🔗 Quick Reference

### Email Addresses:
- **General Atlas**: `khamel83+atlas@gmail.com` → "Atlas" label
- **Newsletters**: Auto-labeled based on content/filters

### Atlas Endpoints:
- **Status**: `GET /gmail/auth/status`
- **Stats**: `GET /gmail/stats`
- **API Docs**: `http://localhost:7444/docs`

### Content Types:
- `gmail_atlas`: From iOS shortcuts and manual emails
- `gmail_newsletter`: From newsletter subscriptions

---

Your iOS shortcuts are now integrated with Atlas for seamless knowledge building!