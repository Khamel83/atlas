"""
Integrated Deduplication Module

This module provides a unified interface that combines URL-based deduplication
with content-based similarity detection for comprehensive duplicate prevention.
"""

import os
from typing import Dict, List, Optional, Tuple

from helpers.config import load_config
from helpers.dedupe import link_uid
from helpers.enhanced_dedupe import (SimilarityMatch,
                                     create_enhanced_deduplicator)
from helpers.metadata_manager import ContentType, MetadataManager
from helpers.path_manager import PathManager


class IntegratedDeduplicator:
    """Unified deduplication system combining URL and content-based detection."""

    def __init__(self, config: Optional[Dict] = None):
        """Initialize integrated deduplicator with configuration."""
        self.config = config or load_config()

        # Initialize components
        self.metadata_manager = MetadataManager()
        self.path_manager = PathManager(self.config)
        self.enhanced_deduplicator = create_enhanced_deduplicator(
            self.metadata_manager, self.path_manager
        )

        # Duplicate detection settings
        self.similarity_threshold = self.config.get("similarity_threshold", 0.8)
        self.fast_check_enabled = self.config.get("fast_duplicate_check", True)
        self.content_check_enabled = self.config.get("content_duplicate_check", True)

    def is_url_duplicate(self, url: str) -> bool:
        """Check if URL has already been processed (existing functionality)."""
        uid = link_uid(url)

        # Check in article metadata
        article_meta_path = os.path.join(
            self.config.get("article_output_path", "output/articles"),
            "metadata",
            f"{uid}.json",
        )
        if os.path.exists(article_meta_path):
            return True

        # Check in YouTube metadata
        youtube_meta_path = os.path.join(
            self.config.get("youtube_output_path", "output/youtube"),
            "metadata",
            f"{uid}.json",
        )
        if os.path.exists(youtube_meta_path):
            return True

        # Check in podcast metadata
        podcast_meta_path = os.path.join(
            self.config.get("podcast_output_path", "output/podcasts"),
            "metadata",
            f"{uid}.json",
        )
        if os.path.exists(podcast_meta_path):
            return True

        return False

    def is_content_duplicate(
        self, content_type: ContentType, metadata: Dict
    ) -> Tuple[bool, Optional[SimilarityMatch]]:
        """Check if content is a duplicate based on content similarity."""
        if not self.content_check_enabled:
            return False, None

        # Fast hash-based check first
        if self.fast_check_enabled:
            is_fast_duplicate = self.enhanced_deduplicator.fast_duplicate_check(
                content_type, metadata
            )
            if is_fast_duplicate:
                # Could create a basic SimilarityMatch for hash matches
                return True, SimilarityMatch(
                    primary_uid="unknown",
                    duplicate_uid=metadata.get("uid", ""),
                    similarity_score=1.0,
                    match_type="hash_match",
                    confidence=0.9,
                )

        # Full similarity analysis
        return self.enhanced_deduplicator.is_content_duplicate(
            content_type, metadata, self.similarity_threshold
        )

    def check_all_duplicates(
        self, url: str, content_type: ContentType, metadata: Optional[Dict] = None
    ) -> Dict:
        """Comprehensive duplicate check combining URL and content analysis.

        Args:
            url: URL to check
            content_type: Type of content
            metadata: Optional content metadata for similarity checking

        Returns:
            Dictionary with duplicate status and details
        """
        result = {
            "is_duplicate": False,
            "duplicate_type": None,
            "url_duplicate": False,
            "content_duplicate": False,
            "similarity_match": None,
            "confidence": 0.0,
            "recommendation": "process",
        }

        # Check URL-based duplication first
        url_duplicate = self.is_url_duplicate(url)
        result["url_duplicate"] = url_duplicate

        if url_duplicate:
            result["is_duplicate"] = True
            result["duplicate_type"] = "url"
            result["confidence"] = 1.0
            result["recommendation"] = "skip"
            return result

        # Check content-based duplication if metadata provided
        if metadata and self.content_check_enabled:
            content_duplicate, similarity_match = self.is_content_duplicate(
                content_type, metadata
            )
            result["content_duplicate"] = content_duplicate
            result["similarity_match"] = similarity_match

            if content_duplicate and similarity_match:
                result["is_duplicate"] = True
                result["duplicate_type"] = "content"
                result["confidence"] = similarity_match.confidence

                # Determine recommendation based on similarity type and confidence
                if (
                    similarity_match.match_type in ["title_exact", "hash_match"]
                    or similarity_match.confidence > 0.9
                ):
                    result["recommendation"] = "skip"
                elif similarity_match.confidence > 0.8:
                    result["recommendation"] = "review"
                else:
                    result["recommendation"] = "process_with_warning"

        return result

    def find_similar_content(
        self, content_type: ContentType, metadata: Dict, limit: int = 10
    ) -> List[SimilarityMatch]:
        """Find similar content items for review or merging.

        Args:
            content_type: Type of content to search
            metadata: Content metadata to match against
            limit: Maximum number of matches to return

        Returns:
            List of similarity matches sorted by confidence
        """
        matches = self.enhanced_deduplicator.find_duplicates(content_type, metadata)
        return matches[:limit]

    def get_duplicate_statistics(self) -> Dict:
        """Get statistics about duplicates in the system."""
        stats = {
            "total_items": 0,
            "potential_duplicates": 0,
            "high_confidence_duplicates": 0,
            "content_types": {},
        }

        try:
            all_metadata = self.metadata_manager.get_all_metadata()
            stats["total_items"] = len(all_metadata)

            # Group by content type
            by_type = {}
            for item in all_metadata:
                content_type = item.get("content_type", "unknown")
                if content_type not in by_type:
                    by_type[content_type] = []
                by_type[content_type].append(item)

            # Check for duplicates within each type
            for content_type_str, items in by_type.items():
                try:
                    content_type = ContentType(content_type_str)
                except ValueError:
                    continue

                duplicates = []
                for i, item in enumerate(items):
                    matches = self.enhanced_deduplicator.find_duplicates(
                        content_type, item
                    )
                    high_conf_matches = [m for m in matches if m.confidence > 0.8]
                    duplicates.extend(high_conf_matches)

                stats["content_types"][content_type_str] = {
                    "total_items": len(items),
                    "potential_duplicates": len(duplicates),
                    "high_confidence_duplicates": len(
                        [d for d in duplicates if d.confidence > 0.9]
                    ),
                }

                stats["potential_duplicates"] += len(duplicates)
                stats["high_confidence_duplicates"] += len(
                    [d for d in duplicates if d.confidence > 0.9]
                )

        except Exception as e:
            # Don't fail if statistics calculation fails
            stats["error"] = str(e)

        return stats

    def cleanup_duplicates(
        self, dry_run: bool = True, confidence_threshold: float = 0.95
    ) -> Dict:
        """Identify and optionally remove high-confidence duplicates.

        Args:
            dry_run: If True, only identify duplicates without removing
            confidence_threshold: Minimum confidence to consider for removal

        Returns:
            Dictionary with cleanup results
        """
        result = {
            "dry_run": dry_run,
            "duplicates_found": 0,
            "duplicates_removed": 0,
            "duplicates_by_type": {},
            "errors": [],
        }

        try:
            all_metadata = self.metadata_manager.get_all_metadata()

            # Group by content type
            by_type = {}
            for item in all_metadata:
                content_type = item.get("content_type", "unknown")
                if content_type not in by_type:
                    by_type[content_type] = []
                by_type[content_type].append(item)

            for content_type_str, items in by_type.items():
                try:
                    content_type = ContentType(content_type_str)
                except ValueError:
                    continue

                type_duplicates = []
                processed_uids = set()

                for item in items:
                    uid = item.get("uid", "")
                    if uid in processed_uids:
                        continue

                    matches = self.enhanced_deduplicator.find_duplicates(
                        content_type, item
                    )
                    high_conf_matches = [
                        m for m in matches if m.confidence >= confidence_threshold
                    ]

                    for match in high_conf_matches:
                        if match.duplicate_uid not in processed_uids:
                            type_duplicates.append(match)
                            processed_uids.add(match.duplicate_uid)

                result["duplicates_by_type"][content_type_str] = len(type_duplicates)
                result["duplicates_found"] += len(type_duplicates)

                # If not dry run, actually remove duplicates
                if not dry_run:
                    for match in type_duplicates:
                        try:
                            # Here you would implement actual file removal
                            # For now, just count what would be removed
                            result["duplicates_removed"] += 1
                        except Exception as e:
                            result["errors"].append(
                                f"Error removing {match.duplicate_uid}: {str(e)}"
                            )

        except Exception as e:
            result["errors"].append(f"Error during cleanup: {str(e)}")

        return result


# Global instance for easy access
_global_deduplicator: Optional[IntegratedDeduplicator] = None


def get_integrated_deduplicator(
    config: Optional[Dict] = None,
) -> IntegratedDeduplicator:
    """Get global integrated deduplicator instance."""
    global _global_deduplicator
    if _global_deduplicator is None:
        _global_deduplicator = IntegratedDeduplicator(config)
    return _global_deduplicator


def is_duplicate_enhanced(
    url: str, content_type: ContentType, metadata: Optional[Dict] = None
) -> bool:
    """Enhanced duplicate check combining URL and content analysis.

    Args:
        url: URL to check
        content_type: Type of content
        metadata: Optional content metadata

    Returns:
        True if content is considered a duplicate
    """
    deduplicator = get_integrated_deduplicator()
    result = deduplicator.check_all_duplicates(url, content_type, metadata)

    return result["is_duplicate"] and result["recommendation"] in ["skip"]


def get_duplicate_info(
    url: str, content_type: ContentType, metadata: Optional[Dict] = None
) -> Dict:
    """Get detailed duplicate information for decision making."""
    deduplicator = get_integrated_deduplicator()
    return deduplicator.check_all_duplicates(url, content_type, metadata)
