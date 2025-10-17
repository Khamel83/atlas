# Atlas iOS Shortcuts Guide

Complete guide for creating iOS shortcuts to send content to Atlas via Gmail.

## 🎯 Overview

Send any content from iOS to Atlas using:
- **Email address**: `khamel83+atlas@gmail.com`
- **Auto-labeling**: Gmail filter applies "Atlas" label
- **Real-time processing**: Atlas v3 processes within 5 seconds
- **Universal sharing**: Works from any app that supports sharing

## 📱 Method 1: Universal "Send to Atlas" Shortcut

### Step-by-Step Creation

1. **Open Shortcuts App**
   - Launch iOS Shortcuts app
   - Tap "+" to create new shortcut

2. **Add Input Handling**
   - Add action: **"Receive Input with Share"**
   - Set "Content Types" to: **Text, URLs, Images**

3. **Extract URL (if present)**
   - Add action: **"Get URLs from Input"**
   - Set "Get All" to: **On**

4. **Prepare Content**
   - Add action: **"Text"**
   - Set text to: **Shortcut Input**
   - This captures the full content (URL + text)

5. **Get Title/Subject**
   - Add action: **"Get Name from URL"** (if URL detected)
   - Add action: **"Get Article from Safari Page"** (if from Safari)
   - Fallback to: **First 50 characters of text**

6. **Send Email**
   - Add action: **"Send Email"**
   - **Recipients**: `khamel83+atlas@gmail.com`
   - **Subject**: `Atlas Bookmark: [Title from step 5]`
   - **Body**: Use variable from step 4 (full content)

7. **Add to Share Sheet**
   - Tap shortcut name (top) to rename
   - Name: **"Send to Atlas"**
   - Tap "Add to Share Sheet"
   - Select "Content Types" where it appears

### Advanced Version with Multiple URLs

For handling multiple URLs in one message:

1. **Input**: Text/URLs from Share Sheet
2. **Extract URLs**: Get all URLs from input
3. **Count URLs**: Check if multiple URLs
4. **Format Content**:
   - If single URL: `URL [optional notes]`
   - If multiple URLs:
     ```
     Multiple Links:
     1. URL1
     2. URL2
     ...
     Notes: [additional text]
     ```
5. **Send Email**: Same as above

## 📧 Method 2: Simple Email Shortcut

### Quick Version

1. **Create Shortcut**
2. **Action**: **"Send Email"**
3. **To**: `khamel83+atlas@gmail.com`
4. **Subject**: `Atlas Bookmark: [Ask for Input]`
5. **Body**: **"Text"** → **"Ask for Input"** → Prompt: "Enter URL or content"
6. **Name**: **"Atlas Quick Email"**

## 🌐 Method 3: Safari Web Clipper

### From Safari Pages

1. **Create Shortcut**
2. **Input**: Safari Web Page
3. **Actions**:
   - **Get URL from Safari Page**
   - **Get Title from Safari Page**
   - **Get Text from Safari Page** (selected text or page excerpt)
4. **Send Email**:
   - To: `khamel83+atlas@gmail.com`
   - Subject: `Atlas: [Title]`
   - Body:
     ```
     URL: [URL]
     Notes: [Selected text/excerpt]
     ```

## 📋 Method 4: Article Reader Integration

### For Safari Reader View

1. **Input**: Safari Web Page
2. **Get Article**: Use **"Get Article from Safari Page"**
3. **Extract**:
   - Title, URL, Excerpt
4. **Send Email** with structured content

## 🎛️ Customization Options

### Subject Line Formats

- **Simple**: `Atlas Bookmark: [Title]`
- **Categorized**: `Atlas - [Category]: [Title]`
- **Timestamped**: `Atlas [YYYY-MM-DD]: [Title]`

### Content Formatting

#### URLs Only
```
https://example.com/article
```

#### URL with Notes
```
https://example.com/article

Important: Read section 3 about machine learning applications
```

#### Multiple Links
```
Links for review:
1. https://example.com/article1
2. https://example.com/article2

Context: Research on distributed systems
```

## ⚙️ Gmail Filter Setup

### Automatic Labeling

1. **Open Gmail** (desktop)
2. **Settings** → **See all settings**
3. **Filters and Blocked Addresses** → **Create new filter**

#### Filter for Atlas Emails
- **From**: Doesn't matter
- **To**: `khamel83+atlas@gmail.com`
- **Has the words**: Doesn't matter
- **Doesn't have**: Doesn't matter
- **Size**: Doesn't matter

**Actions**:
- ✅ **Apply the label**: Atlas (create if needed)
- ✅ **Mark as read**: Optional
- ✅ **Apply star**: Optional

#### Filter for Newsletters
- **From**: Specific newsletter senders
- **Subject**: Newsletter patterns
- **Actions**: Apply "Newsletter" label

## 🚀 Testing Your Shortcut

### Test Cases

1. **Single URL**: Share a URL from Safari
2. **Text with URL**: Share selected text with embedded URL
3. **Multiple URLs**: Share text with multiple links
4. **Just Text**: Share notes without URLs
5. **From Apps**: Try from different apps (Reddit, Twitter, etc.)

### Verification

1. **Send test email** using shortcut
2. **Check Gmail** - should have "Atlas" label
3. **Check Atlas** - URL should appear in database
4. **Timing** - Should process within 5 seconds

## 🎯 Best Practices

### Shortcut Naming

- **Universal**: "Send to Atlas"
- **Safari**: "Atlas Safari Clipper"
- **Quick**: "Atlas Quick Email"

### Content Tips

- **Include context**: Add brief notes when useful
- **Multiple URLs**: Number them for clarity
- **Clean URLs**: Ensure URLs are complete and accessible
- **Rich content**: Include excerpts when available

### Organization

- **Share Sheet**: Add to most relevant content types
- **Home Screen**: Add frequently used shortcuts
- **Safari**: Use for web-specific shortcuts

## 🔧 Troubleshooting

### Common Issues

1. **Email not arriving**
   - Check Gmail filter configuration
   - Verify email address: `khamel83+atlas@gmail.com`

2. **No URLs extracted**
   - Check shortcut URL extraction logic
   - Test with plain text URL

3. **Subject formatting**
   - Ensure variables are properly set
   - Test different input types

4. **Share Sheet not showing**
   - Check shortcut's "Content Types" settings
   - Restart Shortcuts app if needed

### Debug Mode

Add **"Show Result"** action before email to verify content.

## 🎉 Success Indicators

✅ **Shortcut appears** in Share Sheet
✅ **Email arrives** at `khamel83+atlas@gmail.com`
✅ **"Atlas" label applied** automatically
✅ **URL appears** in Atlas database
✅ **Processing time** under 5 seconds

## 📞 Support

For shortcut issues:
1. Test shortcut step by step
2. Verify Gmail filters
3. Check Atlas server status
4. Review Atlas logs: `logs/atlas_v3_gmail.log`

---

**Result**: Complete iOS shortcut system for sending any content to Atlas via Gmail with real-time processing.