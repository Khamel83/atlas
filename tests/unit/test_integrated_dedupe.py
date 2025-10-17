from unittest.mock import Mock, patch

import pytest

from helpers.enhanced_dedupe import SimilarityMatch
from helpers.integrated_dedupe import (IntegratedDeduplicator,
                                       get_duplicate_info,
                                       get_integrated_deduplicator,
                                       is_duplicate_enhanced)
from helpers.metadata_manager import ContentType


class TestIntegratedDeduplicator:
    """Test IntegratedDeduplicator class methods."""

    @pytest.fixture
    def mock_config(self):
        """Create mock configuration."""
        return {
            "article_output_path": "/test/articles",
            "youtube_output_path": "/test/youtube",
            "podcast_output_path": "/test/podcasts",
            "similarity_threshold": 0.8,
            "fast_duplicate_check": True,
            "content_duplicate_check": True,
        }

    @pytest.fixture
    def deduplicator(self, mock_config):
        """Create IntegratedDeduplicator instance with mocked dependencies."""
        with patch("helpers.integrated_dedupe.MetadataManager") as mock_mm, patch(
            "helpers.integrated_dedupe.PathManager"
        ) as mock_pm, patch(
            "helpers.integrated_dedupe.create_enhanced_deduplicator"
        ) as mock_ed:

            mock_mm.return_value = Mock()
            mock_pm.return_value = Mock()
            mock_ed.return_value = Mock()

            return IntegratedDeduplicator(mock_config)

    def test_init(self, deduplicator, mock_config):
        """Test deduplicator initialization."""
        assert deduplicator.config == mock_config
        assert deduplicator.similarity_threshold == 0.8
        assert deduplicator.fast_check_enabled is True
        assert deduplicator.content_check_enabled is True

    def test_init_with_defaults(self):
        """Test initialization with default config."""
        with patch("helpers.integrated_dedupe.load_config") as mock_config, patch(
            "helpers.integrated_dedupe.MetadataManager"
        ) as mock_mm, patch("helpers.integrated_dedupe.PathManager") as mock_pm, patch(
            "helpers.integrated_dedupe.create_enhanced_deduplicator"
        ) as mock_ed:

            mock_config.return_value = {"similarity_threshold": 0.7}
            mock_mm.return_value = Mock()
            mock_pm.return_value = Mock()
            mock_ed.return_value = Mock()

            deduplicator = IntegratedDeduplicator()
            assert deduplicator.similarity_threshold == 0.7

    @patch("os.path.exists")
    def test_is_url_duplicate_true(self, mock_exists, deduplicator):
        """Test URL duplicate detection when duplicate exists."""
        mock_exists.return_value = True

        result = deduplicator.is_url_duplicate("https://example.com/article")
        assert result is True

    @patch("os.path.exists")
    def test_is_url_duplicate_false(self, mock_exists, deduplicator):
        """Test URL duplicate detection when no duplicate exists."""
        mock_exists.return_value = False

        result = deduplicator.is_url_duplicate("https://example.com/article")
        assert result is False

    def test_is_content_duplicate_disabled(self, deduplicator):
        """Test content duplicate check when disabled."""
        deduplicator.content_check_enabled = False

        result, match = deduplicator.is_content_duplicate(
            ContentType.ARTICLE, {"title": "Test"}
        )
        assert result is False
        assert match is None

    def test_is_content_duplicate_fast_match(self, deduplicator):
        """Test content duplicate with fast hash match."""
        deduplicator.enhanced_deduplicator.fast_duplicate_check.return_value = True

        result, match = deduplicator.is_content_duplicate(
            ContentType.ARTICLE, {"uid": "test1", "title": "Test"}
        )
        assert result is True
        assert match is not None
        assert match.match_type == "hash_match"

    def test_is_content_duplicate_similarity_match(self, deduplicator):
        """Test content duplicate with similarity analysis."""
        deduplicator.enhanced_deduplicator.fast_duplicate_check.return_value = False

        similarity_match = SimilarityMatch(
            primary_uid="existing1",
            duplicate_uid="test1",
            similarity_score=0.85,
            match_type="content_high",
            confidence=0.9,
        )
        deduplicator.enhanced_deduplicator.is_content_duplicate.return_value = (
            True,
            similarity_match,
        )

        result, match = deduplicator.is_content_duplicate(
            ContentType.ARTICLE, {"uid": "test1", "title": "Test"}
        )
        assert result is True
        assert match == similarity_match

    def test_check_all_duplicates_url_duplicate(self, deduplicator):
        """Test comprehensive check with URL duplicate."""
        with patch.object(deduplicator, "is_url_duplicate", return_value=True):
            result = deduplicator.check_all_duplicates(
                "https://example.com/test", ContentType.ARTICLE
            )

        assert result["is_duplicate"] is True
        assert result["duplicate_type"] == "url"
        assert result["url_duplicate"] is True
        assert result["confidence"] == 1.0
        assert result["recommendation"] == "skip"

    def test_check_all_duplicates_content_duplicate(self, deduplicator):
        """Test comprehensive check with content duplicate."""
        with patch.object(
            deduplicator, "is_url_duplicate", return_value=False
        ), patch.object(deduplicator, "is_content_duplicate") as mock_content:

            similarity_match = SimilarityMatch(
                primary_uid="existing1",
                duplicate_uid="test1",
                similarity_score=0.9,
                match_type="title_exact",
                confidence=0.95,
            )
            mock_content.return_value = (True, similarity_match)

            result = deduplicator.check_all_duplicates(
                "https://example.com/test", ContentType.ARTICLE, {"title": "Test"}
            )

        assert result["is_duplicate"] is True
        assert result["duplicate_type"] == "content"
        assert result["content_duplicate"] is True
        assert result["confidence"] == 0.95
        assert result["recommendation"] == "skip"  # High confidence exact match

    def test_check_all_duplicates_medium_similarity(self, deduplicator):
        """Test comprehensive check with medium similarity."""
        with patch.object(
            deduplicator, "is_url_duplicate", return_value=False
        ), patch.object(deduplicator, "is_content_duplicate") as mock_content:

            similarity_match = SimilarityMatch(
                primary_uid="existing1",
                duplicate_uid="test1",
                similarity_score=0.82,
                match_type="content_medium",
                confidence=0.85,
            )
            mock_content.return_value = (True, similarity_match)

            result = deduplicator.check_all_duplicates(
                "https://example.com/test", ContentType.ARTICLE, {"title": "Test"}
            )

        assert result["is_duplicate"] is True
        assert result["duplicate_type"] == "content"
        assert result["recommendation"] == "review"  # Medium confidence

    def test_check_all_duplicates_no_duplicate(self, deduplicator):
        """Test comprehensive check with no duplicates."""
        with patch.object(
            deduplicator, "is_url_duplicate", return_value=False
        ), patch.object(
            deduplicator, "is_content_duplicate", return_value=(False, None)
        ):

            result = deduplicator.check_all_duplicates(
                "https://example.com/test", ContentType.ARTICLE, {"title": "Test"}
            )

        assert result["is_duplicate"] is False
        assert result["duplicate_type"] is None
        assert result["recommendation"] == "process"

    def test_find_similar_content(self, deduplicator):
        """Test finding similar content."""
        mock_matches = [
            SimilarityMatch("uid1", "test", 0.9, "title_high", 0.85),
            SimilarityMatch("uid2", "test", 0.8, "content_medium", 0.75),
        ]
        deduplicator.enhanced_deduplicator.find_duplicates.return_value = mock_matches

        result = deduplicator.find_similar_content(
            ContentType.ARTICLE, {"title": "Test"}, limit=5
        )

        assert result == mock_matches
        assert len(result) <= 5

    def test_get_duplicate_statistics(self, deduplicator):
        """Test getting duplicate statistics."""
        mock_metadata = [
            {"uid": "item1", "content_type": "article", "title": "Article 1"},
            {"uid": "item2", "content_type": "article", "title": "Article 2"},
            {"uid": "item3", "content_type": "youtube", "title": "Video 1"},
        ]
        deduplicator.metadata_manager.get_all_metadata.return_value = mock_metadata

        # Mock find_duplicates to return some matches
        mock_matches = [SimilarityMatch("item1", "item2", 0.85, "title_high", 0.9)]
        deduplicator.enhanced_deduplicator.find_duplicates.return_value = mock_matches

        stats = deduplicator.get_duplicate_statistics()

        assert stats["total_items"] == 3
        assert "content_types" in stats
        assert "article" in stats["content_types"]

    def test_cleanup_duplicates_dry_run(self, deduplicator):
        """Test duplicate cleanup in dry run mode."""
        mock_metadata = [
            {"uid": "item1", "content_type": "article", "title": "Article 1"},
            {"uid": "item2", "content_type": "article", "title": "Article 2"},
        ]
        deduplicator.metadata_manager.get_all_metadata.return_value = mock_metadata

        # Mock high confidence duplicate
        mock_matches = [SimilarityMatch("item1", "item2", 0.98, "title_exact", 0.99)]
        deduplicator.enhanced_deduplicator.find_duplicates.return_value = mock_matches

        result = deduplicator.cleanup_duplicates(
            dry_run=True, confidence_threshold=0.95
        )

        assert result["dry_run"] is True
        assert result["duplicates_found"] >= 0
        assert result["duplicates_removed"] == 0  # Dry run, no actual removal


