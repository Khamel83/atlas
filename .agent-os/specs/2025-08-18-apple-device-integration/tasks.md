# Tasks: Apple Device Integration for Personal Knowledge Capture

## Phase 1: Simple API Endpoint (1 hour)

### Task 1.1: Create Capture API Endpoint
**File**: `api/capture.py`

**Atomic Implementation**:
```python
from flask import Flask, request, jsonify
import json
import uuid
from datetime import datetime
from pathlib import Path

class CaptureAPI:
    def capture_content(self):
        # Validate input
        # Generate unique ID
        # Queue for processing
        # Return success/error

    def queue_for_processing(self, content_data):
        # Write to capture queue file
        # Background service will pick up

@app.route('/api/capture', methods=['POST'])
def capture_endpoint():
    # Handle URL, text, voice content types
    # Add metadata (source device, timestamp, notes)
    # Queue for Atlas processing
```

**Acceptance Criteria**:
- [ ] API accepts URLs, text content, and metadata
- [ ] Content queued reliably for background processing
- [ ] Simple JSON responses for success/error states
- [ ] Integration with existing Atlas ingestion pipeline

### Task 1.2: Background Service Integration
**File**: `scripts/atlas_background_service.py`

**Atomic Implementation**:
```python
def process_capture_queue(self):
    # Check for new capture queue files
    # Process through appropriate ingestor
    # Clean up processed items
    # Handle errors and retries

def _process_captured_item(self, item):
    # Route to article/text/voice ingestor
    # Preserve original metadata
    # Update capture status
```

**Acceptance Criteria**:
- [ ] Background service monitors capture queue
- [ ] Captured content processed through existing ingestors
- [ ] Error handling and retry logic implemented
- [ ] Capture processing logged and tracked

## Phase 2: iOS Share Extension (1.5 hours)

### Task 2.1: Create iOS App Project
**Directory**: `ios/AtlasCapture/`

**Atomic Implementation**:
```swift
// AtlasCapture app
struct ContentView: View {
    @State private var serverURL = "http://192.168.1.100:5000"
    @State private var captureHistory: [CaptureItem] = []

    var body: some View {
        NavigationView {
            // Simple settings and history
        }
    }
}

// Settings for Atlas server configuration
struct SettingsView: View {
    // Server URL configuration
    // Connection testing
    // Basic preferences
}
```

**Acceptance Criteria**:
- [ ] Basic iOS app with server configuration
- [ ] Simple UI for viewing capture history
- [ ] Connection testing to Atlas API
- [ ] Settings persistence in UserDefaults

### Task 2.2: Share Extension Implementation
**Directory**: `ios/AtlasCapture/ShareExtension/`

**Atomic Implementation**:
```swift
class ShareViewController: UIViewController {
    func extractContent() {
        // Extract URL or text from share context
        // Show simple UI for optional notes
        // Send to Atlas API
    }

    func sendToAtlas(_ content: CaptureContent) {
        // HTTP POST to capture API
        // Handle offline queueing
        // Show success/error feedback
    }
}

struct CaptureContent {
    let type: ContentType // url, text
    let content: String
    let metadata: [String: Any]
    let timestamp: Date
}
```

**Acceptance Criteria**:
- [ ] Share extension extracts URLs and text from any app
- [ ] Optional UI for adding notes or tags
- [ ] HTTP POST to Atlas capture API
- [ ] Offline queue when server unreachable
- [ ] Success/error feedback to user

## Phase 3: Shortcuts Integration (0.5 hours)

### Task 3.1: Create Shortcuts Templates
**Files**: `shortcuts/atlas-shortcuts.json`

**Atomic Implementation**:
```json
{
  "shortcuts": [
    {
      "name": "Add to Atlas",
      "description": "Send current content to Atlas",
      "actions": [
        "get_clipboard",
        "http_post_to_atlas",
        "show_notification"
      ]
    },
    {
      "name": "Voice to Atlas",
      "description": "Record voice memo and send to Atlas",
      "actions": [
        "dictate_text",
        "http_post_to_atlas",
        "show_result"
      ]
    }
  ]
}
```

