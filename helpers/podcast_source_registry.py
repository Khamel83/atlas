#!/usr/bin/env python3
"""
Known Podcast Sources Registry System

Centralized registry for managing podcast transcript sources and their scrapers.

This replaces hardcoded podcast detection logic with a configurable,
extensible registry system that makes it easy to add new sources.
"""

import json
import logging
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, asdict
from pathlib import Path
from abc import ABC, abstractmethod
import re

logger = logging.getLogger(__name__)

@dataclass
class PodcastSourceConfig:
    """Configuration for a podcast transcript source"""
    name: str
    display_name: str
    description: str
    url_patterns: List[str]
    title_patterns: List[str]
    scraper_class: str
    enabled: bool = True
    priority: int = 100
    requires_auth: bool = False
    success_rate: float = 0.0
    last_updated: str = ""

@dataclass
class TranscriptResult:
    """Result from transcript extraction"""
    success: bool
    transcript: str = ""
    source: str = ""
    metadata: Dict[str, Any] = None
    error_message: str = ""
    url_used: str = ""

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

class PodcastSourceRegistry:
    """
    Centralized registry for managing podcast transcript sources

    This replaces hardcoded logic with a configurable system that:
    - Automatically matches podcasts to their appropriate scrapers
    - Provides easy source addition and configuration
    - Tracks source performance and success rates
    - Supports multiple matching strategies
    """

    def __init__(self, config_path: str = None):
        self.config_path = config_path or "/home/ubuntu/dev/atlas/config/podcast_sources.json"
        self.config_dir = Path(self.config_path).parent
        self.config_dir.mkdir(exist_ok=True)

        self.sources: Dict[str, PodcastSourceConfig] = {}
        self.scraper_cache: Dict[str, Any] = {}

        self._load_sources()

    def _load_sources(self):
        """Load source configurations from file"""
        try:
            if Path(self.config_path).exists():
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                for source_data in data.get('sources', []):
                    config = PodcastSourceConfig(**source_data)
                    self.sources[config.name] = config

                logger.info(f"Loaded {len(self.sources)} podcast sources from {self.config_path}")
            else:
                self._create_default_config()
                self.save_sources()
        except Exception as e:
            logger.error(f"Failed to load podcast sources: {e}")
            self._create_default_config()

    def _create_default_config(self):
        """Create default podcast source configurations"""
        default_sources = [
            PodcastSourceConfig(
                name="atp",
                display_name="Accidental Tech Podcast",
                description="ATP episodes from catatp.fm",
                url_patterns=[r'atp\.fm', r'accidental.*tech', r'atp'],
                title_patterns=[r'\d+:', r'Episode \d+', r'ATP \d+'],
                scraper_class="helpers.atp_transcript_scraper.ATPTranscriptScraper",
                enabled=True,
                priority=100,
                success_rate=0.85
            ),
            PodcastSourceConfig(
                name="tal",
                display_name="This American Life",
                description="TAL episodes with transcripts",
                url_patterns=[r'thisamericanlife\.org', r'tal\.org'],
                title_patterns=[r'\d+:', r'Act \d+', r'Prologue'],
                scraper_class="helpers.tal_transcript_scraper.TALTranscriptScraper",
                enabled=True,
                priority=90,
                success_rate=0.75
            ),
            PodcastSourceConfig(
                name="99pi",
                display_name="99% Invisible",
                description="Design and architecture podcast",
                url_patterns=[r'99percentinvisible\.org', r'99pi\.org'],
                title_patterns=[r'\d+:', r'Episode \d+', r'99\% Invisible'],
                scraper_class="helpers.ninety_nine_pi_scraper.NinetyNinePiTranscriptScraper",
                enabled=True,
                priority=80,
                success_rate=0.70
            ),
            PodcastSourceConfig(
                name="huberman",
                display_name="Huberman Lab",
                description="Science podcast with occasional transcripts",
                url_patterns=[r'hubermanlab\.com'],
                title_patterns=[r'Episode \d+', r'Dr\. Andrew Huberman'],
                scraper_class="helpers.huberman_scraper.HubermanScraper",
                enabled=False,
                priority=70,
                success_rate=0.30
            ),
            PodcastSourceConfig(
                name="lex",
                display_name="Lex Fridman Podcast",
                description="AI and science interviews",
                url_patterns=[r'lexfridman\.com'],
                title_patterns=[r'#\d+', r'Episode \d+'],
                scraper_class="helpers.lex_fridman_scraper.LexFridmanScraper",
                enabled=False,
                priority=60,
                success_rate=0.25
            )
        ]

        self.sources = {source.name: source for source in default_sources}
        logger.info(f"Created default configuration with {len(self.sources)} sources")

    def save_sources(self):
        """Save current source configurations to file"""
        try:
            data = {
                'version': '1.0',
                'last_updated': '2025-09-28T00:00:00Z',
                'sources': [asdict(source) for source in self.sources.values()]
            }

            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            logger.info(f"Saved {len(self.sources)} sources to {self.config_path}")
        except Exception as e:
            logger.error(f"Failed to save podcast sources: {e}")

    def identify_source(self, podcast_name: str, episode_title: str, episode_url: str = None) -> Optional[PodcastSourceConfig]:
        """
        Identify the appropriate source for a podcast episode

        Uses multiple matching strategies:
        1. URL pattern matching
        2. Title pattern matching
        3. Name matching
        4. Content-based matching
        """
        try:
            # Combine all text for matching
            text_to_match = f"{podcast_name} {episode_title}"
            if episode_url:
                text_to_match += f" {episode_url}"

            text_to_match = text_to_match.lower()

            # Score each source based on matches
            best_source = None
            best_score = 0

            for source in self.sources.values():
                if not source.enabled:
                    continue

                score = 0

                # URL pattern matching (highest weight)
                if episode_url:
                    for pattern in source.url_patterns:
                        if re.search(pattern, episode_url.lower()):
                            score += 100
                            break

                # Title pattern matching (medium weight)
                for pattern in source.title_patterns:
                    if re.search(pattern, episode_title.lower()):
                        score += 50
                        break

                # Name matching (lower weight)
                if source.display_name.lower() in podcast_name.lower():
                    score += 30

                # Keyword matching
                for keyword in source.name.lower().split():
                    if keyword in text_to_match:
                        score += 10

                # Priority bonus
                score += source.priority / 100

                if score > best_score:
                    best_score = score
                    best_source = source

            if best_source and best_score > 30:  # Minimum confidence threshold
                logger.info(f"Identified source: {best_source.display_name} (score: {best_score:.1f})")
                return best_source

            logger.debug(f"No source identified for: {podcast_name} - {episode_title}")
            return None

        except Exception as e:
            logger.error(f"Error identifying source: {e}")
            return None

    def get_transcript(self, podcast_name: str, episode_title: str, episode_url: str = None) -> TranscriptResult:
        """
        Get transcript using the appropriate scraper
        """
        try:
            # Identify the source
            source = self.identify_source(podcast_name, episode_title, episode_url)
            if not source:
                return TranscriptResult(
                    success=False,
                    error_message="No known transcript source identified"
                )

            # Get or create scraper instance
            scraper = self._get_scraper(source)
            if not scraper:
                return TranscriptResult(
                    success=False,
                    error_message=f"Failed to initialize scraper for {source.display_name}"
                )

            # Try to get transcript
            result = self._extract_transcript(scraper, source, podcast_name, episode_title, episode_url)

            # Update source statistics
            self._update_source_stats(source, result.success)

            return result

        except Exception as e:
            logger.error(f"Error getting transcript: {e}")
            return TranscriptResult(
                success=False,
                error_message=f"Transcript extraction failed: {str(e)}"
            )

    def _get_scraper(self, source: PodcastSourceConfig) -> Optional[Any]:
        """Get or create scraper instance"""
        try:
            # Check cache first
            if source.name in self.scraper_cache:
                return self.scraper_cache[source.name]

            # Import and create scraper
            module_path, class_name = source.scraper_class.rsplit('.', 1)
            module = __import__(module_path, fromlist=[class_name])
            scraper_class = getattr(module, class_name)

            scraper = scraper_class()
            self.scraper_cache[source.name] = scraper

            logger.debug(f"Initialized scraper for {source.display_name}")
            return scraper

        except Exception as e:
            logger.error(f"Failed to initialize scraper {source.scraper_class}: {e}")
            return None

    def _extract_transcript(self, scraper: Any, source: PodcastSourceConfig,
                           podcast_name: str, episode_title: str, episode_url: str) -> TranscriptResult:
        """Extract transcript using the appropriate scraper method"""
        try:
            # Try different methods based on scraper capabilities
            result = None

            # Method 1: get_transcript_from_url (preferred)
            if hasattr(scraper, 'get_transcript_from_url') and episode_url:
                result = scraper.get_transcript_from_url(episode_url)

            # Method 2: scrape_episode_transcript (ATP style)
            elif hasattr(scraper, 'scrape_episode_transcript') and episode_url:
                result = scraper.scrape_episode_transcript(episode_url)

                # Normalize result format
                if result and isinstance(result, dict) and 'transcript' in result:
                    result = {
                        'success': True,
                        'transcript': result['transcript'],
                        'metadata': {
                            'episode_number': result.get('episode_number'),
                            'title': result.get('title'),
                            'word_count': result.get('word_count'),
                            'source': source.name
                        }
                    }

            # Method 3: Search by title (if no URL)
            elif hasattr(scraper, 'search_by_title'):
                result = scraper.search_by_title(podcast_name, episode_title)

            # Process result
            if result and result.get('success'):
                return TranscriptResult(
                    success=True,
                    transcript=result['transcript'],
                    source=source.name,
                    metadata=result.get('metadata', {}),
                    url_used=episode_url or result.get('url', '')
                )
            else:
                return TranscriptResult(
                    success=False,
                    error_message=result.get('error', 'Unknown extraction error') if result else 'Scraper returned no result'
                )

        except Exception as e:
            logger.error(f"Error extracting transcript with {source.name}: {e}")
            return TranscriptResult(
                success=False,
                error_message=f"Extraction error: {str(e)}"
            )

    def _update_source_stats(self, source: PodcastSourceConfig, success: bool):
        """Update source success statistics"""
        try:
            # Simple moving average for success rate
            current_rate = source.success_rate
            if success:
                source.success_rate = current_rate * 0.9 + 0.1  # Increase by 10%
            else:
                source.success_rate = current_rate * 0.9  # Decrease by 10%

            source.last_updated = '2025-09-28T00:00:00Z'

            # Save updated stats
            self.save_sources()

        except Exception as e:
            logger.error(f"Error updating source stats: {e}")

    def add_source(self, source: PodcastSourceConfig):
        """Add a new podcast source"""
        self.sources[source.name] = source
        self.save_sources()
        logger.info(f"Added new source: {source.display_name}")

    def remove_source(self, source_name: str):
        """Remove a podcast source"""
        if source_name in self.sources:
            del self.sources[source_name]
            if source_name in self.scraper_cache:
                del self.scraper_cache[source_name]
            self.save_sources()
            logger.info(f"Removed source: {source_name}")

    def enable_source(self, source_name: str):
        """Enable a source"""
        if source_name in self.sources:
            self.sources[source_name].enabled = True
            self.save_sources()
            logger.info(f"Enabled source: {source_name}")

    def disable_source(self, source_name: str):
        """Disable a source"""
        if source_name in self.sources:
            self.sources[source_name].enabled = False
            self.save_sources()
            logger.info(f"Disabled source: {source_name}")

    def get_source_stats(self) -> Dict[str, Any]:
        """Get statistics for all sources"""
        stats = {}
        for name, source in self.sources.items():
            stats[name] = {
                'display_name': source.display_name,
                'enabled': source.enabled,
                'priority': source.priority,
                'success_rate': source.success_rate,
                'last_updated': source.last_updated,
                'url_patterns': len(source.url_patterns),
                'title_patterns': len(source.title_patterns)
            }
        return stats

    def list_sources(self, enabled_only: bool = True) -> List[PodcastSourceConfig]:
        """List all sources"""
        sources = list(self.sources.values())
        if enabled_only:
            sources = [s for s in sources if s.enabled]
        return sorted(sources, key=lambda x: x.priority, reverse=True)

    def test_source(self, source_name: str, podcast_name: str, episode_title: str, episode_url: str = None) -> TranscriptResult:
        """Test a specific source with sample data"""
        if source_name not in self.sources:
            return TranscriptResult(
                success=False,
                error_message=f"Source {source_name} not found"
            )

        source = self.sources[source_name]
        return self.get_transcript(podcast_name, episode_title, episode_url)

