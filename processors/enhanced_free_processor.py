#!/usr/bin/env python3
"""
Enhanced FREE Atlas Transcript Processor
Multiple tool calls in while loop for higher success rate
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
import random

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EnhancedFreeProcessor:
    """Enhanced free processor with multiple tool calls"""

    def __init__(self):
        # Only use Tavily for search (generous free tier)
        self.tavily_key = os.getenv('TAVILY_API_KEY')

        if not self.tavily_key:
            raise ValueError("TAVILY_API_KEY not found in environment")

        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        })

        # Track usage
        self.tavily_calls = 0

        # Additional user agents for better access
        self.user_agents = [
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:121.0) Gecko/20100101 Firefox/121.0',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0'
        ]

    def log_api_usage(self):
        """Log current API usage"""
        print(f"\n📊 API Usage (100% FREE):")
        print(f"   Tavily calls: {self.tavily_calls}")
        print(f"   Total cost: $0.00")

    def search_transcript_sources(self, podcast_name, episode_title):
        """Search for transcripts using multiple Tavily queries"""

        # Comprehensive search queries
        queries = [
            f'"{episode_title}" transcript {podcast_name}',
            f'"{episode_title}" transcript',
            f'{podcast_name} {episode_title} full transcript',
            f'{episode_title} {podcast_name} interview transcript',
            f'{episode_title} podcast transcript',
            f'{episode_title} show transcript',
            f'{episode_title} conversation transcript',
            f'{episode_title} discussion transcript',
            f'{episode_title} talk transcript',
            f'site:{podcast_name.lower().replace(" ", "").replace("&", "").replace("!", "")} transcript',
            f'"{episode_title}" episode transcript',
            f'{podcast_name} transcripts'
        ]

        all_results = []

        # Try each query with Tavily
        for query in queries:
            print(f"🔍 Searching: {query[:80]}...")

            url = "https://api.tavily.com/search"
            payload = {
                "api_key": self.tavily_key,
                "query": query,
                "max_results": 15,
                "search_depth": "basic",
                "include_domains": [
                    "lexfridman.com", "stratechery.com", "happyscribe.com", "podscripts.co", "tapesearch.com", "transcripts.fm",
                    "omny.fm", "simplecast.com", "buzzsprout.com", "spreaker.com", "soundcloud.com", "anchor.fm",
                    "podbean.com", "libsyn.com", "spotify.com", "apple.com/podcasts", "stitcher.com",
                    "player.fm", "overcast.fm", "castbox.fm", "podbay.fm", "radiopublic.com",
                    "acquired.fm", "theknowledgeproject.com", "atp.fm", "hardfork.email"
                ]
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
                if "429" in str(e):
                    print(f"   🚫 Rate limited, waiting 30 seconds...")
                    time.sleep(30)
                else:
                    print(f"   🚫 Error: {e}")

            time.sleep(3)  # Rate limiting (avoid 429 errors)

        return all_results

    def extract_with_different_agents(self, url):
        """Try different user agents to bypass blocks"""

        for i, user_agent in enumerate(self.user_agents):
            print(f"   🔄 Trying user agent {i+1}/{len(self.user_agents)}...")

            headers = self.session.headers.copy()
            headers['User-Agent'] = user_agent

            try:
                response = requests.get(url, headers=headers, timeout=15)
                response.raise_for_status()

                soup = BeautifulSoup(response.content, 'html.parser')

                # Remove unwanted elements
                for element in soup(['script', 'style', 'nav', 'footer', 'header', 'aside', 'iframe', 'form']):
                    element.decompose()

                text = soup.get_text()

                # Clean up text
                lines = [line.strip() for line in text.split('\n') if line.strip() and len(line.strip()) > 10]
                clean_text = ' '.join(lines)

                if clean_text and len(clean_text) > 1000:
                    print(f"   ✅ SUCCESS with user agent {i+1}: {len(clean_text)} characters")
                    return clean_text

            except Exception as e:
                print(f"   🚫 Agent {i+1} failed: {e}")
                continue

        return None

    def extract_with_multiple_archives(self, url):
        """Try multiple archive sources for older content"""

        archives = [
            # Primary archives (broadest coverage)
            ("Wayback Machine", f"http://web.archive.org/web/20240101000000/{url}"),
            ("Archive.is", f"https://archive.ph/{url}"),

            # Secondary archives
            ("Perma.cc", f"https://perma.cc/{url}"),
            ("Ghostarchive", f"https://ghostarchive.org/ghost/{url}"),
            ("Arquivo.pt", f"https://arquivo.pt/wayback/20240101000000/{url}"),

            # Aggregator archives
            ("Memento Time Travel", f"https://timetravel.mementoweb.org/20240101000000/{url}"),

            # Alternative Wayback snapshots
            ("Wayback Recent", f"http://web.archive.org/web/2/{url}"),
            ("Wayback 2023", f"http://web.archive.org/web/20231201000000/{url}"),
            ("Wayback 2022", f"http://web.archive.org/web/20221201000000/{url}"),
        ]

        for archive_name, archive_url in archives:
            try:
                print(f"   🕰️ Trying {archive_name}: {archive_url[:80]}...")

                response = requests.get(archive_url, timeout=20)
                response.raise_for_status()

                if response.status_code == 200:
                    soup = BeautifulSoup(response.content, 'html.parser')

                    # Remove unwanted elements
                    for element in soup(['script', 'style', 'nav', 'footer', 'header', 'aside', 'iframe', 'form']):
                        element.decompose()

                    text = soup.get_text()

                    # Clean up text
                    lines = [line.strip() for line in text.split('\n') if line.strip() and len(line.strip()) > 10]
                    clean_text = ' '.join(lines)

                    if clean_text and len(clean_text) > 1000:
                        print(f"   ✅ {archive_name} SUCCESS: {len(clean_text)} characters")
                        return clean_text
                    else:
                        print(f"   ❌ {archive_name}: No useful content found")

            except Exception as e:
                print(f"   🚫 {archive_name} failed: {str(e)[:50]}...")
                continue

        return None

    def extract_with_alternative_sources(self, podcast_name, episode_title):
        """Try to find alternative sources"""

        # Try searching for show notes or articles
        search_terms = [
            f"{episode_title} {podcast_name} show notes",
            f"{episode_title} {podcast_name} article",
            f"{episode_title} {podcast_name} summary",
            f"{episode_title} {podcast_name} highlights"
        ]

        for term in search_terms:
            print(f"   🔎 Searching for show notes: {term[:60]}...")

            url = "https://api.tavily.com/search"
            payload = {
                "api_key": self.tavily_key,
                "query": term,
                "max_results": 5,
                "search_depth": "basic"
            }

            try:
                response = requests.post(url, json=payload, timeout=15)
                response.raise_for_status()
                data = response.json()
                self.tavily_calls += 1

                for result in data.get('results', []):
                    if result.get('content', '').count('transcript') == 0:  # Not looking for transcripts, but related content
                        content = self.extract_transcript_content(result['url'], result['title'])
                        if content:
                            return {
                                'content': content,
                                'url': result['url'],
                                'title': result['title'],
                                'source': f"shownotes_{term}"
                            }

            except Exception as e:
                print(f"   🚫 Show notes search failed: {e}")

        return None

    def extract_transcript_content(self, url, title=""):
        """Extract transcript content with multiple methods"""

        print(f"🕷️  Extracting from: {title[:60]}...")

        # Method 1: Standard extraction
        content = self.extract_with_different_agents(url)
        if content and self.looks_like_transcript(content):
            print(f"   ✅ SUCCESS: Standard extraction ({len(content)} characters) - FREE!")
            return content

        # Method 2: Multiple Archive Sources
        content = self.extract_with_multiple_archives(url)
        if content and self.looks_like_transcript(content):
            print(f"   ✅ SUCCESS: Archive extraction ({len(content)} characters) - FREE!")
            return content

        # Method 3: Try related content
        print("   🔄 Trying alternative content sources...")
        # This would extract show notes, articles, etc. related to the episode
        related = self.extract_with_alternative_sources("", title)  # Would need to pass podcast_name
        if related:
            return related['content']

        print(f"   ❌ No content found")
        return None

    def extract_with_alternative_sources(self, podcast_name, episode_title):
        """Extract related content when transcript not found"""
        # This would be enhanced to find show notes, articles, etc.
        return None

    def looks_like_transcript(self, text):
        """Check if text looks like a REAL transcript (not metadata)"""

        # Basic length checks
        if len(text) < 5000:  # Minimum 5K characters (~800 words)
            return False

        word_count = len(text.split())
        if word_count < 1000:  # Must have at least 1000 words
            return False

        # Strong transcript indicators (must have at least 3)
        strong_indicators = [
            'transcript', 'speaker', 'host', 'guest', 'interview', 'conversation',
            'question:', 'answer:', 'q:', 'a:', '[music]', '[applause]', 'laughs'
        ]

        # Secondary indicators
        secondary_indicators = [
            'show notes', 'episode notes', 'summary', 'highlights',
            '主持人', '嘉宾', '采访', '对话'
        ]

        strong_count = sum(1 for indicator in strong_indicators if indicator.lower() in text.lower())
        secondary_count = sum(1 for indicator in secondary_indicators if indicator.lower() in text.lower())

        # Must have at least 3 strong indicators OR 2 strong + 2 secondary
        indicator_requirement = (strong_count >= 3) or (strong_count >= 2 and secondary_count >= 2)
        if not indicator_requirement:
            return False

        # Dialogue structure validation
        dialogue_count = text.count(':') + text.count('"') + text.count("'")
        if dialogue_count < 20:  # Must have at least 20 dialogue indicators
            return False

        # Sentence structure validation
        sentence_count = text.count('.') + text.count('!') + text.count('?')
        if sentence_count < 50:  # Must have at least 50 sentences
            return False

        # Quality score calculation
        score = (strong_count * 2) + secondary_count + (dialogue_count / 10) + (sentence_count / 25)

        # Additional quality checks
        # Check for paragraph structure (multiple paragraphs)
        paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
        if len(paragraphs) < 5:  # Must have at least 5 paragraphs
            return False

        # Check average word length (avoid random character strings)
        avg_word_length = sum(len(word) for word in text.split()) / word_count
        if avg_word_length < 3 or avg_word_length > 10:  # Unusual word lengths
            return False

        # Check for variety in sentence lengths (avoid repetitive patterns)
        sentence_lengths = [len(s.split()) for s in text.split('.') if s.strip()]
        if len(sentence_lengths) > 10:
            avg_sentence_length = sum(sentence_lengths) / len(sentence_lengths)
            if avg_sentence_length < 5:  # Too short on average
                return False

        # Calculate estimated podcast length from word count
        # Assuming 150-160 words per minute for speech
        estimated_minutes = word_count / 155
        if estimated_minutes < 5:  # Must be at least 5 minutes of content
            return False

        print(f"   📊 Transcript quality analysis:")
        print(f"      Words: {word_count:,} (~{estimated_minutes:.1f} minutes)")
        print(f"      Strong indicators: {strong_count}, Secondary: {secondary_count}")
        print(f"      Dialogue markers: {dialogue_count}, Sentences: {sentence_count}")
        print(f"      Quality score: {score:.1f}")

        # Final quality threshold
        return score >= 8  # Higher threshold for real transcripts

    def save_transcript(self, episode_id, transcript_info):
        """Save transcript to database"""

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
        """Process a single episode with multiple tool calls"""

        episode_id, title, link, podcast_id, podcast_name = episode

        print(f"\n🎙️  Podcast: {podcast_name}")
        print(f"📄 Episode: {title[:80]}...")

        # Tool Call 1: Search for transcript sources
        print(f"🔧 Tool Call 1: Searching transcript sources...")
        sources = self.search_transcript_sources(podcast_name, title)

        if not sources:
            print("❌ No sources found")
            self.mark_failed(episode_id)
            return False

        # Tool Call 2: Try extraction with multiple methods
        print(f"🔧 Tool Call 2: Multi-method extraction...")

        # Try each source with enhanced extraction
        for i, source in enumerate(sources[:10]):  # Try first 10 sources
            print(f"\n  📖 Source {i+1}: {source['title'][:60]}...")

            content = self.extract_transcript_content(source['url'], source['title'])

            if content:
                transcript_info = {
                    'content': content,
                    'url': source['url'],
                    'title': source['title'],
                    'source': f"multi_tool_{source.get('query', 'search')}"
                }

                self.save_transcript(episode_id, transcript_info)
                print(f"💾 SAVED content ({len(content)} characters) - 100% FREE!")
                return True

        print("❌ No content extracted")
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
        print(f"💰 100% FREE PROCESSING with Multiple Tool Calls!")
        print(f"🔧 Tools: Tavily + Multiple Extraction Methods")

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
            time.sleep(2)  # Rate limiting

        print(f"\n🏁 Chunk complete!")
        print(f"📊 Results: {successful} successful, {failed} failed, {errors} errors")
        print(f"📈 Success rate: {(successful/(successful+failed))*100:.1f}%" if (successful+failed) > 0 else "No episodes processed")

        self.log_api_usage()

        return successful

    def run_continuous(self, chunk_size=100, max_chunks=None):
        """Run continuous processing in chunks"""

        print("🚀 Starting Enhanced FREE Atlas Transcript Processor")
        print("=" * 70)
        print(f"🎯 Processing in chunks of {chunk_size}")
        print(f"🔧 Multiple Tool Calls for Higher Success Rate")
        print(f"💰 COST: $0.00")
        print(f"📚 Extract FULL content - no limits!")

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
                print(f"💰 Total cost: $0.00")
                break

            print(f"📊 {pending} episodes remaining")

            # Small delay between chunks
            print("⏳ Waiting 5 seconds before next chunk...")
            time.sleep(5)

        print(f"\n🏁 PROCESSING COMPLETE!")
        print(f"📊 Final stats: {total_successful} transcripts found across {chunk_count} chunks")
        print(f"💰 Total cost: $0.00 - 100% FREE!")

if __name__ == "__main__":
    processor = EnhancedFreeProcessor()
    processor.run_continuous(chunk_size=100)