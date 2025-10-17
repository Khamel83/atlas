# Velja Shortcuts Integration Guide

## 🎯 Creating Shortcuts for Atlas Integration

### Method 1: Direct URL Processing

#### Shortcut: "Send to Atlas"
1. Open Shortcuts app
2. Create new shortcut named "Send to Atlas"
3. Add actions:

**Action 1: Get URL from Input**
- Type: "Get URLs from Input"
- Set input to "Shortcut Input"

**Action 2: Run Shell Script**
- Type: "Run Shell Script"
- Shell: "/bin/zsh"
- Input: "python3 /path/to/atlas/url_ingestion_service.py ingest {URL} shortcuts high"

**Action 3: Show Result**
- Type: "Show Notification"
- Title: "Sent to Atlas"
- Body: "URL queued for processing"

#### Set Shortcut Trigger:
- Right-click shortcut → "Add to Home Screen"
- Or add to Share Sheet for "URLs"

### Method 2: Bulk Processing

#### Shortcut: "Process Velja Bookmarks"
1. Create new shortcut named "Process Velja Bookmarks"
2. Add actions:

**Action 1: Find Velja Data**
- Type: "Run Shell Script"
- Shell: "/bin/zsh"
- Script: `python3 /path/to/atlas/velja_integration.py import`

**Action 2: Show Summary**
- Type: "Show Notification"
- Title: "Velja Processing Complete"
- Body: Processed {result} URLs

### Method 3: Automated Monitoring

#### Shortcut: "Start Atlas Monitoring"
1. Create new shortcut named "Start Atlas Monitoring"
2. Add actions:

**Action 1: Start Background Processing**
- Type: "Run Shell Script"
- Shell: "/bin/zsh"
- Script: `nohup python3 /path/to/atlas/velja_integration.py monitor 60 > /tmp/atlas_monitor.log 2>&1 &`

**Action 2: Confirm Started**
- Type: "Show Notification"
- Title: "Atlas Monitoring Started"
- Body: "Monitoring Velja for new URLs"

### Method 4: Integration with Other Apps

#### With Drafts:
1. Create action to send URL to Atlas
2. Use URL scheme: `atlas://ingest?url={draft_url}`

#### With DevonThink:
1. Create script to extract URLs
2. Send to Atlas ingestion service

#### With Obsidian:
1. Use URL extraction plugin
2. Integrate with Atlas via shell script

### Method 5: Voice Control Integration

#### Siri Shortcut:
1. Create shortcut "Send Link to Atlas"
2. Trigger phrase: "Hey Siri, send this to Atlas"
3. Action: Process current URL

### Method 6: Automation with Velja Rules

#### Export Existing Rules:
1. Open Velja Preferences
2. Go to Rules tab
3. Select "Export Rules" → Save as JSON

#### Import Enhanced Rules:
```json
{
  "rules": [
    {
      "name": "Atlas Documentation",
      "pattern": "*github.com*",
      "action": "save",
      "destination": "atlas_queue",
      "tag": "documentation"
    },
    {
      "name": "Atlas Technical",
      "pattern": "*stackoverflow.com*",
      "action": "save",
      "destination": "atlas_queue",
      "tag": "technical"
    },
    {
      "name": "Atlas Podcasts",
      "pattern": "*npr.org*",
      "action": "save",
      "destination": "atlas_queue",
      "tag": "podcast"
    }
  ]
}
```

### Method 7: Advanced URL Schemes

#### Direct Atlas Integration:
```
atlas://ingest?url=https://example.com&source=velja&priority=high
atlas://status?check=true
atlas://monitor?start=true
```

#### AppleScript Integration:
```applescript
-- Save as AtlasIntegration.applescript
on processURL(url)
    set atlasPath to "/path/to/atlas"
    set command to "python3 " & atlasPath & "/url_ingestion_service.py ingest " & url & " velja high"
    do shell script command
    return "URL sent to Atlas"
end processURL
```

### Method 8: File-Based Automation

