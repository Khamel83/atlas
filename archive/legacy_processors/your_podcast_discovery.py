#!/usr/bin/env python3
"""
YOUR Podcast Discovery System
Focuses on YOUR specific podcasts with targeted strategies
"""

import json
import requests
import re
from typing import Dict, Any, List, Optional
from pathlib import Path
import sys
import os

sys.path.append('.')

class YourPodcastDiscovery:
    """Discovery system for YOUR specific podcasts"""

    def __init__(self):
        # Load YOUR podcasts
        with open('config/your_priority_podcasts.json', 'r') as f:
            self.your_podcasts = json.load(f)

        # Load YOUR sources
        with open('config/your_podcast_sources.json', 'r') as f:
            self.your_sources = json.load(f)

        # Universal strategies for any content
        self.strategies = {
            'direct_fetch': self._direct_fetch,
            'show_notes': self._extract_show_notes,
            'transcript_page': self._find_transcript_page,
            'content_extraction': self._extract_article_content
        }

        print(f"✅ Loaded YOUR podcast discovery system")
        print(f"   • {len(self.your_podcasts)} priority podcasts")
        print(f"   • {len(self.your_sources)} with dedicated sources")

    def discover_transcript(self, podcast_name: str, episode_title: str, episode_url: str) -> Optional[str]:
        """Discover transcript for YOUR podcast episode"""

        print(f"🔍 Discovering transcript for: {podcast_name} - {episode_title}")

        # Strategy 1: Use your dedicated sources
        if podcast_name in self.your_sources:
            sources = self.your_sources[podcast_name]
            print(f"   📋 Using {len(sources)} dedicated sources for {podcast_name}")

            for source in sources:
                try:
                    content = self._try_source(source, podcast_name, episode_title)
                    if content and len(content) > 1000:
                        print(f"   ✅ Found transcript via {source['method']}: {len(content)} chars")
                        return content[:50000]
                except Exception as e:
                    print(f"   ❌ Source {source['method']} failed: {e}")
                    continue

        # Strategy 2: Universal discovery for any content
        print(f"   🌐 Using universal discovery strategies...")

        # Try direct episode URL
        try:
            content = self._direct_fetch(episode_url)
            if content and len(content) > 1000:
                print(f"   ✅ Found transcript via direct fetch: {len(content)} chars")
                return content[:50000]
        except Exception as e:
            print(f"   ❌ Direct fetch failed: {e}")

        # Strategy 3: Enhanced content extraction
        try:
            content = self._extract_enhanced_content(podcast_name, episode_title)
            if content and len(content) > 1000:
                print(f"   ✅ Found transcript via enhanced extraction: {len(content)} chars")
                return content[:50000]
        except Exception as e:
            print(f"   ❌ Enhanced extraction failed: {e}")

        print(f"   ❌ No transcript found for {podcast_name} - {episode_title}")
        return None

    def _try_source(self, source: Dict, podcast_name: str, episode_title: str) -> Optional[str]:
        """Try a specific source strategy"""
        method = source.get('method', 'direct_fetch')
        url = source.get('url', '')

        if method in self.strategies:
            # For site-based strategies, enhance URL
            if method == 'direct_site':
                enhanced_url = self._build_episode_url(url, podcast_name, episode_title)
                return self.strategies['direct_fetch'](enhanced_url)
            else:
                return self.strategies[method](url, podcast_name, episode_title)

        return None

    def _direct_fetch(self, url: str, podcast_name: str = "", episode_title: str = "") -> Optional[str]:
        """Direct content fetch with transcript-specific extraction"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            response = requests.get(url, headers=headers, timeout=15)

            if response.status_code == 200:
                content = response.text

                # Look for actual transcript content first
                transcript_patterns = [
                    r'<div[^>]*class="[^"]*transcript-container[^"]*"[^>]*>(.*?)</div>',
                    r'<div[^>]*class="[^"]*rich-text-block-6[^"]*"[^>]*>(.*?)</div>',
                    r'<div[^>]*class="[^"]*transcript[^"]*"[^>]*>(.*?)</div>',
                    r'<section[^>]*class="[^"]*transcript[^"]*"[^>]*>(.*?)</section>',
                    r'<div[^>]*id="[^"]*transcript[^"]*"[^>]*>(.*?)</div>',
                    r'<article[^>]*class="[^"]*transcript[^"]*"[^>]*>(.*?)</article>',
                    # NPR-specific patterns
                    r'<div[^>]*data-metrics=\'[^"]*transcript[^"]*\'[^>]*>(.*?)</div>',
                ]

                for pattern in transcript_patterns:
                    matches = re.findall(pattern, content, re.DOTALL | re.IGNORECASE)
                    if matches:
                        # Clean the transcript content
                        transcript_text = re.sub(r'<script[^>]*>.*?</script>', '', matches[0], flags=re.DOTALL)
                        transcript_text = re.sub(r'<style[^>]*>.*?</style>', '', transcript_text, flags=re.DOTALL)
                        transcript_text = re.sub(r'<[^>]+>', ' ', transcript_text)
                        transcript_text = re.sub(r'\s+', ' ', transcript_text).strip()

                        # Only return if it's substantial content (real transcripts)
                        if len(transcript_text) > 10000:  # At least 10k characters for real transcripts
                            print(f"   ✅ Found transcript content: {len(transcript_text)} chars")
                            return transcript_text

                # If no transcript found, look for main content but require it to be substantial
                content_patterns = [
                    r'<article[^>]*>(.*?)</article>',
                    r'<main[^>]*>(.*?)</main>',
                    r'<div[^>]*class="[^"]*content[^"]*"[^>]*>(.*?)</div>',
                    r'<div[^>]*class="[^"]*story[^"]*"[^>]*>(.*?)</div>',
                ]

                for pattern in content_patterns:
                    matches = re.findall(pattern, content, re.DOTALL)
                    if matches:
                        # Clean the content
                        clean_content = re.sub(r'<script[^>]*>.*?</script>', '', matches[0], flags=re.DOTALL)
                        clean_content = re.sub(r'<style[^>]*>.*?</style>', '', clean_content, flags=re.DOTALL)
                        clean_content = re.sub(r'<nav[^>]*>.*?</nav>', '', clean_content, flags=re.DOTALL)
                        clean_content = re.sub(r'<header[^>]*>.*?</header>', '', clean_content, flags=re.DOTALL)
                        clean_content = re.sub(r'<footer[^>]*>.*?</footer>', '', clean_content, flags=re.DOTALL)
                        clean_content = re.sub(r'<[^>]+>', ' ', clean_content)
                        clean_content = re.sub(r'\s+', ' ', clean_content).strip()

                        # Only return if it's substantial (likely to be real content)
                        if len(clean_content) > 10000:
                            print(f"   ✅ Found substantial content: {len(clean_content)} chars")
                            return clean_content
                        else:
                            print(f"   ❌ Content too short ({len(clean_content)} chars) - likely metadata")

        except Exception as e:
            print(f"   ❌ Fetch error: {e}")

        return None

    def _extract_show_notes(self, url: str, podcast_name: str, episode_title: str) -> Optional[str]:
        """Extract from show notes"""
        content = self._direct_fetch(url)
        if content:
            # Look for show notes sections
            patterns = [
                r'<div[^>]*class="[^"]*show-notes[^"]*"[^>]*>(.*?)</div>',
                r'<div[^>]*class="[^"]*episode-notes[^"]*"[^>]*>(.*?)</div>',
                r'<section[^>]*class="[^"]*notes[^"]*"[^>]*>(.*?)</section>'
            ]

            for pattern in patterns:
                matches = re.findall(pattern, content, re.DOTALL)
                if matches:
                    # Clean and combine
                    notes_text = re.sub(r'<[^>]+>', ' ', ' '.join(matches))
                    notes_text = re.sub(r'\s+', ' ', notes_text).strip()
                    if len(notes_text) > 500:
                        return notes_text

        return None

    def _find_transcript_page(self, url: str, podcast_name: str, episode_title: str) -> Optional[str]:
        """Find transcript-specific pages"""
        # Try common transcript URL patterns
        base_url = url.rstrip('/')

        transcript_urls = [
            f"{base_url}/transcript",
            f"{base_url}/transcripts",
            f"{base_url.replace('/episodes', '/transcripts')}",
            f"{base_url}-transcript"
        ]

        for t_url in transcript_urls:
            content = self._direct_fetch(t_url)
            if content and len(content) > 1000:
                return content

        return None

    def _extract_article_content(self, url: str, podcast_name: str = "", episode_title: str = "") -> Optional[str]:
        """Extract article-style content"""
        content = self._direct_fetch(url)
        if content:
            # Look for article content
            patterns = [
                r'<article[^>]*>(.*?)</article>',
                r'<main[^>]*>(.*?)</main>',
                r'<div[^>]*class="[^"]*content[^"]*"[^>]*>(.*?)</div>'
            ]

            for pattern in patterns:
                matches = re.findall(pattern, content, re.DOTALL)
                if matches:
                    article_text = re.sub(r'<[^>]+>', ' ', ' '.join(matches))
                    article_text = re.sub(r'\s+', ' ', article_text).strip()
                    if len(article_text) > 1000:
                        return article_text

        return None

    def _extract_enhanced_content(self, podcast_name: str, episode_title: str) -> Optional[str]:
        """Enhanced content extraction using multiple strategies"""
        # Build search query
        search_query = f'"{podcast_name}" "{episode_title}" transcript'

        # Try known transcript sites
        transcript_sites = [
            f"https://slate.com/news-and-politics/{podcast_name.lower().replace(' ', '-')}",
            f"https://www.npr.org/sections/{podcast_name.lower().replace(' ', '-')}",
            f"https://www.vox.com/{podcast_name.lower().replace(' ', '-')}"
        ]

        for site in transcript_sites:
            content = self._direct_fetch(site)
            if content and len(content) > 1000:
                # Look for episode mentions
                if episode_title.lower() in content.lower():
                    return content

        return None

    def _build_episode_url(self, base_url: str, podcast_name: str, episode_title: str) -> str:
        """Build episode URL from base URL"""
        # Clean episode title for URL
        clean_title = re.sub(r'[^\w\s-]', '', episode_title).strip()
        clean_title = re.sub(r'\s+', '-', clean_title).lower()

        # Common URL patterns
        patterns = [
            f"{base_url}/{clean_title}",
            f"{base_url}/episode/{clean_title}",
            f"{base_url}/episodes/{clean_title}",
            f"{base_url}/show/{clean_title}"
        ]

        return patterns[0]  # Return first pattern

    def get_stats(self) -> Dict[str, Any]:
        """Get your podcast discovery stats"""
        return {
            "your_podcasts_count": len(self.your_podcasts),
            "your_sources_count": len(self.your_sources),
            "top_podcasts": sorted(self.your_podcasts, key=lambda x: x['count'], reverse=True)[:10],
            "strategies_available": list(self.strategies.keys()),
            "system_ready": True
        }


def main():
    """Test YOUR podcast discovery system"""
    print("🎯 YOUR PODCAST DISCOVERY SYSTEM")
    print("=" * 50)

    discovery = YourPodcastDiscovery()
    stats = discovery.get_stats()

    print(f"📊 System Stats:")
    print(f"   • Your Podcasts: {stats['your_podcasts_count']}")
    print(f"   • With Sources: {stats['your_sources_count']}")
    print(f"   • Strategies: {', '.join(stats['strategies_available'])}")
    print(f"   • System Ready: {stats['system_ready']}")

    print(f"\n🎯 Your Top 10 Podcasts:")
    for i, podcast in enumerate(stats['top_podcasts'], 1):
        print(f"   {i}. {podcast['name']} (Priority: {podcast['count']})")


if __name__ == "__main__":
    main()