# 🔍 Add Search to Existing OOS Projects

If you already have OOS working in another project, here's how to add the new search functionality:

## 📂 Copy These Files to Your Existing OOS

Copy these 3 files from this OOS directory to your existing project:

```bash
# Copy search engine
cp src/free_search_alternatives.py /path/to/your/project/src/

# Copy safety manager
cp src/perplexity_usage_manager.py /path/to/your/project/src/

# Copy usage data directory
cp -r data /path/to/your/project/
```

## 🔧 Add Search Command to Your CLI

If your existing OOS has a CLI, add this to your command processor:

```python
# In your existing oos_cli.py or main CLI file:

elif command.startswith('search'):
    return await self.handle_search_command(command)

# Add this method:
async def handle_search_command(self, command: str) -> int:
    """Handle search commands with automatic free + paid search integration"""
    query = command.replace('search', '').strip().strip('"').strip("'")

    if not query:
        print("Usage: oos search \"your query\"")
        return 0

    print(f"🔍 Searching for: {query}")

    try:
        from free_search_alternatives import search_free
        results = await search_free(query, max_results=8)

        if results:
            print(f"✅ Found {len(results)} results")
            for i, result in enumerate(results, 1):
                print(f"{i}. {result.title}")
                print(f"   [{result.source}] {result.snippet[:100]}...")
                if result.url:
                    print(f"   🔗 {result.url}")
                print()

            # Show cost if Perplexity was used
            perplexity_used = any(r.source == 'Perplexity' for r in results)
            if perplexity_used:
                from perplexity_usage_manager import usage_manager
                summary = usage_manager.get_usage_summary()
                print(f"💰 Monthly Perplexity usage: ${summary['total_cost']:.2f} / ${summary['monthly_limit']:.2f}")
            else:
                print("💰 Search cost: $0.00 (used free sources)")
        else:
            print("❌ No results found")

    except Exception as e:
        print(f"Search failed: {e}")
        return 1

    return 0
```

## 🎯 Quick Integration

If you want the **minimal** integration, just import the search function directly:

```python
# In any Python file in your existing OOS:
import sys
from pathlib import Path

# Add this OOS search to your path
sys.path.insert(0, '/home/ubuntu/dev/oos/src')

# Import and use
from free_search_alternatives import search_free
import asyncio

async def quick_search(query):
    results = await search_free(query, max_results=5)
    for result in results:
        print(f"• {result.title} - {result.url}")

# Use it:
asyncio.run(quick_search("python tutorials"))
```

## 🔑 Environment Setup

Make sure your existing project has the Perplexity API key:

```bash
# In your existing project's .env:
echo "PERPLEXITY_API_KEY=pplx-your-key-here" >> .env
```

## 🚀 One-Line Integration

**Simplest approach** - just copy the search module and call it:

```bash
# From your existing OOS project directory:
cp /home/ubuntu/dev/oos/src/free_search_alternatives.py ./

# Then in any Python file:
from free_search_alternatives import search_free
```

That's it! Your existing OOS now has the same bulletproof search system.

## 🎯 What You Get

- ✅ Same 4 free search engines (DuckDuckGo, Wikipedia, GitHub, Stack Overflow)
- ✅ Same Perplexity Pro integration with safety controls
- ✅ Same cost tracking and permission prompts
- ✅ Same $4.50 safety stop
- ✅ Works with your existing OOS architecture

**Bottom line: Copy 1-3 files, add 1 command handler, done!** 🎉