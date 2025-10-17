#!/usr/bin/env python3
"""
Duplicate Detector for Atlas

This module detects exact and near-duplicate content using content fingerprinting
and semantic similarity analysis.
"""

import re
import hashlib
from typing import List, Dict, Any, Set, Tuple
from collections import defaultdict
import math


class DuplicateDetector:
    """Content duplicate detection system"""

    def __init__(self):
        """Initialize the duplicate detector"""
        # Fingerprinting parameters
        self.fingerprint_length = 128
        self.shingle_size = 5

        # Similarity thresholds
        self.similarity_thresholds = {
            'exact_duplicate': 0.99,
            'near_duplicate': 0.8,
            'similar': 0.6
        }

    def create_content_fingerprint(self, content: str) -> str:
        """
        Create a fingerprint for content using hashing

        Args:
            content (str): Content to fingerprint

        Returns:
            str: Content fingerprint (hash)
        """
        # Normalize content
        normalized_content = self._normalize_content(content)

        # Create SHA256 hash
        fingerprint = hashlib.sha256(normalized_content.encode('utf-8')).hexdigest()

        return fingerprint

    def create_minhash_fingerprint(self, content: str) -> List[int]:
        """
        Create a MinHash fingerprint for approximate duplicate detection

        Args:
            content (str): Content to fingerprint

        Returns:
            List[int]: MinHash fingerprint
        """
        # Normalize and tokenize content
        normalized_content = self._normalize_content(content)
        shingles = self._create_shingles(normalized_content, self.shingle_size)

        # Create MinHash signature
        minhash = self._compute_minhash(shingles, self.fingerprint_length)

        return minhash

    def detect_exact_duplicates(self, content_items: List[Dict[str, Any]]) -> List[Tuple[int, int]]:
        """
        Detect exact duplicate content items

        Args:
            content_items (List[Dict[str, Any]]): Content items to check

        Returns:
            List[Tuple[int, int]]: Pairs of duplicate indices
        """
        print(f"Detecting exact duplicates among {len(content_items)} items...")

        # Create fingerprints for all items
        fingerprints = []
        for i, item in enumerate(content_items):
            content = item.get('content', '') + item.get('title', '')
            fingerprint = self.create_content_fingerprint(content)
            fingerprints.append((i, fingerprint))

        # Find duplicates
        duplicates = []
        seen_fingerprints = {}

        for index, fingerprint in fingerprints:
            if fingerprint in seen_fingerprints:
                # Found duplicate
                original_index = seen_fingerprints[fingerprint]
                duplicates.append((original_index, index))
            else:
                # First time seeing this fingerprint
                seen_fingerprints[fingerprint] = index

        print(f"Found {len(duplicates)} exact duplicate pairs")
        return duplicates

    def detect_near_duplicates(self, content_items: List[Dict[str, Any]]) -> List[Tuple[int, int, float]]:
        """
        Detect near-duplicate content items using MinHash and Jaccard similarity

        Args:
            content_items (List[Dict[str, Any]]): Content items to check

        Returns:
            List[Tuple[int, int, float]]: Pairs of near-duplicate indices with similarity scores
        """
        print(f"Detecting near duplicates among {len(content_items)} items...")

        # Create MinHash fingerprints for all items
        minhash_signatures = []
        for i, item in enumerate(content_items):
            content = item.get('content', '') + ' ' + item.get('title', '')
            minhash = self.create_minhash_fingerprint(content)
            minhash_signatures.append((i, minhash))

        # Compare all pairs
        near_duplicates = []
        for i in range(len(minhash_signatures)):
            for j in range(i + 1, len(minhash_signatures)):
                idx1, hash1 = minhash_signatures[i]
                idx2, hash2 = minhash_signatures[j]

                # Calculate Jaccard similarity using MinHash
                similarity = self._minhash_similarity(hash1, hash2)

                if similarity >= self.similarity_thresholds['near_duplicate']:
                    near_duplicates.append((idx1, idx2, similarity))

        # Sort by similarity (highest first)
        near_duplicates.sort(key=lambda x: x[2], reverse=True)

        print(f"Found {len(near_duplicates)} near-duplicate pairs")
        return near_duplicates

    def detect_cross_source_duplicates(self, content_items: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """
        Detect duplicates across different content sources

        Args:
            content_items (List[Dict[str, Any]]): Content items to check

        Returns:
            Dict[str, List[Dict[str, Any]]]: Duplicates grouped by canonical source
        """
        print("Detecting cross-source duplicates...")

        # Group by content similarity
        similarity_groups = defaultdict(list)

        # Create MinHash fingerprints
        minhash_data = []
        for i, item in enumerate(content_items):
            content = item.get('content', '') + ' ' + item.get('title', '')
            minhash = self.create_minhash_fingerprint(content)
            minhash_data.append((i, item, minhash))

        # Group similar items
        processed_indices = set()
        for i in range(len(minhash_data)):
            if i in processed_indices:
                continue

            current_idx, current_item, current_hash = minhash_data[i]
            current_group = [current_item]
            processed_indices.add(i)

            # Find similar items
            for j in range(i + 1, len(minhash_data)):
                if j in processed_indices:
                    continue

                compare_idx, compare_item, compare_hash = minhash_data[j]
                similarity = self._minhash_similarity(current_hash, compare_hash)

                if similarity >= self.similarity_thresholds['similar']:
                    current_group.append(compare_item)
                    processed_indices.add(j)

            if len(current_group) > 1:
                # Determine canonical source (prefer sources with better reputation)
                canonical_item = self._select_canonical_source(current_group)
                group_key = f"{canonical_item.get('title', 'unknown')}_{len(current_group)}"
                similarity_groups[group_key] = {
                    'canonical': canonical_item,
                    'duplicates': [item for item in current_group if item != canonical_item],
                    'count': len(current_group)
                }

        print(f"Found {len(similarity_groups)} cross-source duplicate groups")
        return dict(similarity_groups)

    def track_content_versions(self, content_items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Track content versions and updates

        Args:
            content_items (List[Dict[str, Any]]): Content items to analyze

        Returns:
            List[Dict[str, Any]]: Content items with version tracking information
        """
        print("Tracking content versions...")

        # Group by title similarity
        version_groups = defaultdict(list)

        # Create simplified fingerprints for titles
        title_data = []
        for i, item in enumerate(content_items):
            title = item.get('title', '').lower()
            fingerprint = self.create_content_fingerprint(title)
            title_data.append((i, item, fingerprint, title))

        # Group similar titles
        processed_indices = set()
        for i in range(len(title_data)):
            if i in processed_indices:
                continue

            current_idx, current_item, current_fingerprint, current_title = title_data[i]
            current_group = [current_item]
            processed_indices.add(i)

            # Find items with same title fingerprint
            for j in range(i + 1, len(title_data)):
                if j in processed_indices:
                    continue

                compare_idx, compare_item, compare_fingerprint, compare_title = title_data[j]

                if current_fingerprint == compare_fingerprint:
                    # Exact title match
                    current_group.append(compare_item)
                    processed_indices.add(j)
                elif self._title_similarity(current_title, compare_title) > 0.9:
                    # Very similar titles
                    current_group.append(compare_item)
                    processed_indices.add(j)

            if len(current_group) > 1:
                # Sort by date to identify versions
                current_group.sort(key=lambda x: x.get('timestamp', ''), reverse=True)

                # Add version tracking info
                for version_idx, item in enumerate(current_group):
                    item['version_info'] = {
                        'is_latest': version_idx == 0,
                        'version_number': len(current_group) - version_idx,
                        'total_versions': len(current_group),
                        'previous_version': current_group[version_idx + 1] if version_idx < len(current_group) - 1 else None,
                        'next_version': current_group[version_idx - 1] if version_idx > 0 else None
                    }

                version_groups[f"version_group_{len(version_groups)}"] = current_group

        # Flatten results
        versioned_items = []
        for group in version_groups.values():
            versioned_items.extend(group)

        print(f"Tracked versions for {len(versioned_items)} content items")
        return versioned_items

    def identify_canonical_sources(self, duplicate_groups: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Identify canonical sources from duplicate groups

        Args:
            duplicate_groups (Dict[str, Dict[str, Any]]): Duplicate groups

        Returns:
            List[Dict[str, Any]]: Canonical sources with duplicate information
        """
        canonical_sources = []

        for group_key, group_data in duplicate_groups.items():
            canonical = group_data['canonical']
            duplicates = group_data['duplicates']

            # Add duplicate information to canonical source
            canonical['duplicate_info'] = {
                'group_key': group_key,
                'duplicate_count': len(duplicates),
                'duplicates': duplicates,
                'canonical_reason': self._determine_canonical_reason(canonical, duplicates)
            }

            canonical_sources.append(canonical)

        return canonical_sources

    def _normalize_content(self, content: str) -> str:
        """
        Normalize content for fingerprinting

        Args:
            content (str): Content to normalize

        Returns:
            str: Normalized content
        """
        # Convert to lowercase
        content = content.lower()

        # Remove extra whitespace
        content = re.sub(r'\s+', ' ', content)

        # Remove HTML tags
        content = re.sub(r'<[^>]+>', '', content)

        # Remove URLs
        content = re.sub(r'https?://\S+', '', content)

        # Remove punctuation (except apostrophes within words)
        content = re.sub(r'[^\w\s\']', ' ', content)

        # Remove extra spaces again
        content = re.sub(r'\s+', ' ', content).strip()

        return content

    def _create_shingles(self, content: str, shingle_size: int) -> Set[str]:
        """
        Create shingles (n-grams) from content

        Args:
            content (str): Content to shingle
            shingle_size (int): Size of shingles

        Returns:
            Set[str]: Set of shingles
        """
        words = content.split()
        shingles = set()

        for i in range(len(words) - shingle_size + 1):
            shingle = ' '.join(words[i:i + shingle_size])
            shingles.add(shingle)

        return shingles

    def _compute_minhash(self, shingles: Set[str], signature_length: int) -> List[int]:
        """
        Compute MinHash signature for shingles

        Args:
            shingles (Set[str]): Set of shingles
            signature_length (int): Length of MinHash signature

        Returns:
            List[int]: MinHash signature
        """
        # Simple implementation using hash functions
        signature = []

        for i in range(signature_length):
            min_hash = float('inf')
            for shingle in shingles:
                # Create hash with different seeds
                hash_value = hash(f"{shingle}_{i}") % (2**32)
                min_hash = min(min_hash, hash_value)
            signature.append(min_hash)

        return signature

    def _minhash_similarity(self, hash1: List[int], hash2: List[int]) -> float:
        """
        Calculate Jaccard similarity using MinHash signatures

        Args:
            hash1 (List[int]): First MinHash signature
            hash2 (List[int]): Second MinHash signature

        Returns:
            float: Jaccard similarity estimate
        """
        if len(hash1) != len(hash2):
            return 0.0

        matches = sum(1 for a, b in zip(hash1, hash2) if a == b)
        similarity = matches / len(hash1)

        return similarity

    def _select_canonical_source(self, content_group: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Select canonical source from a group of similar content

        Args:
            content_group (List[Dict[str, Any]]): Group of similar content items

        Returns:
            Dict[str, Any]: Canonical source
        """
        # Prefer sources based on:
        # 1. Higher quality score
        # 2. More complete content
        # 3. Better source reputation
        # 4. Earlier publication date (more original)

        def source_score(item):
            quality = item.get('quality_score', 0.5)
            word_count = len(item.get('content', '').split())
            reputation = self._source_reputation(item.get('source_url', ''))
            timestamp = item.get('timestamp', '9999-12-31')  # Default to future date

            # Convert timestamp to sortable value (lower = better for original content)
            try:
                import datetime
                ts_value = datetime.datetime.fromisoformat(timestamp.replace('Z', '+00:00')).timestamp()
            except:
                ts_value = 0  # If parsing fails, treat as earliest

            # Calculate composite score (higher is better)
            score = (
                quality * 0.4 +
                min(word_count / 1000, 1.0) * 0.3 +
                reputation * 0.2 +
                (1 - ts_value / (2**32)) * 0.1  # Invert timestamp value
            )

            return score

        return max(content_group, key=source_score)

    def _source_reputation(self, source_url: str) -> float:
        """
        Estimate source reputation

        Args:
            source_url (str): Source URL

        Returns:
            float: Reputation score (0.0 to 1.0)
        """
        # Simple reputation scoring based on known domains
        reputable_domains = {
            'wikipedia.org': 0.95,
            'github.com': 0.9,
            'stackoverflow.com': 0.9,
            'medium.com': 0.8,
            'towardsdatascience.com': 0.8,
            'realpython.com': 0.85,
            'javascript.info': 0.85,
            'arxiv.org': 0.95,
            'nature.com': 0.95,
            'science.org': 0.95
        }

        import re
        domain_match = re.search(r'https?://([^/]+)', source_url)
        if domain_match:
            domain = domain_match.group(1)
            return reputable_domains.get(domain, 0.5)

        return 0.5

    def _title_similarity(self, title1: str, title2: str) -> float:
        """
        Calculate similarity between two titles

        Args:
            title1 (str): First title
            title2 (str): Second title

        Returns:
            float: Similarity score (0.0 to 1.0)
        """
        # Simple word overlap similarity
        words1 = set(title1.lower().split())
        words2 = set(title2.lower().split())

        if not words1 and not words2:
            return 1.0
        if not words1 or not words2:
            return 0.0

        intersection = len(words1.intersection(words2))
        union = len(words1.union(words2))

        return intersection / union if union > 0 else 0.0

    def _determine_canonical_reason(self, canonical: Dict[str, Any],
                                 duplicates: List[Dict[str, Any]]) -> str:
        """
        Determine reason for selecting canonical source

        Args:
            canonical (Dict[str, Any]): Canonical source
            duplicates (List[Dict[str, Any]]): Duplicate sources

        Returns:
            str: Reason for canonical selection
        """
        # Check if it has the highest quality
        canonical_quality = canonical.get('quality_score', 0)
        highest_quality = max(
            [canonical_quality] + [d.get('quality_score', 0) for d in duplicates]
        )

        if canonical_quality == highest_quality:
            return "highest_quality"

        # Check if it's the most complete
        canonical_length = len(canonical.get('content', ''))
        longest_content = max(
            [canonical_length] + [len(d.get('content', '')) for d in duplicates]
        )

        if canonical_length == longest_content:
            return "most_complete"

        # Check if it's the original source
        canonical_timestamp = canonical.get('timestamp', '9999-12-31')
        earliest_timestamp = min(
            [canonical_timestamp] + [d.get('timestamp', '9999-12-31') for d in duplicates]
        )

        if canonical_timestamp == earliest_timestamp:
            return "original_source"

        return "comprehensive_assessment"


def main():
    """Example usage of DuplicateDetector"""
    # Create duplicate detector
    detector = DuplicateDetector()

    # Sample content items
    sample_content = [
        {
            'title': 'Introduction to Python Programming',
            'content': 'Python is a high-level programming language known for its simplicity and readability. It is widely used in web development, data science, and automation.',
            'source_url': 'https://realpython.com/python-intro',
            'timestamp': '2023-01-01T10:00:00Z',
            'quality_score': 0.85
        },
        {
            'title': 'Python Programming Basics',
            'content': 'Python is a high-level programming language known for its simplicity and readability. It is widely used in web development, data science, and automation.',
            'source_url': 'https://example.com/python-basics',
            'timestamp': '2023-01-02T10:00:00Z',
            'quality_score': 0.75
        },
        {
            'title': 'Getting Started with Python',
            'content': 'Python is a versatile programming language. This tutorial covers variables, loops, functions, and basic syntax. Perfect for beginners.',
            'source_url': 'https://tutorials.com/python-start',
            'timestamp': '2023-01-03T10:00:00Z',
            'quality_score': 0.80
        },
        {
            'title': 'Advanced JavaScript Techniques',
            'content': 'Learn advanced JavaScript concepts including closures, prototypes, and asynchronous programming patterns.',
            'source_url': 'https://javascript.info/advanced',
            'timestamp': '2023-02-01T10:00:00Z',
            'quality_score': 0.90
        },
        {
            'title': 'Advanced JavaScript Techniques',
            'content': 'Learn advanced JavaScript concepts including closures, prototypes, and asynchronous programming patterns.',
            'source_url': 'https://example.com/js-advanced',
            'timestamp': '2023-02-02T10:00:00Z',
            'quality_score': 0.85
        }
    ]

    # Detect exact duplicates
    print("Detecting exact duplicates...")
    exact_duplicates = detector.detect_exact_duplicates(sample_content)
    print(f"Found {len(exact_duplicates)} exact duplicate pairs")
    for idx1, idx2 in exact_duplicates:
        print(f"  Duplicate: '{sample_content[idx1]['title']}' and '{sample_content[idx2]['title']}'")

    # Detect near duplicates
    print("\nDetecting near duplicates...")
    near_duplicates = detector.detect_near_duplicates(sample_content)
    print(f"Found {len(near_duplicates)} near duplicate pairs")
    for idx1, idx2, similarity in near_duplicates[:5]:  # Show top 5
        print(f"  Near duplicate ({similarity:.3f}): '{sample_content[idx1]['title']}' and '{sample_content[idx2]['title']}'")

    # Detect cross-source duplicates
    print("\nDetecting cross-source duplicates...")
    cross_source_duplicates = detector.detect_cross_source_duplicates(sample_content)
    print(f"Found {len(cross_source_duplicates)} cross-source duplicate groups")
    for group_key, group_data in list(cross_source_duplicates.items())[:2]:  # Show first 2
        print(f"  Group: {group_key}")
        print(f"    Canonical: {group_data['canonical']['title']}")
        print(f"    Duplicates: {group_data['count'] - 1}")
        for dup in group_data['duplicates'][:2]:  # Show first 2 duplicates
            print(f"      - {dup['title']} from {dup['source_url']}")

    # Track content versions
    print("\nTracking content versions...")
    versioned_content = detector.track_content_versions(sample_content)
    versioned_items = [item for item in versioned_content if 'version_info' in item]
    print(f"Tracked versions for {len(versioned_items)} items")
    for item in versioned_items[:3]:  # Show first 3
        version_info = item['version_info']
        print(f"  {item['title']}: Version {version_info['version_number']} of {version_info['total_versions']}")
        print(f"    Latest: {version_info['is_latest']}")

    # Test fingerprinting
    print("\n\nTesting content fingerprinting...")
    test_content = "This is a test content for fingerprinting."
    fingerprint = detector.create_content_fingerprint(test_content)
    minhash = detector.create_minhash_fingerprint(test_content)

    print(f"Content: {test_content}")
    print(f"Fingerprint: {fingerprint[:32]}...")  # Show first 32 characters
    print(f"MinHash length: {len(minhash)}")


if __name__ == "__main__":
    main()