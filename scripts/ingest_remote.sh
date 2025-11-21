#!/bin/bash

# Atlas v3 Remote Ingestion Script
# For Mac Mini connecting to atlas.khamel.com
# Usage: ./ingest_remote.sh "URL"

URL="$1"
ATLAS_SERVER="http://atlas.khamel.com:35555"

if [ -z "$URL" ]; then
    echo "Usage: $0 \"URL\""
    echo "Example: $0 \"https://www.youtube.com/watch?v=jNQXAC9IVRw\""
    exit 1
fi

echo "🌐 Connecting to Atlas v3 at $ATLAS_SERVER..."
echo "📥 Ingesting: $URL"

# Check if Atlas v3 server is reachable
if ! curl -s --connect-timeout 5 "$ATLAS_SERVER/" > /dev/null 2>&1; then
    echo "❌ ERROR: Cannot connect to Atlas v3 server at $ATLAS_SERVER"
    echo "Please ensure:"
    echo "  1. Atlas v3 is running on the server"
    echo "  2. Port 35555 is open on the firewall"
    echo "  3. DNS resolution works for atlas.khamel.com"
    exit 1
fi

# Ingest the URL
response=$(curl -s --connect-timeout 30 "$ATLAS_SERVER/ingest?url=$(echo "$URL" | sed 's/+/%2B/g' | sed 's/&/%26/g' | sed 's/=/%3D/g')")

# Parse and display result
echo "$response" | python3 -c "
import json
import sys
try:
    data = json.load(sys.stdin)
    if data.get('status') == 'success':
        print(f'✅ SUCCESS: {data[\"url\"]}')
        print(f'   Type: {data[\"content_type\"]}')
        print(f'   ID: {data[\"unique_id\"]}')
        if data.get('video_success'):
            title = data[\"video_info\"].get(\"title\", \"Unknown\")
            uploader = data[\"video_info\"].get(\"uploader\", \"Unknown\")
            print(f'   📹 Video: {title}')
            print(f'   🎬 Uploader: {uploader}')
        print(f'   🗄️  Stored on: atlas.khamel.com')
    else:
        print(f'❌ FAILED: {data.get(\"message\", \"Unknown error\")}')
except Exception as e:
    print(f'❌ Failed to parse response: {e}')
    print('Raw response:', sys.stdin.read())
"

echo ""