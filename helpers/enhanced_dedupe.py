"""
Enhanced Deduplication Module

This module provides advanced content-based deduplication capabilities using
Jaccard similarity scoring and multi-level duplicate detection strategies.
"""

import hashlib
import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Set, Tuple

from helpers.metadata_manager import ContentType, MetadataManager
from helpers.path_manager import PathManager


@dataclass
class SimilarityMatch:
    """Represents a content similarity match between two items."""

    primary_uid: str
    duplicate_uid: str
    similarity_score: float
    match_type: str  # 'title', 'content', 'url', 'hybrid'
    confidence: float  # 0.0 to 1.0


class ContentHasher:
    """Generates various types of content hashes for deduplication."""

    @staticmethod
    def title_hash(title: str) -> str:
        """Generate hash of normalized title."""
        if not title:
            return ""
        # Normalize: lowercase, remove special chars, collapse whitespace
        normalized = re.sub(r"[^\w\s]", "", title.lower())
        normalized = re.sub(r"\s+", " ", normalized).strip()
        return hashlib.md5(normalized.encode("utf-8")).hexdigest()[:16]

    @staticmethod
    def content_hash(content: str, n_chars: int = 1000) -> str:
        """Generate hash of first N characters of content."""
        if not content:
            return ""
        # Use first n_chars to avoid full content variations affecting hash
        truncated = content[:n_chars].strip().lower()
        return hashlib.md5(truncated.encode("utf-8")).hexdigest()[:16]

    @staticmethod
    def fuzzy_content_hash(content: str) -> str:
        """Generate fuzzy hash ignoring whitespace and punctuation."""
        if not content:
            return ""
        # Remove all whitespace and punctuation, keep only alphanumeric
        normalized = re.sub(r"[^\w]", "", content.lower())
        return hashlib.md5(normalized.encode("utf-8")).hexdigest()[:16]


class JaccardSimilarity:
    """Jaccard similarity implementation for content deduplication."""

    @staticmethod
    def tokenize(text: str, method: str = "words") -> Set[str]:
        """Tokenize text for Jaccard similarity calculation.

        Args:
            text: Text to tokenize
            method: 'words', 'shingles', or 'chars'
        """
        if not text:
            return set()

        text = text.lower()

        if method == "words":
            # Split into words, remove short words
            words = re.findall(r"\w+", text)
            return set(word for word in words if len(word) > 2)

        elif method == "shingles":
            # Create word shingles (3-grams)
            words = re.findall(r"\w+", text)
            if len(words) < 3:
                return set(words)
            shingles = []
            for i in range(len(words) - 2):
                shingle = " ".join(words[i : i + 3])
                shingles.append(shingle)
            return set(shingles)

        elif method == "chars":
            # Character n-grams
            clean_text = re.sub(r"\s+", "", text)
            if len(clean_text) < 5:
                return {clean_text}
            return set(clean_text[i : i + 5] for i in range(len(clean_text) - 4))

        else:
            raise ValueError(f"Unknown tokenization method: {method}")

    @staticmethod
    def calculate_similarity(set1: Set[str], set2: Set[str]) -> float:
        """Calculate Jaccard similarity coefficient."""
        if not set1 and not set2:
            return 1.0
        if not set1 or not set2:
            return 0.0

        intersection = len(set1 & set2)
        union = len(set1 | set2)

        return intersection / union if union > 0 else 0.0

    @classmethod
    def text_similarity(cls, text1: str, text2: str, method: str = "words") -> float:
        """Calculate Jaccard similarity between two texts."""
        tokens1 = cls.tokenize(text1, method)
        tokens2 = cls.tokenize(text2, method)
        return cls.calculate_similarity(tokens1, tokens2)


