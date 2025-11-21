#!/usr/bin/env python3
"""
Direct Transcript Processor
Gets actual transcript outcomes without RelayQ dependency
"""

import sqlite3
import requests
import re
import time
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from urllib.parse import urljoin, urlparse
import feedparser
from bs4 import BeautifulSoup

class DirectTranscriptProcessor:
    def __init__(self):
        self.db_path = "podcast_processing.db"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })

    def get_pending_episodes(self, limit: int = 20) -> List[Dict]:
        """Get pending episodes prioritized by podcast priority"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row

        query = """
        SELECT e.*, p.name as podcast_name, p.rss_feed
        FROM episodes e
        JOIN podcasts p ON e.podcast_id = p.id
        WHERE e.processing_status = 'pending'
        AND e.transcript_found = FALSE
        ORDER BY p.priority DESC, e.published_date DESC
        LIMIT ?
        """

        cursor = conn.execute(query, (limit,))
        episodes = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return episodes

    def find_transcript_official_site(self, episode: Dict) -> Optional[Tuple[str, str]]:
        """Try to find transcript from episode link"""
        if not episode.get('link'):
            return None

        try:
            response = self.session.get(episode['link'], timeout=10)
            soup = BeautifulSoup(response.content, 'html.parser')

            # Look for transcript links
            transcript_links = soup.find_all('a', href=re.compile(r'transcript', re.I))
            if transcript_links:
                transcript_url = urljoin(episode['link'], transcript_links[0]['href'])
                return self.extract_transcript_from_url(transcript_url)

            # Check if the page itself contains a transcript
            text = soup.get_text(strip=True)
            if len(text) > 5000:  # Reasonable transcript length
                return (episode['link'], text)

        except Exception as e:
            print(f"    Official site failed: {e}")

        return None

    def find_transcript_tapesearch(self, episode: Dict) -> Optional[Tuple[str, str]]:
        """Search TapeSearch for transcripts"""
        search_query = f"{episode['podcast_name']} {episode['title'][:50]}"

        try:
            search_url = f"https://www.tapesearch.io/search?q={requests.utils.quote(search_query)}"
            response = self.session.get(search_url, timeout=10)
            soup = BeautifulSoup(response.content, 'html.parser')

            # Look for result links
            result_links = soup.find_all('a', href=re.compile(r'/transcript/'))
            if result_links:
                transcript_url = f"https://www.tapesearch.io{result_links[0]['href']}"
                return self.extract_transcript_from_url(transcript_url)

        except Exception as e:
            print(f"    TapeSearch failed: {e}")

        return None

    def find_transcript_rss(self, episode: Dict) -> Optional[Tuple[str, str]]:
        """Try to find transcript in RSS feed content"""
        if not episode.get('rss_feed'):
            return None

        try:
            feed = feedparser.parse(episode['rss_feed'])
            for entry in feed.entries:
                if episode['title'] in entry.title:
                    # Check content for transcript
                    if hasattr(entry, 'content') and entry.content:
                        for content in entry.content:
                            if 'transcript' in content.value.lower() or len(content.value) > 10000:
                                return ('RSS Feed', content.value)
                    # Check summary for transcript
                    if hasattr(entry, 'summary') and len(entry.summary) > 10000:
                        return ('RSS Feed', entry.summary)
                    break

        except Exception as e:
            print(f"    RSS search failed: {e}")

        return None

    def extract_transcript_from_url(self, url: str) -> Optional[Tuple[str, str]]:
        """Extract transcript content from a URL"""
        try:
            response = self.session.get(url, timeout=15)
            soup = BeautifulSoup(response.content, 'html.parser')

            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()

            # Try to find transcript content
            content_selectors = [
                '.transcript-content', '.transcript', '#transcript',
                '[data-testid="transcript"]', '.entry-content', '.post-content',
                'article', 'main'
            ]

            for selector in content_selectors:
                content = soup.select_one(selector)
                if content:
                    text = content.get_text(strip=True)
                    if len(text) > 5000:  # Reasonable transcript length
                        return (url, text)

            # Fallback to all text content
            text = soup.get_text(strip=True)
            if len(text) > 5000:
                return (url, text)

        except Exception as e:
            print(f"    Extraction failed for {url}: {e}")

        return None

    def process_episode(self, episode: Dict) -> Dict:
        """Process a single episode for transcript discovery"""
        print(f"Processing: {episode['podcast_name']} - {episode['title'][:50]}...")

        # Try different sources in order
        sources = [
            self.find_transcript_rss,
            self.find_transcript_official_site,
            self.find_transcript_tapesearch
        ]

        for source_func in sources:
            try:
                result = source_func(episode)
                if result:
                    source_url, transcript_text = result
                    return {
                        'success': True,
                        'episode_id': episode['id'],
                        'source': source_func.__name__,
                        'source_url': source_url,
                        'transcript_text': transcript_text,
                        'character_count': len(transcript_text)
                    }
            except Exception as e:
                print(f"    {source_func.__name__} error: {e}")
                continue

        return {
            'success': False,
            'episode_id': episode['id'],
            'error': 'No transcript found in any source'
        }

    def save_transcript_to_db(self, result: Dict):
        """Save transcript result to database"""
        conn = sqlite3.connect(self.db_path)

        if result['success']:
            conn.execute("""
                UPDATE episodes SET
                    transcript_found = TRUE,
                    transcript_source = ?,
                    transcript_url = ?,
                    transcript_text = ?,
                    processing_status = 'completed',
                    last_attempt = ?
                WHERE id = ?
            """, (result['source'], result['source_url'], result['transcript_text'],
                  datetime.now().isoformat(), result['episode_id']))
        else:
            conn.execute("""
                UPDATE episodes SET
                    processing_attempts = processing_attempts + 1,
                    last_attempt = ?,
                    error_message = ?
                WHERE id = ?
            """, (datetime.now().isoformat(), result['error'], result['episode_id']))

        conn.commit()
        conn.close()

    def process_batch(self, limit: int = 20) -> Dict:
        """Process a batch of episodes"""
        print(f"\n🎯 DIRECT TRANSCRIPT PROCESSOR")
        print("=" * 50)
        print(f"Processing {limit} episodes for actual transcripts")
        print()

        episodes = self.get_pending_episodes(limit)
        if not episodes:
            print("✅ No pending episodes found!")
            return {'total': 0, 'successful': 0, 'failed': 0}

        results = []
        successful = 0
        failed = 0

        for i, episode in enumerate(episodes, 1):
            print(f"[{i}/{len(episodes)}] ", end="")

            result = self.process_episode(episode)
            self.save_transcript_to_db(result)
            results.append(result)

            if result['success']:
                successful += 1
                print(f"    ✅ FOUND: {result['character_count']:,} characters from {result['source']}")
            else:
                failed += 1
                print(f"    ❌ Failed: {result['error']}")

            # Small delay between requests
            time.sleep(1)

        print()
        print(f"📊 Batch Results:")
        print(f"   ✅ Successful: {successful}")
        print(f"   ❌ Failed: {failed}")
        print(f"   📝 Total Characters Found: {sum(r.get('character_count', 0) for r in results):,}")

        return {'total': len(episodes), 'successful': successful, 'failed': failed}

if __name__ == "__main__":
    processor = DirectTranscriptProcessor()

    # Process first batch of 10 to test
    result = processor.process_batch(10)

    if result['successful'] > 0:
        print(f"\n🚀 SUCCESS! Found {result['successful']} transcripts. Scaling up...")
        # Continue processing in larger batches until we get 100
        total_found = result['successful']
        while total_found < 100:
            batch_result = processor.process_batch(20)
            total_found += batch_result['successful']
            if batch_result['successful'] == 0:
                print("⚠️ No transcripts found in last batch, continuing anyway...")
            print(f"📈 Progress: {total_found}/100 transcripts found")
    else:
        print("\n⚠️ No transcripts found in test batch. May need to adjust strategy.")