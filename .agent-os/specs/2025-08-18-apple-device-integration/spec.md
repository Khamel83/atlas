# Apple Device Integration for Personal Knowledge Capture

**Date**: August 18, 2025
**Status**: 🎯 PLANNED
**Priority**: HIGH - Core Personal Workflow
**Parent Task**: Personal Knowledge System Completion

## Executive Summary

Create seamless content capture from Apple devices (iPhone, iPad, Mac) to Atlas ingestion system. Focus on **simple, reliable data passing** without complex UIs - just efficient ways to get content from your devices into Atlas for processing.

**Goal**: Make it trivial to capture content from Apple devices and send it to Atlas for automatic processing and search indexing.

## Current Status Analysis

### ✅ What We Have
- Atlas ingestion system operational with articles, podcasts, transcripts
- Background service processing content automatically
- Enhanced search with speaker attribution and topics
- Multiple input methods (files in `inputs/` directory)

### 🎯 What We Need
- **iOS/macOS Share Extension** for instant URL/text capture
- **Simple API endpoint** for receiving content from Apple devices
- **Shortcuts integration** for voice capture and automation
- **Reliable data passing** without complex authentication

## Implementation Strategy

### Phase 1: Simple API Endpoint (1 hour)
**Objective**: Create basic API for receiving content from Apple devices

**Atomic Tasks**:
1. **Create simple ingestion API** (`api/capture.py`)
   - POST endpoint for URLs, text, and metadata
   - Basic validation and queue management
   - Integration with existing ingestion pipeline
   - Simple success/error responses

2. **Add to background service**
   - Monitor API capture queue
   - Process captured content through existing ingestors
   - Error handling and retry logic

### Phase 2: iOS Share Extension (1.5 hours)
**Objective**: Build iOS app with share extension for instant capture

**Atomic Tasks**:
1. **Create iOS share extension** (`ios/AtlasCapture/`)
   - Share extension target for URLs and text
   - Simple UI with optional notes/tags
   - HTTP POST to Atlas API endpoint
   - Local queue for offline capture

2. **Basic iOS app container**
   - Minimal app to host share extension
   - Settings for Atlas server URL configuration
   - Simple capture history and status

### Phase 3: Shortcuts Integration (0.5 hours)
**Objective**: Enable Apple Shortcuts for voice capture and automation

**Atomic Tasks**:
1. **Shortcuts integration**
   - HTTP request templates for Shortcuts app
   - Voice memo → text → Atlas workflow
   - Quick capture shortcuts for common scenarios
   - Integration with existing API endpoint

## Expected Outcomes

### Capture Workflows Enabled
- **Safari → Atlas**: Share any webpage instantly to Atlas
- **Notes → Atlas**: Share text content from any app
- **Voice → Atlas**: "Hey Siri, add this to Atlas" workflows
- **Automation**: Scheduled capture from Reading List, Notes, etc.

### User Experience
- **One-tap capture** from any iOS/macOS app with share button
- **Offline queueing** when Atlas server not reachable
- **Simple feedback** - success/error notifications
- **No authentication complexity** - just reliable data passing

## Technical Architecture

### Core Components
1. **Capture API** (`api/capture.py`)
   ```python
   POST /api/capture
   {
     "type": "url|text|voice",
     "content": "...",
     "metadata": {"source": "ios", "notes": "..."}
   }
   ```

2. **iOS Share Extension** (`ios/AtlasCapture/ShareExtension/`)
   ```swift
   - URL extraction and validation
   - Optional note/tag addition
   - HTTP POST to Atlas API
   - Local storage for offline queue
   ```

3. **Shortcuts Templates**
   ```
   - "Add to Atlas" - General content capture
   - "Voice to Atlas" - Voice memo processing
   - "Reading List to Atlas" - Bulk Safari export
   ```

### Integration Points
- **Atlas ingestion pipeline**: Captured content flows through existing processors
- **Background service**: Monitors capture queue and processes content
- **Search indexing**: Captured content automatically indexed for search
- **Error handling**: Failed captures retry automatically

## Success Criteria

- [ ] Share extension captures URLs from Safari/apps instantly
- [ ] API endpoint processes captured content through Atlas pipeline
- [ ] Shortcuts integration enables voice capture workflows
- [ ] Offline queueing ensures no content loss
- [ ] Simple setup process for connecting devices to Atlas

## Implementation Complexity

- **Low complexity**: Basic HTTP API and simple iOS extension
- **No authentication**: Relies on local network/VPN access
- **Minimal UI**: Focus on function over form
- **Leverages existing**: Uses current Atlas ingestion and processing

---

**Expected Impact**: Seamless content capture from Apple devices enabling effortless knowledge accumulation with existing Atlas processing power.

*This task focuses purely on efficient content capture without complex features.*