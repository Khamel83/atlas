#!/usr/bin/env python3
"""
Known Transcript Sources Registry

Centralized registry of podcast transcript sources with metadata and scraper mappings.
This system manages all known sources where transcripts can be reliably found.
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
import json
import re
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

@dataclass
class TranscriptSource:
    """Metadata for a known transcript source"""
    podcast_name: str
    source_domain: str
    scraper_module: str
    scraper_class: str
    priority: int = 1  # 1=highest, 5=lowest
    confidence: str = "high"  # high, medium, low
    coverage: str = "full"  # full, partial, selective
    notes: str = ""
    indicators: List[str] = None  # Text patterns to identify this podcast

    def __post_init__(self):
        if self.indicators is None:
            self.indicators = []

class KnownTranscriptSourcesRegistry:
    """Registry for managing known transcript sources"""

    def __init__(self):
        self.sources: Dict[str, TranscriptSource] = {}
        self._initialize_known_sources()

    def _initialize_known_sources(self):
        """Initialize the registry with known sources"""

        # Accidental Tech Podcast
        self.add_source(TranscriptSource(
            podcast_name="Accidental Tech Podcast",
            source_domain="catatp.fm",
            scraper_module="helpers.atp_transcript_scraper",
            scraper_class="ATPTranscriptScraper",
            priority=1,
            confidence="high",
            coverage="full",
            notes="Complete transcripts for all episodes available at catatp.fm",
            indicators=[
                "accidental tech podcast",
                "atp.fm",
                "atp",
                "marco arment",
                "casey liss",
                "john siracusa"
            ]
        ))

        # This American Life
        self.add_source(TranscriptSource(
            podcast_name="This American Life",
            source_domain="thisamericanlife.org",
            scraper_module="helpers.tal_transcript_scraper",
            scraper_class="TALTranscriptScraper",
            priority=1,
            confidence="high",
            coverage="full",
            notes="Official transcripts available for most episodes",
            indicators=[
                "this american life",
                "tal",
                "ira glass",
                "thisamericanlife"
            ]
        ))

        # 99% Invisible
        self.add_source(TranscriptSource(
            podcast_name="99% Invisible",
            source_domain="99percentinvisible.org",
            scraper_module="helpers.ninety_nine_pi_scraper",
            scraper_class="NinetyNinePITranscriptScraper",
            priority=1,
            confidence="high",
            coverage="partial",
            notes="Transcripts available for many episodes on the website",
            indicators=[
                "99% invisible",
                "99 percent invisible",
                "99pi",
                "roman mars",
                "99percentinvisible"
            ]
        ))

        # Add more sources as they become available
        self._add_additional_sources()

    def _add_additional_sources(self):
        """Add additional known sources"""

        # Radiolab
        self.add_source(TranscriptSource(
            podcast_name="Radiolab",
            source_domain="radiolab.org",
            scraper_module="helpers.generic_transcript_scraper",
            scraper_class="GenericTranscriptScraper",
            priority=2,
            confidence="medium",
            coverage="partial",
            notes="Some episodes have transcripts on radiolab.org",
            indicators=[
                "radiolab",
                "jad abumrad",
                "robert krulwich"
            ]
        ))

        # NPR shows (general)
        self.add_source(TranscriptSource(
            podcast_name="NPR Shows",
            source_domain="npr.org",
            scraper_module="helpers.generic_transcript_scraper",
            scraper_class="GenericTranscriptScraper",
            priority=2,
            confidence="medium",
            coverage="selective",
            notes="Some NPR shows have transcripts available on npr.org",
            indicators=[
                "npr",
                "national public radio",
                "npr.org"
            ]
        ))

        # Freakonomics
        self.add_source(TranscriptSource(
            podcast_name="Freakonomics Radio",
            source_domain="freakonomics.com",
            scraper_module="helpers.generic_transcript_scraper",
            scraper_class="GenericTranscriptScraper",
            priority=2,
            confidence="medium",
            coverage="partial",
            notes="Transcripts available for many episodes",
            indicators=[
                "freakonomics",
                "stephen dubner"
            ]
        ))

    def add_source(self, source: TranscriptSource):
        """Add a transcript source to the registry"""
        key = source.podcast_name.lower().replace(' ', '_')
        self.sources[key] = source
        logger.info(f"Added transcript source: {source.podcast_name} -> {source.source_domain}")

    def get_source_by_podcast(self, podcast_name: str) -> Optional[TranscriptSource]:
        """Get transcript source by podcast name"""
        key = podcast_name.lower().replace(' ', '_')
        return self.sources.get(key)

    def identify_podcast_source(self, podcast_name: str, episode_title: str = "") -> Optional[TranscriptSource]:
        """Identify the appropriate transcript source for a podcast"""

        combined_text = f"{podcast_name} {episode_title}".lower()

        # First try exact podcast name matching
        exact_match = self.get_source_by_podcast(podcast_name)
        if exact_match:
            return exact_match

        # Then try indicator-based matching
        best_match = None
        best_score = 0

        for source in self.sources.values():
            score = 0
            for indicator in source.indicators:
                if indicator.lower() in combined_text:
                    score += 1

            # Weight by priority (lower priority number = higher weight)
            weighted_score = score * (6 - source.priority)

            if weighted_score > best_score:
                best_score = weighted_score
                best_match = source

        return best_match if best_score > 0 else None

    def get_scraper_for_source(self, source: TranscriptSource):
        """Get scraper instance for a transcript source"""
        try:
            import importlib
            module = importlib.import_module(source.scraper_module)
            scraper_class = getattr(module, source.scraper_class)
            return scraper_class()
        except (ImportError, AttributeError) as e:
            logger.error(f"Failed to load scraper {source.scraper_class} from {source.scraper_module}: {e}")
            return None

    def list_sources(self, priority_filter: Optional[int] = None) -> List[TranscriptSource]:
        """List all sources, optionally filtered by priority"""
        sources = list(self.sources.values())

        if priority_filter is not None:
            sources = [s for s in sources if s.priority <= priority_filter]

        # Sort by priority (ascending) then by podcast name
        sources.sort(key=lambda x: (x.priority, x.podcast_name))
        return sources

    def get_sources_by_domain(self, domain: str) -> List[TranscriptSource]:
        """Get all sources from a specific domain"""
        return [s for s in self.sources.values() if domain.lower() in s.source_domain.lower()]

    def export_registry(self) -> Dict[str, Any]:
        """Export registry as JSON-serializable dict"""
        return {
            "sources": {key: asdict(source) for key, source in self.sources.items()},
            "total_sources": len(self.sources),
            "domains": list(set(s.source_domain for s in self.sources.values()))
        }

    def get_statistics(self) -> Dict[str, Any]:
        """Get registry statistics"""
        sources = list(self.sources.values())

        by_priority = {}
        by_confidence = {}
        by_coverage = {}

        for source in sources:
            by_priority[source.priority] = by_priority.get(source.priority, 0) + 1
            by_confidence[source.confidence] = by_confidence.get(source.confidence, 0) + 1
            by_coverage[source.coverage] = by_coverage.get(source.coverage, 0) + 1

        return {
            "total_sources": len(sources),
            "by_priority": by_priority,
            "by_confidence": by_confidence,
            "by_coverage": by_coverage,
            "domains": list(set(s.source_domain for s in sources)),
            "high_priority_sources": len([s for s in sources if s.priority == 1])
        }

# Global registry instance
_registry = None

def get_registry() -> KnownTranscriptSourcesRegistry:
    """Get the global transcript sources registry instance"""
    global _registry
    if _registry is None:
        _registry = KnownTranscriptSourcesRegistry()
    return _registry

def get_known_sources_registry() -> KnownTranscriptSourcesRegistry:
    """Get the global transcript sources registry instance (alias for compatibility)"""
    return get_registry()

def identify_transcript_source(podcast_name: str, episode_title: str = "") -> Optional[TranscriptSource]:
    """Convenience function to identify transcript source"""
    registry = get_registry()
    return registry.identify_podcast_source(podcast_name, episode_title)

def get_scraper_for_podcast(podcast_name: str, episode_title: str = ""):
    """Convenience function to get scraper for a podcast"""
    source = identify_transcript_source(podcast_name, episode_title)
    if source:
        registry = get_registry()
        return registry.get_scraper_for_source(source)
    return None

def list_all_sources() -> List[TranscriptSource]:
    """Convenience function to list all sources"""
    registry = get_registry()
    return registry.list_sources()

def main():
    """Test and demonstrate the registry system"""
    print("🗂️ Known Transcript Sources Registry")
    print("=" * 50)

    registry = get_registry()

    # Show statistics
    stats = registry.get_statistics()
    print(f"\n📊 Registry Statistics:")
    print(f"Total sources: {stats['total_sources']}")
    print(f"High priority sources: {stats['high_priority_sources']}")
    print(f"Domains: {', '.join(stats['domains'])}")

    # List all sources
    print(f"\n📋 All Known Sources:")
    sources = registry.list_sources()
    for source in sources:
        print(f"  {source.podcast_name:25} -> {source.source_domain:20} (P{source.priority}, {source.confidence})")

    # Test identification
    print(f"\n🔍 Testing Source Identification:")
    test_cases = [
        ("Accidental Tech Podcast", "655: Shorts-Compatible Body Type"),
        ("This American Life", "785: The Wedding We Never Had"),
        ("99% Invisible", "501: The Kipple"),
        ("Unknown Podcast", "Some Episode")
    ]

    for podcast_name, episode_title in test_cases:
        source = registry.identify_podcast_source(podcast_name, episode_title)
        if source:
            print(f"  '{podcast_name}' -> {source.source_domain} ({source.scraper_class})")
        else:
            print(f"  '{podcast_name}' -> No known source")

    # Test scraper loading
    print(f"\n🛠️ Testing Scraper Loading:")
    atp_source = registry.get_source_by_podcast("Accidental Tech Podcast")
    if atp_source:
        scraper = registry.get_scraper_for_source(atp_source)
        if scraper:
            print(f"  ✅ Successfully loaded {atp_source.scraper_class}")
        else:
            print(f"  ❌ Failed to load {atp_source.scraper_class}")

if __name__ == "__main__":
    main()