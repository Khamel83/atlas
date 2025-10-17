#!/usr/bin/env python3
"""
Community Scraper for Atlas
Searches Reddit, Discord, and other community platforms for transcripts
"""

import requests
import json
import re
import time
from typing import List, Dict, Optional, Set
from urllib.parse import urljoin, quote
from bs4 import BeautifulSoup
import logging

logger = logging.getLogger(__name__)

class CommunityScraper:
    """Search community platforms for podcast transcripts and discussions"""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })

        # Reddit configuration (using public API, no auth required for search)
        self.reddit_base_url = "https://www.reddit.com"
        self.reddit_search_url = "https://www.reddit.com/search.json"

    def search_reddit_transcripts(self, podcast_name: str, episode_title: str) -> List[Dict]:
        """Search Reddit for transcript discussions and shared transcripts"""
        try:
            # Build search queries
            search_queries = [
                f"{podcast_name} {episode_title} transcript",
                f"{podcast_name} transcript discussion",
                f"{podcast_name} {episode_title} summary",
                f"{podcast_name} episode transcript"
            ]

            all_results = []

            for query in search_queries:
                try:
                    results = self._reddit_search(query)
                    all_results.extend(results)
                    time.sleep(1)  # Rate limiting
                except Exception as e:
                    logger.warning(f"Reddit search failed for query '{query}': {e}")
                    continue

            # Remove duplicates and sort by score
            unique_results = {}
            for result in all_results:
                key = result['url']
                if key not in unique_results or result['score'] > unique_results[key]['score']:
                    unique_results[key] = result

            # Sort by relevance score
            sorted_results = sorted(unique_results.values(), key=lambda x: x['score'], reverse=True)
            return sorted_results[:10]  # Return top 10 results

        except Exception as e:
            logger.error(f"Reddit transcript search failed: {e}")
            return []

    def _reddit_search(self, query: str) -> List[Dict]:
        """Perform Reddit search (simplified approach)"""
        try:
            # Use web scraping since Reddit API requires auth
            search_url = f"{self.reddit_base_url}/search/"
            params = {
                'q': query,
                'restrict_sr': '1',
                'sort': 'relevance',
                't': 'all'
            }

            response = self.session.get(search_url, params=params, timeout=10)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')

            results = []
            posts = soup.find_all('div', {'data-testid': 'post-container'})

            for post in posts[:5]:  # Limit to top 5 results per query
                try:
                    title_elem = post.find('h3', {'data-testid': 'post-title'})
                    if not title_elem:
                        continue

                    title = title_elem.get_text(strip=True)
                    link_elem = post.find('a', {'data-testid': 'post-title'})
                    url = link_elem.get('href') if link_elem else ''

                    if url.startswith('/'):
                        url = f"{self.reddit_base_url}{url}"

                    # Get score
                    score_elem = post.find('div', {'data-testid': 'post-score'})
                    score = int(score_elem.get_text(strip=True)) if score_elem else 0

                    # Get subreddit
                    subreddit_elem = post.find('a', {'data-testid': 'subreddit-name'})
                    subreddit = subreddit_elem.get_text(strip=True) if subreddit_elem else ''

                    # Calculate relevance
                    relevance_score = self._calculate_reddit_relevance(
                        podcast_name, episode_title, title, subreddit, score
                    )

                    if relevance_score > 0.2:  # Minimum relevance threshold
                        results.append({
                            'url': url,
                            'title': title,
                            'subreddit': subreddit,
                            'score': score,
                            'relevance_score': relevance_score,
                            'source': 'reddit'
                        })

                except Exception as e:
                    logger.warning(f"Failed to parse Reddit post: {e}")
                    continue

            return results

        except Exception as e:
            logger.error(f"Reddit search failed: {e}")
            return []

    def _calculate_reddit_relevance(self, podcast_name: str, episode_title: str,
                                   post_title: str, subreddit: str, post_score: int) -> float:
        """Calculate relevance score for Reddit posts"""
        score = 0.0

        title_lower = post_title.lower()
        podcast_lower = podcast_name.lower()
        episode_lower = episode_title.lower()

        # Direct podcast name match
        if podcast_lower in title_lower:
            score += 0.3

        # Episode title terms
        episode_terms = re.findall(r'\b\w{4,}\b', episode_lower)
        for term in episode_terms:
            if term in title_lower:
                score += 0.1

        # Transcript indicators
        transcript_keywords = ['transcript', 'summary', 'notes', 'recap', 'breakdown', 'discussion']
        for keyword in transcript_keywords:
            if keyword in title_lower:
                score += 0.2

        # Podcast-related subreddits
        podcast_subreddits = ['podcasts', 'podcast', 'transcript', 'summarized']
        if subreddit.lower() in podcast_subreddits:
            score += 0.2

        # Post score (popularity)
        if post_score > 50:
            score += 0.1
        elif post_score > 10:
            score += 0.05

        return min(score, 1.0)

    def get_reddit_post_content(self, post_url: str) -> Optional[str]:
        """Extract content from Reddit post"""
        try:
            response = self.session.get(post_url, timeout=10)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')

            # Try different selectors for post content
            content_selectors = [
                '[data-testid="post-content"]',
                '.post-content',
                '.md',
                '.usertext-body'
            ]

            for selector in content_selectors:
                content_elem = soup.select_one(selector)
                if content_elem:
                    content = content_elem.get_text(separator=' ', strip=True)
                    if len(content) > 200:  # Minimum length
                        return content

            # Fallback: get all text from post
            post_container = soup.find('div', {'data-testid': 'post-container'})
            if post_container:
                text = post_container.get_text(separator=' ', strip=True)
                # Remove navigation and UI elements
                lines = [line.strip() for line in text.split('\n') if len(line.strip()) > 10]
                content = ' '.join(lines)
                if len(content) > 200:
                    return content

            return None

        except Exception as e:
            logger.error(f"Failed to get Reddit post content from {post_url}: {e}")
            return None

    def search_discord_communities(self, podcast_name: str, episode_title: str) -> List[Dict]:
        """Search for Discord communities and public transcript shares"""
        try:
            # Note: Discord scraping is limited without API access
            # This is a simplified approach using public search

            search_query = f"{podcast_name} {episode_title} discord transcript"

            # Use Google search to find Discord communities
            google_search_url = "https://www.googleapis.com/customsearch/v1"
            api_key = os.getenv("GOOGLE_SEARCH_API_KEY")
            engine_id = os.getenv("GOOGLE_SEARCH_ENGINE_ID")

            if not api_key or not engine_id:
                logger.warning("Google API credentials not found for Discord search")
                return []

            params = {
                'key': api_key,
                'cx': engine_id,
                'q': f"{search_query} site:discord.com OR site:discord.gg",
                'num': 5
            }

            response = self.session.get(google_search_url, params=params)
            response.raise_for_status()

            data = response.json()
            results = []

            for item in data.get('items', []):
                results.append({
                    'url': item['link'],
                    'title': item['title'],
                    'snippet': item.get('snippet', ''),
                    'source': 'discord',
                    'relevance_score': 0.5  # Default score for Discord results
                })

            return results

        except Exception as e:
            logger.error(f"Discord search failed: {e}")
            return []

    def search_transcript_forums(self, podcast_name: str, episode_title: str) -> List[Dict]:
        """Search transcript-specific forums and communities"""
        try:
            # Known transcript communities and forums
            forum_sites = [
                "transcript.google.com",
                "otter.ai",
                "rev.com",
                "happy.scribe",
                "sonix.ai"
            ]

            search_query = f"{podcast_name} {episode_title} transcript"

            results = []
            for site in forum_sites:
                try:
                    google_search_url = "https://www.googleapis.com/customsearch/v1"
                    api_key = os.getenv("GOOGLE_SEARCH_API_KEY")
                    engine_id = os.getenv("GOOGLE_SEARCH_ENGINE_ID")

                    if not api_key or not engine_id:
                        continue

                    params = {
                        'key': api_key,
                        'cx': engine_id,
                        'q': f"{search_query} site:{site}",
                        'num': 3
                    }

                    response = self.session.get(google_search_url, params=params)
                    response.raise_for_status()

                    data = response.json()

                    for item in data.get('items', []):
                        results.append({
                            'url': item['link'],
                            'title': item['title'],
                            'snippet': item.get('snippet', ''),
                            'source': f'transcript_forum:{site}',
                            'relevance_score': 0.6
                        })

                    time.sleep(0.5)  # Rate limiting

                except Exception as e:
                    logger.warning(f"Forum search failed for {site}: {e}")
                    continue

            return results

        except Exception as e:
            logger.error(f"Transcript forum search failed: {e}")
            return []

    def find_community_transcript(self, podcast_name: str, episode_title: str) -> Optional[Dict]:
        """Main method to find transcript via community sources"""
        try:
            logger.info(f"Searching community sources for transcript: {podcast_name} - {episode_title}")

            all_results = []

            # Strategy 1: Reddit search
            logger.info("Searching Reddit...")
            reddit_results = self.search_reddit_transcripts(podcast_name, episode_title)
            all_results.extend(reddit_results)

            # Strategy 2: Discord communities
            logger.info("Searching Discord communities...")
            discord_results = self.search_discord_communities(podcast_name, episode_title)
            all_results.extend(discord_results)

            # Strategy 3: Transcript forums
            logger.info("Searching transcript forums...")
            forum_results = self.search_transcript_forums(podcast_name, episode_title)
            all_results.extend(forum_results)

            # Sort all results by relevance
            all_results.sort(key=lambda x: x['relevance_score'], reverse=True)

            # Try to get content from top results
            for result in all_results[:5]:
                logger.info(f"Trying community source: {result['source']} - {result['title']}")

                content = None
                if result['source'] == 'reddit':
                    content = self.get_reddit_post_content(result['url'])
                elif result['source'].startswith('transcript_forum'):
                    # Try to get content from transcript sites
                    try:
                        response = self.session.get(result['url'], timeout=10)
                        if response.status_code == 200:
                            soup = BeautifulSoup(response.content, 'html.parser')
                            content = soup.get_text(separator=' ', strip=True)
                    except Exception:
                        continue

                if content and len(content) > 500:
                    logger.info(f"Found transcript via community source: {result['source']}")
                    return {
                        'transcript': content,
                        'source': result['source'],
                        'source_url': result['url'],
                        'source_title': result['title'],
                        'relevance_score': result['relevance_score']
                    }

            logger.info("No transcripts found via community sources")
            return None

        except Exception as e:
            logger.error(f"Community transcript search failed: {e}")
            return None

# Test function
def test_community_scraper():
    """Test the community scraper"""
    scraper = CommunityScraper()

    # Test with a known podcast
    result = scraper.find_community_transcript(
        "Joe Rogan Experience",
        "Elon Musk",
        "https://www.joerogan.com/podcasts/elon-musk"
    )

    if result:
        print(f"✅ Found transcript via community: {len(result['transcript'])} chars")
        print(f"   Source: {result['source_url']}")
    else:
        print("❌ No transcript found via community sources")

if __name__ == "__main__":
    # Import required for test
    import os
    test_community_scraper()