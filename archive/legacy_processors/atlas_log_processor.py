#!/usr/bin/env python3
"""
Atlas Log-Stream Processor
High-performance podcast episode processing using log-stream architecture
Replaces database bottlenecks with fast file-based operations
"""

import json
import threading
import time
import os
import sys
import re
import requests
import feedparser
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from pathlib import Path

# Import the OOS logger we created
from oos_logger import get_logger

class AtlasLogProcessor:
    """High-performance Atlas processor using log-stream architecture"""

    def __init__(self, log_file: str = "atlas_operations.log"):
        self.logger = get_logger(log_file)
        self.config_file = "config/podcast_config.csv"
        self.rss_file = "config/podcast_rss_feeds.csv"
        self.processed_file = "logs/processed_episodes.log"

        # Ensure directories exist
        os.makedirs("logs", exist_ok=True)
        os.makedirs("content/markdown", exist_ok=True)
        os.makedirs("config", exist_ok=True)

        # Load configurations
        self.podcast_config = self._load_podcast_config()
        self.rss_feeds = self._load_rss_feeds()
        self.processed_episodes = self._load_processed_episodes()

        # Transcript sources registry - UPDATED UNIVERSAL DISCOVERY
        self.transcript_sources = [
            {"name": "universal_discovery", "method": "universal_discovery"},
            {"name": "local_matrix", "method": "local_discovery"},
            {"name": "youtube_fallback", "method": "youtube_transcript"}
        ]
        # Load discovery matrix for known sources
        try:
            import json
            if os.path.exists('config/discovered_transcript_sources.json'):
                with open('config/discovered_transcript_sources.json', 'r') as f:
                    self.discovered_sources = json.load(f)
                print(f"Loaded {len(self.discovered_sources)} podcasts from discovery matrix")
            else:
                self.discovered_sources = {}
        except:
            self.discovered_sources = {}

    def _load_podcast_config(self) -> Dict[str, Dict[str, str]]:
        """Load podcast configuration from CSV"""
        config = {}
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        if line.strip() and not line.startswith('name'):
                            parts = line.strip().split(',')
                            if len(parts) >= 4:
                                config[parts[0]] = {
                                    'rss_url': parts[1],
                                    'network': parts[2],
                                    'active': parts[3]
                                }
        except Exception as e:
            self.logger.fail("system", "config_loader", "podcast_config", {"error": str(e)})

        return config

    def _load_rss_feeds(self) -> List[Dict[str, str]]:
        """Load RSS feed mappings from CSV"""
        feeds = []
        try:
            if os.path.exists(self.rss_file):
                with open(self.rss_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        if line.strip() and not line.startswith('podcast_name'):
                            parts = line.strip().split(',')
                            if len(parts) >= 2:
                                feeds.append({
                                    'podcast_name': parts[0],
                                    'rss_url': parts[1]
                                })
        except Exception as e:
            self.logger.fail("system", "config_loader", "rss_feeds", {"error": str(e)})

        return feeds

    def _load_processed_episodes(self) -> set:
        """Load set of already processed episode IDs from log file"""
        processed = set()
        try:
            if os.path.exists(self.processed_file):
                with open(self.processed_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        if line.strip():
                            parts = line.strip().split('|')
                            if len(parts) >= 5:
                                episode_id = f"{parts[3]}_{parts[4]}"  # source_item_id
                                processed.add(episode_id)
        except Exception as e:
            self.logger.fail("system", "log_loader", "processed_episodes", {"error": str(e)})

        return processed

    def _mark_episode_processed(self, source: str, episode_id: str, data: Dict[str, Any]):
        """Mark an episode as processed in the log file"""
        try:
            with open(self.processed_file, 'a', encoding='utf-8') as f:
                timestamp = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'
                f.write(f"{timestamp}|PROCESSED|podcast|{source}|{episode_id}|{json.dumps(data)}\n")
                f.flush()
        except Exception as e:
            self.logger.fail("system", "log_writer", "mark_processed", {"error": str(e)})

    def discover_episodes(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Discover new episodes from RSS feeds"""
        discovered = []

        self.logger.metrics("rss_discovery", f"batch_{int(time.time())}", {
            "total_feeds": len(self.rss_feeds),
            "limit": limit,
            "start_time": datetime.utcnow().isoformat()
        })

        for feed_info in self.rss_feeds[:limit]:
            try:
                podcast_name = feed_info['podcast_name']
                rss_url = feed_info['rss_url']

                self.logger.process("podcast", podcast_name, f"rss_{podcast_name}", {
                    "action": "fetch_rss",
                    "rss_url": rss_url
                })

                # Fetch RSS feed
                response = requests.get(rss_url, timeout=30, headers={'User-Agent': 'Atlas/1.0'})
                response.raise_for_status()

                # Parse RSS feed
                feed = feedparser.parse(response.content)

                for entry in feed.entries[:10]:  # Limit to 10 most recent episodes
                    episode_id = entry.get('id', entry.get('link', ''))
                    if not episode_id:
                        continue

                    # Check if already processed
                    check_id = f"{podcast_name}_{episode_id}"
                    if check_id in self.processed_episodes:
                        self.logger.skip("podcast", podcast_name, episode_id, {
                            "reason": "already_processed"
                        })
                        continue

                    # Extract episode data
                    episode_data = {
                        'title': entry.get('title', 'Unknown Title'),
                        'link': entry.get('link', ''),
                        'published': entry.get('published', ''),
                        'summary': entry.get('summary', ''),
                        'podcast_name': podcast_name,
                        'network': self.podcast_config.get(podcast_name, {}).get('network', 'unknown'),
                        'duration': self._extract_duration(entry),
                        'audio_url': self._extract_audio_url(entry)
                    }

                    discovered.append(episode_data)

                    self.logger.discover("podcast", podcast_name, episode_id, episode_data)

            except Exception as e:
                self.logger.fail("podcast", feed_info.get('podcast_name', 'unknown'), f"rss_error", {
                    "error": str(e),
                    "rss_url": rss_url
                })

        self.logger.metrics("rss_discovery", f"batch_{int(time.time())}", {
            "discovered_count": len(discovered),
            "end_time": datetime.utcnow().isoformat()
        })

        return discovered

    def _extract_duration(self, entry) -> Optional[str]:
        """Extract duration from podcast entry"""
        if hasattr(entry, 'itunes_duration'):
            return entry.itunes_duration
        return None

    def _extract_audio_url(self, entry) -> Optional[str]:
        """Extract audio URL from podcast entry"""
        if hasattr(entry, 'enclosures'):
            for enclosure in entry.enclosures:
                if enclosure.get('type', '').startswith('audio/'):
                    return enclosure.get('href')
        return None

    def extract_transcript(self, episode_data: Dict[str, Any]) -> Optional[str]:
        """Extract transcript for an episode using various sources"""
        episode_id = episode_data['link']
        podcast_name = episode_data['podcast_name']

        self.logger.process("podcast", podcast_name, episode_id, {
            "action": "extract_transcript",
            "title": episode_data['title']
        })

        # Try different transcript sources
        for source in self.transcript_sources:
            try:
                transcript = self._try_extract_from_source(episode_data, source)
                if transcript:
                    self.logger.complete("podcast", podcast_name, episode_id, {
                        "source": source['name'],
                        "word_count": len(transcript.split()),
                        "file_path": f"content/markdown/content_{episode_id.replace('/', '_')}.md"
                    })
                    return transcript
            except Exception as e:
                self.logger.fail("podcast", podcast_name, episode_id, {
                    "source": source['name'],
                    "error": str(e)
                })

        self.logger.fail("podcast", podcast_name, episode_id, {
            "error": "no_transcript_found"
        })
        return None

    def _try_extract_from_source(self, episode_data: Dict[str, Any], source: Dict[str, str]) -> Optional[str]:
        """Try to extract transcript using web search and discovery matrix"""
        podcast_name = episode_data.get('podcast_name', '')
        episode_title = episode_data.get('title', '')
        episode_url = episode_data.get('link', '')

        print(f"🔍 Searching for transcript: {podcast_name} - {episode_title}")

        # First check if we have sources in the discovery matrix
        if hasattr(self, 'discovered_sources') and podcast_name in self.discovered_sources:
            podcast_sources = self.discovered_sources[podcast_name].get('sources', [])
            print(f"Found {len(podcast_sources)} sources in discovery matrix for {podcast_name}")

            for src in podcast_sources[:3]:  # Try top 3 sources
                if src.get('status') == 'working':
                    try:
                        import requests
                        print(f"Trying source: {src['url']}")
                        response = requests.get(src['url'], timeout=10)
                        if response.status_code == 200:
                            # Extract transcript content from the page
                            content_text = response.text
                            if len(content_text) > 1000:  # Reasonable transcript length
                                print(f"✅ Found transcript from {src['url']} ({len(content_text)} chars)")
                                return content_text[:50000]  # Limit size
                    except Exception as e:
                        print(f"❌ Failed to fetch {src['url']}: {e}")
                        continue

        # Fallback: Use Universal Discovery System
        try:
            print("🌐 Using Universal Discovery System...")
            sys.path.append('.')
            from universal_content_discovery import UniversalContentDiscovery

            discovery = UniversalContentDiscovery()

            # Build enhanced search query
            search_query = f'{podcast_name} {episode_title} transcript'

            print(f"🔍 Universal discovery for: {search_query}")

            # Use universal content discovery
            discovered_items = discovery.discover_content(search_query, "podcast")

            if discovered_items and len(discovered_items) > 0:
                print(f"✅ Found {len(discovered_items)} potential sources")

                # Try each discovered source
                for item in discovered_items[:3]:  # Try top 3
                    try:
                        url = item.get('url', '')
                        if url:
                            print(f"📄 Testing source: {url[:80]}...")
                            transcript = discovery.extract_content(item)

                            if transcript and len(transcript) > 1000:
                                print(f"✅ Found transcript via universal discovery: {len(transcript)} chars")
                                return transcript[:50000]
                    except Exception as e:
                        print(f"❌ Failed to extract from source: {e}")
                        continue
            else:
                print("❌ No sources found via universal discovery")

        except Exception as e:
            print(f"❌ Universal discovery failed: {e}")

        # Final fallback: Try local discovery matrix only
        try:
            print("🔍 Trying local discovery matrix...")
            if hasattr(self, 'discovered_sources') and podcast_name in self.discovered_sources:
                podcast_sources = self.discovered_sources[podcast_name].get('sources', [])
                working_sources = [s for s in podcast_sources if s.get('status') == 'working']

                if working_sources:
                    print(f"Found {len(working_sources)} working sources for {podcast_name}")

                    # Try direct fetch from known sources
                    for source in working_sources[:2]:
                        try:
                            import requests
                            response = requests.get(source['url'], timeout=15)
                            if response.status_code == 200:
                                content = response.text
                                if len(content) > 2000:  # Reasonable content length
                                    print(f"✅ Found transcript from local source: {len(content)} chars")
                                    return content[:50000]
                        except Exception as e:
                            print(f"❌ Failed to fetch local source: {e}")
                            continue
        except Exception as e:
            print(f"❌ Local discovery failed: {e}")


        print(f"❌ No transcript found for {podcast_name} - {episode_title}")
        return None

    def _find_youtube_version(self, podcast_name: str, episode_title: str) -> Optional[str]:
        """Try to find YouTube version of podcast episode"""
        try:
            search_query = f'"{podcast_name}" "{episode_title}" YouTube'
            search_url = f"https://api.duckduckgo.com/?q={search_query}&format=json"
            response = requests.get(search_url, timeout=10)

            if response.status_code == 200:
                results = response.json()
                if 'Results' in results:
                    for result in results['Results'][:3]:
                        url = result.get('FirstURL', '')
                        if 'youtube.com' in url:
                            print(f"Found YouTube version: {url}")
                            return url
        except Exception as e:
            print(f"YouTube search failed: {e}")
        return None

    def _try_youtube_transcript(self, episode_data: Dict[str, Any]) -> Optional[str]:
        """Try to find and extract YouTube transcript for episode"""
        podcast_name = episode_data.get('podcast_name', '')
        episode_title = episode_data.get('title', '')

        try:
            print("📺 Trying YouTube fallback...")
            youtube_url = self._find_youtube_version(podcast_name, episode_title)
            if youtube_url:
                return self._extract_youtube_transcript(youtube_url)
        except Exception as e:
            print(f"❌ YouTube fallback failed: {e}")
        return None

    def _extract_youtube_transcript(self, youtube_url: str) -> Optional[str]:
        """Extract transcript from YouTube video"""
        try:
            # Simple YouTube transcript extraction
            # In a real implementation, you'd use youtube-transcript-api
            print(f"Attempting to extract YouTube transcript from: {youtube_url}")

            # For now, return a placeholder that indicates we found YouTube content
            # This could be enhanced with actual YouTube transcript extraction
            return f"YouTube transcript for: {youtube_url}\n\n[YouTube transcript extraction would be implemented here]"

        except Exception as e:
            print(f"YouTube transcript extraction failed: {e}")
            return None

    def save_transcript(self, episode_data: Dict[str, Any], transcript: str) -> str:
        """Save transcript to file"""
        episode_id = episode_data['link'].replace('/', '_').replace(':', '_')
        filename = f"content/markdown/content_{episode_id}.md"

        try:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(transcript)

            self.logger.complete("podcast", episode_data['podcast_name'], episode_id, {
                "action": "save_transcript",
                "file_path": filename,
                "size_bytes": len(transcript.encode('utf-8'))
            })

            return filename
        except Exception as e:
            self.logger.fail("podcast", episode_data['podcast_name'], episode_id, {
                "action": "save_transcript",
                "error": str(e)
            })
            return ""

    def process_episode(self, episode_data: Dict[str, Any]) -> bool:
        """Process a single episode"""
        episode_id = episode_data['link']
        podcast_name = episode_data['podcast_name']

        try:
            # Extract transcript
            transcript = self.extract_transcript(episode_data)
            if not transcript:
                return False

            # Save transcript
            filename = self.save_transcript(episode_data, transcript)
            if not filename:
                return False

            # Mark as processed
            self._mark_episode_processed(podcast_name, episode_id, {
                "title": episode_data['title'],
                "file_path": filename,
                "network": episode_data['network']
            })

            return True

        except Exception as e:
            self.logger.fail("podcast", podcast_name, episode_id, {
                "error": str(e),
                "stage": "process_episode"
            })
            return False

    def process_batch(self, limit: int = 50) -> Dict[str, Any]:
        """Process a batch of episodes"""
        start_time = time.time()

        self.logger.metrics("batch_processor", f"batch_{int(time.time())}", {
            "action": "start_batch",
            "limit": limit,
            "start_time": datetime.utcnow().isoformat()
        })

        # Discover new episodes
        episodes = self.discover_episodes(limit)

        # Process episodes
        success_count = 0
        fail_count = 0

        for episode in episodes:
            if self.process_episode(episode):
                success_count += 1
            else:
                fail_count += 1

        end_time = time.time()
        duration = end_time - start_time

        self.logger.metrics("batch_processor", f"batch_{int(time.time())}", {
            "action": "complete_batch",
            "discovered": len(episodes),
            "success": success_count,
            "failed": fail_count,
            "duration_seconds": duration,
            "episodes_per_second": len(episodes) / duration if duration > 0 else 0,
            "end_time": datetime.utcnow().isoformat()
        })

        return {
            'discovered': len(episodes),
            'success': success_count,
            'failed': fail_count,
            'duration': duration,
            'eps': len(episodes) / duration if duration > 0 else 0
        }

def main():
    """Main processing loop"""
    processor = AtlasLogProcessor()

    print("🚀 Atlas Log-Stream Processor Starting...")
    print(f"📊 Loaded {len(processor.rss_feeds)} RSS feeds")
    print(f"📝 Loaded {len(processor.podcast_config)} podcast configurations")
    print(f"✅ Already processed {len(processor.processed_episodes)} episodes")

    # Process batches continuously
    batch_count = 0
    while True:
        try:
            batch_count += 1
            print(f"\n🔄 Processing batch #{batch_count}")

            result = processor.process_batch(limit=100)

            print(f"📈 Batch Results:")
            print(f"   Discovered: {result['discovered']}")
            print(f"   Success: {result['success']}")
            print(f"   Failed: {result['failed']}")
            print(f"   Duration: {result['duration']:.2f}s")
            print(f"   Episodes/sec: {result['eps']:.2f}")

            # Sleep between batches to be respectful to sources
            if result['discovered'] > 0:
                sleep_time = 60  # 1 minute between batches with discoveries
            else:
                sleep_time = 300  # 5 minutes between empty batches

            print(f"😴 Sleeping {sleep_time}s before next batch...")
            time.sleep(sleep_time)

        except KeyboardInterrupt:
            print("\n🛑 Stopping Atlas Log-Stream Processor")
            break
        except Exception as e:
            print(f"❌ Error in batch processing: {e}")
            time.sleep(60)  # Wait before retrying

if __name__ == "__main__":
    main()