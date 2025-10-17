# Vejla Webhook Configuration Update

## Atlas v2 Migration Complete ✅

Atlas v2 is now deployed and running at `https://atlas.khamel.com`

## Required Vejla Configuration Changes

### Webhook URL
**Old (Atlas v1):** `https://atlas.khamel.com/api/vejla` (or whatever Atlas v1 was using)
**New (Atlas v2):** `https://atlas.khamel.com/webhook/vejla`

### Authentication
**Method:** Bearer Token
**Header:** `Authorization: Bearer 20d935e30497cacba3937a35246735fac823d00bbc0629e4879fb467b78616e5`

### Payload Format
Atlas v2 expects this JSON structure:
```json
{
  "type": "podcast" | "newsletter" | "youtube" | "article",
  "url": "https://...",
  "source": "Hard Fork",
  "metadata": {
    "title": "...",
    "date": "2025-09-30",
    "duration_minutes": 45
  }
}
```

## Testing
You can test the webhook with curl:
```bash
curl -X POST https://atlas.khamel.com/webhook/vejla \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer 20d935e30497cacba3937a35246735fac823d00bbc0629e4879fb467b78616e5" \
  -d '{"type": "article", "url": "https://example.com/test", "source": "test", "metadata": {"title": "Test", "date": "2025-09-30"}}'
```

Expected response:
```json
{"status":"queued","content_id":"test-article-2025-09-30-test","estimated_processing_time_minutes":2}
```

## Atlas v2 Status
- **Health Check:** `https://atlas.khamel.com/health`
- **API Documentation:** `https://atlas.khamel.com/docs`
- **Database:** 2 test items successfully processed
- **Processing:** Event-driven pipeline active

## Migration Summary
✅ Atlas v2 deployed on OCI instance
✅ Event-driven webhook pipeline tested
✅ Domain switched from Atlas v1 to Atlas v2
⚠️ Vejla webhook configuration needs manual update on macOS

## Next Steps
1. Update Vejla macOS app with new webhook URL and auth token
2. Test content capture workflow end-to-end
3. Verify content processing pipeline