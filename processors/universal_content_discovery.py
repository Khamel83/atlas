#!/usr/bin/env python3
"""
Universal Content Discovery System
Extends Atlas transcript discovery to work with ALL content types:
- Podcast transcripts
- Articles and news
- General web content
- Academic papers
- Documentation

Uses FREE search methods (DuckDuckGo) + existing article source strategies
"""

import json
import requests
import time
import re
from typing import Dict, Any, Optional, List
from pathlib import Path
import sys
import os

# Add current directory to path
sys.path.append('.')

class UniversalContentDiscovery:
    """Universal content discovery system for all content types"""

    def __init__(self):
        self.discovery_matrix = {}
        self.article_sources = {}
        self.search_engines = {
            'duckduckgo': self._search_duckduckgo,
            'brave': self._search_brave,
            'bing': self._search_bing
        }
        self.content_strategies = {}

        # Load configurations
        self._load_configurations()

    def _load_configurations(self):
        """Load all available content sources and configurations"""
        try:
            # Load discovery matrix
            if os.path.exists('config/discovered_transcript_sources.json'):
                with open('config/discovered_transcript_sources.json', 'r') as f:
                    self.discovery_matrix = json.load(f)
                print(f"✅ Loaded discovery matrix with {len(self.discovery_matrix)} sources")

            # Load article sources
            if os.path.exists('config/article_sources.json'):
                with open('config/article_sources.json', 'r') as f:
                    article_config = json.load(f)
                    self.article_sources = {s['name']: s for s in article_config.get('sources', [])}
                print(f"✅ Loaded {len(self.article_sources)} article sources")

            # Load content strategies
            self._load_content_strategies()

        except Exception as e:
            print(f"❌ Configuration loading error: {e}")

    def _load_content_strategies(self):
        """Load content processing strategies"""
        try:
            # Import strategy classes
            from helpers.article_strategies import DirectFetchStrategy, PaywallBypassStrategy
            from helpers.article_strategies import ArchiveTodayStrategy, EnhancedWaybackMachineStrategy

            self.content_strategies = {
                'direct': DirectFetchStrategy(),
                'paywall_bypass': PaywallBypassStrategy(),
                'archive_today': ArchiveTodayStrategy(),
                'wayback_enhanced': EnhancedWaybackMachineStrategy()
            }
            print(f"✅ Loaded {len(self.content_strategies)} content strategies")
        except Exception as e:
            print(f"⚠️  Strategy loading limited: {e}")

    def discover_content(self, query: str, content_type: str = "general") -> List[Dict[str, Any]]:
        """
        Universal content discovery for any query and content type

        Args:
            query: Search query or content identifier
            content_type: Type of content (podcast, article, news, academic, general)

        Returns:
            List of discovered content items with metadata
        """
        print(f"🔍 Universal discovery for: {query} (type: {content_type})")

        results = []

        # Strategy 1: Check known sources first
        known_results = self._check_known_sources(query, content_type)
        results.extend(known_results)

        # Strategy 2: Use free web search
        if len(results) < 5:  # Only search if we don't have enough results
            search_results = self._search_web(query, content_type)
            results.extend(search_results)

        # Strategy 3: Use article strategies for web content
        if len(results) < 10:  # Try article strategies for more results
            strategy_results = self._try_article_strategies(query)
            results.extend(strategy_results)

        # Deduplicate and prioritize results
        unique_results = self._deduplicate_results(results)

        print(f"🎯 Found {len(unique_results)} unique content sources")
        return unique_results[:10]  # Return top 10 results

    def _check_known_sources(self, query: str, content_type: str) -> List[Dict[str, Any]]:
        """Check known sources for content"""
        results = []

        if content_type == "podcast":
            # Check podcast-specific sources
            for podcast_name, podcast_data in self.discovery_matrix.items():
                if podcast_name.lower() in query.lower():
                    sources = podcast_data.get('sources', [])
                    for source in sources:
                        if source.get('status') == 'working':
                            results.append({
                                'url': source['url'],
                                'source_type': 'known_podcast',
                                'confidence': 0.9,
                                'content_type': 'transcript',
                                'method': 'direct_fetch'
                            })

        elif content_type in ["article", "news", "general"]:
            # Check article sources
            for source_name, source_config in self.article_sources.items():
                if source_config.get('enabled', False):
                    results.append({
                        'source_name': source_name,
                        'source_type': 'article_strategy',
                        'confidence': source_config.get('success_rate', 0.5),
                        'content_type': content_type,
                        'method': source_name,
                        'config': source_config
                    })

        return results

    def _search_web(self, query: str, content_type: str) -> List[Dict[str, Any]]:
        """Search web using free search engines"""
        results = []

        # Build enhanced search query based on content type
        search_query = self._build_search_query(query, content_type)

        # Try DuckDuckGo first (free)
        try:
            duckduckgo_results = self._search_duckduckgo(search_query)
            results.extend(duckduckgo_results)
        except Exception as e:
            print(f"⚠️  DuckDuckGo search failed: {e}")

        # Try Brave Search as backup (free)
        if len(results) < 3:
            try:
                brave_results = self._search_brave(search_query)
                results.extend(brave_results)
            except Exception as e:
                print(f"⚠️  Brave search failed: {e}")

        return results

    def _build_search_query(self, query: str, content_type: str) -> str:
        """Build optimized search query based on content type"""
        base_query = query

        # Add content-type specific terms
        if content_type == "podcast":
            base_query += ' transcript transcript full text'
        elif content_type == "article":
            base_query += ' article full text complete'
        elif content_type == "news":
            base_query += ' news article full coverage'
        elif content_type == "academic":
            base_query += ' pdf research paper'
        else:  # general
            base_query += ' content full text'

        # Add site-specific terms for better results
        if content_type in ["article", "news"]:
            base_query += ' (site:medium.com OR site:substack.com OR site:theatlantic.com)'

        return base_query

    def _search_duckduckgo(self, query: str) -> List[Dict[str, Any]]:
        """Search using DuckDuckGo (free API)"""
        results = []
        try:
            search_url = f"https://api.duckduckgo.com/?q={query}&format=json&no_html=1&skip_disambig=1"
            response = requests.get(search_url, timeout=10)

            if response.status_code == 200:
                data = response.json()
                if 'Results' in data:
                    for result in data['Results'][:5]:  # Top 5 results
                        results.append({
                            'url': result.get('FirstURL', ''),
                            'title': result.get('Text', ''),
                            'source_type': 'web_search',
                            'engine': 'duckduckgo',
                            'confidence': 0.7,
                            'content_type': 'general',
                            'method': 'direct_fetch'
                        })
        except Exception as e:
            print(f"❌ DuckDuckGo search error: {e}")

        return results

    def _search_brave(self, query: str) -> List[Dict[str, Any]]:
        """Search using Brave Search (free API)"""
        results = []
        try:
            search_url = f"https://search.brave.com/search?q={query}&source=web"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            response = requests.get(search_url, headers=headers, timeout=10)

            if response.status_code == 200:
                # Parse HTML results (simplified)
                content = response.text
                # Extract URLs from HTML content
                url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
                urls = re.findall(url_pattern, content)

                for url in urls[:5]:  # Top 5 URLs
                    if len(url) > 20:  # Reasonable URL length
                        results.append({
                            'url': url,
                            'source_type': 'web_search',
                            'engine': 'brave',
                            'confidence': 0.6,
                            'content_type': 'general',
                            'method': 'direct_fetch'
                        })
        except Exception as e:
            print(f"❌ Brave search error: {e}")

        return results

    def _search_bing(self, query: str) -> List[Dict[str, Any]]:
        """Search using Bing (fallback)"""
        results = []
        try:
            search_url = f"https://www.bing.com/search?q={query}&setlang=en"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            response = requests.get(search_url, headers=headers, timeout=10)

            if response.status_code == 200:
                content = response.text
                # Extract URLs from Bing results
                url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
                urls = re.findall(url_pattern, content)

                for url in urls[:5]:
                    if len(url) > 20 and 'bing.com' not in url:
                        results.append({
                            'url': url,
                            'source_type': 'web_search',
                            'engine': 'bing',
                            'confidence': 0.5,
                            'content_type': 'general',
                            'method': 'direct_fetch'
                        })
        except Exception as e:
            print(f"❌ Bing search error: {e}")

        return results

    def _try_article_strategies(self, query: str) -> List[Dict[str, Any]]:
        """Try article processing strategies for content discovery"""
        results = []

        # Generate potential URLs from query
        potential_urls = self._generate_urls_from_query(query)

        for url in potential_urls[:3]:  # Try top 3
            for strategy_name, strategy in self.content_strategies.items():
                try:
                    # Test if strategy can handle this URL
                    if hasattr(strategy, 'can_handle') and strategy.can_handle(url):
                        results.append({
                            'url': url,
                            'source_type': 'article_strategy',
                            'strategy': strategy_name,
                            'confidence': 0.8,
                            'content_type': 'article',
                            'method': strategy_name
                        })
                except Exception as e:
                    continue

        return results

    def _generate_urls_from_query(self, query: str) -> List[str]:
        """Generate potential URLs from search query"""
        urls = []

        # Clean query for URL generation
        clean_query = re.sub(r'[^\w\s-]', '', query).strip()
        words = clean_query.split()

        if len(words) >= 2:
            # Generate common URL patterns
            slug = '-'.join(words[:3]).lower()

            # Common article platforms
            platforms = [
                f'https://medium.com/@user/{slug}',
                f'https://{slug}.substack.com',
                f'https://www.example.com/articles/{slug}',
                f'https://en.wikipedia.org/wiki/{words[0]}'
            ]

            urls.extend(platforms)

        return urls

    def _deduplicate_results(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate results and prioritize by confidence"""
        seen_urls = set()
        unique_results = []

        # Sort by confidence first
        results.sort(key=lambda x: x.get('confidence', 0), reverse=True)

        for result in results:
            url = result.get('url', '')
            if url and url not in seen_urls:
                seen_urls.add(url)
                unique_results.append(result)

        return unique_results

    def extract_content(self, content_item: Dict[str, Any]) -> Optional[str]:
        """Extract content from a discovered content item"""
        method = content_item.get('method', 'direct_fetch')
        url = content_item.get('url', '')

        try:
            if method == 'direct_fetch':
                return self._direct_fetch(url)
            elif method in self.content_strategies:
                strategy = self.content_strategies[method]
                if hasattr(strategy, 'extract'):
                    return strategy.extract(url)
            elif method.startswith('known_'):
                return self._direct_fetch(url)
        except Exception as e:
            print(f"❌ Content extraction failed for {method}: {e}")

        return None

    def _direct_fetch(self, url: str) -> Optional[str]:
        """Direct content extraction from URL"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }

            response = requests.get(url, headers=headers, timeout=15)

            if response.status_code == 200:
                content = response.text

                # Basic content extraction
                # Remove scripts, styles, and navigation
                content = re.sub(r'<script[^>]*>.*?</script>', '', content, flags=re.DOTALL)
                content = re.sub(r'<style[^>]*>.*?</style>', '', content, flags=re.DOTALL)
                content = re.sub(r'<nav[^>]*>.*?</nav>', '', content, flags=re.DOTALL)
                content = re.sub(r'<header[^>]*>.*?</header>', '', content, flags=re.DOTALL)
                content = re.sub(r'<footer[^>]*>.*?</footer>', '', content, flags=re.DOTALL)

                # Extract text content
                text = re.sub(r'<[^>]+>', ' ', content)
                text = re.sub(r'\s+', ' ', text).strip()

                if len(text) > 500:  # Reasonable content length
                    return text[:50000]  # Limit size

        except Exception as e:
            print(f"❌ Direct fetch failed for {url}: {e}")

        return None

    def get_system_stats(self) -> Dict[str, Any]:
        """Get system statistics and capabilities"""
        return {
            'discovery_matrix_size': len(self.discovery_matrix),
            'article_sources_count': len(self.article_sources),
            'content_strategies_count': len(self.content_strategies),
            'search_engines': list(self.search_engines.keys()),
            'enabled_article_sources': [
                name for name, config in self.article_sources.items()
                if config.get('enabled', False)
            ],
            'system_capabilities': {
                'podcast_transcripts': bool(self.discovery_matrix),
                'article_extraction': bool(self.article_sources),
                'web_search': bool(self.search_engines),
                'paywall_bypass': any('paywall' in name for name in self.article_sources.keys()),
                'archive_access': any('archive' in name for name in self.article_sources.keys())
            }
        }


def main():
    """Test the universal content discovery system"""
    print("🚀 Universal Content Discovery System Test")
    print("=" * 50)

    # Initialize the system
    discovery = UniversalContentDiscovery()

    # Show system stats
    stats = discovery.get_system_stats()
    print(f"📊 System Statistics:")
    print(f"   • Discovery Matrix: {stats['discovery_matrix_size']} sources")
    print(f"   • Article Sources: {stats['article_sources_count']} sources")
    print(f"   • Content Strategies: {stats['content_strategies_count']} strategies")
    print(f"   • Search Engines: {', '.join(stats['search_engines'])}")
    print(f"   • Enabled Sources: {len(stats['enabled_article_sources'])}")

    # Test different content types
    test_queries = [
        ("Accidental Tech Podcast ATP episode", "podcast"),
        ("artificial intelligence breakthrough 2025", "article"),
        ("climate change news coverage", "news"),
        ("machine learning research paper", "academic"),
        ("web development best practices", "general")
    ]

    print(f"\n🧪 Testing Universal Discovery:")
    print("-" * 50)

    for query, content_type in test_queries:
        print(f"\n🔍 Query: {query}")
        print(f"📂 Type: {content_type}")

        try:
            results = discovery.discover_content(query, content_type)
            print(f"✅ Found {len(results)} sources")

            # Show top results
            for i, result in enumerate(results[:3]):
                confidence = result.get('confidence', 0)
                method = result.get('method', 'unknown')
                url = result.get('url', 'N/A')[:50] + '...' if len(result.get('url', '')) > 50 else result.get('url', 'N/A')
                print(f"   {i+1}. {method} (confidence: {confidence:.1f})")
                print(f"      URL: {url}")

        except Exception as e:
            print(f"❌ Test failed: {e}")

    print(f"\n🎯 Universal Content Discovery System Test Complete")
    print(f"💰 COST: $0.00 (uses only free search APIs)")


if __name__ == "__main__":
    main()