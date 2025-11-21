# iOS/Mac Share Sheet Setup for Atlas - atlas.khamel.com

## 📱 **Method 1: iOS Shortcut (Recommended)**

### Step 1: Create the "Add to Atlas" Shortcut

1. **Open Shortcuts app** on your iPhone
2. **Tap "+"** to create new shortcut
3. **Name it**: "Add to Atlas"
4. **Add actions**:

   **Action 1: Get Input**
   - Accept Types: URLs, Text
   - Show When: Share Sheet

   **Action 2: Get URL from Input** (if URL shared)
   - OR **Get Text from Input** (if text shared)

   **Action 3: Text**
   - Set variable to: `https://atlas.khamel.com/add`

   **Action 4: URL**
   - URL: Variable from Action 3
   - Add query parameters:
     - `content`: [URL or Text from input]
     - `title`: [Optional - extract from input]
     - `source`: `iOS Share Sheet`

   **Action 5: Open URL**

### Step 2: Add to Share Sheet

1. **Tap "..."** on your shortcut
2. **Toggle "Show in Share Sheet"**
3. **Select types**: URLs, Text
4. **Customize** with Atlas icon if desired

## ⚙️ **Common Issues & Fixes**

### Problem: "Instructions don't work"
- **Symptom**: Share sheet shows but Atlas doesn't appear
- **Fix**: Use Method 1 above - iOS Shortcuts are most reliable

### Problem: "URL encoding issues"
- **Symptom**: Links break when containing special characters
- **Fix**: Ensure URL encoding in shortcut

## 🚀 **Testing Your Setup**

1. **Test with Safari**: Open webpage → Share → "Add to Atlas"
2. **Test with Apps**: Try sharing from Twitter, Reddit, etc.
3. **Verify in Atlas**: Check `/add` page shows pre-filled content

## 💡 **Pro Tips**

- **Add Atlas to Home Screen**: Save `/add` page to home screen for quick access
- **Multiple Instances**: Create different shortcuts for different Atlas categories
- **Batch Processing**: Share multiple links quickly using the share sheet

## ✅ **Tested Configuration**

- **Domain**: atlas.khamel.com
- **Share Sheet**: ✅ Works with iOS Shortcuts
- **URL Parameters**: ✅ Working with pre-filled content
- **Mobile Access**: ✅ Accessible from iPhone