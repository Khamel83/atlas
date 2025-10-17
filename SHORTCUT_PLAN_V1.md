# iOS/macOS Shortcuts to Atlas - Detailed Implementation Plan v1

## Project Overview
Create a reliable 1-click solution to send URLs from any iOS/macOS app directly to Atlas using Apple's built-in Shortcuts app.

## Requirements Analysis
- **Simple**: 1-click from share sheet in any app
- **Reliable**: 100% success rate when network is available
- **Universal**: Works on iPhone, iPad, Mac
- **Free**: No paid services or subscriptions
- **Direct**: No intermediary services (no ntfy, no email forwarding)

## Current Atlas Integration Points

### Available Atlas Endpoints
1. **Web Form**: `https://atlas.khamel.com/email-submit` (GET/POST)
2. **Webhook**: `https://atlas.khamel.com/email-webhook` (POST JSON)
3. **Direct Ingest**: `https://atlas.khamel.com/ingest?url=URL` (GET)

### Database Storage
- **Location**: `/home/ubuntu/dev/atlas/data/simple_atlas.db`
- **Table**: `urls` (id, url, created_at, source)
- **Current Status**: Working with webhook endpoint

## Proposed Solution Architecture

### iOS Shortcut Components
1. **Input**: Receive shared content from any app
2. **URL Extraction**: Extract URLs from shared content
3. **HTTP Request**: POST to Atlas webhook endpoint
4. **Confirmation**: Show success/error notification

### macOS Integration
1. **Sync**: Same shortcut syncs via iCloud
2. **Service Integration**: Enable as Quick Action
3. **Share Sheet**: Available in Safari and other apps

## Technical Implementation Details

### Shortcut Configuration
```
Name: "Send to Atlas"
Input Types: URLs, Text, Web Pages
Share Sheet: Enabled
Quick Action: Enabled (macOS)
```

### HTTP Request Format
```json
{
  "url": "[EXTRACTED_URL]",
  "title": "[PAGE_TITLE]",
  "source": "ios_shortcut"
}
```

### Atlas Webhook Handler
- **Endpoint**: `/email-webhook`
- **Method**: POST
- **Content-Type**: application/json
- **Response**: JSON success/error

## Step-by-Step Implementation Tasks

### Phase 1: Atlas Backend Verification (30 minutes)
1. **Verify webhook endpoint is running**
   - Check if `webhook_email_bridge.py` is running
   - Test POST to `https://atlas.khamel.com/email-webhook`
   - Verify database storage is working

2. **Test JSON payload handling**
   - Send test JSON with url field
   - Verify URL extraction and storage
   - Check database entry creation

3. **Confirm HTTPS accessibility**
   - Test from external network
   - Verify SSL certificate validity
   - Check firewall/port accessibility

### Phase 2: iOS Shortcut Creation (45 minutes)
1. **Create base shortcut**
   - Open Shortcuts app
   - Create new shortcut named "Send to Atlas"
   - Configure for share sheet usage

2. **Add input handling**
   - Accept URLs, Text, Web Pages
   - Extract URLs from input
   - Handle multiple URL scenarios

3. **Add HTTP request action**
   - Configure POST to webhook endpoint
   - Set JSON payload format
   - Add proper headers

4. **Add response handling**
   - Parse success/error response
   - Show appropriate notification
   - Handle network failures

5. **Test on iOS device**
   - Test from Safari
   - Test from other apps (Mail, Messages, etc.)
   - Verify database entries created

### Phase 3: macOS Integration (30 minutes)
1. **Sync shortcut to Mac**
   - Verify iCloud sync working
   - Import shortcut to Mac Shortcuts app

2. **Enable Quick Action**
   - Configure as macOS Service
   - Test from Safari share menu
   - Test from other Mac apps

3. **Assign keyboard shortcut (optional)**
   - System Preferences > Keyboard > Shortcuts
   - Assign hotkey to Quick Action

### Phase 4: Testing & Validation (60 minutes)
1. **Comprehensive iOS testing**
   - Safari (various websites)
   - Mail app (shared links)
   - Messages app
   - Twitter/X app
   - News app
   - Files app (if applicable)

2. **Comprehensive macOS testing**
   - Safari (share menu)
   - Chrome (if available)
   - Quick Action from various apps
   - Keyboard shortcut (if configured)

3. **Error condition testing**
   - Atlas server offline
   - Network disconnected
   - Invalid URLs
   - Empty content

4. **Performance testing**
   - Response time measurement
   - Multiple rapid submissions
   - Large URL handling

## Success Criteria

### Functional Requirements
- [ ] Shortcut appears in share sheet on iOS
- [ ] Shortcut appears in share menu on macOS
- [ ] URLs successfully stored in Atlas database
- [ ] Success notification appears after submission
- [ ] Error handling works for failures

### Reliability Requirements
- [ ] 100% success rate with valid URLs and network
- [ ] Graceful failure when Atlas is unreachable
- [ ] No data loss during normal operation
- [ ] Works across iOS app ecosystem

### Usability Requirements
- [ ] 2 taps maximum: Share → Send to Atlas
- [ ] Response time under 3 seconds
- [ ] Clear success/failure feedback
- [ ] Works in airplane mode → online transition

## Risk Assessment

### High Risk Issues
1. **Atlas endpoint reliability**
   - Risk: Webhook service crashes frequently
   - Mitigation: Ensure service stability before shortcut creation

2. **Shortcuts app limitations**
   - Risk: HTTP requests fail or timeout
   - Mitigation: Thorough testing, error handling

3. **Share sheet compatibility**
   - Risk: Some apps don't expose URLs properly
   - Mitigation: Test with major apps, document limitations

### Medium Risk Issues
1. **macOS permission requirements**
   - Risk: Security settings block Quick Actions
   - Mitigation: Clear setup instructions

2. **iCloud sync delays**
   - Risk: Shortcut doesn't sync to all devices
   - Mitigation: Manual export/import option

## Fallback Options

### If Shortcuts Approach Fails
1. **Browser bookmarklet** (already working)
2. **Dedicated iOS app** (requires development)
3. **Email forwarding** (if SMTP can be fixed)

## Documentation Requirements

### User Documentation
1. **iOS Setup Guide** with screenshots
2. **macOS Setup Guide** with screenshots
3. **Troubleshooting Guide**
4. **Alternative Methods** if primary fails

### Technical Documentation
1. **Atlas endpoint specification**
2. **Shortcut configuration export**
3. **Testing procedures**
4. **Maintenance requirements**

## Timeline Estimate
- **Planning & Evaluation**: 30 minutes
- **Implementation**: 2.5 hours
- **Testing**: 1 hour
- **Documentation**: 30 minutes
- **Total**: 4.5 hours

## Dependencies
- Atlas webhook endpoint must be stable
- iOS/macOS devices with Shortcuts app
- iCloud account for sync
- HTTPS access to atlas.khamel.com

---

## Next Steps
1. Evaluate this plan against requirements
2. Test Atlas webhook endpoint stability
3. Create and test iOS shortcut
4. Document setup process with screenshots
5. Validate across device ecosystem