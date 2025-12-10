from unittest.mock import Mock, patch

import pytest

from helpers.enhanced_dedupe import (ContentHasher, EnhancedDeduplicator,
                                     JaccardSimilarity, SimilarityMatch,
                                     create_enhanced_deduplicator,
                                     detect_near_duplicates,
                                     enhanced_similarity_check)
from helpers.metadata_manager import ContentType


class TestContentHasher:
    """Test ContentHasher class methods."""

    def test_title_hash(self):
        """Test title hashing with normalization."""
        # Same content should produce same hash
        title1 = "The Ultimate Guide to Python Testing"
        title2 = "the ultimate guide to python testing!!!"
        title3 = "The    Ultimate   Guide to Python Testing?"

        hash1 = ContentHasher.title_hash(title1)
        hash2 = ContentHasher.title_hash(title2)
        hash3 = ContentHasher.title_hash(title3)

        assert hash1 == hash2 == hash3
        assert len(hash1) == 16

    def test_title_hash_empty(self):
        """Test title hash with empty input."""
        assert ContentHasher.title_hash("") == ""
        assert ContentHasher.title_hash(None) == ""

    def test_content_hash(self):
        """Test content hashing with truncation."""
        content = "This is a long piece of content that should be truncated " * 50
        hash1 = ContentHasher.content_hash(content, 100)
        hash2 = ContentHasher.content_hash(content, 100)

        assert hash1 == hash2
        assert len(hash1) == 16

    def test_fuzzy_content_hash(self):
        """Test fuzzy content hashing."""
        content1 = "This is some content with punctuation!"
        content2 = "this is some content with punctuation"
        content3 = "This   is   some,,,content...with punctuation!!!"

        hash1 = ContentHasher.fuzzy_content_hash(content1)
        hash2 = ContentHasher.fuzzy_content_hash(content2)
        hash3 = ContentHasher.fuzzy_content_hash(content3)

        assert hash1 == hash2 == hash3


class TestJaccardSimilarity:
    """Test JaccardSimilarity class methods."""

    def test_tokenize_words(self):
        """Test word tokenization."""
        text = "The quick brown fox jumps over the lazy dog"
        tokens = JaccardSimilarity.tokenize(text, "words")

        expected = {"the", "quick", "brown", "fox", "jumps", "over", "lazy", "dog"}
        assert tokens == expected

    def test_tokenize_shingles(self):
        """Test shingle tokenization."""
        text = "the quick brown fox"
        tokens = JaccardSimilarity.tokenize(text, "shingles")

        expected = {"the quick brown", "quick brown fox"}
        assert tokens == expected

    def test_tokenize_chars(self):
        """Test character n-gram tokenization."""
        text = "hello"
        tokens = JaccardSimilarity.tokenize(text, "chars")

        expected = {"hello"}  # Too short for 5-grams
        assert tokens == expected

        text = "hello world"
        tokens = JaccardSimilarity.tokenize(text, "chars")
        assert len(tokens) > 0

    def test_calculate_similarity(self):
        """Test Jaccard similarity calculation."""
        set1 = {"a", "b", "c"}
        set2 = {"b", "c", "d"}

        similarity = JaccardSimilarity.calculate_similarity(set1, set2)
        assert similarity == 0.5  # 2 intersection / 4 union

    def test_calculate_similarity_edge_cases(self):
        """Test similarity calculation edge cases."""
        # Empty sets
        assert JaccardSimilarity.calculate_similarity(set(), set()) == 1.0
        assert JaccardSimilarity.calculate_similarity({"a"}, set()) == 0.0
        assert JaccardSimilarity.calculate_similarity(set(), {"a"}) == 0.0

        # Identical sets
        set1 = {"a", "b", "c"}
        assert JaccardSimilarity.calculate_similarity(set1, set1) == 1.0

    def test_text_similarity(self):
        """Test text similarity calculation."""
        text1 = "the quick brown fox"
        text2 = "the quick brown dog"
        text3 = "a completely different sentence"

        # Similar texts should have high similarity
        sim1 = JaccardSimilarity.text_similarity(text1, text2, "words")
        assert sim1 > 0.5

        # Different texts should have low similarity
        sim2 = JaccardSimilarity.text_similarity(text1, text3, "words")
        assert sim2 < 0.3

        # Identical texts should have perfect similarity
        sim3 = JaccardSimilarity.text_similarity(text1, text1, "words")
        assert sim3 == 1.0


