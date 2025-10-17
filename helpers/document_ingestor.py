"""
Document Ingestor for Atlas - Comprehensive Metadata Capture

CORE PRINCIPLE: NEVER LOSE ANY DATA - PRESERVE EVERYTHING!

This ingestor captures ALL available metadata from documents including:
- File system metadata (size, dates, permissions, etc.)
- Document properties (title, author, creation date, etc.)
- Content structure metadata (page count, language, etc.)
- Processing metadata (extraction method, errors, etc.)
- Raw document and processed content preservation
"""

import os
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional, Tuple
from urllib.parse import urlparse
from urllib.request import urlretrieve
import logging

logger = logging.getLogger(__name__)

import requests

from helpers.base_ingestor import BaseIngestor, IngestorResult
from helpers.document_processor import (
    AtlasDocumentProcessor,
    is_document_processing_available,
)
from helpers.metadata_manager import ContentMetadata, ContentType


class DocumentIngestor(BaseIngestor):
    """Ingestor for processing documents using AtlasDocumentProcessor."""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config, ContentType.DOCUMENT, "document_ingestor")

        # Set attributes after calling super().__init__
        self.content_type = ContentType.DOCUMENT
        self.module_name = "document_ingestor"

        # Re-run post-init with correct content_type
        self._post_init()

        # Initialize document processor
        if not is_document_processing_available():
            raise ImportError(
                "Document processing not available. Install with: pip install 'unstructured[all-docs]'"
            )

        self.document_processor = AtlasDocumentProcessor(config)
        self.temp_dir = config.get("temp_directory", tempfile.gettempdir())

        # Supported sources
        self.supported_schemes = ["http", "https", "file"]

        print(
            f"[{self.module_name}] Initialized with {len(self.document_processor.get_supported_extensions())} supported formats"
        )

    def get_content_type(self) -> ContentType:
        """Return the content type this ingestor handles."""
        return ContentType.DOCUMENT

    def get_module_name(self) -> str:
        """Return the module name for logging."""
        return self.module_name

    def is_supported_source(self, source: str) -> bool:
        """Check if source is supported (URL or file path)."""
        logger.info(f"Checking if source is supported: {source}")
        # Check if it's a URL
        parsed = urlparse(source)
        logger.info(f"Parsed scheme: {parsed.scheme}")
        if parsed.scheme in self.supported_schemes:
            logger.info(f"Source is a supported URL: {source}")
            return True

        # Check if it's a local file path
        logger.info(f"Checking file path: {source}")
        logger.info(f"Absolute path: {os.path.abspath(source)}")
        logger.info(f"Path exists: {os.path.exists(source)}")
        is_file = os.path.isfile(source)
        logger.info(f"Is file: {is_file}")
        if is_file:
            logger.info(f"Source is a file: {source}")
            is_supported = self.document_processor.is_supported_format(source)
            logger.info(f"Is supported format: {is_supported}")
            return is_supported

        logger.warning(f"Source is not a supported URL or file: {source}")
        return False

    def fetch_content(
        self, source: str, metadata: ContentMetadata
    ) -> Tuple[bool, Optional[str]]:
        """
        Fetch document from source (URL or file path).

        Args:
            source: Source URL or file path
            metadata: Content metadata object

        Returns:
            Tuple of (success, file_path_or_error_message)
        """
        try:
            parsed = urlparse(source)

            if parsed.scheme in ["http", "https"]:
                # Download from URL
                return self._fetch_from_url(source, metadata)
            elif parsed.scheme == "file" or os.path.isfile(source):
                # Local file
                return self._fetch_from_file(source, metadata)
            else:
                return False, f"Unsupported source type: {source}"

        except Exception as e:
            error_msg = f"Error fetching document from {source}: {str(e)}"
            print(f"ERROR [{self.module_name}]: {error_msg}")
            return False, error_msg

    def _fetch_from_url(
        self, url: str, metadata: ContentMetadata
    ) -> Tuple[bool, Optional[str]]:
        """Download document from URL to temporary file."""
        try:
            # Get file extension from URL
            parsed = urlparse(url)
            path = Path(parsed.path)
            ext = path.suffix.lower()

            if not ext or not self.document_processor.is_supported_format(
                f"dummy{ext}"
            ):
                # Try to get extension from Content-Type header
                response = requests.head(url, timeout=10)
                content_type = response.headers.get("content-type", "").lower()

                # Map common content types to extensions
                content_type_map = {
                    "application/pdf": ".pdf",
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
                    "application/msword": ".doc",
                    "text/plain": ".txt",
                    "text/html": ".html",
                    "application/vnd.ms-excel": ".xls",
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": ".xlsx",
                }

                ext = content_type_map.get(content_type.split(";")[0], ".bin")

            # Create temporary file
            temp_fd, temp_path = tempfile.mkstemp(suffix=ext, dir=self.temp_dir)
            os.close(temp_fd)

            # Download file
            print(f"[{self.module_name}] Downloading {url} to {temp_path}")
            urlretrieve(url, temp_path)

            # Verify file was downloaded and has content
            if os.path.getsize(temp_path) == 0:
                os.unlink(temp_path)
                return False, f"Downloaded file is empty: {url}"

            # Check if format is supported
            if not self.document_processor.is_supported_format(temp_path):
                os.unlink(temp_path)
                return False, f"Unsupported document format: {ext}"

            return True, temp_path

        except Exception as e:
            error_msg = f"Error downloading document from {url}: {str(e)}"
            print(f"ERROR [{self.module_name}]: {error_msg}")
            return False, error_msg

    def _fetch_from_file(
        self, file_path: str, metadata: ContentMetadata
    ) -> Tuple[bool, Optional[str]]:
        """Process local file."""
        try:
            # Handle file:// URLs
            if file_path.startswith("file://"):
                file_path = urlparse(file_path).path

            # Verify file exists
            if not os.path.isfile(file_path):
                return False, f"File not found: {file_path}"

            # Check if format is supported
            if not self.document_processor.is_supported_format(file_path):
                ext = Path(file_path).suffix.lower()
                return False, f"Unsupported document format: {ext}"

            # Return the file path (no need to copy for local files)
            return True, file_path

        except Exception as e:
            error_msg = f"Error accessing local file {file_path}: {str(e)}"
            print(f"ERROR [{self.module_name}]: {error_msg}")
            return False, error_msg

    def process_content(self, file_path: str, metadata: ContentMetadata) -> bool:
        """
        Process document using AtlasDocumentProcessor with comprehensive metadata capture.
        CORE PRINCIPLE: Never lose any data - capture everything!

        Args:
            file_path: Path to document file
            metadata: Content metadata object

        Returns:
            bool: True if successful, False otherwise
        """
        is_temp_file = file_path.startswith(self.temp_dir)

        try:
            print(f"[{self.module_name}] Processing document: {file_path}")

            # COMPREHENSIVE METADATA EXTRACTION - Never lose any data!
            comprehensive_metadata = self._extract_all_document_metadata(
                file_path, metadata.source
            )

            # Add comprehensive metadata to metadata object
            metadata.type_specific.update(comprehensive_metadata["type_specific"])

            # Save raw file for complete preservation (for small files)
            file_size = os.path.getsize(file_path)
            if (
                file_size < 50 * 1024 * 1024
            ):  # Only preserve files under 50MB as raw data
                try:
                    with open(file_path, "rb") as f:
                        raw_data = f.read()
                    self.save_raw_data(raw_data, metadata, "raw_document")
                except Exception as e:
                    print(f"Could not preserve raw file data: {e}")

            # Process document
            result = self.document_processor.process_document(file_path, metadata.uid)

            if result["processing_status"] != "completed":
                error_msg = result.get("error", "Unknown processing error")
                print(
                    f"ERROR [{self.module_name}]: Document processing failed: {error_msg}"
                )
                return False

            # Update metadata with document processing results
            doc_metadata = result.get("metadata", {})

            # Add document-specific metadata to type_specific
            metadata.type_specific.update(
                {
                    "processing_metadata": {
                        "document_processor_version": "atlas-1.0",
                        "processing_timestamp": result["processing_timestamp"],
                        "document_format": doc_metadata.get(
                            "file_extension", "unknown"
                        ),
                        "file_size": doc_metadata.get("file_size", 0),
                        "word_count": doc_metadata.get("word_count", 0),
                        "estimated_reading_time": doc_metadata.get(
                            "estimated_reading_time", 0
                        ),
                        "element_types": doc_metadata.get("element_types", {}),
                        "has_tables": doc_metadata.get("has_tables", False),
                        "structure_analysis": doc_metadata.get(
                            "structure_analysis", {}
                        ),
                    },
                    "content": result["content"],
                    "summary": None,  # Will be set below
                }
            )

            # Set title
            metadata.title = metadata.title or self._extract_title_from_content(
                result["content"]
            )

            # Generate summary if content is long enough
            content = metadata.type_specific["content"]
            if len(content) > 500:
                try:
                    from process.evaluate import summarize_content

                    metadata.type_specific["summary"] = summarize_content(
                        content[:4000], self.config
                    )  # Limit for summarization
                except Exception as e:
                    print(
                        f"ERROR [{self.module_name}]: Failed to generate summary: {str(e)}"
                    )
                    metadata.type_specific["summary"] = (
                        content[:500] + "..." if len(content) > 500 else content
                    )
            else:
                metadata.type_specific["summary"] = content

            # Save output files info
            if "output_files" in result:
                metadata.type_specific["file_paths"] = {
                    "content": result["output_files"]["content"],
                    "structured": result["output_files"]["structured"],
                    "metadata": result["output_files"]["metadata"],
                }
                # Set content_path for compatibility with check_all_content.py
                metadata.content_path = result["output_files"]["content"]

            print(
                f"[{self.module_name}] Successfully processed document: {metadata.uid}"
            )
            return True

        except Exception as e:
            error_msg = f"Error processing document {file_path}: {str(e)}"
            print(f"ERROR [{self.module_name}]: {error_msg}")
            return False

        finally:
            # Clean up temporary file if it was downloaded
            if is_temp_file and file_path and os.path.exists(file_path):
                try:
                    os.unlink(file_path)
                    print(
                        f"[{self.module_name}] Cleaned up temporary file: {file_path}"
                    )
                except Exception as e:
                    print(
                        f"ERROR [{self.module_name}]: Failed to clean up temp file {file_path}: {str(e)}"
                    )

    def _extract_title_from_content(self, content: str) -> str:
        """Extract a title from document content."""
        if not content:
            return "Untitled Document"

        # Try to find a title from the first few lines
        lines = content.split("\n")
        for line in lines[:5]:  # Check first 5 lines
            line = line.strip()
            if line and len(line) < 200:  # Reasonable title length
                # Skip common non-title patterns
                if not any(
                    skip in line.lower()
                    for skip in ["table of contents", "page", "chapter"]
                ):
                    return line

        # Fallback: use first sentence or first 50 words
        sentences = content.split(".")
        first_sentence = sentences[0].strip() if sentences else ""

        if first_sentence and len(first_sentence) < 200:
            return first_sentence

        # Final fallback: first 50 words
        words = content.split()[:50]
        return " ".join(words) + "..." if len(words) == 50 else " ".join(words)

    def _extract_all_document_metadata(
        self, file_path: str, source_url: str
    ) -> Dict[str, Any]:
        """
        Extract ALL available metadata from document file.
        CORE PRINCIPLE: Never lose any data - capture everything!
        """

        # File system metadata
        try:
            stat_info = os.stat(file_path)
            filesystem_metadata = {
                "file_path": file_path,
                "file_size_bytes": stat_info.st_size,
                "file_size_mb": round(stat_info.st_size / (1024 * 1024), 2),
                "created_time": datetime.fromtimestamp(stat_info.st_ctime).isoformat(),
                "modified_time": datetime.fromtimestamp(stat_info.st_mtime).isoformat(),
                "accessed_time": datetime.fromtimestamp(stat_info.st_atime).isoformat(),
                "file_mode": oct(stat_info.st_mode),
                "file_permissions": oct(stat_info.st_mode)[-3:],
                "inode": stat_info.st_ino,
                "device": stat_info.st_dev,
                "hard_links": stat_info.st_nlink,
            }
        except Exception as e:
            filesystem_metadata = {
                "error": f"Could not extract filesystem metadata: {e}"
            }

        # File path analysis
        path_obj = Path(file_path)
        path_metadata = {
            "filename": path_obj.name,
            "stem": path_obj.stem,
            "suffix": path_obj.suffix,
            "suffixes": path_obj.suffixes,
            "parent_directory": str(path_obj.parent),
            "is_absolute": path_obj.is_absolute(),
            "parts": list(path_obj.parts),
        }

        # Document format detection
        format_metadata = {
            "detected_extension": path_obj.suffix.lower(),
            "is_supported_format": (
                self.document_processor.is_supported_format(file_path)
                if hasattr(self, "document_processor")
                else False
            ),
            "supported_extensions": (
                self.document_processor.get_supported_extensions()
                if hasattr(self, "document_processor")
                else []
            ),
        }

        # Content preview (first few bytes for format identification)
        content_preview = {}
        try:
            with open(file_path, "rb") as f:
                first_bytes = f.read(512)  # First 512 bytes
                content_preview = {
                    "first_512_bytes_hex": first_bytes.hex(),
                    "first_512_bytes_preview": first_bytes[:100].decode(
                        "utf-8", errors="ignore"
                    ),
                    "magic_number": first_bytes[:8].hex(),
                    "detected_encoding": "binary",
                }

                # Try to detect text encoding for text files
                try:
                    f.seek(0)
                    text_sample = f.read(1024).decode("utf-8")
                    content_preview["text_sample"] = text_sample[:200]
                    content_preview["detected_encoding"] = "utf-8"
                except UnicodeDecodeError:
                    try:
                        f.seek(0)
                        text_sample = f.read(1024).decode("latin-1")
                        content_preview["text_sample"] = text_sample[:200]
                        content_preview["detected_encoding"] = "latin-1"
                    except Exception:
                        pass
        except Exception as e:
            content_preview = {"error": f"Could not read file preview: {e}"}

        # Source information
        source_metadata = {
            "original_source": source_url,
            "is_remote_source": source_url.startswith(("http://", "https://")),
            "is_local_file": not source_url.startswith(("http://", "https://")),
            "source_domain": (
                urlparse(source_url).netloc
                if source_url.startswith(("http://", "https://"))
                else None
            ),
        }

        # Processing metadata
        processing_metadata = {
            "extraction_timestamp": datetime.now().isoformat(),
            "extraction_method": "atlas_document_ingestor",
            "processor_version": "atlas_v1.0",
            "available_processors": (
                getattr(self.document_processor, "available_processors", [])
                if hasattr(self, "document_processor")
                else []
            ),
        }

        return {
            "type_specific": {
                "document": {
                    "filesystem": filesystem_metadata,
                    "path_analysis": path_metadata,
                    "format_detection": format_metadata,
                    "content_preview": content_preview,
                    "source_information": source_metadata,
                    "processing": processing_metadata,
                }
            }
        }

    def ingest_content(self, source: str, **kwargs) -> IngestorResult:
        """
        Main ingestion method that orchestrates the entire process.

        Args:
            source: Document source (URL or file path)
            **kwargs: Additional metadata parameters

        Returns:
            IngestorResult: Result of the ingestion operation
        """
        try:
            # Check if source is supported
            if not self.is_supported_source(source):
                error_msg = f"Unsupported document source or format: {source}"
                self.handle_error(error_msg, source)
                return IngestorResult(success=False, error=error_msg)

            # Check if should skip (already processed)
            if self.should_skip(source):
                print(
                    f"[{self.module_name}] Skipping already processed document: {source}"
                )
                return IngestorResult(success=True, metadata=None)

            # Create metadata
            title = kwargs.get("title")
            metadata = self.create_metadata(source, title, **kwargs)

            # Fetch content
            success, file_path_or_error = self.fetch_content(source, metadata)
            if not success:
                self.handle_error(file_path_or_error, source, should_retry=True)
                return IngestorResult(
                    success=False, error=file_path_or_error, should_retry=True
                )

            # Process content
            success = self.process_content(file_path_or_error, metadata)
            if not success:
                error_msg = "Failed to process document content"
                self.handle_error(error_msg, source)
                return IngestorResult(success=False, error=error_msg)

            # Save metadata
            if not self.save_metadata(metadata):
                error_msg = "Failed to save metadata"
                self.handle_error(error_msg, source)
                return IngestorResult(success=False, error=error_msg)

            print(f"[{self.module_name}] Successfully ingested document: {source}")
            return IngestorResult(success=True, metadata=metadata)

        except Exception as e:
            error_msg = f"Unexpected error ingesting document {source}: {str(e)}"
            self.handle_error(error_msg, source, should_retry=True)
            return IngestorResult(success=False, error=error_msg, should_retry=True)

    def batch_ingest_directory(
        self, directory_path: str, recursive: bool = True
    ) -> Dict[str, Any]:
        """
        Batch ingest all supported documents from a directory.

        Args:
            directory_path: Path to directory containing documents
            recursive: Whether to process subdirectories recursively

        Returns:
            Dictionary containing batch processing results
        """
        try:
            print(
                f"[{self.module_name}] Starting batch ingestion of directory: {directory_path}"
            )

            results = {
                "total_found": 0,
                "processed": 0,
                "skipped": 0,
                "failed": 0,
                "errors": [],
            }

            # Find all supported files
            pattern = "**/*" if recursive else "*"
            supported_extensions = self.document_processor.get_supported_extensions()

            files_to_process = []
            for ext in supported_extensions:
                files_to_process.extend(Path(directory_path).glob(f"{pattern}{ext}"))

            results["total_found"] = len(files_to_process)
            print(
                f"[{self.module_name}] Found {results['total_found']} supported files"
            )

            # Process each file
            for file_path in files_to_process:
                try:
                    result = self.ingest_content(str(file_path))

                    if result.success:
                        if result.metadata:  # Actually processed (not skipped)
                            results["processed"] += 1
                        else:  # Skipped (already exists)
                            results["skipped"] += 1
                    else:
                        results["failed"] += 1
                        results["errors"].append(
                            {"file": str(file_path), "error": result.error}
                        )

                except Exception as e:
                    results["failed"] += 1
                    results["errors"].append({"file": str(file_path), "error": str(e)})
                    print(
                        f"ERROR [{self.module_name}]: Error processing {file_path}: {str(e)}"
                    )

            print(
                f"[{self.module_name}] Batch ingestion completed: {results['processed']} processed, "
                f"{results['skipped']} skipped, {results['failed']} failed"
            )

            return results

        except Exception as e:
            error_msg = f"Error during batch directory ingestion: {str(e)}"
            print(f"ERROR [{self.module_name}]: {error_msg}")
            return {
                "total_found": 0,
                "processed": 0,
                "skipped": 0,
                "failed": 1,
                "errors": [{"directory": directory_path, "error": error_msg}],
            }


def create_document_ingestor(config: Dict[str, Any]) -> DocumentIngestor:
    """Create and return a DocumentIngestor instance."""
    return DocumentIngestor(config)
