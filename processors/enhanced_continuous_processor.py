#!/usr/bin/env python3
"""
Enhanced Continuous Atlas Transcript Processor
Uses multiple APIs with fallbacks when rate limits are hit
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

class EnhancedContinuousProcessor:
    """Enhanced processor with multiple API fallbacks"""

    def __init__(self):
        # Load all API keys
        self.tavily_key = os.getenv('TAVILY_API_KEY')
        self.tavily_backup = os.getenv('TAVILY_API_KEY_BACKUP')
        self.perplexity_key = os.getenv('PERPLEXITY_API_KEY')
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
        self.tavily_backup_calls = 0
        self.perplexity_calls = 0
        self.youtube_calls = 0
        self.firecrawl_calls = 0

        # Track which APIs are working
        self.tavily_working = True
        self.tavily_backup_working = bool(self.tavily_backup)
        self.perplexity_working = bool(self.perplexity_key)

    def log_api_usage(self):
        """Log current API usage"""
        print(f"\n📊 API Usage Summary:")
        print(f"   Tavily (primary): {self.tavily_calls} {'✅' if self.tavily_working else '❌'}")
        if self.tavily_backup:
            print(f"   Tavily (backup): {self.tavily_backup_calls} {'✅' if self.tavily_backup_working else '❌'}")
        if self.perplexity_key:
            print(f"   Perplexity: {self.perplexity_calls} {'✅' if self.perplexity_working else '❌'}")
        print(f"   YouTube: {self.youtube_calls}")
        print(f"   Firecrawl: {self.firecrawl_calls}")

    def search_with_tavily(self, query):
        """Search with Tavily API with error handling"""

        if not self.tavily_working:
            return None

        url = "https://api.tavily.com/search"
        payload = {
            "api_key": self.tavily_key,
            "query": query,
            "max_results": 5,
            "search_depth": "basic"
        }

        try:
            response = requests.post(url, json=payload, timeout=15)

            if response.status_code == 432:
                print(f"   🚫 Tavily rate limit hit, switching to backup APIs")
                self.tavily_working = False
                return None

            response.raise_for_status()
            data = response.json()
            self.tavily_calls += 1

            return data.get('results', [])

        except Exception as e:
            print(f"   🚫 Tavily error: {e}")
            self.tavily_working = False
            return None

    def search_with_tavily_backup(self, query):
        """Search with backup Tavily API"""

        if not self.tavily_backup or not self.tavily_backup_working:
            return None

        url = "https://api.tavily.com/search"
        payload = {
            "api_key": self.tavily_backup,
            "query": query,
            "max_results": 5,
            "search_depth": "basic"
        }

        try:
            response = requests.post(url, json=payload, timeout=15)

            if response.status_code == 432:
                print(f"   🚫 Backup Tavily also rate limited")
                self.tavily_backup_working = False
                return None

            response.raise_for_status()
            data = response.json()
            self.tavily_backup_calls += 1

            return data.get('results', [])

        except Exception as e:
            print(f"   🚫 Backup Tavily error: {e}")
            self.tavily_backup_working = False
            return None

    def search_with_perplexity(self, query):
        """Search with Perplexity API"""

        if not self.perplexity_key or not self.perplexity_working:
            return None

        url = "https://api.perplexity.ai/chat/completions"
        payload = {
            "model": "llama-3.1-sonar-small-128k-online",
            "messages": [
                {
                    "role": "user",
                    "content": f"Search for information about: {query}\n\nFind transcript sources or detailed information about this content."
                }
            ],
            "max_tokens": 1000,
            "temperature": 0.1
        }

        headers = {
            "Authorization": f"Bearer {self.perplexity_key}",
            "Content-Type": "application/json"
        }

        try:
            response = requests.post(url, json=payload, headers=headers, timeout=20)
            response.raise_for_status()
            data = response.json()
            self.perplexity_calls += 1

            # Extract URLs from Perplexity response
            content = data.get('choices', [{}])[0].get('message', {}).get('content', '')

            # Simple URL extraction
            url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
            urls = re.findall(url_pattern, content)

            # Convert to expected format
            results = []
            for url in urls[:5]:  # Limit to first 5 URLs
                results.append({
                    'url': url,
                    'title': f"Perplexity search result",
                    'content': f"Found via Perplexity search",
                    'query': 'perplexity_search'
                })

            return results

        except Exception as e:
            print(f"   🚫 Perplexity error: {e}")
            self.perplexity_working = False
            return None

    def search_transcript_sources(self, podcast_name, episode_title):
        """Search for transcripts using multiple APIs with fallbacks"""

        # Build search queries
        queries = [
            f'"{episode_title}" transcript {podcast_name}',
            f'"{episode_title}" transcript',
            f'{podcast_name} {episode_title} full transcript'
        ]

        all_results = []

        # Try each query with working APIs
        for query in queries:
            print(f"🔍 Searching: {query[:80]}...")

            # Try Tavily primary first
            if self.tavily_working:
                results = self.search_with_tavily(query)
                if results:
                    for result in results:
                        result['query'] = 'tavily_primary'
                        all_results.append(result)
                    print(f"   📊 Tavily: {len(results)} results")
                    time.sleep(1)  # Rate limiting
                    continue

            # Try Tavily backup if primary failed
            if self.tavily_backup_working:
                results = self.search_with_tavily_backup(query)
                if results:
                    for result in results:
                        result['query'] = 'tavily_backup'
                        all_results.append(result)
                    print(f"   📊 Tavily backup: {len(results)} results")
                    time.sleep(1)
                    continue

            # Try Perplexity if Tavily APIs are down
            if self.perplexity_working:
                results = self.search_with_perplexity(query)
                if results:
                    all_results.extend(results)
                    print(f"   📊 Perplexity: {len(results)} results")
                    time.sleep(2)  # Longer delay for Perplexity
                    continue

            # If all APIs failed, note it
            if not (self.tavily_working or self.tavily_backup_working or self.perplexity_working):
                print(f"   🚫 All search APIs exhausted")
                break

        # Try YouTube for video transcripts
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
            return content
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

    def process_chunk(self, chunk_size=50):
        """Process a chunk of episodes (smaller chunks for better API management)"""

        conn = sqlite3.connect("podcast_processing.db")

        # Get failed episodes prioritized
        cursor = conn.execute("""
            SELECT e.id, e.title, e.link, e.podcast_id, p.name as podcast_name
            FROM episodes e
            JOIN podcasts p ON e.podcast_id = p.id
            WHERE e.processing_status = 'failed'
            ORDER BY RANDOM()
            LIMIT ?
        """, (chunk_size,))

        episodes = cursor.fetchall()
        conn.close()

        if not episodes:
            print("🎉 No more failed episodes!")
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
            time.sleep(2)  # Longer rate limiting to avoid API limits

        print(f"\n🏁 Chunk complete!")
        print(f"📊 Results: {successful} successful, {failed} failed, {errors} errors")
        print(f"📈 Success rate: {(successful/(successful+failed))*100:.1f}%" if (successful+failed) > 0 else "No episodes processed")

        self.log_api_usage()

        return successful

    def run_continuous(self, chunk_size=50, max_chunks=None):
        """Run continuous processing in chunks"""

        print("🚀 Starting Enhanced Continuous Atlas Processor")
        print("=" * 70)
        print(f"🎯 Processing in chunks of {chunk_size} (smaller for API management)")
        print(f"🔧 APIs: Tavily (primary + backup) + Perplexity + YouTube + Firecrawl")

        chunk_count = 0
        total_successful = 0

        while True:
            if max_chunks and chunk_count >= max_chunks:
                print(f"\n🏁 Reached maximum chunks ({max_chunks})")
                break

            # Check if we have working APIs
            if not (self.tavily_working or self.tavily_backup_working or self.perplexity_working):
                print(f"\n🚫 All search APIs are rate limited or failed")
                print(f"⏳ Waiting 5 minutes for API reset...")
                time.sleep(300)  # Wait 5 minutes

                # Reset APIs after wait
                self.tavily_working = True
                if self.tavily_backup:
                    self.tavily_backup_working = True
                if self.perplexity_key:
                    self.perplexity_working = True

                print(f"🔄 APIs reset, continuing...")
                continue

            chunk_count += 1
            print(f"\n{'='*70}")
            print(f"📦 CHUNK {chunk_count}")
            print(f"{'='*70}")

            successful = self.process_chunk(chunk_size)
            total_successful += successful

            # Check if we should continue
            conn = sqlite3.connect("podcast_processing.db")
            cursor = conn.execute("SELECT COUNT(*) FROM episodes WHERE processing_status = 'failed'")
            pending = cursor.fetchone()[0]
            conn.close()

            if pending == 0:
                print(f"\n🎉 ALL FAILED EPISODES PROCESSED!")
                print(f"📊 Total successful: {total_successful}")
                break

            print(f"📊 {pending} failed episodes remaining")

            # Delay between chunks
            print("⏳ Waiting 60 seconds before next chunk...")
            time.sleep(60)

        print(f"\n🏁 PROCESSING COMPLETE!")
        print(f"📊 Final stats: {total_successful} transcripts found across {chunk_count} chunks")
        self.log_api_usage()

if __name__ == "__main__":
    processor = EnhancedContinuousProcessor()
    processor.run_continuous(chunk_size=50)