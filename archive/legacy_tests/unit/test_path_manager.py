import os
from unittest.mock import patch

import pytest

from helpers.metadata_manager import ContentType
from helpers.path_manager import (PathManager, PathSet, PathType,
                                  create_path_manager,
                                  ensure_content_directories,
                                  get_content_paths, get_log_path)


@pytest.fixture
def config(tmp_path):
    return {
        "data_directory": str(tmp_path),
        "article_output_path": os.path.join(str(tmp_path), "articles"),
        "podcast_output_path": os.path.join(str(tmp_path), "podcasts"),
        "youtube_output_path": os.path.join(str(tmp_path), "youtube"),
    }


@pytest.fixture
def minimal_config(tmp_path):
    """Config with minimal settings to test defaults."""
    return {"data_directory": str(tmp_path)}


@pytest.fixture
def path_manager(config):
    return PathManager(config)


@pytest.fixture
def minimal_path_manager(minimal_config):
    return PathManager(minimal_config)


class TestPathManager:
    """Test PathManager class methods."""

    def test_init_with_custom_config(self, config, tmp_path):
        """Test PathManager initialization with custom config."""
        manager = PathManager(config)
        assert manager.data_directory == str(tmp_path)
        assert manager.type_directories[ContentType.ARTICLE] == os.path.join(
            str(tmp_path), "articles"
        )
        assert manager.type_directories[ContentType.PODCAST] == os.path.join(
            str(tmp_path), "podcasts"
        )
        assert manager.type_directories[ContentType.YOUTUBE] == os.path.join(
            str(tmp_path), "youtube"
        )
        assert manager.type_directories[ContentType.INSTAPAPER] == os.path.join(
            str(tmp_path), "articles"
        )

    def test_init_with_defaults(self, minimal_config, tmp_path):
        """Test PathManager initialization with default paths."""
        manager = PathManager(minimal_config)
        assert manager.data_directory == str(tmp_path)
        # Default paths should be built using the data_directory as base
        assert manager.type_directories[ContentType.ARTICLE] == os.path.join(
            str(tmp_path), "articles"
        )
        assert manager.type_directories[ContentType.PODCAST] == os.path.join(
            str(tmp_path), "podcasts"
        )
        assert manager.type_directories[ContentType.YOUTUBE] == os.path.join(
            str(tmp_path), "youtube"
        )

    def test_get_base_directory(self, path_manager, tmp_path):
        """Test getting base directories for different content types."""
        assert path_manager.get_base_directory(ContentType.ARTICLE) == os.path.join(
            str(tmp_path), "articles"
        )
        assert path_manager.get_base_directory(ContentType.PODCAST) == os.path.join(
            str(tmp_path), "podcasts"
        )
        assert path_manager.get_base_directory(ContentType.YOUTUBE) == os.path.join(
            str(tmp_path), "youtube"
        )
        assert path_manager.get_base_directory(ContentType.INSTAPAPER) == os.path.join(
            str(tmp_path), "articles"
        )

    def test_get_path_set_article(self, path_manager, tmp_path):
        """Test getting path set for article content type."""
        path_set = path_manager.get_path_set(ContentType.ARTICLE, "test_uid")
        assert path_set.uid == "test_uid"
        assert path_set.content_type == ContentType.ARTICLE
        assert path_set.base_dir == os.path.join(str(tmp_path), "articles")
        assert path_set.get_path(PathType.METADATA) == os.path.join(
            str(tmp_path), "articles", "metadata", "test_uid.json"
        )
        assert path_set.get_path(PathType.MARKDOWN) == os.path.join(
            str(tmp_path), "articles", "markdown", "test_uid.md"
        )
        assert path_set.get_path(PathType.HTML) == os.path.join(
            str(tmp_path), "articles", "html", "test_uid.html"
        )
        assert path_set.get_path(PathType.LOG) == os.path.join(
            str(tmp_path), "articles", "ingest.log"
        )

    def test_get_path_set_podcast(self, path_manager, tmp_path):
        """Test getting path set for podcast content type."""
        path_set = path_manager.get_path_set(ContentType.PODCAST, "test_uid")
        assert path_set.uid == "test_uid"
        assert path_set.content_type == ContentType.PODCAST
        assert path_set.get_path(PathType.AUDIO) == os.path.join(
            str(tmp_path), "podcasts", "audio", "test_uid.mp3"
        )
        assert path_set.get_path(PathType.TRANSCRIPT) == os.path.join(
            str(tmp_path), "podcasts", "transcripts", "test_uid.txt"
        )

    def test_get_path_set_youtube(self, path_manager, tmp_path):
        """Test getting path set for youtube content type."""
        path_set = path_manager.get_path_set(ContentType.YOUTUBE, "test_uid")
        assert path_set.uid == "test_uid"
        assert path_set.content_type == ContentType.YOUTUBE
        assert path_set.get_path(PathType.VIDEO) == os.path.join(
            str(tmp_path), "youtube", "videos", "test_uid.mp4"
        )
        assert path_set.get_path(PathType.TRANSCRIPT) == os.path.join(
            str(tmp_path), "youtube", "transcripts", "test_uid.txt"
        )

    def test_get_single_path(self, path_manager, tmp_path):
        """Test getting a single path for a content item."""
        metadata_path = path_manager.get_single_path(
            ContentType.ARTICLE, "test_uid", PathType.METADATA
        )
        assert metadata_path == os.path.join(
            str(tmp_path), "articles", "metadata", "test_uid.json"
        )

        # Test non-existent path type
        temp_path = path_manager.get_single_path(
            ContentType.ARTICLE, "test_uid", PathType.TEMP
        )
        assert temp_path is None

    def test_ensure_directories_without_uid(self, path_manager, tmp_path):
        """Test ensuring directories exist without specific UID."""
        result = path_manager.ensure_directories(ContentType.ARTICLE)
        assert result is True

        # Check that directories were created
        base_dir = os.path.join(str(tmp_path), "articles")
        assert os.path.exists(os.path.join(base_dir, "metadata"))
        assert os.path.exists(os.path.join(base_dir, "markdown"))
        assert os.path.exists(os.path.join(base_dir, "html"))

    def test_ensure_directories_with_uid(self, path_manager, tmp_path):
        """Test ensuring directories exist with specific UID."""
        result = path_manager.ensure_directories(ContentType.PODCAST, "test_uid")
        assert result is True

        # Check that directories were created
        base_dir = os.path.join(str(tmp_path), "podcasts")
        assert os.path.exists(os.path.join(base_dir, "metadata"))
        assert os.path.exists(os.path.join(base_dir, "audio"))
        assert os.path.exists(os.path.join(base_dir, "transcripts"))

    @patch("os.makedirs", side_effect=OSError("Permission denied"))
    def test_ensure_directories_os_error(self, mock_makedirs, path_manager):
        """Test ensure_directories with OS error."""
        result = path_manager.ensure_directories(ContentType.ARTICLE)
        assert result is False

    def test_get_log_path(self, path_manager, tmp_path):
        """Test getting log path for content type."""
        log_path = path_manager.get_log_path(ContentType.ARTICLE)
        assert log_path == os.path.join(str(tmp_path), "articles", "ingest.log")

    def test_get_evaluation_path(self, path_manager):
        """Test getting evaluation path for content item."""
        eval_path = path_manager.get_evaluation_path(ContentType.ARTICLE, "test_uid")
        assert eval_path == os.path.join("evaluation", "article", "test_uid.eval.json")

    def test_get_temp_path(self, path_manager, tmp_path):
        """Test getting temporary path for processing."""
        temp_path = path_manager.get_temp_path(ContentType.ARTICLE, "test_uid")
        expected = os.path.join(str(tmp_path), "articles", "temp", "test_uid")
        assert temp_path == expected
        assert os.path.exists(os.path.dirname(temp_path))  # temp dir created

        # Test with suffix
        temp_path_suffix = path_manager.get_temp_path(
            ContentType.ARTICLE, "test_uid", ".tmp"
        )
        expected_suffix = os.path.join(
            str(tmp_path), "articles", "temp", "test_uid.tmp"
        )
        assert temp_path_suffix == expected_suffix

    def test_cleanup_temp_files_specific_uid(self, path_manager, tmp_path):
        """Test cleaning up temp files for specific UID."""
        # Create temp files
        temp_dir = os.path.join(str(tmp_path), "articles", "temp")
        os.makedirs(temp_dir, exist_ok=True)

        # Create test files
        test_file1 = os.path.join(temp_dir, "test_uid_1.tmp")
        test_file2 = os.path.join(temp_dir, "test_uid_2.tmp")
        other_file = os.path.join(temp_dir, "other_uid.tmp")

        for file_path in [test_file1, test_file2, other_file]:
            with open(file_path, "w") as f:
                f.write("test")

        # Cleanup specific UID
        result = path_manager.cleanup_temp_files(ContentType.ARTICLE, "test_uid")
        assert result is True

        # Check that only test_uid files were removed
        assert not os.path.exists(test_file1)
        assert not os.path.exists(test_file2)
        assert os.path.exists(other_file)

    def test_cleanup_temp_files_all(self, path_manager, tmp_path):
        """Test cleaning up all temp files."""
        # Create temp files
        temp_dir = os.path.join(str(tmp_path), "articles", "temp")
        os.makedirs(temp_dir, exist_ok=True)

        test_file = os.path.join(temp_dir, "test.tmp")
        with open(test_file, "w") as f:
            f.write("test")

        # Cleanup all files
        result = path_manager.cleanup_temp_files(ContentType.ARTICLE)
        assert result is True

        # Check that temp directory exists but is empty
        assert os.path.exists(temp_dir)
        assert len(os.listdir(temp_dir)) == 0

    def test_cleanup_temp_files_no_temp_dir(self, path_manager):
        """Test cleanup when temp directory doesn't exist."""
        result = path_manager.cleanup_temp_files(ContentType.ARTICLE)
        assert result is True

    def test_cleanup_temp_files_os_error(self, path_manager, tmp_path):
        """Test cleanup_temp_files with OS error."""
        # Create temp directory and file first
        temp_dir = os.path.join(str(tmp_path), "articles", "temp")
        os.makedirs(temp_dir, exist_ok=True)
        temp_file = os.path.join(temp_dir, "test.tmp")
        with open(temp_file, "w") as f:
            f.write("test")

        # Mock shutil.rmtree to raise an error
        with patch("shutil.rmtree", side_effect=OSError("Permission denied")):
            result = path_manager.cleanup_temp_files(ContentType.ARTICLE)
            assert result is False

    def test_get_relative_path(self, path_manager, tmp_path):
        """Test converting absolute path to relative path."""
        absolute_path = os.path.join(str(tmp_path), "articles", "metadata", "test.json")
        relative_path = path_manager.get_relative_path(absolute_path)
        assert relative_path == os.path.join("articles", "metadata", "test.json")

    def test_get_relative_path_outside_data_dir(self, path_manager):
        """Test get_relative_path with path outside data directory."""
        outside_path = "/completely/different/path/file.txt"
        result = path_manager.get_relative_path(outside_path)
        # os.path.relpath may still compute a relative path, just check it's not the same
        # The actual behavior is that it returns a relative path with .. components
        assert "../" in result or result == outside_path

    @patch("os.path.relpath", side_effect=ValueError("Invalid path"))
    def test_get_relative_path_value_error(self, mock_relpath, path_manager):
        """Test get_relative_path with ValueError exception."""
        test_path = "/some/path/file.txt"
        result = path_manager.get_relative_path(test_path)
        assert result == test_path

    def test_get_absolute_path(self, path_manager, tmp_path):
        """Test converting relative path to absolute path."""
        relative_path = "articles/metadata/test.json"
        absolute_path = path_manager.get_absolute_path(relative_path)
        expected = os.path.join(str(tmp_path), "articles", "metadata", "test.json")
        assert absolute_path == expected

    def test_get_absolute_path_already_absolute(self, path_manager):
        """Test get_absolute_path with already absolute path."""
        absolute_path = "/already/absolute/path.txt"
        result = path_manager.get_absolute_path(absolute_path)
        assert result == absolute_path

    def test_validate_path_valid(self, path_manager, tmp_path):
        """Test validating path within data directory."""
        valid_path = os.path.join(str(tmp_path), "articles", "test.json")
        assert path_manager.validate_path(valid_path) is True

    def test_validate_path_invalid(self, path_manager):
        """Test validating path outside data directory."""
        invalid_path = "/completely/different/path/file.txt"
        assert path_manager.validate_path(invalid_path) is False

    @patch("os.path.abspath", side_effect=OSError("Path error"))
    def test_validate_path_os_error(self, mock_abspath, path_manager):
        """Test validate_path with OS error."""
        result = path_manager.validate_path("/some/path")
        assert result is False

    def test_get_all_content_paths(self, path_manager, tmp_path):
        """Test getting all existing content paths."""
        # Create metadata directory and files
        metadata_dir = os.path.join(str(tmp_path), "articles", "metadata")
        os.makedirs(metadata_dir, exist_ok=True)

        # Create test metadata files
        for uid in ["uid1", "uid2", "uid3"]:
            metadata_file = os.path.join(metadata_dir, f"{uid}.json")
            with open(metadata_file, "w") as f:
                f.write('{"test": "data"}')

        # Also create a non-json file that should be ignored
        non_json_file = os.path.join(metadata_dir, "readme.txt")
        with open(non_json_file, "w") as f:
            f.write("readme")

        path_sets = path_manager.get_all_content_paths(ContentType.ARTICLE)
        assert len(path_sets) == 3

        uids = [ps.uid for ps in path_sets]
        assert "uid1" in uids
        assert "uid2" in uids
        assert "uid3" in uids

    def test_get_all_content_paths_no_metadata_dir(self, path_manager):
        """Test getting all content paths when metadata directory doesn't exist."""
        path_sets = path_manager.get_all_content_paths(ContentType.ARTICLE)
        assert path_sets == []

    def test_migrate_paths(self, path_manager, tmp_path):
        """Test migrating content from old to new directory."""
        # Create old directory with content
        old_dir = os.path.join(str(tmp_path), "old_articles")
        os.makedirs(old_dir, exist_ok=True)

        # Create subdirectories and files
        metadata_dir = os.path.join(old_dir, "metadata")
        os.makedirs(metadata_dir, exist_ok=True)

        test_file = os.path.join(metadata_dir, "test.json")
        with open(test_file, "w") as f:
            f.write('{"test": "data"}')

        # Also create a standalone file
        standalone_file = os.path.join(old_dir, "ingest.log")
        with open(standalone_file, "w") as f:
            f.write("log data")

        # Migrate to new directory
        new_dir = os.path.join(str(tmp_path), "new_articles")
        result = path_manager.migrate_paths(old_dir, new_dir, ContentType.ARTICLE)
        assert result is True

        # Check that content was copied
        assert os.path.exists(os.path.join(new_dir, "metadata", "test.json"))
        assert os.path.exists(os.path.join(new_dir, "ingest.log"))

        # Check that type directory was updated
        assert path_manager.type_directories[ContentType.ARTICLE] == new_dir

    def test_migrate_paths_nonexistent_old_dir(self, path_manager, tmp_path):
        """Test migrate_paths when old directory doesn't exist."""
        old_dir = os.path.join(str(tmp_path), "nonexistent")
        new_dir = os.path.join(str(tmp_path), "new")

        result = path_manager.migrate_paths(old_dir, new_dir, ContentType.ARTICLE)
        assert result is True  # Should succeed when source doesn't exist

    @patch("shutil.copytree", side_effect=OSError("Permission denied"))
    def test_migrate_paths_os_error(self, mock_copytree, path_manager, tmp_path):
        """Test migrate_paths with OS error."""
        old_dir = os.path.join(str(tmp_path), "old")
        os.makedirs(old_dir, exist_ok=True)

        # Create a subdirectory to trigger copytree
        sub_dir = os.path.join(old_dir, "metadata")
        os.makedirs(sub_dir, exist_ok=True)

        new_dir = os.path.join(str(tmp_path), "new")
        result = path_manager.migrate_paths(old_dir, new_dir, ContentType.ARTICLE)
        assert result is False

    def test_get_backup_path(self, path_manager, tmp_path):
        """Test getting backup path with auto-generated timestamp."""
        backup_path = path_manager.get_backup_path(ContentType.ARTICLE, "test_uid")
        expected_base = os.path.join(str(tmp_path), "articles", "backups")
        assert backup_path.startswith(expected_base)
        assert os.path.exists(backup_path)  # Directory should be created

    def test_get_backup_path_with_timestamp(self, path_manager, tmp_path):
        """Test getting backup path with custom timestamp."""
        timestamp = "20231225_180000"
        backup_path = path_manager.get_backup_path(
            ContentType.ARTICLE, "test_uid", timestamp
        )
        expected = os.path.join(str(tmp_path), "articles", "backups", timestamp)
        assert backup_path == expected

    def test_create_backup(self, path_manager, tmp_path):
        """Test creating backup of content item files."""
        # Create content files
        path_set = path_manager.get_path_set(ContentType.ARTICLE, "test_uid")
        path_set.ensure_directories()

        # Create test files
        metadata_path = path_set.get_path(PathType.METADATA)
        markdown_path = path_set.get_path(PathType.MARKDOWN)

        with open(metadata_path, "w") as f:
            f.write('{"test": "metadata"}')
        with open(markdown_path, "w") as f:
            f.write("# Test Markdown")

        # Create backup
        backup_dir = path_manager.create_backup(ContentType.ARTICLE, "test_uid")
        assert backup_dir is not None
        assert os.path.exists(backup_dir)

        # Check that files were backed up
        assert os.path.exists(os.path.join(backup_dir, "test_uid.json"))
        assert os.path.exists(os.path.join(backup_dir, "test_uid.md"))

    @patch("shutil.copy2", side_effect=OSError("Permission denied"))
    def test_create_backup_os_error(self, mock_copy, path_manager, tmp_path):
        """Test create_backup with OS error."""
        # Create a content file
        path_set = path_manager.get_path_set(ContentType.ARTICLE, "test_uid")
        path_set.ensure_directories()

        metadata_path = path_set.get_path(PathType.METADATA)
        with open(metadata_path, "w") as f:
            f.write('{"test": "data"}')

        result = path_manager.create_backup(ContentType.ARTICLE, "test_uid")
        assert result is None


