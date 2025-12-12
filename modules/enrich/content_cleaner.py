"""
Content Cleaner - Orchestrates content enrichment and cleaning.

This module provides the main interface for cleaning content before
it enters the Atlas knowledge base. It coordinates:
- Ad/sponsor removal
- Whitespace normalization
- Metadata extraction
- Quality scoring

Usage:
    from modules.enrich import ContentCleaner, clean_content

    # Simple usage
    clean_text = clean_content(raw_text, content_type="podcast")

    # Full control
    cleaner = ContentCleaner()
    result = cleaner.clean(raw_text, content_type="podcast")
    print(f"Quality score: {result.quality_score}")
    print(f"Cleaned text: {result.cleaned_text}")
"""

import re
import logging
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List
from pathlib import Path
from datetime import datetime

from .ad_stripper import AdStripper, ContentType, StrippingResult

logger = logging.getLogger(__name__)


@dataclass
class CleaningResult:
    """Result of content cleaning operation."""
    original_text: str
    cleaned_text: str
    content_type: ContentType

    # Ad stripping results
    ads_removed: int = 0
    ad_chars_removed: int = 0
    ad_percent_removed: float = 0.0

    # Normalization stats
    whitespace_normalized: bool = False

    # Quality metrics
    word_count: int = 0
    quality_score: float = 0.0  # 0.0-1.0

    # Metadata
    processing_time_ms: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_clean(self) -> bool:
        """Whether content passed quality checks."""
        return self.quality_score >= 0.5


@dataclass
class BatchResult:
    """Result of batch cleaning operation."""
    total: int = 0
    cleaned: int = 0
    failed: int = 0
    skipped: int = 0
    total_ads_removed: int = 0
    avg_quality_score: float = 0.0
    processing_time_ms: float = 0.0
    results: List[CleaningResult] = field(default_factory=list)


