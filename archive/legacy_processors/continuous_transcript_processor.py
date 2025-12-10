#!/usr/bin/env python3
"""
Continuous Atlas Transcript Processor
Processes episodes in 100-episode chunks with full transcript content
"""

import sqlite3
import requests
import time
import json
import re
from bs4 import BeautifulSoup
from datetime import datetime
import os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ContinuousTranscriptProcessor:
    """Continuous processor with full transcripts and chunked processing"""

    def __init__(self):
        # Load environment variables
        self.tavily_key = os.getenv('TAVILY_API_KEY')
        self.youtube_key = os.getenv('YOUTUBE_API_KEY')
        self.firecrawl_key = os.getenv('FIRECRAWL_API_KEY')

        if not self.tavily_key:
            raise ValueError("TAVILY_API_KEY not found in environment")

        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        })

        # Track API usage
        self.tavily_calls = 0
        self.youtube_calls = 0
        self.firecrawl_calls = 0

    def log_api_usage(self):
        """Log current API usage"""
        print(f"\n📊 API Usage Summary:")
        print(f"   Tavily calls: {self.tavily_calls}")
        print(f"   YouTube calls: {self.youtube_calls}")
        print(f"   Firecrawl calls: {self.firecrawl_calls}")

    def search_transcript_sources(self, podcast_name, episode_title):
        """Search for transcripts using working APIs"""

        # Build search queries
        queries = [
            f'"{episode_title}" transcript {podcast_name}',
            f'"{episode_title}" transcript',
            f'{podcast_name} {episode_title} full transcript',
            f'site:{podcast_name.lower().replace(" ", "").replace("&", "").replace("!", "")} transcript'
        ]

        all_results = []

        # Try each query with Tavily
        for query in queries:
            print(f"🔍 Searching: {query[:80]}...")

            url = "https://api.tavily.com/search"
            payload = {
                "api_key": self.tavily_key,
                "query": query,
                "max_results": 5,
                "search_depth": "basic"
            }

            try:
                response = requests.post(url, json=payload, timeout=15)
                response.raise_for_status()
                data = response.json()
                self.tavily_calls += 1

                for result in data.get('results', []):
                    url = result['url']
                    title = result['title']
                    content = result.get('content', '')

                    all_results.append({
                        'url': url,
                        'title': title,
                        'content': content,
                        'query': query
                    })

                print(f"   📊 Found {len(data.get('results', []))} results")

            except Exception as e:
                print(f"   🚫 Error: {e}")

            time.sleep(1)  # Rate limiting

        # Try YouTube for video transcripts (with error handling)
        youtube_results = self.search_youtube_transcripts(podcast_name, episode_title)
        all_results.extend(youtube_results)

        return all_results

    def search_youtube_transcripts(self, podcast_name, episode_title):
        """Search YouTube for video transcripts with error handling"""

        print(f"🎥 Searching YouTube...")
        self.youtube_calls += 1

        search_url = "https://www.googleapis.com/youtube/v3/search"
        params = {
            'part': 'snippet',
            'q': f'{podcast_name} {episode_title}',
            'type': 'video',
            'maxResults': 3,
            'key': self.youtube_key
        }

        try:
            response = requests.get(search_url, params=params, timeout=15)
            response.raise_for_status()
            data = response.json()

            results = []
            for item in data.get('items', []):
                video_id = item['id']['videoId']
                title = item['snippet']['title']

                # Check if video has captions
                if self.has_youtube_captions(video_id):
                    results.append({
                        'url': f"https://www.youtube.com/watch?v={video_id}",
                        'title': title,
                        'content': f"YouTube video with captions available",
                        'video_id': video_id,
                        'query': 'youtube_search'
                    })

            print(f"   📊 Found {len(results)} videos with captions")
            return results

        except Exception as e:
            print(f"   🚫 YouTube error: {e}")
            return []

    def has_youtube_captions(self, video_id):
        """Check if YouTube video has captions"""

        try:
            captions_url = "https://www.googleapis.com/youtube/v3/captions"
            params = {
                'part': 'snippet',
                'videoId': video_id,
                'key': self.youtube_key
            }

            response = requests.get(captions_url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            return len(data.get('items', [])) > 0

        except Exception:
            return False

    def extract_transcript_content(self, url, title=""):
        """Extract transcript content from URL - FULL CONTENT"""

        print(f"🕷️  Extracting from: {title[:60]}...")

        # Try different extraction methods
        content = self.extract_with_requests(url)
        if not content and self.firecrawl_calls < 500:  # Limit Firecrawl usage
            content = self.extract_with_firecrawl(url)

        if content and self.looks_like_transcript(content):
            print(f"   ✅ SUCCESS: Extracted {len(content)} characters")
            return content  # NO LENGTH LIMIT - FULL TRANSCRIPT
        else:
            print(f"   ❌ No valid transcript content found")
            return None

    def extract_with_requests(self, url):
        """Extract content using regular requests"""

        try:
            response = self.session.get(url, timeout=20)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')

            # Remove unwanted elements
            for element in soup(['script', 'style', 'nav', 'footer', 'header', 'aside', 'iframe']):
                element.decompose()

            text = soup.get_text()

            # Clean up text
            lines = []
            for line in text.split('\n'):
                line = line.strip()
                if line and len(line) > 10:
                    lines.append(line)

            return ' '.join(lines)

        except Exception as e:
            logger.error(f"Requests extraction failed: {e}")
            return None

    def extract_with_firecrawl(self, url):
        """Extract content using Firecrawl API"""

        try:
            self.firecrawl_calls += 1
            firecrawl_url = "https://api.firecrawl.dev/v0/scrape"
            payload = {
                "url": url,
                "formats": ["markdown"],
                "onlyMainContent": True
            }
            headers = {
                "Authorization": f"Bearer {self.firecrawl_key}",
                "Content-Type": "application/json"
            }

            response = requests.post(firecrawl_url, json=payload, headers=headers, timeout=30)
            response.raise_for_status()
            data = response.json()

            return data.get('data', {}).get('markdown', '')

        except Exception as e:
            logger.error(f"Firecrawl extraction failed: {e}")
            return None

    def looks_like_transcript(self, text):
        """Check if text looks like a transcript"""

        if len(text) < 800:
            return False

        # Transcript indicators
        indicators = [
            'transcript', 'speaker', 'host', 'guest', 'interview', 'conversation',
            'question:', 'answer:', 'q:', 'a:', '[music]', '[applause]', 'laughs',
            '主持人', '嘉宾', '采访', '对话'
        ]

        indicator_count = sum(1 for indicator in indicators if indicator.lower() in text.lower())

        # Check for dialogue format
        dialogue_score = text.count(':') + text.count('"') + text.count("'")

        # Check sentence structure
        sentence_score = text.count('.')

        # Combined score
        score = indicator_count + (dialogue_score / 30) + (sentence_score / 50)

        return score >= 3

    def save_transcript(self, episode_id, transcript_info):
        """Save transcript to database - FULL CONTENT"""

        conn = sqlite3.connect("podcast_processing.db")
        conn.execute("""
            UPDATE episodes
            SET processing_status = 'completed',
                transcript_found = 1,
                transcript_text = ?,
                transcript_source = ?,
                transcript_url = ?,
                last_attempt = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (transcript_info['content'], transcript_info['source'], transcript_info['url'], episode_id))
        conn.commit()
        conn.close()

    def mark_failed(self, episode_id):
        """Mark episode as failed"""

        conn = sqlite3.connect("podcast_processing.db")
        conn.execute("""
            UPDATE episodes
            SET processing_status = 'failed',
                last_attempt = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (episode_id,))
        conn.commit()
        conn.close()

    def process_episode(self, episode):
        """Process a single episode"""

        episode_id, title, link, podcast_id, podcast_name = episode

        print(f"\n🎙️  Podcast: {podcast_name}")
        print(f"📄 Episode: {title[:80]}...")

        # Search for transcript sources
        sources = self.search_transcript_sources(podcast_name, title)

        if not sources:
            print("❌ No transcript sources found")
            self.mark_failed(episode_id)
            return False

        # Try each source to extract transcript
        for i, source in enumerate(sources[:3]):  # Try first 3 sources
            print(f"\n  📖 Source {i+1}: {source['title'][:60]}...")

            content = self.extract_transcript_content(source['url'], source['title'])

            if content:
                transcript_info = {
                    'content': content,
                    'url': source['url'],
                    'title': source['title'],
                    'source': f"{source.get('query', 'unknown')}_extraction"
                }

                self.save_transcript(episode_id, transcript_info)
                print(f"💾 SAVED transcript ({len(content)} characters) - FULL CONTENT")
                return True

        print("❌ No valid transcripts extracted")
        self.mark_failed(episode_id)
        return False

    def process_chunk(self, chunk_size=100):
        """Process a chunk of episodes"""

        conn = sqlite3.connect("podcast_processing.db")

        # Get episodes for this chunk (prioritize failed episodes)
        cursor = conn.execute("""
            SELECT e.id, e.title, e.link, e.podcast_id, p.name as podcast_name
            FROM episodes e
            JOIN podcasts p ON e.podcast_id = p.id
            WHERE e.processing_status IN ('failed', 'pending')
            ORDER BY
                CASE
                    WHEN e.processing_status = 'failed' THEN 1
                    ELSE 2
                END,
                RANDOM()
            LIMIT ?
        """, (chunk_size,))

        episodes = cursor.fetchall()
        conn.close()

        if not episodes:
            print("🎉 No more pending episodes!")
            return 0

        print(f"\n🚀 Processing chunk of {len(episodes)} episodes...")
        print("=" * 70)

        successful = 0
        failed = 0
        errors = 0

        for episode in episodes:
            try:
                if self.process_episode(episode):
                    successful += 1
                else:
                    failed += 1
            except Exception as e:
                print(f"🚫 ERROR processing episode: {e}")
                errors += 1

            print("-" * 50)
            time.sleep(1.5)  # Rate limiting

        print(f"\n🏁 Chunk complete!")
        print(f"📊 Results: {successful} successful, {failed} failed, {errors} errors")
        print(f"📈 Success rate: {(successful/(successful+failed))*100:.1f}%" if (successful+failed) > 0 else "No episodes processed")

        self.log_api_usage()

        return successful

    def run_continuous(self, chunk_size=100, max_chunks=None):
        """Run continuous processing in chunks"""

        print("🚀 Starting Continuous Atlas Transcript Processor")
        print("=" * 70)
        print(f"🎯 Processing in chunks of {chunk_size}")
        print(f"🔧 APIs: Tavily + YouTube + Firecrawl (FULL TRANSCRIPTS)")
        print(f"📊 Firecrawl credits: 500 available")

        chunk_count = 0
        total_successful = 0

        while True:
            if max_chunks and chunk_count >= max_chunks:
                print(f"\n🏁 Reached maximum chunks ({max_chunks})")
                break

            chunk_count += 1
            print(f"\n{'='*70}")
            print(f"📦 CHUNK {chunk_count}")
            print(f"{'='*70}")

            successful = self.process_chunk(chunk_size)
            total_successful += successful

            # Check if we should continue
            conn = sqlite3.connect("podcast_processing.db")
            cursor = conn.execute("SELECT COUNT(*) FROM episodes WHERE processing_status IN ('failed', 'pending')")
            pending = cursor.fetchone()[0]
            conn.close()

            if pending == 0:
                print(f"\n🎉 ALL EPISODES PROCESSED!")
                print(f"📊 Total successful: {total_successful}")
                break

            print(f"📊 {pending} episodes remaining")

            # Small delay between chunks
            print("⏳ Waiting 30 seconds before next chunk...")
            time.sleep(30)

        print(f"\n🏁 PROCESSING COMPLETE!")
        print(f"📊 Final stats: {total_successful} transcripts found across {chunk_count} chunks")

if __name__ == "__main__":
    processor = ContinuousTranscriptProcessor()
    processor.run_continuous(chunk_size=100)