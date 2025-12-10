"""
Unit tests for AtlasDocumentProcessor module.
"""

import os
import tempfile
from pathlib import Path
from unittest.mock import Mock, mock_open, patch

import pytest

from helpers.document_processor import (AtlasDocumentProcessor,
                                        DocumentMetadata,
                                        DocumentProcessorConfig,
                                        get_document_processor,
                                        is_document_processing_available,
                                        process_document_file)


class TestDocumentProcessorConfig:
    """Test DocumentProcessorConfig class."""

    def test_supported_extensions(self):
        """Test that supported extensions are properly defined."""
        extensions = DocumentProcessorConfig.SUPPORTED_EXTENSIONS

        # Check that common formats are supported
        assert ".pdf" in extensions
        assert ".docx" in extensions
        assert ".txt" in extensions
        assert ".html" in extensions
        assert ".csv" in extensions

        # Check that extensions map to correct types
        assert extensions[".pdf"] == "pdf"
        assert extensions[".docx"] == "docx"
        assert extensions[".txt"] == "text"

    def test_default_settings(self):
        """Test default processing settings."""
        settings = DocumentProcessorConfig.DEFAULT_SETTINGS

        assert "extract_images" in settings
        assert "extract_tables" in settings
        assert "ocr_languages" in settings
        assert "strategy" in settings
        assert "chunking_strategy" in settings

        # Check default values
        assert settings["extract_images"] is False
        assert settings["extract_tables"] is True
        assert settings["strategy"] == "auto"


class TestDocumentMetadata:
    """Test DocumentMetadata class."""

    def test_extract_file_metadata_nonexistent_file(self):
        """Test metadata extraction for non-existent file."""
        metadata = DocumentMetadata.extract_file_metadata("/nonexistent/file.txt")
        assert metadata == {}

    @patch("os.path.exists")
    @patch("os.stat")
    @patch("mimetypes.guess_type")
    def test_extract_file_metadata_success(
        self, mock_guess_type, mock_stat, mock_exists
    ):
        """Test successful metadata extraction."""
        mock_exists.return_value = True
        mock_stat.return_value = Mock(
            st_size=1024, st_ctime=1609459200, st_mtime=1609459300
        )
        mock_guess_type.return_value = ("application/pdf", None)

        with patch(
            "helpers.document_processor.DocumentMetadata._calculate_file_hash",
            return_value="abcd1234",
        ):
            metadata = DocumentMetadata.extract_file_metadata("/test/file.pdf")

        assert metadata["file_size"] == 1024
        assert metadata["file_extension"] == ".pdf"
        assert metadata["file_hash"] == "abcd1234"
        assert "created_at" in metadata
        assert "modified_at" in metadata

    @patch("builtins.open", mock_open(read_data=b"test content"))
    def test_calculate_file_hash(self):
        """Test file hash calculation."""
        hash_result = DocumentMetadata._calculate_file_hash("/test/file.txt")

        assert isinstance(hash_result, str)
        assert len(hash_result) == 16  # First 16 chars of SHA-256

    def test_extract_content_metadata_empty_elements(self):
        """Test content metadata extraction with empty elements."""
        metadata = DocumentMetadata.extract_content_metadata([])

        # Should return empty dict for no elements
        assert metadata == {}

    def test_extract_content_metadata_with_elements(self):
        """Test content metadata extraction with mock elements."""
        # Create mock elements
        mock_element1 = Mock()
        mock_element1.__class__.__name__ = "Title"
        mock_element1.__str__ = Mock(return_value="Test Title")
        mock_element1.metadata = None

        mock_element2 = Mock()
        mock_element2.__class__.__name__ = "NarrativeText"
        mock_element2.__str__ = Mock(
            return_value="This is a test narrative with multiple words."
        )
        mock_element2.metadata = None

        elements = [mock_element1, mock_element2]

        # Mock Table class for isinstance check
        with patch("helpers.document_processor.Table", Mock):
            metadata = DocumentMetadata.extract_content_metadata(elements)

        assert metadata["total_elements"] == 2
        assert metadata["element_types"]["Title"] == 1
        assert metadata["element_types"]["NarrativeText"] == 1
        assert metadata["word_count"] > 0
        assert metadata["estimated_reading_time"] >= 1