class TestGlobalFunctions:
    """Test module-level global functions."""

    @patch("helpers.integrated_dedupe._global_deduplicator", None)
    def test_get_integrated_deduplicator(self):
        """Test getting global deduplicator instance."""
        with patch("helpers.integrated_dedupe.IntegratedDeduplicator") as mock_class:
            mock_instance = Mock()
            mock_class.return_value = mock_instance

            # First call should create instance
            result1 = get_integrated_deduplicator()
            assert result1 == mock_instance
            mock_class.assert_called_once()

            # Second call should return same instance
            result2 = get_integrated_deduplicator()
            assert result2 == mock_instance
            # Should not create another instance
            mock_class.assert_called_once()

    def test_is_duplicate_enhanced_true(self):
        """Test enhanced duplicate check returning True."""
        with patch("helpers.integrated_dedupe.get_integrated_deduplicator") as mock_get:
            mock_deduplicator = Mock()
            mock_deduplicator.check_all_duplicates.return_value = {
                "is_duplicate": True,
                "recommendation": "skip",
            }
            mock_get.return_value = mock_deduplicator

            result = is_duplicate_enhanced(
                "https://example.com/test", ContentType.ARTICLE
            )
            assert result is True

    def test_is_duplicate_enhanced_false(self):
        """Test enhanced duplicate check returning False."""
        with patch("helpers.integrated_dedupe.get_integrated_deduplicator") as mock_get:
            mock_deduplicator = Mock()
            mock_deduplicator.check_all_duplicates.return_value = {
                "is_duplicate": False,
                "recommendation": "process",
            }
            mock_get.return_value = mock_deduplicator

            result = is_duplicate_enhanced(
                "https://example.com/test", ContentType.ARTICLE
            )
            assert result is False

    def test_is_duplicate_enhanced_review_recommendation(self):
        """Test enhanced duplicate check with review recommendation."""
        with patch("helpers.integrated_dedupe.get_integrated_deduplicator") as mock_get:
            mock_deduplicator = Mock()
            mock_deduplicator.check_all_duplicates.return_value = {
                "is_duplicate": True,
                "recommendation": "review",  # Not 'skip', so should return False
            }
            mock_get.return_value = mock_deduplicator

            result = is_duplicate_enhanced(
                "https://example.com/test", ContentType.ARTICLE
            )
            assert result is False  # Only skip recommendation returns True

    def test_get_duplicate_info(self):
        """Test getting detailed duplicate information."""
        with patch("helpers.integrated_dedupe.get_integrated_deduplicator") as mock_get:
            mock_deduplicator = Mock()
            expected_info = {
                "is_duplicate": True,
                "duplicate_type": "content",
                "confidence": 0.85,
                "recommendation": "review",
            }
            mock_deduplicator.check_all_duplicates.return_value = expected_info
            mock_get.return_value = mock_deduplicator

            result = get_duplicate_info(
                "https://example.com/test", ContentType.ARTICLE, {"title": "Test"}
            )
            assert result == expected_info
