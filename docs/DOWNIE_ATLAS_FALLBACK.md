# Downie → Atlas Fallback Integration

## 🎯 Proposed Flow

```
Links → Hyperduck → Downie (tries video first)
                                    ↓
                              [if not video] → Atlas (handles everything else)
```

## 🧪 Downie Research Findings

### Downie Capabilities:
- **Primary**: Video downloads from 1000+ sites
- **Secondary**: Can detect if URL contains video content
- **Limitation**: Discards non-video URLs
- **Potential**: May have scripting/automation features

### Integration Options:

## 🍎 Option 1: Hyperduck Smart Routing

**If Hyperduck can detect content type**:
```
Video URLs → Downie
Non-video URLs → Atlas
```

## 🍎 Option 2: Downie Fallback Script

**If Downie supports AppleScript**:
```applescript
-- Downie fails to process URL → send to Atlas
on process_url(url)
    try
        -- Try Downie processing
        tell application "Downie" to process url
    on error
        -- Downie failed, send to Atlas
        set atlasURL to "http://atlas.khamel.com:35555/ingest?url=" & url
        do shell script "curl '" & atlasURL & "'"
    end try
end process_url
```

## 🍎 Option 3: Hyperduck Parallel Processing

**Send URLs to both systems**:
```
Links → Hyperduck → Downie (parallel) ──┐
                                          └─→ Both get the URL, each handles what they can
Links → Hyperduck → Atlas (parallel) ────┘
```

## 🧪 Recommended Solution: Option 3

**Why this is best**:
- ✅ No dependency on Downie's scripting capabilities
- ✅ Atlas gets everything (never loses URLs)
- ✅ Downie gets videos it can handle
- ✅ Both systems work independently
- ✅ Zero coordination needed

## 🎮 Implementation

**Configure Hyperduck to send URLs to both**:
1. **Downie**: Your existing setup (videos)
2. **Atlas**: `http://atlas.khamel.com:35555/ingest?url={url}`

**Result**:
- Downie downloads videos it can handle
- Atlas stores everything with smart content detection
- No URLs get lost in the process

## 📊 Benefits

- **Redundancy**: Both systems get all URLs
- **Specialization**: Each handles what it does best
- **Future-proof**: If Downie adds support for more sites, it just works
- **Analytics**: Atlas tracks what Downie misses

**Bottom Line**: Let both systems have everything - they'll figure out what to do with it!