@pytest.fixture
def mock_config():
    """Mock configuration for testing."""
    return {
        "document_processing": {"strategy": "fast", "extract_images": True},
        "document_output_path": "/test/output",
        "temp_directory": "/test/temp",
    }


@pytest.fixture
def mock_unstructured_available():
    """Mock unstructured library availability."""
    with patch("helpers.document_processor.UNSTRUCTURED_AVAILABLE", True):
        yield


class TestAtlasDocumentProcessor:
    """Test AtlasDocumentProcessor class."""

    def test_init_without_unstructured(self):
        """Test initialization without unstructured library."""
        with patch("helpers.document_processor.UNSTRUCTURED_AVAILABLE", False):
            with pytest.raises(ImportError, match="Unstructured library not available"):
                AtlasDocumentProcessor()

    @patch("helpers.document_processor.load_config")
    @patch("helpers.document_processor.MetadataManager")
    @patch("helpers.document_processor.PathManager")
    def test_init_success(
        self,
        mock_path_manager,
        mock_metadata_manager,
        mock_load_config,
        mock_unstructured_available,
        mock_config,
    ):
        """Test successful initialization."""
        mock_load_config.return_value = mock_config

        processor = AtlasDocumentProcessor(mock_config)

        assert processor.config == mock_config
        assert processor.processing_settings["strategy"] == "fast"
        assert processor.processing_settings["extract_images"] is True
        assert processor.output_directory == "/test/output"
        assert processor.temp_directory == "/test/temp"

    def test_is_supported_format(self, mock_unstructured_available, mock_config):
        """Test file format support checking."""
        with patch("helpers.document_processor.load_config", return_value=mock_config):
            with patch("helpers.document_processor.MetadataManager"):
                with patch("helpers.document_processor.PathManager"):
                    processor = AtlasDocumentProcessor(mock_config)

        assert processor.is_supported_format("/test/file.pdf") is True
        assert processor.is_supported_format("/test/file.docx") is True
        assert processor.is_supported_format("/test/file.xyz") is False

    def test_get_supported_extensions(self, mock_unstructured_available, mock_config):
        """Test getting supported extensions list."""
        with patch("helpers.document_processor.load_config", return_value=mock_config):
            with patch("helpers.document_processor.MetadataManager"):
                with patch("helpers.document_processor.PathManager"):
                    processor = AtlasDocumentProcessor(mock_config)

        extensions = processor.get_supported_extensions()

        assert isinstance(extensions, list)
        assert ".pdf" in extensions
        assert ".docx" in extensions
        assert ".txt" in extensions

    @patch("os.path.exists")
    def test_process_document_file_not_found(
        self, mock_exists, mock_unstructured_available, mock_config
    ):
        """Test processing non-existent document."""
        mock_exists.return_value = False

        with patch("helpers.document_processor.load_config", return_value=mock_config):
            with patch("helpers.document_processor.MetadataManager"):
                with patch("helpers.document_processor.PathManager"):
                    processor = AtlasDocumentProcessor(mock_config)

        with pytest.raises(FileNotFoundError):
            processor.process_document("/nonexistent/file.pdf")

    @patch("os.path.exists")
    def test_process_document_unsupported_format(
        self, mock_exists, mock_unstructured_available, mock_config
    ):
        """Test processing unsupported document format."""
        mock_exists.return_value = True

        with patch("helpers.document_processor.load_config", return_value=mock_config):
            with patch("helpers.document_processor.MetadataManager"):
                with patch("helpers.document_processor.PathManager"):
                    processor = AtlasDocumentProcessor(mock_config)

        with pytest.raises(ValueError, match="Unsupported document format"):
            processor.process_document("/test/file.xyz")

    @patch("os.path.exists")
    @patch("helpers.document_processor.DocumentMetadata.extract_file_metadata")
    @patch("helpers.document_processor.DocumentMetadata.extract_content_metadata")
    def test_process_document_success(
        self,
        mock_content_metadata,
        mock_file_metadata,
        mock_exists,
        mock_unstructured_available,
        mock_config,
    ):
        """Test successful document processing."""
        mock_exists.return_value = True
        mock_file_metadata.return_value = {"file_size": 1024, "file_extension": ".pdf"}
        mock_content_metadata.return_value = {"word_count": 100}

        mock_elements = [Mock()]
        mock_elements[0].__str__ = Mock(return_value="Test content")

        with patch("helpers.document_processor.load_config", return_value=mock_config):
            with patch("helpers.document_processor.MetadataManager"):
                with patch("helpers.document_processor.PathManager"):
                    processor = AtlasDocumentProcessor(mock_config)

        with patch.object(processor, "_partition_document", return_value=mock_elements):
            with patch.object(
                processor, "_elements_to_text", return_value="Test content"
            ):
                with patch.object(
                    processor, "_elements_to_structured", return_value=[]
                ):
                    with patch.object(processor, "_save_processed_document"):
                        with patch.object(
                            processor, "_generate_document_uid", return_value="test123"
                        ):
                            result = processor.process_document("/test/file.pdf")

        assert result["processing_status"] == "completed"
        assert result["content"] == "Test content"
        assert "uid" in result
        assert result["source_file"] == "/test/file.pdf"

    def test_generate_document_uid(self, mock_unstructured_available, mock_config):
        """Test UID generation for documents."""
        with patch("helpers.document_processor.load_config", return_value=mock_config):
            with patch("helpers.document_processor.MetadataManager"):
                with patch("helpers.document_processor.PathManager"):
                    processor = AtlasDocumentProcessor(mock_config)

        with patch("os.path.exists", return_value=True):
            with patch("os.path.getmtime", return_value=1609459200.0):
                uid = processor._generate_document_uid("/test/file.pdf")

        assert isinstance(uid, str)
        assert len(uid) == 16

    def test_elements_to_text(self, mock_unstructured_available, mock_config):
        """Test converting elements to text."""
        mock_element1 = Mock()
        mock_element1.text = "First element text"

        mock_element2 = Mock()
        mock_element2.text = "Second element text"

        elements = [mock_element1, mock_element2]

        with patch("helpers.document_processor.load_config", return_value=mock_config):
            with patch("helpers.document_processor.MetadataManager"):
                with patch("helpers.document_processor.PathManager"):
                    processor = AtlasDocumentProcessor(mock_config)

        result = processor._elements_to_text(elements)

        assert "First element text" in result
        assert "Second element text" in result
        assert "\n\n" in result  # Elements should be separated by double newlines

    def test_elements_to_structured(self, mock_unstructured_available, mock_config):
        """Test converting elements to structured format."""
        mock_element = Mock()
        mock_element.__class__.__name__ = "Title"
        mock_element.__str__ = Mock(return_value="Test Title")
        mock_element.metadata = None

        elements = [mock_element]

        with patch("helpers.document_processor.load_config", return_value=mock_config):
            with patch("helpers.document_processor.MetadataManager"):
                with patch("helpers.document_processor.PathManager"):
                    processor = AtlasDocumentProcessor(mock_config)

        result = processor._elements_to_structured(elements)

        assert len(result) == 1
        assert result[0]["id"] == 0
        assert result[0]["type"] == "Title"
        assert result[0]["text"] == "Test Title"

    @patch("os.makedirs")
    @patch("builtins.open", new_callable=mock_open)
    @patch("json.dump")
    def test_save_processed_document(
        self,
        mock_json_dump,
        mock_file_open,
        mock_makedirs,
        mock_unstructured_available,
        mock_config,
    ):
        """Test saving processed document."""
        result = {
            "uid": "test123",
            "source_file": "/test/file.pdf",
            "content": "Test content",
            "structured_content": [],
            "processing_timestamp": "2021-01-01T00:00:00",
            "processing_status": "completed",
            "metadata": {},
        }

        with patch("helpers.document_processor.load_config", return_value=mock_config):
            with patch("helpers.document_processor.MetadataManager"):
                with patch("helpers.document_processor.PathManager"):
                    processor = AtlasDocumentProcessor(mock_config)

        processor._save_processed_document(result)

        # Verify directories are created
        mock_makedirs.assert_called_with("/test/output", exist_ok=True)

        # Verify files are written (content, structured, metadata)
        assert mock_file_open.call_count == 3
        assert mock_json_dump.call_count == 2

    @patch("os.path.exists")
    def test_process_directory_not_found(
        self, mock_exists, mock_unstructured_available, mock_config
    ):
        """Test processing non-existent directory."""
        mock_exists.return_value = False

        with patch("helpers.document_processor.load_config", return_value=mock_config):
            with patch("helpers.document_processor.MetadataManager"):
                with patch("helpers.document_processor.PathManager"):
                    processor = AtlasDocumentProcessor(mock_config)

        with pytest.raises(FileNotFoundError):
            processor.process_directory("/nonexistent/dir")

    @patch("os.path.exists")
    def test_process_directory_success(
        self, mock_exists, mock_unstructured_available, mock_config
    ):
        """Test successful directory processing."""
        mock_exists.return_value = True

        # Mock Path.glob to return test files
        mock_files = [Path("/test/file1.pdf"), Path("/test/file2.docx")]

        with patch("helpers.document_processor.load_config", return_value=mock_config):
            with patch("helpers.document_processor.MetadataManager"):
                with patch("helpers.document_processor.PathManager"):
                    processor = AtlasDocumentProcessor(mock_config)

        with patch.object(
            processor, "get_supported_extensions", return_value=[".pdf", ".docx"]
        ):
            with patch("pathlib.Path.glob") as mock_glob:
                # Mock glob to return different results for each extension
                mock_glob.side_effect = lambda pattern: (
                    mock_files if ".pdf" in pattern else []
                )

                with patch.object(processor, "process_document") as mock_process:
                    mock_process.return_value = {
                        "processing_status": "completed",
                        "uid": "test123",
                        "metadata": {"word_count": 100},
                    }

                    result = processor.process_directory("/test/dir")

        assert result["processed_count"] == 2
        assert result["error_count"] == 0
        assert len(result["files_processed"]) == 2

    @patch("os.path.exists")
    @patch("pathlib.Path.glob")
    @patch("json.load")
    @patch("builtins.open", new_callable=mock_open)
    def test_get_processing_stats(
        self,
        mock_file_open,
        mock_json_load,
        mock_glob,
        mock_exists,
        mock_unstructured_available,
        mock_config,
    ):
        """Test getting processing statistics."""
        mock_exists.return_value = True
        mock_glob.return_value = [Path("/test/output/test1_metadata.json")]
        mock_json_load.return_value = {"file_extension": ".pdf", "file_size": 1024}

        with patch("helpers.document_processor.load_config", return_value=mock_config):
            with patch("helpers.document_processor.MetadataManager"):
                with patch("helpers.document_processor.PathManager"):
                    processor = AtlasDocumentProcessor(mock_config)

        stats = processor.get_processing_stats()

        assert "supported_formats" in stats
        assert "processed_documents" in stats
        assert "format_distribution" in stats
        assert "total_processed_size" in stats
        assert stats["processed_documents"] == 1


