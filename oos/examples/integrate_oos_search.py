#!/usr/bin/env python3
"""
Example: How to integrate OOS search into your existing Python project
"""

import sys
import os
from pathlib import Path

# Add OOS to your Python path
oos_path = Path(__file__).parent.parent / 'src'
sys.path.insert(0, str(oos_path))

# Import OOS search
from free_search_alternatives import search_free
from perplexity_usage_manager import safe_perplexity_search
import asyncio


class MyProjectSearchHelper:
    """Add smart search to your existing project"""

    def __init__(self):
        self.search_history = []

    async def smart_search(self, query: str, max_results: int = 5):
        """
        Search with automatic free + paid fallback
        Returns: list of search results
        """
        print(f"🔍 Searching for: {query}")

        # Try free search first
        results = await search_free(query, max_results)

        if len(results) >= 3:
            print(f"✅ Found {len(results)} results from free sources")
            self.search_history.append({
                'query': query,
                'results': len(results),
                'cost': 0.00,
                'source': 'free'
            })
            return results

        # If free search insufficient, try Perplexity with permission
        print(f"⚠️  Only found {len(results)} results from free sources")
        success, message, perplexity_results = await safe_perplexity_search(query, max_results)

        if success:
            all_results = results + perplexity_results
            self.search_history.append({
                'query': query,
                'results': len(all_results),
                'cost': 0.01,  # Estimated
                'source': 'free+perplexity'
            })
            return all_results
        else:
            print(f"💡 {message}")
            self.search_history.append({
                'query': query,
                'results': len(results),
                'cost': 0.00,
                'source': 'free_only'
            })
            return results

    async def search_for_code_examples(self, language: str, topic: str):
        """Search specifically for code examples"""
        query = f"{language} {topic} code examples github"
        return await self.smart_search(query)

    async def search_for_documentation(self, technology: str):
        """Search for documentation"""
        query = f"{technology} documentation tutorial guide"
        return await self.smart_search(query)

    async def search_for_error_solution(self, error_message: str):
        """Search for error solutions"""
        query = f"how to fix {error_message} stackoverflow"
        return await self.smart_search(query)

    def get_search_stats(self):
        """Get search usage statistics"""
        total_searches = len(self.search_history)
        total_cost = sum(s['cost'] for s in self.search_history)
        free_searches = len([s for s in self.search_history if s['cost'] == 0])

        return {
            'total_searches': total_searches,
            'free_searches': free_searches,
            'paid_searches': total_searches - free_searches,
            'total_cost': total_cost,
            'average_results': sum(s['results'] for s in self.search_history) / max(total_searches, 1)
        }


# Example usage in your existing project:
async def example_usage():
    """Example of how to use OOS search in your project"""

    # Create search helper
    search = MyProjectSearchHelper()

    # Search for code examples
    print("=== Searching for React hooks examples ===")
    results = await search.search_for_code_examples("React", "useEffect hooks")
    for i, result in enumerate(results[:3], 1):
        print(f"{i}. {result.title}")
        print(f"   {result.url}")
        print()

    # Search for documentation
    print("=== Searching for Docker documentation ===")
    results = await search.search_for_documentation("Docker Compose")
    for i, result in enumerate(results[:3], 1):
        print(f"{i}. {result.title}")
        print(f"   {result.url}")
        print()

    # Search for error solutions
    print("=== Searching for error solution ===")
    results = await search.search_for_error_solution("ImportError: No module named requests")
    for i, result in enumerate(results[:3], 1):
        print(f"{i}. {result.title}")
        print(f"   {result.url}")
        print()

    # Show usage stats
    stats = search.get_search_stats()
    print("=== Search Statistics ===")
    print(f"Total searches: {stats['total_searches']}")
    print(f"Free searches: {stats['free_searches']}")
    print(f"Paid searches: {stats['paid_searches']}")
    print(f"Total cost: ${stats['total_cost']:.2f}")
    print(f"Average results per search: {stats['average_results']:.1f}")


if __name__ == "__main__":
    asyncio.run(example_usage())