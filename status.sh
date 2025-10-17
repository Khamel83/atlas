#!/bin/bash
# Atlas Status Check Script

echo "📊 Atlas Status Check"
echo "===================="

# Check if Atlas is running
if curl -s https://atlas.khamel.com/health > /dev/null 2>&1; then
    echo "✅ Atlas is RUNNING and accessible at https://atlas.khamel.com"

    # Get basic stats
    echo "📈 System Statistics:"
    curl -s https://atlas.khamel.com/api/health | jq -r '. | "   Total Content: \(.total_content) items\n   Status: \(.status)\n   Timestamp: \(.timestamp)"'
else
    echo "❌ Atlas is NOT running or not accessible"
    echo "💡 Run './start_atlas.sh' to start Atlas"
fi

# Check local process
if pgrep -f "web_interface.py" > /dev/null; then
    echo "✅ Web interface process is running locally"
else
    echo "⚠️  No local web interface process found"
fi

echo ""
echo "📱 Quick Access:"
echo "   Web Interface: https://atlas.khamel.com"
echo "   API Documentation: https://atlas.khamel.com/docs"
echo "   Health Check: https://atlas.khamel.com/api/health"