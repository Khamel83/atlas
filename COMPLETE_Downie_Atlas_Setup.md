# Complete Setup: Phone → Hyperduck → Downie → Atlas

## 🎯 Understanding the Flow

**Current Flow**:
```
Phone → Hyperduck → Mac Mini → Downie (tries video) → [FAILS] → Nothing happens
```

**Desired Flow**:
```
Phone → Hyperduck → Mac Mini → Downie (tries video) → [FAILS] → Atlas
```

## 🍎 Setup Instructions (Mac Mini)

### Step 1: Atlas Server is Running
✅ Atlas v3 is running on `atlas.khamel.com:35555`

### Step 2: Create Downie Monitor Script

Save this script on your Mac Mini as `~/downie-atlas-monitor.sh`:

```bash
#!/bin/bash
ATLAS_SERVER="http://atlas.khamel.com:35555"
DOWNIE_LOG="$HOME/Library/Logs/Downie.log"

send_to_atlas() {
    local url="$1"
    echo "📤 Sending to Atlas: $url"

    response=$(curl -s --connect-timeout 10 "$ATLAS_SERVER/ingest?url=$(echo "$url" | sed 's/+/%2B/g' | sed 's/&/%26/g')")

    if echo "$response" | grep -q '"status":"success"'; then
        echo "✅ Success: $url sent to Atlas"
    else
        echo "❌ Failed: Could not send $url to Atlas"
    fi
}

# Monitor Downie failures
while true; do
    recent_failures=$(tail -n 20 "$DOWNIE_LOG" 2>/dev/null | grep -i "failed\|error\|unsupported" | grep -o 'https\?://[^"]*' | sort -u)

    if [ -n "$recent_failures" ]; then
        echo "🔍 Found Downie failures:"
        echo "$recent_failures" | while read -r url; do
            if [ -n "$url" ]; then
                send_to_atlas "$url"
            fi
        done
    fi

    sleep 10  # Check every 10 seconds
done
```

### Step 3: Make Script Executable
```bash
chmod +x ~/downie-atlas-monitor.sh
```

### Step 4: Start the Monitor
```bash
~/downie-atlas-monitor.sh &
```

### Step 5: Test the Complete Flow
1. Send a URL from your phone through Hyperduck
2. Wait for Downie to try (and fail) to process it
3. Check that the URL appears in Atlas

## 🧪 Alternative: Use AppleScript

If the shell script doesn't work, create this AppleScript:

```applescript
on sendURLToAtlas(url)
    set atlasServer to "http://atlas.khamel.com:35555"
    set atlasURL to atlasServer & "/ingest?url=" & url

    try
        do shell script "curl -s '" & atlasURL & "'"
        log "Sent to Atlas: " & url
    on error errMsg
        log "Failed to send to Atlas: " & errMsg
    end try
end sendURLToAtlas
```

## 🎮 What Happens Now

1. **Phone → Hyperduck**: Your existing setup
2. **Hyperduck → Downie**: Your existing setup
3. **Downie tries video**: Downloads videos it can handle
4. **Downie fails**: For non-video URLs, Downie logs an error
5. **Monitor script**: Detects Downie failures
6. **Automatic**: Failed URLs are sent to Atlas
7. **Atlas processes**: Stores everything with smart content detection

## ✅ Benefits

- **Zero changes** to Hyperduck or Downie
- **Automatic**: No manual intervention needed
- **Complete**: No URLs get lost
- **Smart**: Atlas handles what Downie can't

## 🧪 Test Connection

From your Mac Mini, test:
```bash
curl "http://atlas.khamel.com:35555/ingest?url=https://example.com"
```

If you get a success response, Atlas is ready to receive Downie's failures!