class TestPathSet:
    """Test PathSet class methods."""

    def test_path_set_creation(self):
        """Test PathSet creation and basic functionality."""
        paths = {
            PathType.METADATA: "/path/to/metadata.json",
            PathType.MARKDOWN: "/path/to/content.md",
        }
        path_set = PathSet(
            uid="test_uid",
            content_type=ContentType.ARTICLE,
            base_dir="/base",
            paths=paths,
        )

        assert path_set.uid == "test_uid"
        assert path_set.content_type == ContentType.ARTICLE
        assert path_set.base_dir == "/base"
        assert path_set.get_path(PathType.METADATA) == "/path/to/metadata.json"
        assert path_set.get_path(PathType.MARKDOWN) == "/path/to/content.md"
        assert path_set.get_path(PathType.HTML) is None

    def test_ensure_directories_success(self, tmp_path):
        """Test ensuring directories exist successfully."""
        paths = {
            PathType.METADATA: os.path.join(str(tmp_path), "meta", "test.json"),
            PathType.MARKDOWN: os.path.join(str(tmp_path), "md", "test.md"),
        }
        path_set = PathSet(
            uid="test_uid",
            content_type=ContentType.ARTICLE,
            base_dir=str(tmp_path),
            paths=paths,
        )

        result = path_set.ensure_directories()
        assert result is True
        assert os.path.exists(os.path.join(str(tmp_path), "meta"))
        assert os.path.exists(os.path.join(str(tmp_path), "md"))

    @patch("os.makedirs", side_effect=OSError("Permission denied"))
    def test_ensure_directories_os_error(self, mock_makedirs):
        """Test ensure_directories with OS error."""
        paths = {PathType.METADATA: "/invalid/path/test.json"}
        path_set = PathSet(
            uid="test_uid",
            content_type=ContentType.ARTICLE,
            base_dir="/base",
            paths=paths,
        )

        result = path_set.ensure_directories()
        assert result is False

    def test_base_path_property(self, tmp_path):
        """Test PathSet base_path property."""
        paths = {PathType.METADATA: "/path/to/metadata.json"}
        path_set = PathSet(
            uid="test_uid",
            content_type=ContentType.ARTICLE,
            base_dir=str(tmp_path),
            paths=paths,
        )

        expected_base_path = os.path.join(str(tmp_path), "test_uid")
        assert path_set.base_path == expected_base_path