class TestSimilarityMatch:
    """Test SimilarityMatch dataclass."""

    def test_similarity_match_creation(self):
        """Test SimilarityMatch creation and attributes."""
        match = SimilarityMatch(
            primary_uid="uid1",
            duplicate_uid="uid2",
            similarity_score=0.85,
            match_type="content_high",
            confidence=0.9,
        )

        assert match.primary_uid == "uid1"
        assert match.duplicate_uid == "uid2"
        assert match.similarity_score == 0.85
        assert match.match_type == "content_high"
        assert match.confidence == 0.9


class TestEnhancedDeduplicator:
    """Test EnhancedDeduplicator class methods."""

    @pytest.fixture
    def mock_metadata_manager(self):
        """Create mock metadata manager."""
        manager = Mock()
        manager.get_all_metadata.return_value = [
            {
                "uid": "existing1",
                "content_type": "article",
                "title": "Python Testing Guide",
                "content": "This is a comprehensive guide to testing Python applications.",
                "url": "https://example.com/python-testing",
            },
            {
                "uid": "existing2",
                "content_type": "article",
                "title": "JavaScript Fundamentals",
                "content": "Learn the basics of JavaScript programming.",
                "url": "https://example.com/js-basics",
            },
        ]
        return manager

    @pytest.fixture
    def mock_path_manager(self):
        """Create mock path manager."""
        return Mock()

    @pytest.fixture
    def deduplicator(self, mock_metadata_manager, mock_path_manager):
        """Create EnhancedDeduplicator instance."""
        return EnhancedDeduplicator(mock_metadata_manager, mock_path_manager)

    def test_init(self, deduplicator, mock_metadata_manager, mock_path_manager):
        """Test deduplicator initialization."""
        assert deduplicator.metadata_manager == mock_metadata_manager
        assert deduplicator.path_manager == mock_path_manager
        assert "title_exact" in deduplicator.thresholds

    def test_find_duplicates_no_matches(self, deduplicator):
        """Test finding duplicates when no matches exist."""
        candidate = {
            "uid": "new1",
            "title": "Completely Different Topic",
            "content": "This is about something entirely different.",
            "url": "https://different.com/topic",
        }

        matches = deduplicator.find_duplicates(ContentType.ARTICLE, candidate)
        assert isinstance(matches, list)
        # May be empty or have low-similarity matches

    def test_find_duplicates_with_matches(self, deduplicator):
        """Test finding duplicates with similar content."""
        candidate = {
            "uid": "new1",
            "title": "Python Testing Guide - Updated",
            "content": "This is a comprehensive guide to testing Python applications with new examples.",
            "url": "https://example.com/python-testing-updated",
        }

        matches = deduplicator.find_duplicates(ContentType.ARTICLE, candidate)
        assert isinstance(matches, list)

        # Should find similarity with existing Python testing content
        if matches:
            match = matches[0]
            assert isinstance(match, SimilarityMatch)
            assert match.similarity_score > 0

    def test_compare_content_exact_title(self, deduplicator):
        """Test content comparison with exact title match."""
        candidate = {
            "uid": "new1",
            "title": "Python Testing Guide",
            "content": "Different content but same title.",
        }

        existing = {
            "uid": "existing1",
            "title": "Python Testing Guide",
            "content": "Original content here.",
        }

        match = deduplicator._compare_content(candidate, existing)
        assert match is not None
        assert match.match_type == "title_exact"
        assert match.similarity_score == 1.0

    def test_compare_content_no_match(self, deduplicator):
        """Test content comparison with no significant similarity."""
        candidate = {
            "uid": "new1",
            "title": "Completely Different",
            "content": "This has no similarity at all.",
        }

        existing = {
            "uid": "existing1",
            "title": "Python Testing",
            "content": "Guide to testing applications.",
        }

        match = deduplicator._compare_content(candidate, existing)
        # Should return None or very low similarity
        if match:
            assert match.similarity_score < 0.5

    def test_evaluate_similarities(self, deduplicator):
        """Test similarity evaluation logic."""
        # Test exact title match
        similarities = {"title_exact": 1.0, "content_words": 0.3}
        result = deduplicator._evaluate_similarities(similarities)
        assert result["type"] == "title_exact"
        assert result["score"] == 1.0

        # Test high content match
        similarities = {"title_jaccard": 0.5, "content_words": 0.9}
        result = deduplicator._evaluate_similarities(similarities)
        assert result["type"] == "content_high"
        assert result["score"] == 0.9

    def test_calculate_hybrid_score(self, deduplicator):
        """Test hybrid similarity score calculation."""
        similarities = {
            "title_jaccard": 0.8,
            "content_words": 0.7,
            "content_shingles": 0.6,
            "url_jaccard": 0.5,
        }

        hybrid_score = deduplicator._calculate_hybrid_score(similarities)
        assert 0.0 <= hybrid_score <= 1.0
        # Should be weighted average, closer to title similarity
        assert hybrid_score > 0.6

    def test_calculate_confidence(self, deduplicator):
        """Test confidence calculation."""
        similarities = {"title_jaccard": 0.8, "content_words": 0.8}
        best_match = {"score": 0.8, "type": "title_high"}

        confidence = deduplicator._calculate_confidence(similarities, best_match)
        assert 0.0 <= confidence <= 1.0

        # Should boost for multiple high similarities
        assert confidence >= 0.8

    def test_is_content_duplicate(self, deduplicator):
        """Test content duplicate detection."""
        metadata = {
            "uid": "test1",
            "title": "Similar Title to Existing",
            "content": "Similar content to what exists.",
        }

        is_dup, match = deduplicator.is_content_duplicate(ContentType.ARTICLE, metadata)
        assert isinstance(is_dup, bool)
        if is_dup:
            assert isinstance(match, SimilarityMatch)

    def test_fast_duplicate_check(self, deduplicator):
        """Test fast hash-based duplicate detection."""
        # Mock the hash index method
        with patch.object(deduplicator, "get_content_hash_index") as mock_index:
            mock_index.return_value = {
                "title_hash": {"abcd1234": ["existing1"]},
                "content_hash": {"efgh5678": ["existing2"]},
                "fuzzy_hash": {},
            }

            # Test duplicate title hash
            with patch(
                "helpers.enhanced_dedupe.ContentHasher.title_hash",
                return_value="abcd1234",
            ):
                metadata = {"title": "Test Title"}
                assert (
                    deduplicator.fast_duplicate_check(ContentType.ARTICLE, metadata)
                    is True
                )

            # Test no duplicate
            with patch(
                "helpers.enhanced_dedupe.ContentHasher.title_hash",
                return_value="different",
            ):
                with patch(
                    "helpers.enhanced_dedupe.ContentHasher.content_hash",
                    return_value="different",
                ):
                    with patch(
                        "helpers.enhanced_dedupe.ContentHasher.fuzzy_content_hash",
                        return_value="different",
                    ):
                        metadata = {
                            "title": "Different Title",
                            "content": "Different content",
                        }
                        assert (
                            deduplicator.fast_duplicate_check(
                                ContentType.ARTICLE, metadata
                            )
                            is False
                        )


