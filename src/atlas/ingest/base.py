"""
Base ingestor interface for Atlas v4.

Defines the common interface that all ingestors must implement.
Provides shared functionality and patterns for content ingestion.
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass
import logging

from ..core.validator import ValidationResult, ContentValidator
from ..core.content_hash import generate_content_hash, create_content_identifier
from ..core.url_normalizer import normalize_url, create_canonical_id


@dataclass
class IngestResult:
    """Result of an ingestion operation."""
    success: bool
    items_processed: int
    items_duplicated: int
    items_failed: int
    errors: List[str]
    warnings: List[str]
    metadata: Dict[str, Any]


class BaseIngestor(ABC):
    """
    Base class for all Atlas content ingestors.

    Each ingestor should be a simple, focused tool that does one thing well:
    - Fetch content from a source
    - Convert to standardized format
    - Return list of content items

    All ingestors must be under 300 lines and run independently.
    """

    def __init__(self, source_config: Dict[str, Any]):
        """
        Initialize ingestor with source configuration.

        Args:
            source_config: Configuration specific to this ingestor
        """
        self.source_config = source_config
        self.source_name = source_config.get("name", "unknown")
        self.source_type = source_config.get("type", "unknown")
        self.validation_config = source_config.get("validation", {})
        self.logger = logging.getLogger(f"atlas.ingest.{self.__class__.__name__}")
        self.validator = ContentValidator()

    @abstractmethod
    def ingest(self) -> List[Dict[str, Any]]:
        """
        Ingest content from the configured source.

        Returns:
            List of standardized content items
        """
        pass

    def run(self) -> IngestResult:
        """
        Run the ingestion process with comprehensive error handling.

        Returns:
            IngestResult with comprehensive status information
        """
        self.logger.info(f"Starting ingestion for source: {self.source_name}")

        try:
            # Run ingest
            items = self.ingest()

            # Validate and process items
            results = self._process_items(items)

            # Create result
            ingest_result = IngestResult(
                success=True,
                items_processed=len(results),
                items_duplicated=0,  # Will be calculated during deduplication
                items_failed=0,
                errors=[],
                warnings=[],
                metadata={
                    "source_name": self.source_name,
                    "source_type": self.source_type,
                    "processing_time": datetime.now().isoformat()
                }
            )

            self.logger.info(
                f"Ingestion completed for {self.source_name}",
                items_processed=ingest_result.items_processed
            )

            return ingest_result

        except Exception as e:
            error_msg = f"Ingestion failed for {self.source_name}: {str(e)}"
            self.logger.error(error_msg, exc_info=True)

            return IngestResult(
                success=False,
                items_processed=0,
                items_duplicated=0,
                items_failed=1,
                errors=[error_msg],
                warnings=[],
                metadata={
                    "source_name": self.source_name,
                    "source_type": self.source_type,
                    "error_time": datetime.now().isoformat()
                }
            )

    def _process_items(self, items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Process raw items into standardized Atlas content items.

        Args:
            items: Raw items from ingestion source

        Returns:
            List of standardized content items
        """
        processed_items = []

        for item in items:
            try:
                # Convert to standard format
                standard_item = self._standardize_item(item)

                # Validate content
                validation_result = self.validator.validate_content_item(standard_item)

                if not validation_result.is_valid:
                    self.logger.warning(
                        f"Item failed validation: {validation_result.errors}",
                        item_id=standard_item.get('id', 'unknown')
                    )
                    continue

                # Add validation metadata
                standard_item['validation'] = {
                    'validated_at': datetime.now().isoformat(),
                    'warnings': validation_result.warnings
                }

                processed_items.append(standard_item)

            except Exception as e:
                self.logger.error(
                    f"Failed to process item: {str(e)}",
                    item_id=item.get('id', 'unknown'),
                    exc_info=True
                )

        return processed_items

    @abstractmethod
    def _standardize_item(self, raw_item: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert raw item to Atlas standard format.

        Args:
            raw_item: Raw item from ingestion source

        Returns:
            Standardized content item
        """
        pass

    def _create_base_item(
        self,
        title: str,
        content: str,
        url: Optional[str] = None,
        author: Optional[str] = None,
        date: Optional[Union[str, datetime]] = None,
        guid: Optional[str] = None,
        tags: Optional[List[str]] = None,
        **metadata
    ) -> Dict[str, Any]:
        """
        Create a base content item with required fields.

        Args:
            title: Content title
            content: Content body
            url: Content URL (optional)
            author: Content author (optional)
            date: Publication date (optional)
            guid: Content GUID (optional)
            tags: Content tags (optional)
            **metadata: Additional metadata

        Returns:
            Base content item
        """
        # Create content identifier
        identifiers = create_content_identifier(title, content, url, guid)

        # Create canonical ID
        canonical_id = create_canonical_id(url, guid, title)

        # Format date
        if isinstance(date, datetime):
            formatted_date = date.isoformat()
        elif isinstance(date, str):
            formatted_date = date
        else:
            formatted_date = datetime.now().isoformat()

        # Create base item
        item = {
            # Required fields
            'id': canonical_id,
            'type': self.source_type,
            'source': self.source_name,
            'title': title.strip(),
            'date': formatted_date,
            'ingested_at': datetime.now().isoformat(),
            'content_hash': identifiers['content_hash'],

            # Content
            'content': content.strip(),

            # Optional fields
            'url': url,
            'author': author,
            'tags': tags or [],
            'metadata': metadata
        }

        # Add identifiers if available
        if 'guid' in identifiers:
            item['guid'] = identifiers['guid']
        if 'guid_hash' in identifiers:
            item['guid_hash'] = identifiers['guid_hash']
        if 'url_hash' in identifiers:
            item['url_hash'] = identifiers['url_hash']

        return item

    def _extract_text_from_html(self, html_content: str) -> str:
        """
        Simple HTML text extraction for basic cases.

        Args:
            html_content: HTML content

        Returns:
            Extracted plain text
        """
        import re

        # Remove HTML tags
        text = re.sub(r'<[^>]+>', '', html_content)

        # Clean up whitespace
        text = re.sub(r'\s+', ' ', text).strip()

        return text

    def _should_skip_item(self, item: Dict[str, Any]) -> bool:
        """
        Check if item should be skipped based on configuration.

        Args:
            item: Item to check

        Returns:
            True if item should be skipped
        """
        # Check date filters
        if 'since_days' in self.source_config:
            try:
                item_date = datetime.fromisoformat(
                    item.get('date', '').replace('Z', '+00:00')
                )
                days_old = (datetime.now() - item_date).days
                if days_old > self.source_config['since_days']:
                    self.logger.debug(
                        f"Skipping item due to age: {days_old} days old",
                        item_id=item.get('id', 'unknown')
                    )
                    return True
            except Exception:
                pass  # If date parsing fails, don't skip

        # Check content length filters
        min_length = self.validation_config.get('min_length', 0)
        content_length = len(item.get('content', ''))
        if content_length < min_length:
            self.logger.debug(
                f"Skipping item due to short content: {content_length} chars",
                item_id=item.get('id', 'unknown')
            )
            return True

        return False

    def _log_progress(self, current: int, total: int, message: str = "") -> None:
        """
        Log progress information.

        Args:
            current: Current item count
            total: Total item count
            message: Additional message
        """
        if total > 0:
            progress = (current / total) * 100
            self.logger.info(
                f"Progress: {current}/{total} ({progress:.1f}%) {message}".strip()
            )

    def cleanup(self) -> None:
        """
        Perform cleanup operations after ingestion.

        Subclasses can override this to perform source-specific cleanup.
        """
        pass

    @classmethod
    def get_required_config_keys(cls) -> List[str]:
        """
        Get list of required configuration keys for this ingestor.

        Returns:
            List of required config keys
        """
        return ['name', 'type']

    @classmethod
    def get_optional_config_keys(cls) -> List[str]:
        """
        Get list of optional configuration keys for this ingestor.

        Returns:
            List of optional config keys
        """
        return ['validation', 'since_days']

    def validate_config(self) -> List[str]:
        """
        Validate source configuration.

        Returns:
            List of validation errors (empty if valid)
        """
        errors = []
        required_keys = self.get_required_config_keys()

        for key in required_keys:
            if key not in self.source_config:
                errors.append(f"Missing required config key: {key}")

        return errors


# Utility functions for ingestors
def create_ingest_result(
    success: bool,
    items: List[Dict[str, Any]],
    errors: Optional[List[str]] = None,
    warnings: Optional[List[str]] = None,
    **metadata
) -> IngestResult:
    """
    Helper function to create IngestResult.

    Args:
        success: Whether ingestion was successful
        items: List of processed items
        errors: List of errors
        warnings: List of warnings
        **metadata: Additional metadata

    Returns:
        IngestResult object
    """
    return IngestResult(
        success=success,
        items_processed=len(items),
        items_duplicated=0,
        items_failed=len(errors) if errors else 0,
        errors=errors or [],
        warnings=warnings or [],
        metadata=metadata
    )