class TestConvenienceFunctions:
    """Test module-level convenience functions."""

    def test_create_path_manager(self, config):
        """Test path manager factory function."""
        manager = create_path_manager(config)
        assert isinstance(manager, PathManager)
        assert manager.data_directory == config["data_directory"]

    def test_get_content_paths(self, config, tmp_path):
        """Test convenience function for getting content paths."""
        path_set = get_content_paths(ContentType.ARTICLE, "test_uid", config)
        assert isinstance(path_set, PathSet)
        assert path_set.uid == "test_uid"
        assert path_set.content_type == ContentType.ARTICLE

    def test_ensure_content_directories(self, config):
        """Test convenience function for ensuring directories."""
        result = ensure_content_directories(ContentType.ARTICLE, config)
        assert result is True

    def test_get_log_path_convenience(self, config, tmp_path):
        """Test convenience function for getting log path."""
        log_path = get_log_path(ContentType.ARTICLE, config)
        expected = os.path.join(str(tmp_path), "articles", "ingest.log")
        assert log_path == expected


class TestPathTypeEnum:
    """Test PathType enum values."""

    def test_path_type_values(self):
        """Test that all PathType enum values are correct."""
        assert PathType.METADATA.value == "metadata"
        assert PathType.MARKDOWN.value == "markdown"
        assert PathType.HTML.value == "html"
        assert PathType.AUDIO.value == "audio"
        assert PathType.VIDEO.value == "video"
        assert PathType.TRANSCRIPT.value == "transcript"
        assert PathType.LOG.value == "log"
        assert PathType.EVALUATION.value == "evaluation"
        assert PathType.TEMP.value == "temp"
