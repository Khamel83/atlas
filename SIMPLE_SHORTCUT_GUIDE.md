# Simple iOS Shortcut for Atlas

Quick setup for iOS shortcut to send content to `khamel83+atlas@gmail.com`

## 🎯 Your Workflow Goal

**Click shortcut → Email to khamel83+atlas@gmail.com → Gmail applies "Atlas" label → Atlas processes automatically**

## 📱 Create the Shortcut (30 seconds)

### Method 1: Universal "Atlas Bookmark" (Recommended)

1. **Open Shortcuts app**
2. **Tap "+"** to create new shortcut
3. **Tap "Share Sheet"** at top (make sure it's selected)
4. **Accept Content Types**: Text, URLs, Images
5. **Add "Send Email" action**:
   - Recipients: `khamel83+atlas@gmail.com`
   - Subject: `Atlas: {ShortcutInput}`
   - Body: `{ShortcutInput}`
6. **Tap "Next"**
7. **Name**: "Atlas Bookmark"
8. **Tap "Done"**

### Method 2: Quick Text Version

1. **Create new shortcut**
2. **Add "Ask for Input"** → Text → Prompt: "What to send to Atlas?"
3. **Add "Send Email"**:
   - To: `khamel83+atlas@gmail.com`
   - Subject: `Atlas Bookmark`
   - Body: Input from previous step
4. **Name**: "Quick Atlas"

## 📧 Gmail Filter Setup (2 minutes)

1. **Open Gmail on desktop**
2. **Settings** → **See all settings**
3. **Filters and Blocked Addresses** → **Create new filter**
4. **Fill in**:
   - **To**: `khamel83+atlas@gmail.com`
5. **Create filter**
6. **Apply label**: "Atlas" (create if needed)
7. **Check**: "Mark as read" (optional)
8. **Save**

## ✅ Test It

1. **Test with a URL**:
   - In Safari, go to any webpage
   - Tap Share → "Atlas Bookmark"
   - Check email arrives with "Atlas" label

2. **Test with text**:
   - In Notes app, write something
   - Share → "Atlas Bookmark"
   - Check email arrives

3. **Test with attachments**:
   - In Photos, select image
   - Share → "Atlas Bookmark"
   - Check email includes attachment

## 🎛️ Advanced Options

### Better Subject Lines
Instead of `{ShortcutInput}`, use:
- `Atlas: {URL Name from Input}` (for URLs)
- `Atlas: {First 50 characters of text}` (for text)

### Multiple URLs
If you share text with multiple URLs, they'll all be extracted and stored as separate Atlas content items.

### Attachments
- **Photos**: Sent as email attachments
- **Documents**: Sent as email attachments
- **Size limit**: Up to Gmail's attachment limit (~25MB per email)

## 📊 Expected Behavior

### What Atlas Will Do:
- Extract ALL URLs from your email
- Download ALL attachments
- Create content records in Atlas database
- Mark with `content_type: gmail_atlas`
- Store sender info and timestamp

### Processing Time:
- Email arrives instantly
- Gmail applies "Atlas" label automatically
- Atlas processes within 5 seconds
- Content appears in Atlas database

## 🐛 Quick Troubleshooting

### Shortcut not working:
- Check recipient email: `khamel83+atlas@gmail.com`
- Test with simple text first
- Make sure internet connection is active

### Email not arriving:
- Check if you need to verify khamel83+atlas@gmail.com as your email
- Check Gmail's spam folder
- Verify you can send to that email address

### "Atlas" label not applied:
- Manually create "Atlas" label in Gmail first
- Check filter settings
- Test filter with test email

### Content not in Atlas:
- Check Atlas server is running
- Check Gmail processing logs
- Verify Gmail watch is active

## 🎉 Success Indicators

✅ **Shortcut appears** in Share Sheet
✅ **Email arrives** at khamel83+atlas@gmail.com
✅ **"Atlas" label applied** automatically
✅ **Content appears** in Atlas database within 5 seconds
✅ **Attachments downloaded** and stored

## 📱 Quick Access

### Add to Home Screen:
1. Find your shortcut in Shortcuts app
2. Tap "..." (three dots)
3. Select "Add to Home Screen"
4. One-tap access from anywhere

### Add to Widget:
1. Long press home screen
2. Add Widget → Shortcuts
3. Select "Atlas Bookmark"

---

**Result**: One-click solution to send any content from iOS to Atlas with automatic processing!