class TestGlobalFunctions:
    """Test global functions."""

    def test_is_document_processing_available_false(self):
        """Test availability check when unstructured is not available."""
        with patch("helpers.document_processor.UNSTRUCTURED_AVAILABLE", False):
            assert is_document_processing_available() is False

    def test_is_document_processing_available_true(self):
        """Test availability check when unstructured is available."""
        with patch("helpers.document_processor.UNSTRUCTURED_AVAILABLE", True):
            assert is_document_processing_available() is True

    def test_get_document_processor_not_available(self):
        """Test getting processor when unstructured is not available."""
        with patch("helpers.document_processor.UNSTRUCTURED_AVAILABLE", False):
            with pytest.raises(ImportError):
                get_document_processor()

    @patch("helpers.document_processor.AtlasDocumentProcessor")
    def test_get_document_processor_success(
        self, mock_processor_class, mock_unstructured_available
    ):
        """Test getting processor successfully."""
        mock_processor = Mock()
        mock_processor_class.return_value = mock_processor

        processor = get_document_processor()

        assert processor is mock_processor
        mock_processor_class.assert_called_once()

    @patch("helpers.document_processor.get_document_processor")
    def test_process_document_file_success(
        self, mock_get_processor, mock_unstructured_available
    ):
        """Test convenience function for processing document."""
        mock_processor = Mock()
        mock_processor.process_document.return_value = {
            "processing_status": "completed"
        }
        mock_get_processor.return_value = mock_processor

        result = process_document_file("/test/file.pdf")

        assert result["processing_status"] == "completed"
        mock_processor.process_document.assert_called_once_with("/test/file.pdf")

    @patch("helpers.document_processor.get_document_processor")
    def test_process_document_file_error(
        self, mock_get_processor, mock_unstructured_available
    ):
        """Test convenience function error handling."""
        mock_get_processor.side_effect = Exception("Test error")

        result = process_document_file("/test/file.pdf")

        assert result["processing_status"] == "error"
        assert result["error"] == "Test error"
        assert result["source_file"] == "/test/file.pdf"