class EnhancedDeduplicator:
    """Advanced content deduplication with multiple similarity methods."""

    def __init__(self, metadata_manager: MetadataManager, path_manager: PathManager):
        self.metadata_manager = metadata_manager
        self.path_manager = path_manager

        # Similarity thresholds
        self.thresholds = {
            "title_exact": 1.0,
            "title_high": 0.9,
            "content_high": 0.85,
            "content_medium": 0.7,
            "url_similar": 0.8,
            "hybrid_threshold": 0.75,
        }

    def find_duplicates(
        self, content_type: ContentType, candidate_metadata: Dict
    ) -> List[SimilarityMatch]:
        """Find potential duplicates for new content.

        Args:
            content_type: Type of content being checked
            candidate_metadata: Metadata of the candidate content

        Returns:
            List of similarity matches, sorted by confidence
        """
        matches = []
        existing_items = self.metadata_manager.get_all_metadata()

        # Filter to same content type
        same_type_items = [
            item
            for item in existing_items
            if item.get("content_type") == content_type.value
        ]

        for existing_item in same_type_items:
            similarity_match = self._compare_content(candidate_metadata, existing_item)
            if similarity_match and similarity_match.similarity_score > 0.5:
                matches.append(similarity_match)

        # Sort by confidence (descending) and similarity score
        matches.sort(key=lambda x: (x.confidence, x.similarity_score), reverse=True)

        return matches

    def _compare_content(
        self, candidate: Dict, existing: Dict
    ) -> Optional[SimilarityMatch]:
        """Compare two content items and return similarity match if significant."""
        candidate_uid = candidate.get("uid", "")
        existing_uid = existing.get("uid", "")

        if candidate_uid == existing_uid:
            return None  # Same item

        # Extract comparable fields
        candidate_title = candidate.get("title", "")
        existing_title = existing.get("title", "")
        candidate_content = candidate.get("content", "") or candidate.get("summary", "")
        existing_content = existing.get("content", "") or existing.get("summary", "")
        candidate_url = candidate.get("url", "")
        existing_url = existing.get("url", "")

        # Calculate various similarities
        similarities = {}

        # Title similarity
        if candidate_title and existing_title:
            similarities["title_exact"] = (
                1.0 if candidate_title == existing_title else 0.0
            )
            similarities["title_jaccard"] = JaccardSimilarity.text_similarity(
                candidate_title, existing_title, "words"
            )

        # Content similarity
        if candidate_content and existing_content:
            similarities["content_words"] = JaccardSimilarity.text_similarity(
                candidate_content, existing_content, "words"
            )
            similarities["content_shingles"] = JaccardSimilarity.text_similarity(
                candidate_content, existing_content, "shingles"
            )

        # URL similarity (for near-duplicate URLs)
        if candidate_url and existing_url:
            similarities["url_jaccard"] = JaccardSimilarity.text_similarity(
                candidate_url, existing_url, "chars"
            )

        # Determine best match type and score
        best_match = self._evaluate_similarities(similarities)

        if best_match["score"] < 0.5:
            return None

        return SimilarityMatch(
            primary_uid=existing_uid,
            duplicate_uid=candidate_uid,
            similarity_score=best_match["score"],
            match_type=best_match["type"],
            confidence=self._calculate_confidence(similarities, best_match),
        )

    def _evaluate_similarities(self, similarities: Dict[str, float]) -> Dict:
        """Evaluate all similarity scores and determine the best match."""
        if not similarities:
            return {"score": 0.0, "type": "none"}

        # Check for exact title match
        if similarities.get("title_exact", 0.0) == 1.0:
            return {"score": 1.0, "type": "title_exact"}

        # Check for high title similarity
        title_score = similarities.get("title_jaccard", 0.0)
        if title_score >= self.thresholds["title_high"]:
            return {"score": title_score, "type": "title_high"}

        # Check for high content similarity
        content_score = max(
            similarities.get("content_words", 0.0),
            similarities.get("content_shingles", 0.0),
        )
        if content_score >= self.thresholds["content_high"]:
            return {"score": content_score, "type": "content_high"}

        # Check for medium content similarity
        if content_score >= self.thresholds["content_medium"]:
            return {"score": content_score, "type": "content_medium"}

        # Check for URL similarity
        url_score = similarities.get("url_jaccard", 0.0)
        if url_score >= self.thresholds["url_similar"]:
            return {"score": url_score, "type": "url_similar"}

        # Hybrid scoring: combine multiple signals
        hybrid_score = self._calculate_hybrid_score(similarities)
        if hybrid_score >= self.thresholds["hybrid_threshold"]:
            return {"score": hybrid_score, "type": "hybrid"}

        # Return best individual score
        best_score = max(similarities.values()) if similarities else 0.0
        best_type = max(similarities, key=similarities.get) if similarities else "none"

        return {"score": best_score, "type": best_type}

    def _calculate_hybrid_score(self, similarities: Dict[str, float]) -> float:
        """Calculate weighted hybrid similarity score."""
        weights = {
            "title_jaccard": 0.4,
            "content_words": 0.3,
            "content_shingles": 0.2,
            "url_jaccard": 0.1,
        }

        weighted_sum = 0.0
        total_weight = 0.0

        for key, weight in weights.items():
            if key in similarities:
                weighted_sum += similarities[key] * weight
                total_weight += weight

        return weighted_sum / total_weight if total_weight > 0 else 0.0

    def _calculate_confidence(
        self, similarities: Dict[str, float], best_match: Dict
    ) -> float:
        """Calculate confidence score for the match."""
        base_confidence = best_match["score"]

        # Boost confidence for exact matches
        if best_match["type"] == "title_exact":
            return min(1.0, base_confidence + 0.2)

        # Boost confidence when multiple signals agree
        high_similarities = [score for score in similarities.values() if score > 0.7]
        if len(high_similarities) >= 2:
            return min(1.0, base_confidence + 0.1)

        return base_confidence

    def is_content_duplicate(
        self,
        content_type: ContentType,
        metadata: Dict,
        similarity_threshold: float = 0.8,
    ) -> Tuple[bool, Optional[SimilarityMatch]]:
        """Check if content is a duplicate based on similarity threshold.

        Args:
            content_type: Type of content
            metadata: Content metadata to check
            similarity_threshold: Minimum similarity to consider duplicate

        Returns:
            Tuple of (is_duplicate, best_match)
        """
        matches = self.find_duplicates(content_type, metadata)

        if not matches:
            return False, None

        best_match = matches[0]
        is_duplicate = (
            best_match.similarity_score >= similarity_threshold
            and best_match.confidence >= 0.7
        )

        return is_duplicate, best_match

    def get_content_hash_index(self, content_type: ContentType) -> Dict[str, List[str]]:
        """Build hash-based index for fast duplicate detection.

        Returns:
            Dictionary mapping hashes to lists of UIDs
        """
        index = {"title_hash": {}, "content_hash": {}, "fuzzy_hash": {}}

        existing_items = self.metadata_manager.get_all_metadata()
        same_type_items = [
            item
            for item in existing_items
            if item.get("content_type") == content_type.value
        ]

        for item in same_type_items:
            uid = item.get("uid", "")
            if not uid:
                continue

            title = item.get("title", "")
            content = item.get("content", "") or item.get("summary", "")

            # Build title hash index
            if title:
                title_hash = ContentHasher.title_hash(title)
                if title_hash not in index["title_hash"]:
                    index["title_hash"][title_hash] = []
                index["title_hash"][title_hash].append(uid)

            # Build content hash index
            if content:
                content_hash = ContentHasher.content_hash(content)
                if content_hash not in index["content_hash"]:
                    index["content_hash"][content_hash] = []
                index["content_hash"][content_hash].append(uid)

                fuzzy_hash = ContentHasher.fuzzy_content_hash(content)
                if fuzzy_hash not in index["fuzzy_hash"]:
                    index["fuzzy_hash"][fuzzy_hash] = []
                index["fuzzy_hash"][fuzzy_hash].append(uid)

        return index

    def fast_duplicate_check(self, content_type: ContentType, metadata: Dict) -> bool:
        """Fast hash-based duplicate check before full similarity analysis."""
        hash_index = self.get_content_hash_index(content_type)

        title = metadata.get("title", "")
        content = metadata.get("content", "") or metadata.get("summary", "")

        # Check title hash
        if title:
            title_hash = ContentHasher.title_hash(title)
            if title_hash in hash_index["title_hash"]:
                return True

        # Check content hash
        if content:
            content_hash = ContentHasher.content_hash(content)
            if content_hash in hash_index["content_hash"]:
                return True

            fuzzy_hash = ContentHasher.fuzzy_content_hash(content)
            if fuzzy_hash in hash_index["fuzzy_hash"]:
                return True

        return False


