#!/bin/bash

# Crawl4AI Monitor Script
# Run weekly to check for updates and changes

echo "🔍 Crawl4AI Weekly Monitor - $(date)"
echo "=================================="

# Check latest release
echo "📦 Latest Release:"
curl -s "https://api.github.com/repos/unclecode/crawl4ai/releases" | jq -r '.[0] | "\(.tag_name) - \(.published_at) - \(.name)"'

echo ""
echo "📋 Release Notes:"
curl -s "https://api.github.com/repos/unclecode/crawl4ai/releases" | jq -r '.[0].body' | head -20

echo ""
echo "🐛 Recent Issues (Last 7 Days)"
curl -s "https://api.github.com/repos/unclecode/crawl4ai/issues?state=open&since=$(date -d '7 days ago' -Iseconds)" | jq -r '.[] | "- \(.title) (\(.created_at))"'

echo ""
echo "📚 Current PyPI Version:"
pip show crawl4ai | grep Version

echo ""
echo "🧪 Quick Test:"
python3 -c "
import asyncio
from crawl4ai import AsyncWebCrawler

async def test():
    try:
        async with AsyncWebCrawler() as crawler:
            result = await crawler.arun('https://httpbin.org/html')
            print(f'✅ Crawl4AI working: {result.success}')
            if hasattr(result, 'markdown'):
                print(f'✅ New API: markdown available')
            if hasattr(result, 'cleaned_text'):
                print(f'✅ Old API: cleaned_text available')
    except Exception as e:
        print(f'❌ Error: {e}')

asyncio.run(test())
"

echo ""
echo "📊 Monitor Complete: $(date)"