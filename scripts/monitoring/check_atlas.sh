#!/bin/bash
# Simple Atlas v2 Monitor - Run this to check if processing is working

echo "🔍 Atlas v2 Status Check - $(date)"
echo "=================================="

# Check if container is running
if ! docker ps | grep atlas-v2 > /dev/null; then
    echo "❌ Atlas v2 container is NOT running"
    echo "🚀 Starting Atlas v2..."
    docker start atlas-v2
    sleep 10
fi

# Check health
echo "📊 Health Status:"
curl -s http://localhost:8000/health | python3 -m json.tool || echo "❌ Health check failed"

# Check queue size
echo ""
echo "📋 Queue Status:"
sqlite3 /home/ubuntu/dev/atlas/atlas_v2/data/atlas_v2.db "
SELECT
    status,
    COUNT(*) as count
FROM processing_queue
GROUP BY status
ORDER BY count DESC;"

# Check recent activity
echo ""
echo "⏰ Recent Processing Activity:"
sqlite3 /home/ubuntu/dev/atlas/atlas_v2/data/atlas_v2.db "
SELECT
    content_type,
    COUNT(*) as count
FROM processed_content
WHERE created_at > datetime('now', '-1 hour')
GROUP BY content_type;"

echo ""
echo "🎯 If no items are being processed, run: python3 test_atlas_processing.py"
