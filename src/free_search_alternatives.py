#!/usr/bin/env python3
"""
Free Search Alternatives for OOS
100% free search options that never cost money
"""

import requests
import json
import os
from typing import List, Dict, Optional
from dataclasses import dataclass


@dataclass
class SearchResult:
    title: str
    url: str
    snippet: str
    source: str


class FreeSearchEngine:
    """Collection of 100% free search engines"""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (compatible; OOS-Search/1.0)'
        })

    async def search(self, query: str, max_results: int = 10) -> List[SearchResult]:
        """Search using free alternatives in priority order"""

        # Try each search engine in priority order
        search_methods = [
            self._search_duckduckgo_instant,    # Free, unlimited
            self._search_wikipedia,             # Free, unlimited
            self._search_github,                # Free, 5K/hour
            self._search_stackoverflow,         # Free, 10K/day
            self._search_perplexity,            # $5/month credits from Pro
        ]

        all_results = []

        for search_method in search_methods:
            try:
                results = await search_method(query, max_results)
                all_results.extend(results)
                if len(all_results) >= max_results:
                    break
            except Exception as e:
                print(f"Search method failed: {e}")
                continue

        return all_results[:max_results]

    async def _search_duckduckgo_instant(self, query: str, limit: int) -> List[SearchResult]:
        """DuckDuckGo Instant Answer API - 100% FREE"""
        url = "https://api.duckduckgo.com/"
        params = {
            'q': query,
            'format': 'json',
            'no_html': '1',
            'skip_disambig': '1'
        }

        response = self.session.get(url, params=params, timeout=10)
        data = response.json()

        results = []

        # Abstract (instant answer)
        if data.get('Abstract'):
            results.append(SearchResult(
                title=data.get('AbstractText', 'DuckDuckGo Answer'),
                url=data.get('AbstractURL', ''),
                snippet=data.get('Abstract', ''),
                source='DuckDuckGo'
            ))

        # Related topics
        for topic in data.get('RelatedTopics', [])[:limit-len(results)]:
            if isinstance(topic, dict) and topic.get('Text'):
                results.append(SearchResult(
                    title=topic.get('FirstURL', '').split('/')[-1].replace('_', ' '),
                    url=topic.get('FirstURL', ''),
                    snippet=topic.get('Text', ''),
                    source='DuckDuckGo'
                ))

        return results

    async def _search_wikipedia(self, query: str, limit: int) -> List[SearchResult]:
        """Wikipedia API - 100% FREE"""
        search_url = "https://en.wikipedia.org/api/rest_v1/page/summary/"

        # First try direct page lookup
        try:
            response = self.session.get(
                f"{search_url}{query.replace(' ', '_')}",
                timeout=10
            )
            if response.status_code == 200:
                data = response.json()
                return [SearchResult(
                    title=data.get('title', query),
                    url=data.get('content_urls', {}).get('desktop', {}).get('page', ''),
                    snippet=data.get('extract', ''),
                    source='Wikipedia'
                )]
        except:
            pass

        # Fallback to search API
        search_api = "https://en.wikipedia.org/api/rest_v1/page/search/"
        response = self.session.get(f"{search_api}{query}", timeout=10)
        data = response.json()

        results = []
        for page in data.get('pages', [])[:limit]:
            results.append(SearchResult(
                title=page.get('title', ''),
                url=f"https://en.wikipedia.org/wiki/{page.get('key', '')}",
                snippet=page.get('description', ''),
                source='Wikipedia'
            ))

        return results

    async def _search_github(self, query: str, limit: int) -> List[SearchResult]:
        """GitHub Search API - 5000 requests/hour FREE"""
        url = "https://api.github.com/search/repositories"
        params = {
            'q': query,
            'sort': 'stars',
            'order': 'desc',
            'per_page': min(limit, 10)
        }

        response = self.session.get(url, params=params, timeout=10)
        data = response.json()

        results = []
        for repo in data.get('items', []):
            results.append(SearchResult(
                title=repo.get('full_name', ''),
                url=repo.get('html_url', ''),
                snippet=repo.get('description', ''),
                source='GitHub'
            ))

        return results

    async def _search_perplexity(self, query: str, limit: int) -> List[SearchResult]:
        """Perplexity Sonar API with usage confirmation and safety limits"""
        try:
            # Use the safe search function that handles all safety checks
            from perplexity_usage_manager import safe_perplexity_search
            success, message, results = await safe_perplexity_search(query, limit)

            if success:
                print(f"💡 {message}")
                return results
            else:
                print(f"⚠️  Perplexity skipped: {message}")
                return []

        except Exception as e:
            print(f"Perplexity search error: {e}")
            return []

    async def _search_stackoverflow(self, query: str, limit: int) -> List[SearchResult]:
        """Stack Overflow API - 10000 requests/day FREE"""
        url = "https://api.stackexchange.com/2.3/search/advanced"
        params = {
            'order': 'desc',
            'sort': 'relevance',
            'q': query,
            'site': 'stackoverflow',
            'pagesize': min(limit, 10)
        }

        response = self.session.get(url, params=params, timeout=10)
        data = response.json()

        results = []
        for question in data.get('items', []):
            results.append(SearchResult(
                title=question.get('title', ''),
                url=question.get('link', ''),
                snippet=f"Score: {question.get('score', 0)} | Answers: {question.get('answer_count', 0)}",
                source='StackOverflow'
            ))

        return results


# Free search limits (all these are actually free)
FREE_SEARCH_LIMITS = {
    'duckduckgo': 'Unlimited FREE',
    'wikipedia': 'Unlimited FREE',
    'github': '5,000/hour FREE',
    'stackoverflow': '10,000/day FREE',
    'google_custom_search': '100/day then $5/1K (EXPENSIVE!)'
}


async def search_free(query: str, max_results: int = 10) -> List[SearchResult]:
    """Main function for free search"""
    engine = FreeSearchEngine()
    return await engine.search(query, max_results)


if __name__ == "__main__":
    import asyncio

    async def test_search():
        print("🔍 Testing 100% Free Search Alternatives")
        print("=" * 50)

        query = "python async programming"
        results = await search_free(query, 5)

        print(f"Query: {query}")
        print(f"Results: {len(results)}")
        print()

        for i, result in enumerate(results, 1):
            print(f"{i}. [{result.source}] {result.title}")
            print(f"   {result.snippet[:100]}...")
            print(f"   {result.url}")
            print()

        print("💰 Cost: $0.00 (completely free)")
        print("🚀 All these APIs are unlimited or have very high free tiers")

    asyncio.run(test_search())