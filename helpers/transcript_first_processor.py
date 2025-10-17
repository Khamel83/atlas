#!/usr/bin/env python3
"""
Transcript-First Podcast Processor

Solves the space problem by prioritizing transcripts over audio storage.
Only downloads/keeps audio for specifically flagged podcasts where you want physical media.

Strategy:
1. Check for existing professional transcripts first
2. If found, scrape transcript + metadata (no audio download)
3. If not found, evaluate if audio is worth keeping vs transcribing
4. Delete audio after transcription for most podcasts
5. Keep audio only for "physical media priority" podcasts

This eliminates the 64GB+ audio storage problem while maximizing searchable content.
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Set
import requests
from bs4 import BeautifulSoup
import time
import logging
from urllib.parse import urljoin

from universal_transcript_discoverer import UniversalTranscriptDiscoverer
from atp_transcript_scraper import ATPTranscriptScraper

logger = logging.getLogger(__name__)

class TranscriptFirstProcessor:
    """Process podcasts prioritizing transcripts over audio storage"""

    def __init__(self, atlas_root: Path):
        self.atlas_root = atlas_root
        self.podcasts_dir = atlas_root / "output" / "podcasts"
        self.discoverer = UniversalTranscriptDiscoverer(atlas_root)

        # Podcasts where we want to keep physical audio files
        self.physical_media_priority = {
            "this american life",
            "radiolab",
            "99% invisible",
            "serial",
            "s-town",
            "heavyweight",
            "the memory palace",
            "song exploder"
        }

        # Known transcript scrapers we can build
        self.transcript_scrapers = {
            "atp": ATPTranscriptScraper(),
            "this_american_life": None,  # Will build
            "npr": None,  # Will build
            "vox": None,  # Will build
            "slate": None  # Will build
        }

    def should_keep_audio(self, podcast_title: str) -> bool:
        """Determine if we should keep audio files for this podcast"""
        title_lower = podcast_title.lower()

        for priority_podcast in self.physical_media_priority:
            if priority_podcast in title_lower:
                return True

        return False

    def load_existing_episodes(self) -> Dict[str, Dict]:
        """Load all existing podcast episode metadata"""
        episodes = {}

        for metadata_file in self.podcasts_dir.glob("*_rss_entry.json"):
            try:
                episode_id = metadata_file.stem.replace("_rss_entry", "")

                with open(metadata_file) as f:
                    data = json.load(f)

                episodes[episode_id] = {
                    "metadata": data,
                    "has_audio": (self.podcasts_dir / "audio" / f"{episode_id}.mp3").exists() or
                                (self.podcasts_dir / "audio" / f"{episode_id}.m4a").exists(),
                    "has_transcript": (self.podcasts_dir / "markdown" / f"{episode_id}.md").exists() and
                                    (self.podcasts_dir / "markdown" / f"{episode_id}.md").stat().st_size > 5000,
                    "podcast_source": data.get("source", ""),
                    "podcast_title": self._extract_podcast_title(data)
                }

            except Exception as e:
                logger.warning(f"Failed to load episode {metadata_file}: {e}")

        return episodes

    def _extract_podcast_title(self, metadata: Dict) -> str:
        """Extract podcast title from metadata"""
        raw_data = metadata.get("raw_data", {})

        # Try different fields for podcast title
        title_candidates = [
            raw_data.get("podcast_title", ""),
            raw_data.get("author", ""),
            metadata.get("source", "").split('/')[-1],
            raw_data.get("title", "").split(":")[0] if ":" in raw_data.get("title", "") else ""
        ]

        for candidate in title_candidates:
            if candidate and len(candidate) > 3:
                return candidate

        return "Unknown Podcast"

    def analyze_storage_by_podcast(self) -> Dict:
        """Analyze current storage usage by podcast"""
        episodes = self.load_existing_episodes()

        podcast_stats = {}

        for episode_id, episode_data in episodes.items():
            podcast_title = episode_data["podcast_title"]

            if podcast_title not in podcast_stats:
                podcast_stats[podcast_title] = {
                    "episode_count": 0,
                    "episodes_with_audio": 0,
                    "episodes_with_transcripts": 0,
                    "audio_size_mb": 0,
                    "should_keep_audio": self.should_keep_audio(podcast_title),
                    "space_saveable_mb": 0,
                    "episode_ids": []
                }

            stats = podcast_stats[podcast_title]
            stats["episode_count"] += 1
            stats["episode_ids"].append(episode_id)

            if episode_data["has_audio"]:
                stats["episodes_with_audio"] += 1

                # Calculate audio file size
                for ext in [".mp3", ".m4a"]:
                    audio_file = self.podcasts_dir / "audio" / f"{episode_id}{ext}"
                    if audio_file.exists():
                        size_mb = audio_file.stat().st_size / (1024 * 1024)
                        stats["audio_size_mb"] += size_mb

                        # If we shouldn't keep audio, this is saveable space
                        if not stats["should_keep_audio"]:
                            stats["space_saveable_mb"] += size_mb

            if episode_data["has_transcript"]:
                stats["episodes_with_transcripts"] += 1

        return podcast_stats

    def prioritize_transcript_processing(self, podcast_stats: Dict) -> List[Dict]:
        """Create priority list for transcript processing"""

        priorities = []

        for podcast_title, stats in podcast_stats.items():
            episodes_without_transcripts = stats["episode_count"] - stats["episodes_with_transcripts"]

            if episodes_without_transcripts > 0:
                priority = {
                    "podcast_title": podcast_title,
                    "episodes_needing_transcripts": episodes_without_transcripts,
                    "total_episodes": stats["episode_count"],
                    "audio_size_mb": stats["audio_size_mb"],
                    "space_saveable_mb": stats["space_saveable_mb"],
                    "should_keep_audio": stats["should_keep_audio"],
                    "episode_ids": stats["episode_ids"],
                    "priority_score": self._calculate_priority_score(stats, episodes_without_transcripts)
                }

                priorities.append(priority)

        # Sort by priority score (highest first)
        priorities.sort(key=lambda x: x["priority_score"], reverse=True)

        return priorities

    def _calculate_priority_score(self, stats: Dict, episodes_without_transcripts: int) -> float:
        """Calculate priority score for transcript processing"""

        # Base score: number of episodes needing transcripts
        score = episodes_without_transcripts * 10

        # Bonus for space savings (if we can delete audio after)
        if not stats["should_keep_audio"]:
            score += stats["space_saveable_mb"] / 10  # 1 point per 10MB saveable

        # Bonus for podcasts with lots of existing audio (big impact)
        score += stats["audio_size_mb"] / 100  # 1 point per 100MB

        # Penalty for podcasts we want to keep audio (lower priority)
        if stats["should_keep_audio"]:
            score *= 0.5

        return score

    def build_transcript_scraper(self, podcast_title: str, sample_urls: List[str]) -> Optional[callable]:
        """Build a custom transcript scraper for a specific podcast"""

        # Check if it's a known podcast type
        title_lower = podcast_title.lower()

        if "this american life" in title_lower:
            return self._build_tal_scraper()
        elif "npr" in title_lower or "planet money" in title_lower:
            return self._build_npr_scraper()
        elif "radiolab" in title_lower:
            return self._build_radiolab_scraper()
        elif "slate" in title_lower:
            return self._build_slate_scraper()
        else:
            # Try to build a generic scraper based on sample URLs
            return self._build_generic_scraper(sample_urls)

    def _build_tal_scraper(self) -> callable:
        """Build This American Life transcript scraper"""
        def scrape_tal_transcript(episode_url: str) -> Optional[str]:
            try:
                response = requests.get(episode_url, timeout=30)
                response.raise_for_status()

                soup = BeautifulSoup(response.content, 'html.parser')

                # TAL transcript structure
                transcript_elem = soup.find('div', class_='transcript') or \
                                soup.find('div', id='transcript') or \
                                soup.find('article')

                if transcript_elem:
                    return transcript_elem.get_text(separator='\n', strip=True)

                return None
            except Exception as e:
                logger.error(f"Failed to scrape TAL transcript from {episode_url}: {e}")
                return None

        return scrape_tal_transcript

    def _build_npr_scraper(self) -> callable:
        """Build NPR/Planet Money transcript scraper"""
        def scrape_npr_transcript(episode_url: str) -> Optional[str]:
            try:
                response = requests.get(episode_url, timeout=30)
                response.raise_for_status()

                soup = BeautifulSoup(response.content, 'html.parser')

                # NPR transcript structure
                transcript_elem = soup.find('div', class_='transcript') or \
                                soup.find('div', id='storytext') or \
                                soup.find('article', class_='story')

                if transcript_elem:
                    return transcript_elem.get_text(separator='\n', strip=True)

                return None
            except Exception as e:
                logger.error(f"Failed to scrape NPR transcript from {episode_url}: {e}")
                return None

        return scrape_npr_transcript

    def _build_radiolab_scraper(self) -> callable:
        """Build Radiolab transcript scraper"""
        def scrape_radiolab_transcript(episode_url: str) -> Optional[str]:
            try:
                response = requests.get(episode_url, timeout=30)
                response.raise_for_status()

                soup = BeautifulSoup(response.content, 'html.parser')

                # Radiolab transcript structure (WNYC)
                transcript_elem = soup.find('div', class_='transcript') or \
                                soup.find('div', class_='story-text') or \
                                soup.find('article')

                if transcript_elem:
                    return transcript_elem.get_text(separator='\n', strip=True)

                return None
            except Exception as e:
                logger.error(f"Failed to scrape Radiolab transcript from {episode_url}: {e}")
                return None

        return scrape_radiolab_transcript

    def _build_generic_scraper(self, sample_urls: List[str]) -> Optional[callable]:
        """Build a generic scraper by analyzing sample URLs"""
        # This would analyze the structure of sample episode pages
        # and build a custom scraper - simplified for now

        def scrape_generic_transcript(episode_url: str) -> Optional[str]:
            try:
                response = requests.get(episode_url, timeout=30)
                response.raise_for_status()

                soup = BeautifulSoup(response.content, 'html.parser')

                # Try common transcript selectors
                selectors = [
                    '.transcript',
                    '#transcript',
                    '.episode-transcript',
                    'article',
                    '.content',
                    '.story-text',
                    '.episode-content'
                ]

                for selector in selectors:
                    elem = soup.select_one(selector)
                    if elem:
                        text = elem.get_text(separator='\n', strip=True)
                        if len(text) > 1000:  # Minimum length check
                            return text

                return None
            except Exception as e:
                logger.error(f"Failed to scrape generic transcript from {episode_url}: {e}")
                return None

        return scrape_generic_transcript

    def process_podcast_for_transcripts(self, podcast_priority: Dict) -> Dict:
        """Process a single podcast to get transcripts and free space"""

        results = {
            "podcast_title": podcast_priority["podcast_title"],
            "episodes_processed": 0,
            "transcripts_obtained": 0,
            "audio_files_deleted": 0,
            "space_freed_mb": 0,
            "errors": []
        }

        # Try to get professional transcripts first via discovery
        logger.info(f"Processing {podcast_priority['podcast_title']} for transcripts...")

        # For now, focus on space savings by deleting audio where we have transcripts
        for episode_id in podcast_priority["episode_ids"]:
            try:
                results["episodes_processed"] += 1

                # Check if we already have a transcript
                transcript_file = self.podcasts_dir / "markdown" / f"{episode_id}.md"
                has_substantial_transcript = transcript_file.exists() and transcript_file.stat().st_size > 5000

                # If we have a transcript and shouldn't keep audio, delete audio
                if has_substantial_transcript and not podcast_priority["should_keep_audio"]:

                    for ext in [".mp3", ".m4a"]:
                        audio_file = self.podcasts_dir / "audio" / f"{episode_id}{ext}"
                        if audio_file.exists():
                            size_mb = audio_file.stat().st_size / (1024 * 1024)
                            audio_file.unlink()  # Delete the audio file

                            results["audio_files_deleted"] += 1
                            results["space_freed_mb"] += size_mb

                            logger.info(f"Deleted audio for {episode_id} (freed {size_mb:.1f}MB)")

                if has_substantial_transcript:
                    results["transcripts_obtained"] += 1

            except Exception as e:
                error_msg = f"Error processing episode {episode_id}: {e}"
                logger.error(error_msg)
                results["errors"].append(error_msg)

        results["space_freed_mb"] = round(results["space_freed_mb"], 2)
        return results


def main():
    """Run transcript-first processing"""
    atlas_root = Path("/home/ubuntu/dev/atlas")
    processor = TranscriptFirstProcessor(atlas_root)

    print("🎯 Transcript-First Podcast Processing")
    print("📊 Analyzing storage and prioritizing transcript processing...")

    # Analyze current storage
    podcast_stats = processor.analyze_storage_by_podcast()

    # Calculate total savings potential
    total_saveable_mb = sum(stats["space_saveable_mb"] for stats in podcast_stats.values())
    total_audio_mb = sum(stats["audio_size_mb"] for stats in podcast_stats.values())

    print(f"\n📊 Storage Analysis:")
    print(f"   Total audio storage: {total_audio_mb:.1f} MB ({total_audio_mb/1024:.1f} GB)")
    print(f"   Potential space savings: {total_saveable_mb:.1f} MB ({total_saveable_mb/1024:.1f} GB)")
    print(f"   Space savings %: {(total_saveable_mb/total_audio_mb)*100:.1f}%")

    # Get processing priorities
    priorities = processor.prioritize_transcript_processing(podcast_stats)

    print(f"\n🎯 Top 10 Priorities for Transcript Processing:")
    for i, priority in enumerate(priorities[:10], 1):
        print(f"   {i}. {priority['podcast_title']}")
        print(f"      Episodes needing transcripts: {priority['episodes_needing_transcripts']}")
        print(f"      Space saveable: {priority['space_saveable_mb']:.1f} MB")
        print(f"      Keep audio: {priority['should_keep_audio']}")

    # Process top priorities for immediate space savings
    print(f"\n🚀 Processing top 3 podcasts for immediate space savings...")

    total_freed = 0
    for priority in priorities[:3]:
        if priority["space_saveable_mb"] > 100:  # Only process if significant savings
            results = processor.process_podcast_for_transcripts(priority)

            print(f"\n✅ {results['podcast_title']}:")
            print(f"   Episodes processed: {results['episodes_processed']}")
            print(f"   Audio files deleted: {results['audio_files_deleted']}")
            print(f"   Space freed: {results['space_freed_mb']} MB")

            total_freed += results['space_freed_mb']

    print(f"\n🎉 Total space freed: {total_freed:.1f} MB ({total_freed/1024:.1f} GB)")


if __name__ == "__main__":
    main()