class TestTableExtraction:
    """Test table extraction functionality."""

    def test_extract_table_data_simple(self, mock_unstructured_available, mock_config):
        """Test simple table data extraction."""
        # Mock table element
        mock_table = Mock()
        mock_table.__str__ = Mock(return_value="Header1\tHeader2\nValue1\tValue2")

        with patch("helpers.document_processor.load_config", return_value=mock_config):
            with patch("helpers.document_processor.MetadataManager"):
                with patch("helpers.document_processor.PathManager"):
                    processor = AtlasDocumentProcessor(mock_config)

        result = processor._extract_table_data(mock_table)

        assert "rows" in result
        assert "columns" in result
        assert "has_header" in result
        assert len(result["rows"]) == 2
        assert result["columns"] == 2

    def test_extract_table_data_error(self, mock_unstructured_available, mock_config):
        """Test table extraction error handling."""
        # Mock table element that raises error
        mock_table = Mock()
        mock_table.__str__ = Mock(side_effect=Exception("Table error"))

        with patch("helpers.document_processor.load_config", return_value=mock_config):
            with patch("helpers.document_processor.MetadataManager"):
                with patch("helpers.document_processor.PathManager"):
                    processor = AtlasDocumentProcessor(mock_config)

        result = processor._extract_table_data(mock_table)

        # Should return empty structure on error
        assert result["rows"] == []
        assert result["columns"] == 0
        assert result["has_header"] is False


