"""
Document Processing Module

This module provides multi-format document processing capabilities using the
Unstructured library to support PDF, Word, and 20+ document formats with
enhanced metadata extraction.
"""

import hashlib
import logging
import mimetypes
import os
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, TypedDict

try:
    from unstructured.documents.elements import (CompositeElement, Element,
                                                 Table)
    from unstructured.partition.auto import partition
    from unstructured.staging.base import elements_to_json

    UNSTRUCTURED_AVAILABLE = True
except ImportError:
    class Element:
        pass
    class CompositeElement(Element):
        pass
    class Table(CompositeElement):
        pass
    def partition(*args, **kwargs) -> List[Element]:
        return []
    def elements_to_json(*args, **kwargs) -> str:
        return ""
    UNSTRUCTURED_AVAILABLE = False

from helpers.config import load_config
from helpers.metadata_manager import MetadataManager
from helpers.path_manager import PathManager

logger = logging.getLogger(__name__)


class ProcessResult(TypedDict):
    uid: str
    source_file: str
    processing_status: str
    processing_timestamp: str
    content: str
    structured_content: List[Dict[str, Any]]
    metadata: Dict[str, Any]
    error: Optional[str]


class DocumentProcessorConfig:
    """Configuration for document processing settings."""

    # Supported file extensions and their types
    SUPPORTED_EXTENSIONS = {
        # Text documents
        ".txt": "text",
        ".md": "text",
        ".rst": "text",
        # PDF documents
        ".pdf": "pdf",
        # Microsoft Office
        ".doc": "docx",
        ".docx": "docx",
        ".ppt": "pptx",
        ".pptx": "pptx",
        ".xls": "xlsx",
        ".xlsx": "xlsx",
        # LibreOffice/OpenDocument
        ".odt": "odt",
        ".ods": "ods",
        ".odp": "odp",
        # Rich Text Format
        ".rtf": "rtf",
        # CSV and TSV
        ".csv": "csv",
        ".tsv": "tsv",
        # Email formats
        ".eml": "email",
        ".msg": "msg",
        # HTML and XML
        ".html": "html",
        ".htm": "html",
        ".xml": "xml",
        # Image formats (with OCR)
        ".png": "image",
        ".jpg": "image",
        ".jpeg": "image",
        ".tiff": "image",
        ".bmp": "image",
        # Archive formats
        ".zip": "zip",
        ".tar": "tar",
        ".gz": "tar",
    }

    # Default processing parameters
    DEFAULT_SETTINGS = {
        "extract_images": False,
        "extract_tables": True,
        "ocr_languages": ["eng"],
        "strategy": "auto",  # auto, fast, ocr_only, hi_res
        "chunking_strategy": "by_title",
        "max_characters": 1500,
        "new_after_n_chars": 1000,
        "overlap": 200,
    }


