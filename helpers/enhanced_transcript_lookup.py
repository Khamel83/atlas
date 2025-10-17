#!/usr/bin/env python3
"""
Enhanced Transcript Lookup System

Uses the podcast sources registry for improved transcript discovery.
This replaces the hardcoded logic with a flexible, configurable system.
"""

import json
import logging
import sqlite3
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from helpers.podcast_source_registry import podcast_source_registry, TranscriptResult

logger = logging.getLogger(__name__)

@dataclass
class EnhancedTranscriptLookupResult:
    """Enhanced result with source registry information"""
    success: bool
    podcast_name: str
    episode_title: str
    transcript: str = ""
    source: str = ""
    source_display_name: str = ""
    confidence_score: float = 0.0
    fallback_used: bool = False
    metadata: Dict[str, Any] = None
    error_message: str = ""
    processing_time: float = 0.0

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

class EnhancedTranscriptLookup:
    """
    Enhanced transcript lookup using the podcast sources registry

    This system:
    - Uses the centralized registry for source identification
    - Provides better error handling and fallback mechanisms
    - Tracks source performance and confidence scores
    - Supports multiple extraction strategies
    """

    def __init__(self, db_path: str = "/home/ubuntu/dev/atlas/data/atlas.db"):
        self.db_path = db_path
        self.registry = podcast_source_registry
        self._init_database()

    def _init_database(self):
        """Initialize database connection"""
        try:
            self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self.conn.execute("PRAGMA journal_mode=WAL")
            self.conn.execute("PRAGMA synchronous=NORMAL")
            self.conn.execute("PRAGMA cache_size=10000")
            logger.info(f"Connected to database: {self.db_path}")
        except Exception as e:
            logger.error(f"Database connection failed: {e}")
            raise

    def lookup_transcript(self, podcast_name: str, episode_title: str,
                         episode_url: str = None, use_fallback: bool = True) -> EnhancedTranscriptLookupResult:
        """
        Look up transcript using enhanced registry-based system
        """
        import time
        start_time = time.time()

        try:
            # Step 1: Check database first
            db_result = self._check_database(podcast_name, episode_title)
            if db_result.success:
                processing_time = time.time() - start_time
                return EnhancedTranscriptLookupResult(
                    success=True,
                    podcast_name=podcast_name,
                    episode_title=episode_title,
                    transcript=db_result.transcript,
                    source=db_result.source,
                    confidence_score=1.0,
                    fallback_used=False,
                    metadata=db_result.metadata,
                    processing_time=processing_time
                )

            # Step 2: Use registry-based extraction
            registry_result = self._extract_from_registry(podcast_name, episode_title, episode_url)
            if registry_result.success:
                processing_time = time.time() - start_time

                # Store in database
                self._store_transcript(
                    podcast_name, episode_title,
                    registry_result.transcript,
                    registry_result.source,
                    episode_url or registry_result.url_used,
                    {
                        "source_display_name": registry_result.metadata.get("source_display_name", ""),
                        "confidence_score": registry_result.metadata.get("confidence_score", 0.8),
                        "extraction_method": "registry"
                    }
                )

                return EnhancedTranscriptLookupResult(
                    success=True,
                    podcast_name=podcast_name,
                    episode_title=episode_title,
                    transcript=registry_result.transcript,
                    source=registry_result.source,
                    source_display_name=registry_result.metadata.get("source_display_name", ""),
                    confidence_score=registry_result.metadata.get("confidence_score", 0.8),
                    fallback_used=False,
                    metadata=registry_result.metadata,
                    processing_time=processing_time
                )

            # Step 3: Try fallback methods if enabled
            if use_fallback:
                fallback_result = self._try_fallback_methods(podcast_name, episode_title, episode_url)
                if fallback_result.success:
                    processing_time = time.time() - start_time
                    return EnhancedTranscriptLookupResult(
                        success=True,
                        podcast_name=podcast_name,
                        episode_title=episode_title,
                        transcript=fallback_result.transcript,
                        source=fallback_result.source,
                        confidence_score=0.5,
                        fallback_used=True,
                        metadata=fallback_result.metadata,
                        processing_time=processing_time
                    )

            # No transcript found
            processing_time = time.time() - start_time
            return EnhancedTranscriptLookupResult(
                success=False,
                podcast_name=podcast_name,
                episode_title=episode_title,
                error_message=registry_result.error_message or "No transcript found",
                processing_time=processing_time
            )

        except Exception as e:
            processing_time = time.time() - start_time
            logger.error(f"Enhanced transcript lookup failed: {e}")
            return EnhancedTranscriptLookupResult(
                success=False,
                podcast_name=podcast_name,
                episode_title=episode_title,
                error_message=f"Lookup failed: {str(e)}",
                processing_time=processing_time
            )

    def _check_database(self, podcast_name: str, episode_title: str) -> TranscriptResult:
        """Check if transcript exists in database"""
        try:
            cursor = self.conn.cursor()
            query = """
                SELECT transcript, source, metadata
                FROM content
                WHERE podcast_name = ? AND episode_title = ?
                AND transcript IS NOT NULL AND transcript != ''
                ORDER BY created_at DESC
                LIMIT 1
            """
            cursor.execute(query, (podcast_name, episode_title))
            result = cursor.fetchone()

            if result and result[0]:
                transcript, source, metadata_json = result
                metadata = json.loads(metadata_json) if metadata_json else {}

                logger.info(f"Found existing transcript in database: {podcast_name} - {episode_title}")
                return TranscriptResult(
                    success=True,
                    transcript=transcript,
                    source=source,
                    metadata=metadata
                )

            return TranscriptResult(
                success=False,
                error_message="No transcript found in database"
            )

        except Exception as e:
            logger.error(f"Database check failed: {e}")
            return TranscriptResult(
                success=False,
                error_message=f"Database error: {str(e)}"
            )

    def _extract_from_registry(self, podcast_name: str, episode_title: str, episode_url: str) -> TranscriptResult:
        """Extract transcript using the registry"""
        try:
            result = self.registry.get_transcript(podcast_name, episode_title, episode_url)

            if result.success:
                # Add enhanced metadata
                source_config = self.registry.identify_source(podcast_name, episode_title, episode_url)
                if source_config:
                    result.metadata.update({
                        "source_display_name": source_config.display_name,
                        "confidence_score": min(0.9, source_config.success_rate + 0.1),
                        "source_priority": source_config.priority
                    })

                logger.info(f"Registry extraction successful: {podcast_name} - {episode_title}")
            else:
                logger.debug(f"Registry extraction failed: {podcast_name} - {episode_title}")

            return result

        except Exception as e:
            logger.error(f"Registry extraction failed: {e}")
            return TranscriptResult(
                success=False,
                error_message=f"Registry error: {str(e)}"
            )

    def _try_fallback_methods(self, podcast_name: str, episode_title: str, episode_url: str) -> TranscriptResult:
        """Try fallback extraction methods"""
        try:
            # Try the old hardcoded system as fallback
            from helpers.podcast_transcript_lookup import PodcastTranscriptLookup, TranscriptLookupResult

            old_lookup = PodcastTranscriptLookup()
            old_result = old_lookup.lookup_transcript(podcast_name, episode_title, episode_url)

            if old_result.success:
                return TranscriptResult(
                    success=True,
                    transcript=old_result.transcript,
                    source=old_result.source + "_fallback",
                    metadata={"fallback_method": "legacy_system"}
                )

            return TranscriptResult(
                success=False,
                error_message="Fallback methods also failed"
            )

        except Exception as e:
            logger.error(f"Fallback methods failed: {e}")
            return TranscriptResult(
                success=False,
                error_message=f"Fallback error: {str(e)}"
            )

    def _store_transcript(self, podcast_name: str, episode_title: str, transcript: str,
                         source: str, url: str = None, metadata: Dict[str, Any] = None):
        """Store transcript in database"""
        try:
            cursor = self.conn.cursor()

            # Check if already exists
            cursor.execute("""
                SELECT id FROM content
                WHERE podcast_name = ? AND episode_title = ?
                LIMIT 1
            """, (podcast_name, episode_title))

            existing = cursor.fetchone()

            metadata_json = json.dumps(metadata) if metadata else None

            if existing:
                # Update existing record
                cursor.execute("""
                    UPDATE content
                    SET transcript = ?, source = ?, url = ?, metadata = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (transcript, source, url, metadata_json, existing[0]))
            else:
                # Insert new record
                cursor.execute("""
                    INSERT INTO content (podcast_name, episode_title, transcript, source, url, metadata, content_type)
                    VALUES (?, ?, ?, ?, ?, ?, 'transcript')
                """, (podcast_name, episode_title, transcript, source, url, metadata_json))

            self.conn.commit()
            logger.info(f"Stored transcript: {podcast_name} - {episode_title} (source: {source})")

        except Exception as e:
            logger.error(f"Failed to store transcript: {e}")
            self.conn.rollback()

    def get_source_statistics(self) -> Dict[str, Any]:
        """Get statistics about source usage"""
        try:
            stats = {
                "registry_stats": self.registry.get_source_stats(),
                "database_stats": self._get_database_stats(),
                "recent_extractions": self._get_recent_extractions()
            }

            return stats

        except Exception as e:
            logger.error(f"Failed to get source statistics: {e}")
            return {"error": str(e)}

    def _get_database_stats(self) -> Dict[str, Any]:
        """Get database statistics"""
        try:
            cursor = self.conn.cursor()

            # Total transcripts
            cursor.execute("""
                SELECT COUNT(*) FROM content
                WHERE transcript IS NOT NULL AND transcript != ''
            """)
            total_transcripts = cursor.fetchone()[0]

            # Transcripts by source
            cursor.execute("""
                SELECT source, COUNT(*) as count
                FROM content
                WHERE transcript IS NOT NULL AND transcript != ''
                GROUP BY source
                ORDER BY count DESC
            """)
            by_source = dict(cursor.fetchall())

            # Recent transcripts
            cursor.execute("""
                SELECT COUNT(*) FROM content
                WHERE transcript IS NOT NULL AND transcript != ''
                AND created_at >= datetime('now', '-7 days')
            """)
            recent_count = cursor.fetchone()[0]

            return {
                "total_transcripts": total_transcripts,
                "by_source": by_source,
                "recent_transcripts": recent_count
            }

        except Exception as e:
            logger.error(f"Failed to get database stats: {e}")
            return {"error": str(e)}

    def _get_recent_extractions(self) -> List[Dict[str, Any]]:
        """Get recent extraction results"""
        try:
            cursor = self.conn.cursor()

            cursor.execute("""
                SELECT podcast_name, episode_title, source, created_at,
                       LENGTH(transcript) as length
                FROM content
                WHERE transcript IS NOT NULL AND transcript != ''
                ORDER BY created_at DESC
                LIMIT 10
            """)

            results = []
            for row in cursor.fetchall():
                results.append({
                    "podcast_name": row[0],
                    "episode_title": row[1],
                    "source": row[2],
                    "created_at": row[3],
                    "length": row[4]
                })

            return results

        except Exception as e:
            logger.error(f"Failed to get recent extractions: {e}")
            return []

    def optimize_source_performance(self):
        """Optimize source configuration based on performance"""
        try:
            # Get source performance data
            cursor = self.conn.cursor()

            cursor.execute("""
                SELECT source,
                       COUNT(*) as total_attempts,
                       COUNT(CASE WHEN transcript IS NOT NULL AND transcript != '' THEN 1 END) as successes,
                       AVG(LENGTH(transcript)) as avg_length
                FROM content
                WHERE created_at >= datetime('now', '-30 days')
                GROUP BY source
                HAVING total_attempts >= 5
            """)

            performance_data = cursor.fetchall()

            # Update source configurations based on performance
            for source_name, total, successes, avg_length in performance_data:
                success_rate = successes / total if total > 0 else 0

                # Update registry source priority based on performance
                if source_name in self.registry.sources:
                    source = self.registry.sources[source_name]

                    # Adjust priority based on success rate and transcript quality
                    if success_rate > 0.8 and avg_length > 1000:
                        source.priority = max(source.priority, 90)
                        source.success_rate = success_rate
                    elif success_rate > 0.5:
                        source.priority = max(source.priority, 70)
                        source.success_rate = success_rate
                    elif success_rate < 0.2:
                        source.priority = min(source.priority, 30)
                        source.enabled = False
                        source.success_rate = success_rate

            # Save updated configurations
            self.registry.save_sources()

            logger.info(f"Optimized {len(performance_data)} sources based on performance")

        except Exception as e:
            logger.error(f"Failed to optimize source performance: {e}")

    def close(self):
        """Close database connection"""
        if hasattr(self, 'conn'):
            self.conn.close()
            logger.info("Database connection closed")

    def __del__(self):
        """Cleanup on destruction"""
        try:
            self.close()
        except:
            pass

# Convenience function for quick lookups
def lookup_transcript_enhanced(podcast_name: str, episode_title: str, episode_url: str = None) -> EnhancedTranscriptLookupResult:
    """Quick lookup using the enhanced system"""
    lookup = EnhancedTranscriptLookup()
    return lookup.lookup_transcript(podcast_name, episode_title, episode_url)

# Test function
def test_enhanced_lookup():
    """Test the enhanced lookup system"""
    print("🧪 Testing Enhanced Transcript Lookup System")

    # Test cases
    test_cases = [
        ("Accidental Tech Podcast", "657: Ears Are Weird", "https://atp.fm/657"),
        ("This American Life", "Act 1: The Test", None),
        ("99% Invisible", "657: Urban Planning", None),
        ("Unknown Podcast", "Random Episode", None)
    ]

    lookup = EnhancedTranscriptLookup()

    for podcast, episode, url in test_cases:
        print(f"\n🔍 Testing: {podcast} - {episode}")
        result = lookup.lookup_transcript(podcast, episode, url)

        print(f"  Success: {result.success}")
        print(f"  Source: {result.source_display_name or result.source}")
        print(f"  Confidence: {result.confidence_score:.2f}")
        print(f"  Fallback: {result.fallback_used}")
        print(f"  Processing time: {result.processing_time:.3f}s")

        if result.success:
            print(f"  Transcript length: {len(result.transcript)} chars")
        else:
            print(f"  Error: {result.error_message}")

    # Show statistics
    print(f"\n📊 Source Statistics:")
    stats = lookup.get_source_statistics()
    for source_name, source_stats in stats.get("registry_stats", {}).items():
        enabled = "✅" if source_stats["enabled"] else "🚫"
        print(f"  {enabled} {source_stats['display_name']}: {source_stats['success_rate']:.1%}")

    lookup.close()

if __name__ == "__main__":
    test_enhanced_lookup()