class ContentCleaner:
    """
    Main content cleaning orchestrator.

    Coordinates ad stripping, normalization, and quality scoring
    for content before it enters the Atlas knowledge base.
    """

    def __init__(
        self,
        config_path: Optional[Path] = None,
        strip_ads: bool = True,
        normalize_whitespace: bool = True,
        min_quality_score: float = 0.3,
        ad_confidence: float = 0.6,
    ):
        """
        Initialize the content cleaner.

        Args:
            config_path: Path to YAML config file
            strip_ads: Whether to remove detected ads
            normalize_whitespace: Whether to normalize whitespace
            min_quality_score: Minimum quality to accept content
            ad_confidence: Minimum confidence for ad detection
        """
        self.strip_ads_enabled = strip_ads
        self.normalize_whitespace = normalize_whitespace
        self.min_quality_score = min_quality_score

        if strip_ads:
            self.ad_stripper = AdStripper(
                config_path=config_path,
                min_confidence=ad_confidence,
            )
        else:
            self.ad_stripper = None

        self.stats = {
            "total_processed": 0,
            "total_ads_removed": 0,
            "total_chars_removed": 0,
            "avg_quality_score": 0.0,
        }

    def clean(
        self,
        text: str,
        content_type: str = "unknown",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> CleaningResult:
        """
        Clean content for the knowledge base.

        Args:
            text: Raw content to clean
            content_type: One of: podcast, youtube, article, newsletter, unknown
            metadata: Optional metadata to include in result

        Returns:
            CleaningResult with cleaned text and metrics
        """
        import time
        start_time = time.time()

        content_type_enum = ContentType(content_type.lower())
        cleaned = text
        ads_removed = 0
        ad_chars_removed = 0
        ad_percent_removed = 0.0

        # Step 1: Strip ads
        if self.strip_ads_enabled and self.ad_stripper:
            strip_result = self.ad_stripper.strip(cleaned, content_type_enum)
            cleaned = strip_result.cleaned_text
            ads_removed = strip_result.ads_found
            ad_chars_removed = strip_result.chars_removed
            ad_percent_removed = strip_result.percent_removed

        # Step 2: Normalize whitespace
        whitespace_normalized = False
        if self.normalize_whitespace:
            cleaned, whitespace_normalized = self._normalize_whitespace(cleaned)

        # Step 3: Calculate quality score
        quality_score = self._calculate_quality_score(cleaned, content_type_enum)

        # Calculate word count
        word_count = len(cleaned.split())

        processing_time = (time.time() - start_time) * 1000

        # Update stats
        self.stats["total_processed"] += 1
        self.stats["total_ads_removed"] += ads_removed
        self.stats["total_chars_removed"] += ad_chars_removed
        # Running average
        n = self.stats["total_processed"]
        self.stats["avg_quality_score"] = (
            (self.stats["avg_quality_score"] * (n - 1) + quality_score) / n
        )

        return CleaningResult(
            original_text=text,
            cleaned_text=cleaned,
            content_type=content_type_enum,
            ads_removed=ads_removed,
            ad_chars_removed=ad_chars_removed,
            ad_percent_removed=ad_percent_removed,
            whitespace_normalized=whitespace_normalized,
            word_count=word_count,
            quality_score=quality_score,
            processing_time_ms=processing_time,
            metadata=metadata or {},
        )

    def _normalize_whitespace(self, text: str) -> tuple[str, bool]:
        """
        Normalize whitespace in text.

        Returns:
            Tuple of (normalized_text, was_modified)
        """
        original = text

        # Normalize line endings
        text = text.replace("\r\n", "\n").replace("\r", "\n")

        # Remove trailing whitespace on lines
        text = re.sub(r"[ \t]+$", "", text, flags=re.MULTILINE)

        # Collapse multiple blank lines to max 2
        text = re.sub(r"\n{3,}", "\n\n", text)

        # Remove leading/trailing whitespace
        text = text.strip()

        return text, text != original

    def _calculate_quality_score(
        self,
        text: str,
        content_type: ContentType,
    ) -> float:
        """
        Calculate a quality score for the content.

        Factors:
        - Length (too short = low quality)
        - Sentence structure (proper punctuation)
        - Word diversity (not repetitive)
        - Content-type specific checks

        Returns:
            Score between 0.0 and 1.0
        """
        if not text or len(text) < 100:
            return 0.0

        scores = []

        # Length score (log scale, max at ~10k words)
        word_count = len(text.split())
        length_score = min(1.0, word_count / 1000)  # 1000 words = 1.0
        scores.append(length_score)

        # Sentence structure score
        sentences = re.split(r"[.!?]+", text)
        sentences = [s.strip() for s in sentences if s.strip()]
        if sentences:
            avg_sentence_length = sum(len(s.split()) for s in sentences) / len(sentences)
            # Good range: 10-25 words per sentence
            if 10 <= avg_sentence_length <= 25:
                structure_score = 1.0
            elif 5 <= avg_sentence_length < 10 or 25 < avg_sentence_length <= 40:
                structure_score = 0.7
            else:
                structure_score = 0.4
            scores.append(structure_score)

        # Word diversity score (unique words / total words)
        words = text.lower().split()
        if words:
            unique_ratio = len(set(words)) / len(words)
            diversity_score = min(1.0, unique_ratio * 2)  # 0.5 ratio = 1.0
            scores.append(diversity_score)

        # Content-type specific checks
        if content_type == ContentType.PODCAST:
            # Podcasts should have dialogue markers or speaker patterns
            has_dialogue = bool(re.search(r"[:\-]|\b(said|says|asked|replied)\b", text, re.I))
            scores.append(0.8 if has_dialogue else 0.6)

        elif content_type == ContentType.ARTICLE:
            # Articles should have paragraphs
            paragraphs = text.split("\n\n")
            has_structure = len(paragraphs) >= 3
            scores.append(0.9 if has_structure else 0.6)

        # Average all scores
        return sum(scores) / len(scores) if scores else 0.5

    def clean_batch(
        self,
        items: List[Dict[str, Any]],
        text_key: str = "text",
        type_key: str = "content_type",
    ) -> BatchResult:
        """
        Clean a batch of content items.

        Args:
            items: List of dicts with text and content_type
            text_key: Key for text in each dict
            type_key: Key for content type in each dict

        Returns:
            BatchResult with aggregate statistics
        """
        import time
        start_time = time.time()

        result = BatchResult(total=len(items))

        for item in items:
            text = item.get(text_key, "")
            content_type = item.get(type_key, "unknown")

            if not text:
                result.skipped += 1
                continue

            try:
                clean_result = self.clean(text, content_type, metadata=item)
                result.results.append(clean_result)
                result.cleaned += 1
                result.total_ads_removed += clean_result.ads_removed
            except Exception as e:
                logger.error(f"Failed to clean item: {e}")
                result.failed += 1

        result.processing_time_ms = (time.time() - start_time) * 1000

        if result.results:
            result.avg_quality_score = (
                sum(r.quality_score for r in result.results) / len(result.results)
            )

        return result

    def get_stats(self) -> Dict[str, Any]:
        """Get cleaning statistics."""
        return self.stats.copy()


def clean_content(
    text: str,
    content_type: str = "unknown",
    strip_ads: bool = True,
) -> str:
    """
    Convenience function to clean content.

    Args:
        text: Raw content to clean
        content_type: One of: podcast, youtube, article, newsletter, unknown
        strip_ads: Whether to remove detected ads

    Returns:
        Cleaned text
    """
    cleaner = ContentCleaner(strip_ads=strip_ads)
    result = cleaner.clean(text, content_type)
    return result.cleaned_text


# CLI for testing and batch processing
if __name__ == "__main__":
    import argparse
    import sys
    import json

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    parser = argparse.ArgumentParser(description="Clean content for Atlas")
    parser.add_argument("file", nargs="?", help="File to process (or stdin)")
    parser.add_argument("--type", "-t", default="unknown",
                        choices=["podcast", "youtube", "article", "newsletter", "unknown"],
                        help="Content type")
    parser.add_argument("--no-ads", action="store_true",
                        help="Disable ad stripping")
    parser.add_argument("--json", "-j", action="store_true",
                        help="Output result as JSON")
    parser.add_argument("--stats", "-s", action="store_true",
                        help="Show cleaning statistics")
    args = parser.parse_args()

    # Read input
    if args.file:
        text = Path(args.file).read_text()
    else:
        text = sys.stdin.read()

    cleaner = ContentCleaner(strip_ads=not args.no_ads)
    result = cleaner.clean(text, args.type)

    if args.json:
        output = {
            "cleaned_text": result.cleaned_text,
            "content_type": result.content_type.value,
            "ads_removed": result.ads_removed,
            "ad_chars_removed": result.ad_chars_removed,
            "ad_percent_removed": result.ad_percent_removed,
            "word_count": result.word_count,
            "quality_score": result.quality_score,
            "processing_time_ms": result.processing_time_ms,
        }
        print(json.dumps(output, indent=2))
    elif args.stats:
        print(f"Content Type: {result.content_type.value}")
        print(f"Ads Removed: {result.ads_removed}")
        print(f"Chars Removed: {result.ad_chars_removed} ({result.ad_percent_removed:.1f}%)")
        print(f"Word Count: {result.word_count}")
        print(f"Quality Score: {result.quality_score:.2f}")
        print(f"Processing Time: {result.processing_time_ms:.1f}ms")
        print("---")
        print(result.cleaned_text)
    else:
        print(result.cleaned_text)
