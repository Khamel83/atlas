#!/usr/bin/env python3
"""
Network-Specific Transcript Scrapers

Builds custom scrapers for major podcast networks that have professional transcripts:
- NPR (This American Life, Planet Money, etc.)
- Radiolab/WNYC
- Vox Media
- Slate Podcasts
- Gimlet/Spotify

These scrapers know the specific HTML structure for each network.
"""

import requests
from bs4 import BeautifulSoup
import json
import re
from pathlib import Path
from typing import Dict, List, Optional
import time
from urllib.parse import urljoin, urlparse
import logging

logger = logging.getLogger(__name__)

class NPRTranscriptScraper:
    """Scraper for NPR network podcasts (This American Life, Planet Money, etc.)"""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        })

    def scrape_this_american_life(self, episode_url: str) -> Optional[Dict]:
        """Scrape This American Life transcript"""
        try:
            response = self.session.get(episode_url, timeout=30)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')

            # TAL has transcripts in specific sections
            transcript_content = ""

            # Look for transcript sections
            transcript_sections = soup.find_all(['div', 'section'],
                                              class_=re.compile(r'transcript|story-text', re.IGNORECASE))

            if transcript_sections:
                for section in transcript_sections:
                    transcript_content += section.get_text(separator='\n', strip=True) + '\n\n'

            # Fallback: look for main content
            if not transcript_content:
                main_content = soup.find('article') or soup.find('main') or soup.find('.content')
                if main_content:
                    transcript_content = main_content.get_text(separator='\n', strip=True)

            if len(transcript_content) > 1000:
                # Extract metadata
                title_elem = soup.find('h1')
                title = title_elem.get_text(strip=True) if title_elem else "This American Life Episode"

                return {
                    "title": title,
                    "transcript": transcript_content,
                    "word_count": len(transcript_content.split()),
                    "source": "thisamericanlife.org",
                    "url": episode_url
                }

            return None

        except Exception as e:
            logger.error(f"Failed to scrape TAL transcript from {episode_url}: {e}")
            return None

    def scrape_planet_money(self, episode_url: str) -> Optional[Dict]:
        """Scrape Planet Money transcript"""
        try:
            response = self.session.get(episode_url, timeout=30)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')

            # NPR's standard structure
            transcript_elem = soup.find('div', id='storytext') or \
                            soup.find('div', class_='storytext') or \
                            soup.find('article', class_='story')

            if transcript_elem:
                transcript_content = transcript_elem.get_text(separator='\n', strip=True)

                if len(transcript_content) > 500:
                    title_elem = soup.find('h1')
                    title = title_elem.get_text(strip=True) if title_elem else "Planet Money Episode"

                    return {
                        "title": title,
                        "transcript": transcript_content,
                        "word_count": len(transcript_content.split()),
                        "source": "npr.org/planet-money",
                        "url": episode_url
                    }

            return None

        except Exception as e:
            logger.error(f"Failed to scrape Planet Money transcript from {episode_url}: {e}")
            return None


class RadiolabTranscriptScraper:
    """Scraper for Radiolab/WNYC network"""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        })

    def scrape_radiolab(self, episode_url: str) -> Optional[Dict]:
        """Scrape Radiolab transcript"""
        try:
            response = self.session.get(episode_url, timeout=30)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')

            # WNYC/Radiolab structure
            transcript_elem = soup.find('div', class_='transcript') or \
                            soup.find('div', class_='story-text') or \
                            soup.find('div', class_='episode-body') or \
                            soup.find('article')

            if transcript_elem:
                transcript_content = transcript_elem.get_text(separator='\n', strip=True)

                if len(transcript_content) > 1000:
                    title_elem = soup.find('h1')
                    title = title_elem.get_text(strip=True) if title_elem else "Radiolab Episode"

                    return {
                        "title": title,
                        "transcript": transcript_content,
                        "word_count": len(transcript_content.split()),
                        "source": "radiolab.org",
                        "url": episode_url
                    }

            return None

        except Exception as e:
            logger.error(f"Failed to scrape Radiolab transcript from {episode_url}: {e}")
            return None