#### Watch Velja Data Directory:
```bash
# Create a folder action for Velja data
# This triggers when new files are added

cat > ~/Library/Workflows/Applications/Folder Actions/atlas-velja.workflow/Contents/document.wflow << 'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>AMWorkflowBuildIdentifier</key>
    <string>com.apple.Automator.atlas-velja</string>
    <key>AMWorkflowApplicationIdentifier</key>
    <array>
        <string>com.apple.finder</string>
    </array>
    <key>AMWorkflowApplicationPath</key>
    <array>
        <string>/System/Library/CoreServices/Finder.app</string>
    </array>
    <key>AMWorkflowIconName</key>
    <string>FolderAction</string>
    <key>AMWorkflowServices</key>
    <array/>
    <key>AMWorkflowTypeIdentifier</key>
    <string>com.apple.Automator.no-actions</string>
    <key>AMWorkflowUUID</key>
    <string>12345678-1234-1234-1234-123456789012</string>
    <key>actions</key>
    <array>
        <dict>
            <key>AMActionBuildVersion</key>
            <string>522</string>
            <key>AMActionError</key>
            <dict>
                <key>AMActionExitError</key>
                <integer>0</integer>
                <key>AMActionErrorType</key>
                <integer>0</integer>
                <key>AMActionSignal</key>
                <integer>0</integer>
            </dict>
            <key>AMActionFlags</key>
            <integer>0</integer>
            <key>AMActionIcon</key>
            <dict>
                <key>AMActionIconName</key>
                <string>RunShellScript</string>
                <key>AMActionIconProvider</key>
                <integer>0</integer>
            </dict>
            <key>AMActionInput</key>
            <dict>
                <key>AMActionInputType</key>
                <string>com.apple.cocoa.string</string>
            </dict>
            <key>AMActionName</key>
            <string>Run Shell Script</string>
            <key>AMActionOutput</key>
            <dict>
                <key>AMActionOutputType</key>
                <string>com.apple.cocoa.string</string>
            </dict>
            <key>AMActionUUID</key>
            <string>12345678-1234-1234-1234-123456789012</string>
            <key>AMActionVersion</key>
            <string>1.0.1</string>
            <key>AMActionParameters</key>
            <dict>
                <key>command</key>
                <string>python3 /path/to/atlas/velja_integration.py import</string>
                <key>input</key>
                <string>as arguments</string>
                <key>path</key>
                <string></string>
                <key>runAsUser</key>
                <true/>
                <key>shell</key>
                <string>/bin/zsh</string>
            </dict>
        </dict>
    </array>
    <key>workflowMetaData</key>
    <dict>
        <key>AMWorkflowImportedAtDate</key>
        <date>2025-09-25T10:00:00Z</date>
        <key>AMWorkflowImportedFrom</key>
        <string>Folder Actions</string>
        <key>AMWorkflowName</key>
        <string>Atlas Velja Integration</string>
    </dict>
</dict>
</plist>
EOF
```

### Method 9: Calendar-Based Automation

#### Schedule Regular Processing:
```bash
# Add to crontab
echo "0 * * * * python3 /path/to/atlas/velja_integration.py import" | crontab -
```

### Method 10: Hazel Integration

#### If using Hazel for file automation:
1. Create rule for Velja data files
2. Set condition: "File name contains urls.json"
3. Action: "Run shell script" → Atlas integration
4. Set to monitor Velja directory

### Testing Your Shortcuts

#### Test Each Method:
1. **Manual Test**: Share a URL to Velja
2. **Import Test**: Run import script manually
3. **Monitor Test**: Start monitoring system
4. **Automation Test**: Trigger via automation

#### Verify Results:
- Check Atlas ingestion logs
- Verify URLs appear in queue
- Confirm processing completes
- Check content is stored correctly

### Troubleshooting Shortcuts

#### Common Issues:
- **Permission denied**: Check script permissions
- **Path not found**: Verify Atlas installation path
- **Velja data not accessible**: Check file permissions
- **Automation not triggering**: Check Shortcuts permissions

#### Debug Steps:
1. Run shortcuts manually first
2. Check log files for errors
3. Test with simple URLs
4. Verify all paths are correct

---

**Status**: 🚀 **Ready for Implementation** - Multiple integration methods provided