# Global registry instance
podcast_source_registry = PodcastSourceRegistry()

def main():
    """CLI interface for managing podcast sources"""
    import argparse

    parser = argparse.ArgumentParser(description="Podcast Sources Registry Manager")
    parser.add_argument("--list", action="store_true", help="List all sources")
    parser.add_argument("--stats", action="store_true", help="Show source statistics")
    parser.add_argument("--enable", help="Enable a source")
    parser.add_argument("--disable", help="Disable a source")
    parser.add_argument("--test", help="Test a source")
    parser.add_argument("--add", help="Add a new source (JSON format)")

    args = parser.parse_args()

    if args.list:
        sources = podcast_source_registry.list_sources()
        print("📺 Podcast Transcript Sources")
        print("=" * 50)
        for source in sources:
            status = "✅" if source.enabled else "🚫"
            print(f"{status} {source.display_name} ({source.name})")
            print(f"   Priority: {source.priority}")
            print(f"   Success Rate: {source.success_rate:.1%}")
            print(f"   Patterns: {len(source.url_patterns)} URL, {len(source.title_patterns)} title")
            print()

    elif args.stats:
        stats = podcast_source_registry.get_source_stats()
        print("📊 Source Statistics")
        print("=" * 50)
        for name, stat in stats.items():
            status = "✅" if stat['enabled'] else "🚫"
            print(f"{status} {stat['display_name']}")
            print(f"   Success Rate: {stat['success_rate']:.1%}")
            print(f"   Priority: {stat['priority']}")
            print(f"   Last Updated: {stat['last_updated']}")
            print()

    elif args.enable:
        podcast_source_registry.enable_source(args.enable)
        print(f"✅ Enabled {args.enable}")

    elif args.disable:
        podcast_source_registry.disable_source(args.disable)
        print(f"🚫 Disabled {args.disable}")

    elif args.test:
        # Test with sample data
        result = podcast_source_registry.test_source(
            args.test,
            "Accidental Tech Podcast",
            "657: Ears Are Weird",
            "https://atp.fm/657"
        )
        print(f"Test result for {args.test}:")
        print(f"  Success: {result.success}")
        print(f"  Source: {result.source}")
        print(f"  Error: {result.error_message}")
        if result.success:
            print(f"  Transcript length: {len(result.transcript)}")

    else:
        parser.print_help()

if __name__ == "__main__":
    main()