def create_enhanced_deduplicator(
    metadata_manager: MetadataManager, path_manager: PathManager
) -> EnhancedDeduplicator:
    """Factory function to create enhanced deduplicator."""
    return EnhancedDeduplicator(metadata_manager, path_manager)


# Convenience functions for integration with existing code
def enhanced_similarity_check(content1: Dict, content2: Dict) -> float:
    """Calculate similarity between two content items."""
    title_sim = (
        JaccardSimilarity.text_similarity(
            content1.get("title", ""), content2.get("title", ""), "words"
        )
        if content1.get("title") and content2.get("title")
        else 0.0
    )

    content_sim = (
        JaccardSimilarity.text_similarity(
            content1.get("content", ""), content2.get("content", ""), "words"
        )
        if content1.get("content") and content2.get("content")
        else 0.0
    )

    # Weight title more heavily
    return 0.6 * title_sim + 0.4 * content_sim


def detect_near_duplicates(
    items: List[Dict], threshold: float = 0.8
) -> List[Tuple[str, str, float]]:
    """Detect near-duplicate pairs in a list of content items.

    Args:
        items: List of content metadata dictionaries
        threshold: Similarity threshold for near-duplicates

    Returns:
        List of (uid1, uid2, similarity_score) tuples
    """
    duplicates = []

    for i in range(len(items)):
        for j in range(i + 1, len(items)):
            item1, item2 = items[i], items[j]
            similarity = enhanced_similarity_check(item1, item2)

            if similarity >= threshold:
                uid1 = item1.get("uid", str(i))
                uid2 = item2.get("uid", str(j))
                duplicates.append((uid1, uid2, similarity))

    return duplicates
