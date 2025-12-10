#!/usr/bin/env python3
"""
Failed Episode Retry System - Different strategies for failed episodes
"""

import sqlite3
import os
import requests
import time
from bs4 import BeautifulSoup

class FailedEpisodeRetry:
    def __init__(self):
        self.tavily_key = os.getenv('TAVILY_API_KEY')
        if not self.tavily_key:
            raise ValueError("TAVILY_API_KEY not found in environment")

    def get_failed_episodes(self, limit=50):
        """Get failed episodes for retry"""
        conn = sqlite3.connect("podcast_processing.db")
        cursor = conn.execute("""
            SELECT e.id, e.title, e.link, e.podcast_id, p.name as podcast_name
            FROM episodes e
            JOIN podcasts p ON e.podcast_id = p.id
            WHERE e.processing_status = 'failed'
            ORDER BY RANDOM()
            LIMIT ?
        """, (limit,))

        episodes = cursor.fetchall()
        conn.close()
        return episodes

    def reset_to_pending(self, episode_id):
        """Reset failed episode to pending for retry"""
        conn = sqlite3.connect("podcast_processing.db")
        conn.execute("""
            UPDATE episodes
            SET processing_status = 'pending',
                transcript_found = 0,
                transcript_text = NULL,
                transcript_source = NULL,
                quality_score = 5
            WHERE id = ?
        """, (episode_id,))
        conn.commit()
        conn.close()

    def simple_search_fallback(self, podcast_name, episode_title):
        """Simpler search for failed episodes"""

        # Very basic search queries
        simple_queries = [
            f'"{episode_title}" transcript',
            f'{podcast_name} "{episode_title}" transcript',
            f'{episode_title} full transcript'
        ]

        for query in simple_queries[:3]:  # Limit to 3 queries
            try:
                response = requests.post(
                    'https://api.tavily.com/search',
                    json={
                        'api_key': self.tavily_key,
                        'query': query,
                        'search_depth': 'basic',
                        'max_results': 5
                    },
                    timeout=10
                )

                if response.status_code == 200:
                    data = response.json()
                    results = data.get('results', [])

                    if results:
                        print(f"   🔍 Simple search found: {len(results)} results")
                        return results

            except Exception as e:
                print(f"   🚫 Simple search error: {e}")
                continue

            time.sleep(2)  # Rate limiting

        return []

    def try_direct_site_search(self, podcast_name, episode_title):
        """Search specific transcript sites directly"""

        # Common transcript sites to check
        transcript_sites = [
            ("Podscripts", f"https://podscripts.co/search?q={episode_title}"),
            ("Transcript.FM", f"https://transcript.fm/search?q={episode_title}"),
            ("Listen Notes", f"https://www.listennotes.com/search/?q={episode_title}"),
        ]

        results = []

        for site_name, search_url in transcript_sites:
            try:
                print(f"   🔍 Searching {site_name}...")

                response = requests.get(search_url, timeout=15, headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                })

                if response.status_code == 200:
                    soup = BeautifulSoup(response.content, 'html.parser')

                    # Look for links that might be transcripts
                    links = soup.find_all('a', href=True)

                    for link in links[:5]:  # Check first 5 links
                        href = link.get('href', '')
                        text = link.get_text().strip()

                        if episode_title.lower() in text.lower() or 'transcript' in text.lower():
                            results.append({
                                'title': text,
                                'url': href if href.startswith('http') else f"https://podscripts.co{href}",
                                'source': site_name
                            })
                            print(f"   ✅ Found potential transcript: {text[:50]}...")

            except Exception as e:
                print(f"   🚫 {site_name} search failed: {e}")
                continue

            time.sleep(1)  # Be respectful

        return results

    def extract_simple_content(self, url):
        """Simple content extraction"""
        try:
            response = requests.get(url, timeout=20, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            })

            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')

                # Remove unwanted elements
                for element in soup(['script', 'style', 'nav', 'footer', 'header', 'aside']):
                    element.decompose()

                text = soup.get_text()

                # Basic cleanup
                lines = [line.strip() for line in text.split('\n') if line.strip() and len(line.strip()) > 5]
                clean_text = '\n'.join(lines)

                if len(clean_text) > 2000:  # Reasonable length
                    return clean_text

        except Exception as e:
            print(f"   🚫 Simple extraction failed: {e}")

        return None

    def retry_failed_episode(self, episode):
        """Try different approaches for failed episode"""
        episode_id, title, link, podcast_id, podcast_name = episode

        print(f"\n🔄 Retrying failed episode: {title[:60]}...")

        # Strategy 1: Simpler search
        print("   Strategy 1: Simple search...")
        results = self.simple_search_fallback(podcast_name, title)

        if results:
            for result in results[:2]:  # Try top 2 results
                url = result.get('url', '')
                if url:
                    content = self.extract_simple_content(url)
                    if content and len(content) > 2000:
                        print(f"   ✅ SUCCESS: Simple approach found content ({len(content)} chars)")
                        self.save_transcript(episode_id, {
                            'content': content,
                            'source': f"retry_simple_{result.get('source', 'unknown')}"
                        })
                        return True

        # Strategy 2: Direct site search
        print("   Strategy 2: Direct site search...")
        results = self.try_direct_site_search(podcast_name, title)

        if results:
            for result in results[:2]:  # Try top 2 results
                url = result.get('url', '')
                if url:
                    content = self.extract_simple_content(url)
                    if content and len(content) > 2000:
                        print(f"   ✅ SUCCESS: Direct search found content ({len(content)} chars)")
                        self.save_transcript(episode_id, {
                            'content': content,
                            'source': f"retry_direct_{result.get('source', 'unknown')}"
                        })
                        return True

        print("   ❌ All retry strategies failed")
        return False

    def save_transcript(self, episode_id, transcript_info):
        """Save successful retry transcript"""
        conn = sqlite3.connect("podcast_processing.db")
        conn.execute("""
            UPDATE episodes
            SET processing_status = 'completed',
                transcript_found = 1,
                transcript_text = ?,
                transcript_source = ?,
                quality_score = 7
            WHERE id = ?
        """, (transcript_info['content'], transcript_info['source'], episode_id))
        conn.commit()
        conn.close()

    def process_failed_batch(self, batch_size=50):
        """Process a batch of failed episodes"""

        print("🔄 Failed Episode Retry System")
        print("=" * 50)
        print(f"📊 Processing {batch_size} failed episodes with different strategies")
        print()

        failed_episodes = self.get_failed_episodes(batch_size)

        if not failed_episodes:
            print("✅ No failed episodes to retry!")
            return

        print(f"📋 Found {len(failed_episodes)} failed episodes to retry")
        print()

        successful = 0
        still_failed = 0

        for episode in failed_episodes:
            if self.retry_failed_episode(episode):
                successful += 1
            else:
                still_failed += 1

            time.sleep(3)  # Rate limiting

        print(f"\n🏁 Retry batch complete!")
        print(f"📊 Results: {successful} recovered, {still_failed} still failed")
        print(f"📈 Recovery rate: {(successful/len(failed_episodes))*100:.1f}%")

if __name__ == "__main__":
    retry = FailedEpisodeRetry()
    retry.process_failed_batch(50)