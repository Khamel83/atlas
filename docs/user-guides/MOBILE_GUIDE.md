# Atlas Mobile Usage Guide

This comprehensive guide covers everything you need to know about using Atlas on your iPhone and iPad. From setting up iOS Shortcuts to using voice commands and the mobile web dashboard, this guide will help you seamlessly capture and manage content on the go.

## Table of Contents

1. [iOS Shortcuts Setup](#ios-shortcuts-setup)
2. [Voice Commands](#voice-commands)
3. [Safari Integration](#safari-integration)
4. [Mobile Web Dashboard](#mobile-web-dashboard)
5. [Offline Functionality](#offline-functionality)
6. [iPhone and iPad Specific Instructions](#iphone-and-ipad-specific-instructions)
7. [Permissions and Privacy Settings](#permissions-and-privacy-settings)
8. [Mobile Workflow Examples](#mobile-workflow-examples)
9. [Troubleshooting iOS-Specific Issues](#troubleshooting-ios-specific-issues)

## iOS Shortcuts Setup

### Installing and Using Atlas Shortcuts

Atlas provides powerful iOS Shortcuts that make it easy to capture content directly from your iPhone or iPad:

#### Installation Steps

**🎯 Method 1: Direct Mobile Installation (Easiest)**

1. **Get Your Atlas URL**:
   - Run `./get_mobile_url.sh` on your Mac/server
   - This shows the URL to use: `http://YOUR_IP:8000/shortcuts`

2. **Install from Your iPhone**:
   - Open the URL shown above on your iPhone
   - Tap each shortcut you want to install
   - Follow iOS prompts: "Get Shortcut" → "Add Shortcut"
   - No computer file access needed!

**💻 Method 2: Install from Computer**

1. **Run Install Script**:
   - On your Mac/server: `./install_shortcuts.sh`
   - Follow terminal instructions

2. **Manual Installation**:
   - Visit your Atlas server's web interface at `/shortcuts`
   - Download the `.shortcut` files to your device
   - Open each file to import into the Shortcuts app

#### Available Shortcuts

1. **Save to Atlas**:
   - Captures the current web page or selected text
   - Works from Safari, Notes, and other apps
   - Usage: Share → Save to Atlas

2. **Voice Memo to Atlas**:
   - Records and transcribes voice memos
   - Automatically saves transcription to Atlas
   - Usage: "Hey Siri, record voice memo to Atlas"

3. **Screenshot to Atlas**:
   - Takes a screenshot and OCRs the text
   - Saves both image and extracted text
   - Usage: "Hey Siri, capture screenshot to Atlas"

4. **Current Page to Atlas**:
   - Saves the current web page with full content
   - Preserves formatting and images
   - Usage: Share → Current Page to Atlas

### Customizing Shortcuts

#### Adding Custom Parameters

1. Open the Shortcuts app
2. Select an Atlas shortcut
3. Tap the three dots (...) to edit
4. Modify parameters in the "Text" or "Variables" sections
5. Save your changes

#### Creating Custom Shortcuts

You can create your own shortcuts that integrate with Atlas:

1. Open the Shortcuts app
2. Tap the "+" button to create a new shortcut
3. Add actions:
   - "Get Contents of Web Page" for web content
   - "Record Audio" for voice memos
   - "Take Screenshot" for visual content
4. Add a "Run Shell Script" or "Run JavaScript on Web Page" action
5. Configure the action to send content to your Atlas server

Example JavaScript for saving web content:
```javascript
// Save to Atlas bookmarklet
javascript:(function(){
    var title = document.title;
    var url = window.location.href;
    var xhr = new XMLHttpRequest();
    xhr.open("POST", "https://atlas.khamel.com/api/v1/content/save", true);
    xhr.setRequestHeader("Content-Type", "application/json");
    xhr.send(JSON.stringify({
        title: title,
        url: url,
        content: document.body.innerText
    }));
})();
```

## Voice Commands

### Using Siri for Content Capture

Atlas integrates with Siri to enable hands-free content capture:

#### Setting Up Voice Commands

1. Open the Shortcuts app
2. Select an Atlas shortcut
3. Tap the three dots (...) to edit
4. Tap "Add to Siri"
5. Record your preferred voice command
6. Tap "Done"

#### Recommended Voice Commands

- "Save this page to Atlas"
- "Record a voice memo to Atlas"
- "Capture this screenshot to Atlas"
- "Process this document with Atlas"
- "Add to my reading list in Atlas"

#### Advanced Voice Commands

You can create more complex voice commands:

1. **Context-Aware Capture**:
   - "Hey Siri, capture my current work context to Atlas"
   - Saves current app, time, and location context

2. **Batch Processing**:
   - "Hey Siri, process all my notes to Atlas"
   - Sends multiple notes or documents at once

3. **Scheduled Capture**:
   - "Hey Siri, remind me to capture my evening thoughts to Atlas at 9 PM"
   - Sets up a scheduled capture

### Voice Memo Workflows

#### Recording and Transcribing

1. Say your preferred voice command
2. Speak naturally about your topic
3. Atlas automatically transcribes and processes
4. Content appears in your Atlas dashboard

#### Best Practices for Voice Capture

- Speak clearly and at a moderate pace
- Minimize background noise
- Use specific terminology for better categorization
- Include context about the topic or purpose

## Safari Integration

### Share Sheet Integration

Atlas integrates with Safari's share sheet for seamless content capture:

#### Using the Share Sheet

1. Open any web page in Safari
2. Tap the share button (box with arrow)
3. Scroll to find "Save to Atlas" or your custom shortcut
4. Select the action to capture the content

#### Reading List Integration

1. Add pages to Safari's Reading List
2. Atlas can automatically import Reading List items
3. Configure in Atlas settings to check for new Reading List items

#### Bookmark Integration

1. Create Safari bookmarks that trigger Atlas shortcuts
2. Use bookmarklets to send content to Atlas
3. Organize bookmarks in folders for different content types

### Safari Extension (Advanced)

For advanced users, Atlas can integrate as a Safari extension:

#### Installation Steps

1. Enable Developer Mode in iOS Settings
2. Install the Safari extension from Xcode
3. Configure extension permissions
4. Customize capture settings

#### Features

- One-tap capture from Safari toolbar
- Automatic content categorization
- Preview before saving
- Batch capture of multiple tabs

## Mobile Web Dashboard

### Using Atlas Cognitive Features on Phone

The Atlas web dashboard is fully responsive and works great on mobile devices:

#### Accessing the Dashboard

1. Open your mobile browser
2. Navigate to your Atlas server (e.g., `http://192.168.1.100:8000`)
3. Tap the menu icon to access different features

#### Mobile-Specific Features

1. **Touch-Friendly Interface**:
   - Large buttons and touch targets
   - Swipe gestures for navigation
   - Optimized layouts for small screens

2. **Voice Input**:
   - Microphone button for voice search
   - Speech-to-text for content entry
   - Voice commands for navigation

3. **Camera Integration**:
   - Camera button for scanning documents
   - QR code scanning for quick access
   - Photo upload for visual content

#### Cognitive Features on Mobile

1. **Proactive Surfacer**:
   - Swipe to browse forgotten content
   - Tap to revisit items
   - Sort by relevance or date

2. **Temporal Relationships**:
   - Timeline view optimized for mobile
   - Tap to explore content relationships
   - Filter by date ranges

3. **Socratic Questions**:
   - Voice input for questions
   - Tap to generate new questions
   - Save interesting questions for later

4. **Active Recall**:
   - Flashcard view for mobile
   - Swipe to mark items as reviewed
   - Progress tracking

5. **Pattern Detector**:
   - Tag cloud view for mobile
   - Tap to explore patterns
   - Filter by content type

## Offline Functionality

### What Works Without Internet Connection

Atlas provides limited offline functionality on mobile devices:

#### Offline Content Capture

1. **Voice Memos**:
   - Record voice memos offline
   - Automatically queue for processing when online
   - View recording history

2. **Notes and Text**:
   - Create notes in Shortcuts app
   - Save to offline queue
   - Sync when connection restored

3. **Photos and Screenshots**:
   - Capture images offline
   - Store in local gallery
   - Process when online

#### Offline Queue Management

1. **View Pending Items**:
   - See what content is queued for processing
   - View capture timestamps and types
   - Estimated processing time

2. **Manage Queue**:
   - Delete items from queue
   - Prioritize specific items
   - Pause/resume synchronization

#### Limitations

- No real-time processing
- No access to web dashboard
- Limited cognitive features
- No search functionality
- No content updates

## iPhone and iPad Specific Instructions

### iPhone-Specific Features

#### Portrait Mode Optimizations

1. **Single-Column Layout**:
   - Content optimized for narrow screens
   - Easy thumb navigation
   - Large touch targets

2. **Quick Actions**:
   - 3D Touch shortcuts (if supported)
   - Widget integration
   - Notification actions

#### iPhone Workflows

1. **Commuting**:
   - Listen to podcasts with Atlas integration
   - Capture thoughts during travel
   - Review content in queue

2. **Meetings**:
   - Record voice memos
   - Capture meeting notes
   - Process action items

### iPad-Specific Features

#### Landscape Mode Optimizations

1. **Multi-Column Layout**:
   - Side-by-side content viewing
   - Split-screen multitasking
   - Keyboard shortcuts

2. **Apple Pencil Support**:
   - Handwriting recognition
   - Sketch annotation
   - Drawing capture

#### iPad Workflows

1. **Research**:
   - Multi-tab browsing with capture
   - Side-by-side note taking
   - Content organization

2. **Content Creation**:
   - Document drafting and capture
   - Multimedia content creation
   - Project management

## Permissions and Privacy Settings

### Required Permissions

Atlas requires several permissions to function properly on iOS:

#### Microphone Access

**Purpose**: Voice memo recording and transcription
**Usage**: "Voice Memo to Atlas" shortcut
**Privacy**: Audio is processed locally when possible

#### Camera Access

**Purpose**: Screenshot capture and document scanning
**Usage**: "Screenshot to Atlas" shortcut
**Privacy**: Images are processed according to your settings

#### Files Access

**Purpose**: Document and file processing
**Usage**: Share sheet integration
**Privacy**: Files are processed according to your settings

#### Location Access

**Purpose**: Context-aware content capture
**Usage**: Optional location tagging
**Privacy**: Location data is only stored if enabled

### Privacy Configuration

#### Data Handling

1. **Local Processing**:
   - Content processed on your device when possible
   - Encryption for sensitive data
   - Secure storage

2. **Server Communication**:
   - HTTPS encryption for all communication
   - API key authentication
   - Minimal data transmission

#### Privacy Settings

1. **Disable Location**:
   - Turn off location services for Atlas
   - Remove location data from existing content

2. **Limit Data Sharing**:
   - Configure what data is sent to Atlas server
   - Set retention policies
   - Enable data deletion

## Mobile Workflow Examples

### Commute Workflow

#### Morning Commute

1. **Listen and Capture**:
   - Play podcasts with Atlas integration
   - Capture interesting segments
   - Queue for transcription

2. **Reading**:
   - Browse articles in Safari
   - Save interesting content to Atlas
   - Add personal notes

#### Evening Commute

1. **Review and Reflect**:
   - Review captured content from the day
   - Add thoughts and annotations
   - Process voice memos

### Meeting Workflow

#### Before Meeting

1. **Preparation**:
   - Review relevant content in Atlas
   - Prepare questions using Socratic engine
   - Set up voice recording

#### During Meeting

1. **Capture**:
   - Record voice memos
   - Take notes in Shortcuts app
   - Capture whiteboard photos

#### After Meeting

1. **Processing**:
   - Transcribe voice memos
   - Extract action items
   - Categorize content

### Research Workflow

#### Initial Research

1. **Content Gathering**:
   - Browse and save articles
   - Capture PDFs and documents
   - Record initial thoughts

#### Deep Dive

1. **Analysis**:
   - Use pattern detector to find connections
   - Generate socratic questions
   - Review temporal relationships

#### Synthesis

1. **Creation**:
   - Combine insights into new content
   - Use active recall for key concepts
   - Surface related forgotten content

## Troubleshooting iOS-Specific Issues

### Common Issues and Solutions

#### Shortcuts Not Appearing

**Problem**: Atlas shortcuts don't appear in share sheet
**Solutions**:
1. Check that shortcuts are properly installed
2. Restart the Shortcuts app
3. Re-import the shortcut files
4. Check iOS version compatibility

#### Voice Commands Not Working

**Problem**: Siri doesn't recognize Atlas voice commands
**Solutions**:
1. Re-add voice commands to Siri
2. Check microphone permissions
3. Speak commands clearly
4. Update iOS to latest version

#### Content Not Saving

**Problem**: Captured content doesn't appear in Atlas
**Solutions**:
1. Check Atlas server connectivity
2. Verify server URL in shortcut settings
3. Check offline queue for pending items
4. Review Atlas logs for errors

#### Offline Sync Issues

**Problem**: Offline content not syncing when online
**Solutions**:
1. Check internet connectivity
2. Force sync from Shortcuts app
3. Restart Atlas server
4. Clear offline queue and retry

### Advanced Troubleshooting

#### Debugging Shortcuts

1. **Enable Debug Mode**:
   - Open shortcut in editor
   - Tap "Show More" to see all actions
   - Check for error messages

2. **Check Logs**:
   - View shortcut run history
   - Check Atlas server logs
   - Look for specific error codes

#### Network Issues

1. **Local Network**:
   - Ensure Atlas server is accessible
   - Check firewall settings
   - Verify IP address and port

2. **Remote Access**:
   - Configure port forwarding
   - Set up VPN access
   - Use cloud-based Atlas instance

### Performance Optimization

#### Battery Life

1. **Optimize Processing**:
   - Schedule heavy processing for charging
   - Reduce background activity
   - Use low-power mode settings

#### Storage Management

1. **Clear Cache**:
   - Regularly clear shortcut cache
   - Delete processed offline items
   - Manage photo storage

#### Memory Usage

1. **Limit Concurrent Operations**:
   - Process one item at a time
   - Close unused apps
   - Restart device periodically

## Getting Help

### Community Support

Join the Atlas community:
- Discord: https://discord.gg/atlas
- Reddit: r/AtlasPlatform
- GitHub Discussions: https://github.com/your-username/atlas/discussions

### Professional Support

For enterprise support:
- Email: support@atlas-platform.com
- Phone: +1 (555) 123-4567
- SLA: 24-hour response time

### Reporting Issues

Report bugs and issues on GitHub:
- Repository: https://github.com/your-username/atlas
- Issue Template: Include device information, iOS version, and reproduction steps

Happy mobile content processing! 📱🧠✨