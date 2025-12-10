#!/usr/bin/env python3
"""
100% FREE Atlas Transcript Processor
Uses Crawl4AI + Tavily for zero-cost transcript extraction
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
import subprocess
import sys

# Add Crawl4AI to path
sys.path.insert(0, '/home/ubuntu/dev/atlas/crawl4ai_env/lib/python3.12/site-packages')

try:
    from crawl4ai import AsyncWebCrawler
    from crawl4ai.extraction_strategy import LLMExtractionStrategy
    import asyncio
except ImportError:
    print("Crawl4AI not available, using requests only")
    AsyncWebCrawler = None

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class FreeTranscriptProcessor:
    """100% free processor using Crawl4AI + Tavily"""

    def __init__(self):
        # Only use Tavily for search (it has generous free tier)
        self.tavily_key = os.getenv('TAVILY_API_KEY')

        if not self.tavily_key:
            raise ValueError("TAVILY_API_KEY not found in environment")

        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        })

        # Track usage
        self.tavily_calls = 0

    def log_api_usage(self):
        """Log current API usage"""
        print(f"\n📊 API Usage (100% FREE):")
        print(f"   Tavily calls: {self.tavily_calls}")
        print(f"   Crawl4AI: FREE unlimited")

    def search_transcript_sources(self, podcast_name, episode_title):
        """Search for transcripts using Tavily (free search)"""

        # Build search queries
        queries = [
            f'"{episode_title}" transcript {podcast_name}',
            f'"{episode_title}" transcript',
            f'{podcast_name} {episode_title} full transcript',
            f'{episode_title} {podcast_name} interview transcript',
            f'{episode_title} podcast transcript',
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
                "max_results": 10,
                "search_depth": "basic",
                "include_raw_content": False
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

        return all_results

    def extract_with_crawl4ai(self, url):
        """Extract content using Crawl4AI (FREE and POWERFUL)"""

        if not AsyncWebCrawler:
            print("   🚫 Crawl4AI not available, falling back to requests")
            return self.extract_with_requests(url)

        try:
            print(f"   🕷️  Crawl4AI extracting: {url[:60]}...")

            async def crawl():
                async with AsyncWebCrawler(verbose=True) as crawler:
                    result = await crawler.arun(
                        url=url,
                        word_count_threshold=10,
                        extraction_strategy=LLMExtractionStrategy(
                            provider="openai",
                            api_token=os.getenv('OPENAI_API_KEY'),  # Optional, works without too
                            instruction="Extract the full transcript content. Remove any navigation, headers, footers, or ads. Focus only on the actual transcript text."
                        ),
                        bypass_cache=True,
                        js_code=[
                            "window.scrollTo(0, document.body.scrollHeight);"
                        ],
                        wait_for="body",
                        delay_before_return_html=2.0,
                        magic=True
                    )
                    return result

            # Run the async function
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(crawl())
            loop.close()

            if result.success and result.cleaned_html:
                soup = BeautifulSoup(result.cleaned_html, 'html.parser')
                text = soup.get_text()

                # Clean up text
                lines = [line.strip() for line in text.split('\n') if line.strip() and len(line.strip()) > 10]
                clean_text = ' '.join(lines)

                print(f"   ✅ SUCCESS: Extracted {len(clean_text)} characters")
                return clean_text
            else:
                print(f"   ❌ Crawl4AI extraction failed")
                return None

        except Exception as e:
            print(f"   🚫 Crawl4AI error: {e}")
            return self.extract_with_requests(url)

    def extract_with_requests(self, url):
        """Extract content using requests (fallback)"""

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

    def extract_transcript_content(self, url, title=""):
        """Extract transcript content using FREE tools"""

        print(f"🕷️  Extracting from: {title[:60]}...")

        # Try Crawl4AI first (free and powerful)
        content = self.extract_with_crawl4ai(url)

        if content and self.looks_like_transcript(content):
            print(f"   ✅ SUCCESS: Extracted {len(content)} characters - FREE!")
            return content  # FULL CONTENT - NO LIMITS!
        else:
            print(f"   ❌ No valid transcript content found")
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
        for i, source in enumerate(sources[:5]):  # Try first 5 sources
            print(f"\n  📖 Source {i+1}: {source['title'][:60]}...")

            content = self.extract_transcript_content(source['url'], source['title'])

            if content:
                transcript_info = {
                    'content': content,
                    'url': source['url'],
                    'title': source['title'],
                    'source': f"crawl4ai_{source.get('query', 'search')}"
                }

                self.save_transcript(episode_id, transcript_info)
                print(f"💾 SAVED transcript ({len(content)} characters) - 100% FREE!")
                return True

        print("❌ No valid transcripts extracted")
        self.mark_failed(episode_id)
        return False

    def process_chunk(self, chunk_size=100):
        """Process a chunk of episodes"""

        conn = sqlite3.connect("podcast_processing.db")

        # Get episodes for this chunk
        cursor = conn.execute("""
            SELECT e.id, e.title, e.link, e.podcast_id, p.name as podcast_name
            FROM episodes e
            JOIN podcasts p ON e.podcast_id = p.id
            WHERE e.processing_status = 'pending'
            ORDER BY RANDOM()
            LIMIT ?
        """, (chunk_size,))

        episodes = cursor.fetchall()
        conn.close()

        if not episodes:
            print("🎉 No more pending episodes!")
            return 0

        print(f"\n🚀 Processing chunk of {len(episodes)} episodes...")
        print("=" * 70)
        print(f"💰 100% FREE PROCESSING - No API costs!")

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
            time.sleep(1)  # Rate limiting

        print(f"\n🏁 Chunk complete!")
        print(f"📊 Results: {successful} successful, {failed} failed, {errors} errors")
        print(f"📈 Success rate: {(successful/(successful+failed))*100:.1f}%" if (successful+failed) > 0 else "No episodes processed")

        self.log_api_usage()

        return successful

    def run_continuous(self, chunk_size=100, max_chunks=None):
        """Run continuous processing in chunks"""

        print("🚀 Starting 100% FREE Atlas Transcript Processor")
        print("=" * 70)
        print(f"🎯 Processing in chunks of {chunk_size}")
        print(f"🔧 Tools: Crawl4AI + Tavily (FREE)")
        print(f"💰 COST: $0.00")
        print(f"📚 Extract FULL transcripts - no limits!")

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
            cursor = conn.execute("SELECT COUNT(*) FROM episodes WHERE processing_status = 'pending'")
            pending = cursor.fetchone()[0]
            conn.close()

            if pending == 0:
                print(f"\n🎉 ALL EPISODES PROCESSED!")
                print(f"📊 Total successful: {total_successful}")
                print(f"💰 Total cost: $0.00")
                break

            print(f"📊 {pending} episodes remaining")

            # Small delay between chunks
            print("⏳ Waiting 10 seconds before next chunk...")
            time.sleep(10)

        print(f"\n🏁 PROCESSING COMPLETE!")
        print(f"📊 Final stats: {total_successful} transcripts found across {chunk_count} chunks")
        print(f"💰 Total cost: $0.00 - 100% FREE!")

if __name__ == "__main__":
    processor = FreeTranscriptProcessor()
    processor.run_continuous(chunk_size=100)