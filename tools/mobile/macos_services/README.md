# macOS Services - Right-Click File Context Menu

Add "Send to Atlas" to your Finder's right-click context menu for any file.

## 🚀 Quick Installation

```bash
cd macos_services
./install_service.sh
```

## 🎯 How to Use

1. **Right-click any file** in Finder
2. **Select Services → Send to Atlas**
3. **Get notification** when file is saved to Atlas

## 📄 Supported Files

- **Text Files**: `.txt`, `.md`, `.py`, `.js`, `.html` (content extracted)
- **PDF Documents**: Filename and metadata saved
- **Any Other File**: Filename and basic info saved

## ✅ Features

- **Native macOS Integration**: Uses Automator Services
- **Notification Feedback**: Shows success/failure notifications
- **Smart Content Extraction**: Reads text file contents automatically
- **Atlas API Integration**: Saves to your Atlas database via REST API
- **Error Handling**: Graceful failure with helpful messages

## 🔧 Requirements

- **Atlas running** on port 7444 (`python atlas_service_manager.py start`)
- **Python 3** with requests library
- **macOS** (tested on macOS 11+)

## 🛠️ Manual Installation

If the script doesn't work:

1. **Open Automator**
2. **Create New → Service**
3. **Drag "Run Shell Script"** action to workflow
4. **Copy script content** from `Send to Atlas.workflow/Contents/document.wflow`
5. **Save as "Send to Atlas"**

## 🔍 Troubleshooting

**Service not appearing in context menu:**
- Run `/System/Library/CoreServices/pbs -flush`
- Restart Finder: `killall Finder`
- Check Services in System Preferences → Keyboard → Shortcuts

**Files not saving:**
- Ensure Atlas is running: `python atlas_status.py`
- Check Atlas logs for API errors
- Verify port 7444 is accessible

**No notifications:**
- Check notification permissions in System Preferences
- Test with a simple text file first

Perfect complement to browser extensions and voice capture!