class DocumentMetadata:
    """Enhanced metadata extraction for documents."""

    @staticmethod
    def extract_file_metadata(file_path: str) -> Dict[str, Any]:
        """Extract basic file system metadata."""
        if not os.path.exists(file_path):
            return {}

        stat = os.stat(file_path)
        file_size = stat.st_size

        return {
            "file_size": file_size,
            "file_extension": Path(file_path).suffix.lower(),
            "mime_type": mimetypes.guess_type(file_path)[0],
            "created_at": datetime.fromtimestamp(stat.st_ctime).isoformat(),
            "modified_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            "file_hash": DocumentMetadata._calculate_file_hash(file_path), # type: ignore
        }

    @staticmethod
    def _calculate_file_hash(file_path: str) -> str:
        """Calculate SHA-256 hash of file."""
        hash_sha256 = hashlib.sha256()
        try:
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_sha256.update(chunk)
            return hash_sha256.hexdigest()[:16]  # First 16 chars for brevity
        except Exception:
            return ""

    @staticmethod
    def extract_content_metadata(elements: List[Element]) -> Dict[str, Any]:
        """Extract metadata from Unstructured elements."""
        if not elements:
            return {}

        metadata = {
            "total_elements": len(elements),
            "element_types": {},
            "has_tables": False,
            "has_images": False,
            "estimated_reading_time": 0,
            "language": "unknown",
            "structure_analysis": {},
        }

        # Count element types
        for element in elements:
            element_type = type(element).__name__
            metadata["element_types"][element_type] = (
                metadata["element_types"].get(element_type, 0) + 1
            )

            # Check for special content
            if isinstance(element, Table):
                metadata["has_tables"] = True

            # Extract language if available
            if hasattr(element, "metadata") and element.metadata: # type: ignore
                elem_meta = element.metadata # type: ignore
                if hasattr(elem_meta, "languages") and elem_meta.languages: # type: ignore
                    metadata["language"] = elem_meta.languages[0] # type: ignore

        # Estimate reading time (average 200 words per minute)
        total_text = " ".join([str(el) for el in elements])
        word_count = len(total_text.split())
        metadata["word_count"] = word_count
        metadata["estimated_reading_time"] = max(1, word_count // 200)

        # Structure analysis
        metadata["structure_analysis"] = {
            "titles": metadata["element_types"].get("Title", 0),
            "narrative_texts": metadata["element_types"].get("NarrativeText", 0),
            "list_items": metadata["element_types"].get("ListItem", 0),
            "tables": metadata["element_types"].get("Table", 0),
        }

        return metadata


class AtlasDocumentProcessor:
    """Multi-format document processor for Atlas."""

    def __init__(self, config: Optional[Dict] = None):
        """Initialize document processor."""
        if not UNSTRUCTURED_AVAILABLE:
            raise ImportError(
                "Unstructured library not available. Install with: pip install 'unstructured[all-docs]'"
            )

        self.config = config or load_config()
        self.metadata_manager = MetadataManager()
        self.path_manager = PathManager(self.config)

        # Processing settings
        self.processing_settings = DocumentProcessorConfig.DEFAULT_SETTINGS.copy()
        if "document_processing" in self.config:
            self.processing_settings.update(self.config["document_processing"])

        # Output settings
        self.output_directory = self.config.get(
            "document_output_path", "output/documents"
        )
        self.temp_directory = self.config.get("temp_directory", tempfile.gettempdir())

        logger.info("Document processor initialized")

    def is_supported_format(self, file_path: str) -> bool:
        """Check if file format is supported."""
        ext = Path(file_path).suffix.lower()
        return ext in DocumentProcessorConfig.SUPPORTED_EXTENSIONS

    def get_supported_extensions(self) -> List[str]:
        """Get list of supported file extensions."""
        return list(DocumentProcessorConfig.SUPPORTED_EXTENSIONS.keys())

    def process_document(
        self, file_path: str, uid: Optional[str] = None
    ) -> ProcessResult:
        """Process a document file and extract content with metadata.

        Args:
            file_path: Path to the document file
            uid: Optional unique identifier (auto-generated if not provided)

        Returns:
            Dictionary containing processed content and metadata
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Document file not found: {file_path}")

        if not self.is_supported_format(file_path):
            ext = Path(file_path).suffix.lower()
            raise ValueError(f"Unsupported document format: {ext}")

        # Generate UID if not provided
        if not uid:
            uid = self._generate_document_uid(file_path)

        result: ProcessResult = {
            "uid": uid,
            "source_file": file_path,
            "processing_status": "started",
            "processing_timestamp": datetime.now().isoformat(),
            "content": "",
            "structured_content": [],
            "metadata": {},
            "error": None,
        }

        logger.info(f"Processing document: {file_path} with UID: {uid}")

        try:
            logger.info(f"Processing document: {file_path}")

            # Extract file metadata
            file_metadata = DocumentMetadata.extract_file_metadata(file_path)
            result["metadata"].update(file_metadata) # type: ignore

            # Process with Unstructured
            elements = self._partition_document(file_path)

            # Extract content and metadata
            content_metadata = DocumentMetadata.extract_content_metadata(elements)
            result["metadata"].update(content_metadata) # type: ignore

            # Convert elements to text and structured format
            result["content"] = self._elements_to_text(elements)
            result["structured_content"] = self._elements_to_structured(elements)

            # Save processed content
            self._save_processed_document(result)

            result["processing_status"] = "completed"
            logger.info(f"Successfully processed document: {file_path}")

        except Exception as e:
            result["processing_status"] = "error"
            result["error"] = str(e)
            logger.error(f"Error processing document {file_path}: {e}")

        return result

    def _generate_document_uid(self, file_path: str) -> str:
        """Generate unique identifier for document."""
        # Use file path and modification time for uniqueness
        path_str = os.path.abspath(file_path)
        mtime = str(os.path.getmtime(file_path)) if os.path.exists(file_path) else "0"

        uid_string = f"{path_str}_{mtime}"
        return hashlib.sha1(uid_string.encode("utf-8")).hexdigest()[:16]

    def _partition_document(self, file_path: str) -> List[Element]:
        """Partition document using Unstructured."""
        try:
            # Determine processing strategy based on file type
            ext = Path(file_path).suffix.lower()
            doc_type = DocumentProcessorConfig.SUPPORTED_EXTENSIONS.get(ext, "auto")

            partition_kwargs = {
                "filename": file_path,
                "strategy": self.processing_settings.get("strategy", "auto"),
                "include_page_breaks": True,
            }

            # Add format-specific parameters
            if doc_type in ["pdf", "image"]:
                partition_kwargs.update(
                    {
                        "extract_images_in_pdf": self.processing_settings.get(
                            "extract_images", False
                        ),
                        "infer_table_structure": self.processing_settings.get(
                            "extract_tables", True
                        ),
                    }
                )

            if doc_type == "image":
                partition_kwargs["ocr_languages"] = self.processing_settings.get(
                    "ocr_languages", ["eng"]
                )

            # Partition the document
            logger.info(f"Partitioning with kwargs: {partition_kwargs}")
            elements = partition(**partition_kwargs) # type: ignore

            return elements

        except Exception as e:
            logger.error(f"Error partitioning document {file_path}: {e}")
            raise

    def _elements_to_text(self, elements: List[Element]) -> str:
        """Convert elements to clean text."""
        text_parts = []

        for element in elements:
            if hasattr(element, "text"):
                text = element.text.strip()
                if text:
                    text_parts.append(text)

        return "\n\n".join(text_parts)

    def _elements_to_structured(self, elements: List[Element]) -> List[Dict]:
        """Convert elements to structured format."""
        structured = []

        for i, element in enumerate(elements):
            elem_dict = {
                "id": i,
                "type": type(element).__name__,
                "text": str(element).strip(),
            }

            # Add metadata if available
            if hasattr(element, "metadata") and element.metadata:
                elem_metadata = {}

                # Common metadata fields
                for attr in ["page_number", "coordinates", "parent_id", "category"]:
                    if hasattr(element.metadata, attr):
                        value = getattr(element.metadata, attr)
                        if value is not None:
                            elem_metadata[attr] = value

                if elem_metadata:
                    elem_dict["metadata"] = elem_metadata

            # Special handling for tables
            if isinstance(element, Table):
                elem_dict["table_data"] = self._extract_table_data(element)

            structured.append(elem_dict)

        return structured

    def _extract_table_data(self, table_element: Table) -> Dict:
        """Extract structured data from table element."""
        table_data = {"rows": [], "columns": 0, "has_header": False}

        try:
            # Try to extract table structure if available
            table_text = str(table_element)

            # Simple parsing - split by common delimiters
            lines = table_text.split("\n")
            rows = []

            for line in lines:
                # Try different delimiters
                for delimiter in ["\t", "|", ","]:
                    if delimiter in line:
                        cells = [cell.strip() for cell in line.split(delimiter)]
                        if len(cells) > 1:
                            rows.append(cells)
                            break
                else:
                    # If no delimiter found, treat as single cell
                    if line.strip():
                        rows.append([line.strip()])

            if rows:
                table_data["rows"] = rows
                table_data["columns"] = max(len(row) for row in rows)
                # Assume first row is header if it's different from others
                if len(rows) > 1:
                    first_row_len = len(rows[0])
                    table_data["has_header"] = all(
                        len(row) == first_row_len for row in rows[1:]
                    )

        except Exception as e:
            logger.warning(f"Error extracting table data: {e}")

        return table_data

    def _save_processed_document(self, result: Dict[str, Any]):
        """Save processed document content and metadata."""
        uid = result["uid"]

        try:
            # Ensure output directory exists
            os.makedirs(self.output_directory, exist_ok=True)

            # Save main content as markdown
            content_path = os.path.join(self.output_directory, f"{uid}.md")
            with open(content_path, "w", encoding="utf-8") as f:
                f.write(f"# Document: {Path(result['source_file']).name}\n\n")
                f.write(result["content"])

            # Save structured content as JSON
            structured_path = os.path.join(
                self.output_directory, f"{uid}_structured.json"
            )
            with open(structured_path, "w", encoding="utf-8") as f:
                import json

                json.dump(
                    {
                        "uid": uid,
                        "source_file": result["source_file"],
                        "structured_content": result["structured_content"],
                        "processing_timestamp": result["processing_timestamp"],
                    },
                    f,
                    indent=2,
                    ensure_ascii=False,
                )

            # Save metadata
            metadata_path = os.path.join(self.output_directory, f"{uid}_metadata.json")
            with open(metadata_path, "w", encoding="utf-8") as f:
                import json

                json.dump(
                    {
                        "uid": uid,
                        "source_file": result["source_file"],
                        "content_type": "document",
                        "processing_status": result["processing_status"],
                        "processing_timestamp": result["processing_timestamp"],
                        **result["metadata"],
                    },
                    f,
                    indent=2,
                    ensure_ascii=False,
                )

            # Update result with file paths
            result["output_files"] = {
                "content": content_path,
                "structured": structured_path,
                "metadata": metadata_path,
            }

            logger.info(f"Saved processed document files for UID: {uid}")

        except Exception as e:
            logger.error(f"Error saving processed document {uid}: {e}")
            raise

    def process_directory(
        self, directory_path: str, recursive: bool = True
    ) -> Dict[str, Any]:
        """Process all supported documents in a directory.

        Args:
            directory_path: Path to directory containing documents
            recursive: Whether to process subdirectories recursively

        Returns:
            Processing results summary
        """
        if not os.path.exists(directory_path):
            raise FileNotFoundError(f"Directory not found: {directory_path}")

        results = {
            "processed_count": 0,
            "error_count": 0,
            "skipped_count": 0,
            "files_processed": [],
            "errors": [],
            "processing_time": 0,
        }

        start_time = datetime.now()

        try:
            # Find all supported files
            pattern = "**/*" if recursive else "*"
            files_to_process: List[Path] = []

            for ext in self.get_supported_extensions():
                files_to_process.extend(Path(directory_path).glob(f"{pattern}{ext}"))

            logger.info(f"Found {len(files_to_process)} supported files to process")

            # Process each file
            for file_path in files_to_process:
                try:
                    result = self.process_document(str(file_path))

                    if result["processing_status"] == "completed":
                        results["processed_count"] += 1 # type: ignore
                        results["files_processed"].append( # type: ignore
                            {
                                "file": str(file_path),
                                "uid": result["uid"],
                                "word_count": result["metadata"].get("word_count", 0),
                            }
                        )
                    else:
                        results["error_count"] += 1 # type: ignore
                        results["errors"].append( # type: ignore
                            {
                                "file": str(file_path),
                                "error": result.get("error", "Unknown error"),
                            }
                        )

                except Exception as e:
                    results["error_count"] += 1 # type: ignore
                    results["errors"].append({"file": str(file_path), "error": str(e)}) # type: ignore
                    logger.error(f"Error processing {file_path}: {e}")

            results["processing_time"] = (datetime.now() - start_time).total_seconds()
            logger.info(
                f"Directory processing completed: {results['processed_count']} files processed"
            )

        except Exception as e:
            results["errors"].append(f"Directory processing error: {str(e)}")
            logger.error(f"Error processing directory {directory_path}: {e}")

        return results

    def get_processing_stats(self) -> Dict[str, Any]:
        """Get document processing statistics."""
        stats = {
            "supported_formats": len(DocumentProcessorConfig.SUPPORTED_EXTENSIONS),
            "supported_extensions": self.get_supported_extensions(),
            "output_directory": self.output_directory,
            "processing_settings": self.processing_settings.copy(),
        }

        # Count processed documents
        try:
            if os.path.exists(self.output_directory):
                processed_files = list(
                    Path(self.output_directory).glob("*_metadata.json")
                )
                stats["processed_documents"] = len(processed_files)

                # Analyze processed document types
                format_counts: Dict[str, int] = {}
                total_size = 0

                for metadata_file in processed_files:
                    try:
                        import json

                        with open(metadata_file, "r", encoding="utf-8") as f:
                            metadata = json.load(f)

                        ext = metadata.get("file_extension", "unknown")
                        format_counts[ext] = format_counts.get(ext, 0) + 1
                        total_size += metadata.get("file_size", 0)

                    except Exception:
                        continue

                stats["format_distribution"] = format_counts
                stats["total_processed_size"] = total_size
            else:
                stats["processed_documents"] = 0

        except Exception as e:
            stats["stats_error"] = str(e)

        return stats


# Global document processor instance
_global_document_processor: Optional[AtlasDocumentProcessor] = None


def get_document_processor(config: Optional[Dict] = None) -> AtlasDocumentProcessor:
    """Get global document processor instance."""
    global _global_document_processor

    if not UNSTRUCTURED_AVAILABLE:
        raise ImportError(
            "Unstructured library not available. Install with: pip install 'unstructured[all-docs]'"
        )

    if _global_document_processor is None:
        _global_document_processor = AtlasDocumentProcessor(config)

    return _global_document_processor


def process_document_file(file_path: str) -> Dict[str, Any]:
    """Convenience function to process a single document."""
    try:
        processor = get_document_processor()
        return processor.process_document(file_path)
    except Exception as e:
        logger.error(f"Document processing error: {e}")
        return {"processing_status": "error", "error": str(e), "source_file": file_path}


def is_document_processing_available() -> bool:
    """Check if document processing is available."""
    return UNSTRUCTURED_AVAILABLE