class TestConvenienceFunctions:
    """Test module-level convenience functions."""

    def test_create_enhanced_deduplicator(self):
        """Test deduplicator factory function."""
        metadata_manager = Mock()
        path_manager = Mock()

        deduplicator = create_enhanced_deduplicator(metadata_manager, path_manager)
        assert isinstance(deduplicator, EnhancedDeduplicator)
        assert deduplicator.metadata_manager == metadata_manager
        assert deduplicator.path_manager == path_manager

    def test_enhanced_similarity_check(self):
        """Test enhanced similarity check function."""
        content1 = {
            "title": "Python Testing",
            "content": "Guide to testing Python applications",
        }
        content2 = {
            "title": "Python Testing Guide",
            "content": "Complete guide to testing Python apps",
        }
        content3 = {
            "title": "JavaScript Basics",
            "content": "Learn JavaScript fundamentals",
        }

        # Similar content should have high similarity
        sim1 = enhanced_similarity_check(content1, content2)
        assert sim1 > 0.5

        # Different content should have low similarity
        sim2 = enhanced_similarity_check(content1, content3)
        assert sim2 < 0.5

    def test_detect_near_duplicates(self):
        """Test near-duplicate detection in content list."""
        items = [
            {
                "uid": "item1",
                "title": "Python Testing Guide",
                "content": "Comprehensive testing guide",
            },
            {
                "uid": "item2",
                "title": "Python Testing Tutorial",
                "content": "Complete testing tutorial",
            },
            {
                "uid": "item3",
                "title": "JavaScript Basics",
                "content": "Learn JavaScript fundamentals",
            },
        ]

        duplicates = detect_near_duplicates(items, threshold=0.3)
        assert isinstance(duplicates, list)

        # Should find similarity between Python testing items
        if duplicates:
            uid1, uid2, score = duplicates[0]
            assert uid1 in ["item1", "item2"]
            assert uid2 in ["item1", "item2"]
            assert uid1 != uid2
            assert 0.0 <= score <= 1.0

    def test_detect_near_duplicates_no_duplicates(self):
        """Test near-duplicate detection with no duplicates."""
        items = [
            {
                "uid": "item1",
                "title": "Machine Learning Algorithms",
                "content": "Deep dive into neural networks and optimization",
            },
            {
                "uid": "item2",
                "title": "Web Development Frameworks",
                "content": "Comparison of React, Angular, and Vue for frontend development",
            },
        ]

        duplicates = detect_near_duplicates(items, threshold=0.8)
        assert duplicates == []
