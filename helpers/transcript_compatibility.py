#!/usr/bin/env python3
"""
Transcript Processing Compatibility Layer

Handles the transition from 10 separate transcript modules to unified TranscriptManager.
Provides compatibility imports and migration utilities.

MIGRATION STATUS:
✅ TranscriptManager created (helpers/transcript_manager.py)
✅ Compatibility layer active
🔄 Gradual migration in progress
❌ Old modules will be removed after migration complete

USAGE FOR NEW CODE:
from helpers.transcript_manager import TranscriptManager

COMPATIBILITY IMPORTS:
This module provides imports that work with old code while using new functionality.
"""

import warnings
from helpers.transcript_manager import TranscriptManager, TranscriptInfo

# Compatibility imports - redirect old imports to new functionality
def _deprecated_import_warning(old_module: str, new_class: str = "TranscriptManager"):
    warnings.warn(
        f"Importing from {old_module} is deprecated. "
        f"Use 'from helpers.transcript_manager import {new_class}' instead. "
        "This compatibility layer will be removed after migration is complete.",
        DeprecationWarning,
        stacklevel=3
    )

# ATP Transcript Scraper compatibility
class ATPTranscriptScraper:
    def __init__(self, *args, **kwargs):
        _deprecated_import_warning("helpers.atp_transcript_scraper", "TranscriptManager")
        self._manager = TranscriptManager()

    def scrape_transcript(self, url):
        transcript_info = TranscriptInfo(url=url, title="ATP Episode", source="atp")
        result = self._manager.fetch_transcript(transcript_info)
        return result.content if result else None

    def discover_episodes(self, limit=50):
        transcripts = self._manager.discover_transcripts('atp', limit=limit)
        return [{'url': t.url, 'title': t.title} for t in transcripts]

# Network Transcript Scrapers compatibility
class NetworkTranscriptScrapers:
    def __init__(self, *args, **kwargs):
        _deprecated_import_warning("helpers.network_transcript_scrapers", "TranscriptManager")
        self._manager = TranscriptManager()

    def scrape_network_transcript(self, url, network='auto'):
        transcript_info = TranscriptInfo(url=url, title="Network Episode", source="network")
        result = self._manager.fetch_transcript(transcript_info)
        return result.content if result else None

# Universal Transcript Discoverer compatibility
class UniversalTranscriptDiscoverer:
    def __init__(self, *args, **kwargs):
        _deprecated_import_warning("helpers.universal_transcript_discoverer", "TranscriptManager")
        self._manager = TranscriptManager()

    def discover_transcripts(self, urls):
        return self._manager.discover_transcripts('universal', urls=urls)

# Transcript Processor compatibility
class TranscriptProcessor:
    def __init__(self, *args, **kwargs):
        _deprecated_import_warning("helpers.transcript_first_processor", "TranscriptManager")
        self._manager = TranscriptManager()

    def process_transcript(self, content):
        # For compatibility, just return the content as-is
        # Real processing happens in TranscriptManager
        return content

# Transcript Search compatibility
class TranscriptSearchIndexer:
    def __init__(self, *args, **kwargs):
        _deprecated_import_warning("helpers.transcript_search_indexer", "TranscriptManager")
        self._manager = TranscriptManager()

    def index_transcript(self, transcript):
        # Indexing is handled automatically by TranscriptManager
        return True

    def search_transcripts(self, query):
        return self._manager.search_transcripts(query)

# Transcript Search Ranking compatibility
class TranscriptSearchRanking:
    def __init__(self, *args, **kwargs):
        _deprecated_import_warning("helpers.transcript_search_ranking", "TranscriptManager")
        self._manager = TranscriptManager()

    def rank_results(self, results, query):
        # Ranking is handled by TranscriptManager.search_transcripts
        return results

# Podcast Transcript Ingestor compatibility
class PodcastTranscriptIngestor:
    def __init__(self, *args, **kwargs):
        _deprecated_import_warning("helpers.podcast_transcript_ingestor", "TranscriptManager")
        self._manager = TranscriptManager()

    def ingest_transcripts(self, urls):
        return self._manager.bulk_process_transcripts(urls)

# Module-level convenience functions that maintain old interfaces
def find_transcripts(*args, **kwargs):
    """Compatibility function - use TranscriptManager.discover_transcripts instead"""
    _deprecated_import_warning("helpers.transcript_lookup", "TranscriptManager")
    manager = TranscriptManager()
    return manager.discover_transcripts(*args, **kwargs)

def scrape_transcript(url):
    """Compatibility function - use TranscriptManager.fetch_transcript instead"""
    _deprecated_import_warning("transcript scraping functions", "TranscriptManager")
    manager = TranscriptManager()
    transcript_info = TranscriptInfo(url=url, title="Episode", source="universal")
    result = manager.fetch_transcript(transcript_info)
    return result.content if result else None

def search_transcripts(query, max_results=10):
    """Compatibility function - use TranscriptManager.search_transcripts instead"""
    _deprecated_import_warning("transcript search functions", "TranscriptManager")
    manager = TranscriptManager()
    return manager.search_transcripts(query, max_results)

def parse_transcript(content):
    """Compatibility function - parsing is integrated into TranscriptManager"""
    _deprecated_import_warning("helpers.transcript_parser", "TranscriptManager")
    # For compatibility, just return content as-is
    # Real parsing happens in TranscriptManager
    return content

def enhance_transcript(content):
    """Compatibility function - enhancement is integrated into TranscriptManager"""
    _deprecated_import_warning("helpers.atp_enhanced_transcript", "TranscriptManager")
    # For compatibility, just return content as-is
    # Real enhancement happens in TranscriptManager
    return content

# Migration utility functions
def get_migration_status():
    """Get status of transcript processing migration"""
    return {
        'status': 'in_progress',
        'unified_manager': 'active',
        'compatibility_layer': 'active',
        'old_modules': 'deprecated',
        'next_phase': 'remove_old_modules_after_testing'
    }

def validate_transcript_functionality():
    """Validate that transcript functionality is working after migration"""
    try:
        manager = TranscriptManager()
        health = manager.health_check()
        stats = manager.get_processing_stats()

        return {
            'transcript_manager_healthy': health.get('status') == 'healthy',
            'processed_transcripts': stats.get('total_processed', 0),
            'output_directory_exists': health.get('output_directory_exists', False),
            'migration_status': 'functional'
        }
    except Exception as e:
        return {
            'transcript_manager_healthy': False,
            'error': str(e),
            'migration_status': 'needs_attention'
        }

# For imports that expect specific class names, provide them
ATP_Transcript_Scraper = ATPTranscriptScraper  # Handle different naming conventions
PodcastTranscriptProcessor = PodcastTranscriptIngestor
TranscriptFinder = UniversalTranscriptDiscoverer

if __name__ == '__main__':
    # Test compatibility layer
    print("Testing transcript processing compatibility layer...")

    # Test unified manager
    manager = TranscriptManager()
    health = manager.health_check()
    print(f"TranscriptManager health: {health}")

    # Test migration status
    status = get_migration_status()
    print(f"Migration status: {status}")

    # Test validation
    validation = validate_transcript_functionality()
    print(f"Functionality validation: {validation}")

    print("Compatibility layer test complete.")