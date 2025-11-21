# Velja Configuration for Atlas Integration

## 🎯 Required Velja Setup

### 1. Enable Velja Data Access
Velja stores data in macOS containers. You need to ensure the data is accessible:

#### Default Velja Data Locations:
```
~/Library/Application Support/Velja/          (Standard installation)
~/Library/Containers/com.sindresorhus.Velja/Data/Library/Application Support/Velja/  (App Store version)
```

#### Required Files:
- `urls.json` - Main URL storage
- `history.json` - Historical data
- `bookmarks.json` - Bookmarked URLs
- `links.json` - Shared links

### 2. Configure Velja Settings

#### In Velja Preferences:
1. **General Tab**
   - ✅ Enable "Keep history"
   - ✅ Enable "Sync with iCloud" (for cross-device capture)

2. **Rules Tab**
   - Create rules for Atlas integration
   - Export rules as JSON for backup

3. **Advanced Tab**
   - Enable any automation features
   - Note data storage location

### 3. Create Automation Rules

#### Method 1: Velja Rules (Recommended)
Create rules in Velja to automatically handle certain URLs:

```json
{
  "rules": [
    {
      "name": "Atlas Documentation",
      "pattern": "*github.com*",
      "action": "save",
      "destination": "atlas_queue"
    },
    {
      "name": "Atlas Podcasts",
      "pattern": "*npr.org*",
      "action": "save",
      "destination": "atlas_queue"
    }
  ]
}
```

#### Method 2: Shortcuts Integration
Create a macOS Shortcut that triggers Atlas processing:

```applescript
# Shortcut: "Process with Atlas"
# Trigger: When sharing to Velja
# Action: Run Atlas ingestion script
```

### 4. File Permissions (Critical)

#### Ensure Atlas Can Read Velja Data:
```bash
# Check Velja data directory exists
ls -la ~/Library/Application\ Support/Velja/

# Check permissions
ls -la ~/Library/Containers/com.sindresorhus.Velja/

# If needed, add read permissions (be careful with this)
chmod +r ~/Library/Application\ Support/Velja/*.json
```

#### Alternative: Symbolic Link Approach
```bash
# Create a shared directory
mkdir -p ~/shared_velja_data

# Create symlink from Velja data to shared location
ln -s ~/Library/Application\ Support/Velja/urls.json ~/shared_velja_data/
```

### 5. URL Scheme Integration

#### Use Velja's URL Schemes:
```
velja:open?url=https://example.com&app=atlas
velja:save?url=https://example.com&tag=documentation
```

#### AppleScript Integration:
```applescript
tell application "Velja"
    open url "https://example.com" with tag "atlas"
    save url "https://example.com" to "atlas_queue"
end tell
```

### 6. Automation Setup Options

#### Option A: File Monitoring (Recommended)
```bash
# Atlas monitors Velja data files
# No Velja changes needed - just ensure data is readable
```

#### Option B: AppleScript Automation
```applescript
-- Save this as Atlas Integration.scpt
on process_url(url)
    tell application "Velja"
        set urlData to get url data for url
        return urlData
    end tell
end process_url
```

#### Option C: Shortcuts App
1. Create new Shortcut "Send to Atlas"
2. Add action "Get URLs from Velja"
3. Add action "Run Shell Script" pointing to Atlas ingestion
4. Set trigger to "When sharing to Velja"

### 7. Data Format Considerations

#### Expected Velja Data Structure:
```json
{
  "urls": [
    {
      "url": "https://example.com",
      "title": "Example Page",
      "timestamp": "2025-09-25T10:00:00Z",
      "source": "mobile",
      "tags": ["documentation", "tech"]
    }
  ],
  "metadata": {
    "version": "1.0",
    "last_sync": "2025-09-25T10:00:00Z"
  }
}
```

#### If Velja uses different format:
The Atlas integration is flexible and can adapt to different JSON structures.

### 8. Testing Your Setup

#### Test Data Access:
```bash
# 1. Check if Velja data is accessible
ls ~/Library/Application\ Support/Velja/

# 2. Test Atlas integration with sample data
python3 velja_integration.py find

# 3. Manual import test
python3 velja_integration.py import
```

#### Test Automation:
```bash
# 4. Start monitoring
python3 velja_integration.py monitor 30

# 5. In a separate terminal, add a test URL to Velja
# Then check if Atlas detects it
```

### 9. Troubleshooting

#### Common Issues:

**Permission Denied**
```bash
# Fix permissions
chmod 755 ~/Library/Application\ Support/Velja/
chmod 644 ~/Library/Application\ Support/Velja/*.json
```

**Velja Data Not Found**
- Ensure Velja has been used at least once
- Check both standard and App Store installation paths
- Verify iCloud sync is enabled if using multiple devices

**Integration Not Working**
- Test with manual import first
- Check log files: `logs/velja_integration.log`
- Verify URL classification: `python3 url_ingestion_service.py ingest <test-url>`

### 10. Production Deployment

#### LaunchAgent Setup (Optional):
```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.user.atlas.velja-monitor</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/bin/python3</string>
        <string>/path/to/atlas/velja_integration.py</string>
        <string>monitor</string>
        <string>60</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
</dict>
</plist>
```

#### Install LaunchAgent:
```bash
# Copy to LaunchAgents directory
cp com.user.atlas.velja-monitor.plist ~/Library/LaunchAgents/

# Load the agent
launchctl load ~/Library/LaunchAgents/com.user.atlas.velja-monitor.plist
```

## 🎉 Summary

**Minimal Velja Changes Required:**
1. ✅ Enable history keeping
2. ✅ Enable iCloud sync (optional but recommended)
3. ✅ Ensure data files are readable
4. ✅ Optionally create automation rules

**The Atlas system handles the rest automatically!**

---

**Status**: 🚀 **Ready for Production** - Configuration documented