class SlateTranscriptScraper:
    """Scraper for Slate podcasts"""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        })

    def scrape_slate_podcast(self, episode_url: str) -> Optional[Dict]:
        """Scrape Slate podcast transcript"""
        try:
            response = self.session.get(episode_url, timeout=30)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')

            # Slate structure
            transcript_elem = soup.find('div', class_='transcript') or \
                            soup.find('div', class_='episode-content') or \
                            soup.find('article')

            if transcript_elem:
                transcript_content = transcript_elem.get_text(separator='\n', strip=True)

                if len(transcript_content) > 500:
                    title_elem = soup.find('h1')
                    title = title_elem.get_text(strip=True) if title_elem else "Slate Podcast Episode"

                    return {
                        "title": title,
                        "transcript": transcript_content,
                        "word_count": len(transcript_content.split()),
                        "source": "slate.com",
                        "url": episode_url
                    }

            return None

        except Exception as e:
            logger.error(f"Failed to scrape Slate transcript from {episode_url}: {e}")
            return None


class NetworkTranscriptProcessor:
    """Processes podcasts using network-specific scrapers"""

    def __init__(self, atlas_root: Path):
        self.atlas_root = atlas_root
        self.podcasts_dir = atlas_root / "output" / "podcasts"

        # Initialize scrapers
        self.npr_scraper = NPRTranscriptScraper()
        self.radiolab_scraper = RadiolabTranscriptScraper()
        self.slate_scraper = SlateTranscriptScraper()

    def identify_podcast_network(self, podcast_source: str, podcast_title: str) -> Optional[str]:
        """Identify which network a podcast belongs to"""

        source_lower = podcast_source.lower()
        title_lower = podcast_title.lower()

        # NPR network
        if any(indicator in source_lower for indicator in ['npr.org', 'thisamericanlife.org']):
            if 'this american life' in title_lower:
                return 'this_american_life'
            elif 'planet money' in title_lower:
                return 'planet_money'
            else:
                return 'npr_general'

        # Radiolab/WNYC
        if any(indicator in source_lower for indicator in ['radiolab.org', 'wnycstudios.org']):
            return 'radiolab'

        # Slate
        if 'slate.com' in source_lower:
            return 'slate'

        return None

    def get_episode_webpage_url(self, episode_metadata: Dict) -> Optional[str]:
        """Extract episode webpage URL from metadata"""

        raw_data = episode_metadata.get("raw_data", {})

        # Try different fields for episode URL
        url_candidates = [
            raw_data.get("link", ""),
            raw_data.get("url", ""),
            raw_data.get("guid", ""),
            episode_metadata.get("source", "")
        ]

        for url in url_candidates:
            if url and url.startswith('http') and not url.endswith('.mp3') and not url.endswith('.m4a'):
                return url

        return None

    def process_network_podcasts(self, limit: Optional[int] = None) -> Dict:
        """Process podcasts that belong to known networks"""

        results = {
            "total_processed": 0,
            "transcripts_found": 0,
            "space_freed_mb": 0,
            "by_network": {},
            "errors": []
        }

        # Load all episodes
        processed_count = 0

        for metadata_file in self.podcasts_dir.glob("*_rss_entry.json"):
            if limit and processed_count >= limit:
                break

            try:
                episode_id = metadata_file.stem.replace("_rss_entry", "")

                with open(metadata_file) as f:
                    metadata = json.load(f)

                # Check if we already have a substantial transcript
                transcript_file = self.podcasts_dir / "markdown" / f"{episode_id}.md"
                if transcript_file.exists() and transcript_file.stat().st_size > 5000:
                    continue  # Skip if we already have a transcript

                # Identify network
                podcast_source = metadata.get("source", "")
                podcast_title = self._extract_podcast_title(metadata)

                network = self.identify_podcast_network(podcast_source, podcast_title)

                if network:
                    results["total_processed"] += 1
                    processed_count += 1

                    if network not in results["by_network"]:
                        results["by_network"][network] = {"processed": 0, "transcripts": 0}

                    results["by_network"][network]["processed"] += 1

                    # Get episode URL
                    episode_url = self.get_episode_webpage_url(metadata)

                    if episode_url:
                        logger.info(f"Processing {network} episode: {podcast_title}")

                        # Scrape transcript based on network
                        transcript_data = self._scrape_by_network(network, episode_url)

                        if transcript_data:
                            # Save transcript
                            markdown_content = self._format_network_transcript(transcript_data, metadata)

                            with open(transcript_file, 'w', encoding='utf-8') as f:
                                f.write(markdown_content)

                            results["transcripts_found"] += 1
                            results["by_network"][network]["transcripts"] += 1

                            # Delete audio file to free space
                            space_freed = self._delete_audio_file(episode_id)
                            results["space_freed_mb"] += space_freed

                            logger.info(f"Saved transcript for {podcast_title} (freed {space_freed}MB)")

                        # Rate limiting
                        time.sleep(2)

            except Exception as e:
                error_msg = f"Error processing {metadata_file}: {e}"
                logger.error(error_msg)
                results["errors"].append(error_msg)

        return results

    def _extract_podcast_title(self, metadata: Dict) -> str:
        """Extract podcast title from metadata"""
        raw_data = metadata.get("raw_data", {})
        return raw_data.get("author", raw_data.get("title", "Unknown")).split(":")[0]

    def _scrape_by_network(self, network: str, episode_url: str) -> Optional[Dict]:
        """Scrape transcript using appropriate network scraper"""

        if network == 'this_american_life':
            return self.npr_scraper.scrape_this_american_life(episode_url)
        elif network in ['planet_money', 'npr_general']:
            return self.npr_scraper.scrape_planet_money(episode_url)
        elif network == 'radiolab':
            return self.radiolab_scraper.scrape_radiolab(episode_url)
        elif network == 'slate':
            return self.slate_scraper.scrape_slate_podcast(episode_url)

        return None

    def _format_network_transcript(self, transcript_data: Dict, metadata: Dict) -> str:
        """Format network transcript as markdown"""

        raw_data = metadata.get("raw_data", {})

        return f"""---
title: "{transcript_data.get('title', 'Unknown Episode')}"
type: network_podcast_transcript
source: {transcript_data.get('source', 'unknown')}
word_count: {transcript_data.get('word_count', 0)}
published: "{raw_data.get('published', 'Unknown')}"
duration: "{raw_data.get('itunes_duration', 'Unknown')}"
scraped_from: {transcript_data.get('source', 'unknown')}
original_url: {transcript_data.get('url', '')}
scraped_at: {time.strftime('%Y-%m-%d %H:%M:%S')}
---

# {transcript_data.get('title', 'Podcast Episode')}

**Published:** {raw_data.get('published', 'Unknown')}
**Duration:** {raw_data.get('itunes_duration', 'Unknown')}
**Source:** {transcript_data.get('source', 'Unknown')}

## Episode Description

{raw_data.get('summary', 'No description available').strip()}

## Transcript

{transcript_data.get('transcript', 'No transcript available')}
"""

    def _delete_audio_file(self, episode_id: str) -> float:
        """Delete audio file and return space freed in MB"""

        space_freed = 0

        for ext in [".mp3", ".m4a"]:
            audio_file = self.podcasts_dir / "audio" / f"{episode_id}{ext}"
            if audio_file.exists():
                size_mb = audio_file.stat().st_size / (1024 * 1024)
                audio_file.unlink()
                space_freed += size_mb

        return round(space_freed, 2)


def main():
    """Test network transcript scrapers"""
    atlas_root = Path("/home/ubuntu/dev/atlas")
    processor = NetworkTranscriptProcessor(atlas_root)

    print("🎯 Network Transcript Processing")
    print("📊 Processing podcasts from major networks with professional transcripts...")

    # Process network podcasts
    results = processor.process_network_podcasts(limit=20)  # Test with 20 episodes

    print(f"\n✅ Results:")
    print(f"   Episodes processed: {results['total_processed']}")
    print(f"   Transcripts found: {results['transcripts_found']}")
    print(f"   Space freed: {results['space_freed_mb']} MB")

    print(f"\n📊 By Network:")
    for network, stats in results['by_network'].items():
        success_rate = (stats['transcripts'] / stats['processed']) * 100 if stats['processed'] > 0 else 0
        print(f"   {network}: {stats['transcripts']}/{stats['processed']} ({success_rate:.1f}% success)")

    if results['errors']:
        print(f"\n❌ Errors ({len(results['errors'])}):")
        for error in results['errors'][:3]:
            print(f"   - {error}")


if __name__ == "__main__":
    main()