#!/bin/bash

# Atlas v3 Background Ingestion Script
# Usage: ./ingest_background.sh "URL"

URL="$1"

if [ -z "$URL" ]; then
    echo "Usage: $0 \"URL\""
    exit 1
fi

# Check if Atlas v3 server is running
if ! curl -s "http://localhost:35555/" > /dev/null 2>&1; then
    echo "Atlas v3 server not running. Starting it..."
    python3 atlas_v3_dual_ingestion.py &
    sleep 3
fi

# Ingest the URL
echo "Ingesting: $URL"
response=$(curl -s "http://localhost:35555/ingest?url=$(echo "$URL" | sed 's/+/%2B/g' | sed 's/&/%26/g' | sed 's/=/%3D/g')")

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
            print(f'   📹 Video detected: {data[\"video_info\"].get(\"title\", \"Unknown\")}')
    else:
        print(f'❌ FAILED: {data.get(\"message\", \"Unknown error\")}')
except:
    print('❌ Failed to parse response')
"

echo ""