@pytest.mark.integration
class TestDocumentProcessorIntegration:
    """Integration tests for document processor."""

    def test_process_text_document_integration(self, mock_unstructured_available):
        """Integration test for processing text document."""
        # Create temporary text file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write(
                "This is a test document.\nIt has multiple lines.\nAnd some content."
            )
            temp_file = f.name

        try:
            # Mock the unstructured partition function
            mock_elements = [Mock()]
            mock_elements[0].text = (
                "This is a test document.\nIt has multiple lines.\nAnd some content."
            )
            mock_elements[0].__class__.__name__ = "NarrativeText"
            mock_elements[0].__str__ = Mock(return_value=mock_elements[0].text)
            mock_elements[0].metadata = None

            with patch(
                "helpers.document_processor.partition", return_value=mock_elements
            ):
                with patch("helpers.document_processor.load_config", return_value={}):
                    with patch("helpers.document_processor.MetadataManager"):
                        with patch("helpers.document_processor.PathManager"):
                            with tempfile.TemporaryDirectory() as temp_dir:
                                config = {"document_output_path": temp_dir}
                                processor = AtlasDocumentProcessor(config)

                                result = processor.process_document(temp_file)

            assert result["processing_status"] == "completed"
            assert len(result["content"]) > 0
            assert result["metadata"]["word_count"] > 0

        finally:
            # Clean up temp file
            os.unlink(temp_file)
