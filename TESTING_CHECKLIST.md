# 🧪 iOS/macOS Shortcuts Testing Checklist

## ✅ Pre-Implementation Verification

- [x] **Atlas webhook endpoint working**: `https://atlas.khamel.com/email-webhook`
- [x] **Service running**: `webhook_email_bridge.py` on port 7447
- [x] **JSON response verified**: Returns success message with UUID
- [x] **Caddy routing confirmed**: `/email-webhook` → `127.0.0.1:7447`

## 📱 iOS Testing Plan

### Phase 1: Basic Shortcut Creation
- [ ] Open Shortcuts app on iOS device
- [ ] Create new shortcut named "Send to Atlas"
- [ ] Add all 4 required actions in correct order
- [ ] Configure webhook URL and JSON payload
- [ ] Enable "Use with Share Sheet"
- [ ] Test from Shortcuts app directly

### Phase 2: Share Sheet Integration
- [ ] **Safari**: Share website URL
- [ ] **Twitter/X**: Share tweet with link
- [ ] **Mail**: Share email with URL
- [ ] **Messages**: Share text message with URL
- [ ] **News**: Share news article
- [ ] **Files**: Share document with embedded URLs
- [ ] **Notes**: Share note containing URLs
- [ ] **Podcasts**: Share podcast episode (if applicable)

### Phase 3: Content Type Testing
- [ ] **Single URL**: Standard webpage
- [ ] **Multiple URLs**: Text with several links
- [ ] **PDF documents**: With embedded URLs
- [ ] **Text snippets**: Containing URLs
- [ ] **Email forwards**: With links in body
- [ ] **URL with parameters**: Query strings and anchors

### Phase 4: Error Scenarios
- [ ] **No internet**: Verify error notification
- [ ] **Atlas down**: Test with service stopped
- [ ] **Invalid URLs**: Malformed links
- [ ] **Empty content**: Share with no URLs
- [ ] **Large content**: Very long text with URLs

## 🖥️ macOS Testing Plan

### Phase 1: iCloud Sync
- [ ] Wait 5 minutes after iOS creation
- [ ] Open Shortcuts app on Mac
- [ ] Verify "Send to Atlas" appears
- [ ] Test shortcut directly from Shortcuts app

### Phase 2: Quick Action Setup
- [ ] Right-click shortcut → "Use as Quick Action"
- [ ] Select "Services Menu and Quick Actions"
- [ ] Verify in System Preferences → Extensions → Sharing

### Phase 3: Browser Testing
- [ ] **Safari**: Share button → "Send to Atlas"
- [ ] **Safari**: Right-click URL → Services → "Send to Atlas"
- [ ] **Chrome**: Highlight URL → right-click → Services
- [ ] **Firefox**: Copy URL → right-click → Services
- [ ] **Edge**: Browser share functionality

### Phase 4: Application Testing
- [ ] **Mail**: Right-click URLs in emails
- [ ] **Slack**: Share links from messages
- [ ] **Discord**: Share links from chat
- [ ] **Terminal**: URLs in command output
- [ ] **TextEdit**: URLs in documents
- [ ] **Pages/Word**: URLs in documents

## 🔍 Verification Steps

### For Each Test:
1. **Action**: Document what you shared
2. **Source**: Which app/method used
3. **Response**: Note success notification
4. **Database**: Verify URL stored in Atlas
5. **Timing**: Record response time

### Expected Results:
- [ ] **Notification**: "Sent to Atlas ✅" appears
- [ ] **Response time**: Under 3 seconds
- [ ] **Database entry**: New URL in Atlas with correct metadata
- [ ] **No errors**: No network timeouts or failures

## 📊 Success Criteria Validation

### Functional Requirements ✅
- [ ] Shortcut appears in share sheet on iOS
- [ ] Shortcut appears in Services menu on macOS
- [ ] URLs successfully stored in Atlas database
- [ ] Success notification appears after submission
- [ ] Error handling works for failure cases

### Reliability Requirements ✅
- [ ] 100% success rate with valid URLs and network
- [ ] Graceful failure when Atlas unreachable
- [ ] No data loss during normal operation
- [ ] Works across iOS/macOS app ecosystem

### Usability Requirements ✅
- [ ] Maximum 2 taps: Share → "Send to Atlas"
- [ ] Response time consistently under 3 seconds
- [ ] Clear success/failure feedback
- [ ] Works after airplane mode → online transition

## 🚨 Common Issues & Solutions

### Issue: "Send to Atlas" not in share sheet
**Solution**: Shortcuts app → Find shortcut → Settings → "Use with Share Sheet" ON

### Issue: Network timeout errors
**Solution**: Check webhook service: `ps aux | grep webhook`

### Issue: macOS Services not working
**Solution**: System Preferences → Extensions → Sharing → Enable "Send to Atlas"

### Issue: iCloud sync delay
**Solution**: Force sync by opening Shortcuts on both devices

### Issue: JSON format errors
**Solution**: Verify webhook expects: `{"url": "...", "title": "...", "source": "..."}`

## 📋 Final Verification Command

```bash
# Test webhook endpoint
curl -X POST https://atlas.khamel.com/email-webhook \
  -H "Content-Type: application/json" \
  -d '{"url": "https://test-final-verification.com", "source": "final_test"}'

# Check database entry
sqlite3 /home/ubuntu/dev/atlas/data/simple_atlas.db \
  "SELECT * FROM urls WHERE url LIKE '%test-final-verification%';"
```

## 🎯 Success Definition

**PASS Criteria**:
- iOS shortcut works in 8+ different apps
- macOS integration works in 5+ different contexts
- 100% success rate during 20 test submissions
- Average response time under 2 seconds
- Zero data loss or corruption

**READY FOR PRODUCTION**: All checkboxes ✅ and success criteria met