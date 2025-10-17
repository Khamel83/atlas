# Velja → Atlas Connection Guide

## 🎯 Single Connection Point

**Atlas v3 Endpoint**: `http://atlas.khamel.com:35555/ingest?url={url}`

That's it! Send every URL to this endpoint and Atlas will figure out what to do with it.

## 🔧 Velja Configuration

### Method 1: HTTP POST/GET Request
```bash
# In your Velja service, make a request to:
curl "http://atlas.khamel.com:35555/ingest?url={url}"
```

### Method 2: If Velja supports webhooks
**Webhook URL**: `http://atlas.khamel.com:35555/ingest`
**Method**: GET or POST
**Parameter**: `url={your_url_here}`

### Method 3: If Velja has output configuration
**Output Format**: URL
**Destination**: `http://atlas.khamel.com:35555/ingest?url={url}`

## 📋 What Atlas Does Automatically

1. **Content Detection**: Identifies if URL is video, article, audio, social, etc.
2. **Video Processing**: Extracts metadata from YouTube, Vimeo, etc.
3. **Database Storage**: Stores every URL with unique ID
4. **Smart Filtering**: Keeps useful content, ignores inappropriate content
5. **No Failures**: Atlas always succeeds, even if video processing fails

## 🧪 Test Connection

From your Mac Mini, test with:
```bash
curl "http://atlas.khamel.com:35555/ingest?url=https://example.com"
```

Expected response:
```json
{
  "status": "success",
  "unique_id": "uuid-here",
  "url": "https://example.com",
  "content_type": "web",
  "atlas_success": true,
  "message": "URL ingested as web"
}
```

## ✅ What to Configure in Velja

**Just one setting**: Point Velja's output/webhook to:
```
http://atlas.khamel.com:35555/ingest?url={url}
```

Replace `{url}` with whatever variable Velja uses for the URL placeholder.

## 🎮 That's It!

- Velja sends URL → Atlas processes it
- Atlas extracts what it can, ignores what it can't
- Everything gets stored with unique ID
- No manual intervention needed

**Bottom line**: Configure Velja to send ALL URLs to `http://atlas.khamel.com:35555/ingest?url={url}` and Atlas handles the rest!