**Acceptance Criteria**:
- [ ] Shortcuts templates for common capture scenarios
- [ ] Voice memo → text → Atlas workflow
- [ ] Clipboard content capture shortcut
- [ ] Simple setup instructions for importing shortcuts

### Task 3.2: API Integration Documentation
**File**: `docs/apple-integration.md`

**Atomic Implementation**:
```markdown
# Apple Device Integration Setup

## iOS Share Extension
1. Install AtlasCapture.app
2. Configure server URL in settings
3. Use share button from any app

## Shortcuts Setup
1. Import Atlas shortcuts
2. Configure server URL in shortcut
3. "Hey Siri, add to Atlas"

## API Endpoints
POST /api/capture
{
  "type": "url|text",
  "content": "...",
  "metadata": {"notes": "..."}
}
```

**Acceptance Criteria**:
- [ ] Clear setup instructions for iOS integration
- [ ] Shortcuts import and configuration guide
- [ ] API documentation for custom integrations
- [ ] Troubleshooting guide for common issues

## Database Schema Updates

### Task: Add Capture Tracking
**File**: `migrations/add_capture_tracking.sql`

**Atomic Implementation**:
```sql
-- Track content captured from devices
CREATE TABLE IF NOT EXISTS capture_queue (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    capture_id TEXT UNIQUE NOT NULL,
    content_type TEXT NOT NULL, -- url, text, voice
    content TEXT NOT NULL,
    metadata TEXT, -- JSON metadata
    source_device TEXT,
    captured_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    processed_at TIMESTAMP,
    status TEXT DEFAULT 'queued', -- queued, processing, completed, failed
    error_message TEXT
);

CREATE INDEX IF NOT EXISTS idx_capture_queue_status ON capture_queue(status);
CREATE INDEX IF NOT EXISTS idx_capture_queue_captured_at ON capture_queue(captured_at);
```

## Integration Points

### Task: Atlas Pipeline Integration
**Files**: Modified existing ingestors

**Atomic Implementation**:
```python
# Add source tracking to existing ingestors
def process_captured_content(self, capture_item):
    # Extract content and metadata
    # Route to appropriate ingestor (article, text, etc.)
    # Preserve capture metadata in Atlas metadata
    # Update capture status

# Add capture source to content metadata
metadata['capture_info'] = {
    'captured_from': 'ios_share_extension',
    'captured_at': capture_item['captured_at'],
    'capture_notes': capture_item.get('notes')
}
```

## Acceptance Criteria

### Functional Requirements
- [ ] iOS share extension captures content from any app instantly
- [ ] API endpoint queues content reliably for Atlas processing
- [ ] Shortcuts integration enables voice capture workflows
- [ ] Offline queueing prevents content loss
- [ ] Captured content flows through existing Atlas ingestion pipeline

### Performance Requirements
- [ ] Share extension responds within 2 seconds
- [ ] API endpoint handles requests under 500ms
- [ ] Offline queue syncs automatically when connection restored
- [ ] Background processing handles capture queue within 5 minutes

### Quality Requirements
- [ ] URL extraction works from Safari, apps, messages
- [ ] Text capture preserves formatting when possible
- [ ] Error handling provides clear feedback to user
- [ ] No data loss during network interruptions

### Integration Requirements
- [ ] Captured content appears in Atlas search within 30 minutes
- [ ] Existing Atlas features work with captured content
- [ ] Simple setup process requiring minimal technical knowledge
- [ ] Works with existing Atlas deployment and configuration

## Success Metrics

### Immediate
- [ ] Share extension successfully installed and configured
- [ ] API endpoint receiving and processing content
- [ ] Basic Shortcuts integration functional

### Short-term
- [ ] Daily content capture workflow established
- [ ] Captured content discoverable through Atlas search
- [ ] Offline queueing tested and reliable

### Long-term
- [ ] Seamless knowledge capture becomes primary Atlas input method
- [ ] Voice capture workflows integrated into daily routine
- [ ] Apple device integration feels native and effortless

---

**Total Estimated Time**: 3 hours across 3 phases
**Dependencies**: Existing Atlas ingestion pipeline, iOS development environment
**Risk Level**: Low (simple HTTP API and basic iOS extension)
**Output**: Seamless Apple device integration for personal knowledge capture