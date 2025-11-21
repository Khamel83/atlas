"""
Fallback processing for Atlas v4.

Provides alternative processing strategies when primary methods fail,
including degraded content extraction and simplified processing.
"""

import hashlib
import re
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional, Callable
from urllib.parse import urlparse

from .retry import RetryHandler, RetryConfig


class FallbackStrategy:
    """Base class for fallback processing strategies."""

    def __init__(self, name: str):
        self.name = name
        self.logger = logging.getLogger(f"atlas.core.{self.__class__.__name__}")

    def can_handle(self, error: Exception, context: Dict[str, Any]) -> bool:
        """
        Check if this strategy can handle the given error.

        Args:
            error: The error that occurred
            context: Processing context information

        Returns:
            True if this strategy can handle the error
        """
        raise NotImplementedError

    def process(self, data: Any, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process data using fallback strategy.

        Args:
            data: Original data to process
            context: Processing context

        Returns:
            Processed content item
        """
        raise NotImplementedError


class TitleExtractionFallback(FallbackStrategy):
    """Fallback for title extraction when primary methods fail."""

    def __init__(self):
        super().__init__("title_extraction")

    def can_handle(self, error: Exception, context: Dict[str, Any]) -> bool:
        return "title" in str(error).lower() or "extraction" in str(error).lower()

    def process(self, data: Any, context: Dict[str, Any]) -> Dict[str, Any]:
        """Extract title using fallback methods."""
        if isinstance(data, str):
            return {"title": self._extract_title_from_text(data)}
        elif isinstance(data, dict):
            # Try various title sources
            title_sources = [
                data.get("title"),
                data.get("subject"),
                data.get("headline"),
                data.get("name"),
                data.get("url"),
                data.get("link")
            ]

            for source in title_sources:
                if source and isinstance(source, str):
                    title = self._clean_title(source)
                    if title and len(title) > 5:  # Reasonable minimum length
                        return {"title": title}

            # Generate title from content hash if all else fails
            content_hash = hashlib.md5(str(data).encode()).hexdigest()[:8]
            return {"title": f"Untitled Content {content_hash}"}

        return {"title": "Untitled Content"}

    def _extract_title_from_text(self, text: str) -> str:
        """Extract title from text content."""
        if not text:
            return "Untitled Content"

        lines = text.strip().split('\n')
        for line in lines:
            line = line.strip()
            if line and len(line) > 5 and len(line) < 200:
                # Skip obvious non-title lines
                if not line.startswith(('http', 'www', 'By ', 'Posted on', 'Category:')):
                    return line

        return text[:100].strip() + "..."

    def _clean_title(self, title: str) -> str:
        """Clean and normalize title."""
        if not title:
            return ""

        # Remove common prefixes/suffixes
        title = re.sub(r'^(?:Re:|Fwd:|FW:)\s*', '', title, flags=re.IGNORECASE)

        # Remove extra whitespace
        title = re.sub(r'\s+', ' ', title).strip()

        # Remove special characters but keep basic punctuation
        title = re.sub(r'[^\w\s\-.,!?():]', '', title)

        return title


class ContentExtractionFallback(FallbackStrategy):
    """Fallback for content extraction when primary methods fail."""

    def __init__(self):
        super().__init__("content_extraction")

    def can_handle(self, error: Exception, context: Dict[str, Any]) -> bool:
        return any(keyword in str(error).lower()
                  for keyword in ["content", "extraction", "parse", "readability"])

    def process(self, data: Any, context: Dict[str, Any]) -> Dict[str, Any]:
        """Extract content using fallback methods."""
        if isinstance(data, str):
            return {"content": self._sanitize_content(data)}
        elif isinstance(data, dict):
            # Try various content sources
            content_sources = [
                data.get("content"),
                data.get("body"),
                data.get("description"),
                data.get("summary"),
                data.get("text")
            ]

            for source in content_sources:
                if source and isinstance(source, str):
                    content = self._sanitize_content(source)
                    if len(content) > 50:  # Reasonable minimum length
                        return {"content": content}

            # Combine multiple fields if single field is insufficient
            combined_parts = []
            for field in ["title", "description", "summary", "url"]:
                value = data.get(field)
                if value and isinstance(value, str):
                    combined_parts.append(f"{field.title()}: {value}")

            if combined_parts:
                return {"content": "\n".join(combined_parts)}

        return {"content": "Content extraction failed - minimal information available"}

    def _sanitize_content(self, content: str) -> str:
        """Sanitize and normalize content."""
        if not content:
            return ""

        # Remove HTML tags (basic)
        content = re.sub(r'<[^>]+>', ' ', content)

        # Normalize whitespace
        content = re.sub(r'\s+', ' ', content).strip()

        # Remove very short lines
        lines = [line.strip() for line in content.split('\n') if len(line.strip()) > 10]

        return '\n'.join(lines)


class DateExtractionFallback(FallbackStrategy):
    """Fallback for date extraction when primary methods fail."""

    def __init__(self):
        super().__init__("date_extraction")

    def can_handle(self, error: Exception, context: Dict[str, Any]) -> bool:
        return "date" in str(error).lower()

    def process(self, data: Any, context: Dict[str, Any]) -> Dict[str, Any]:
        """Extract date using fallback methods."""
        current_date = datetime.now().isoformat()

        if isinstance(data, dict):
            # Try various date sources
            date_sources = [
                data.get("date"),
                data.get("published"),
                data.get("created"),
                data.get("timestamp"),
                data.get("pubDate"),
                data.get("updated")
            ]

            for source in date_sources:
                if source:
                    date_str = self._normalize_date(source)
                    if date_str:
                        return {"date": date_str}

        return {"date": current_date}

    def _normalize_date(self, date_input: Any) -> Optional[str]:
        """Normalize various date formats to ISO format."""
        if not date_input:
            return None

        if isinstance(date_input, datetime):
            return date_input.isoformat()

        if isinstance(date_input, str):
            # Try common date formats
            date_formats = [
                "%Y-%m-%d",
                "%Y-%m-%d %H:%M:%S",
                "%Y-%m-%dT%H:%M:%S",
                "%Y-%m-%dT%H:%M:%SZ",
                "%d/%m/%Y",
                "%m/%d/%Y",
                "%B %d, %Y",
                "%d %B %Y"
            ]

            for fmt in date_formats:
                try:
                    dt = datetime.strptime(date_input.strip(), fmt)
                    return dt.isoformat()
                except ValueError:
                    continue

        return None


class URLExtractionFallback(FallbackStrategy):
    """Fallback for URL extraction when primary methods fail."""

    def __init__(self):
        super().__init__("url_extraction")

    def can_handle(self, error: Exception, context: Dict[str, Any]) -> bool:
        return "url" in str(error).lower()

    def process(self, data: Any, context: Dict[str, Any]) -> Dict[str, Any]:
        """Extract URL using fallback methods."""
        if isinstance(data, str):
            # Look for URLs in text
            urls = self._extract_urls_from_text(data)
            if urls:
                return {"url": urls[0]}

        elif isinstance(data, dict):
            # Try various URL sources
            url_sources = [
                data.get("url"),
                data.get("link"),
                data.get("href"),
                data.get("source"),
                data.get("permalink")
            ]

            for source in url_sources:
                if source and isinstance(source, str):
                    if self._is_valid_url(source):
                        return {"url": source}

        return {"url": ""}

    def _extract_urls_from_text(self, text: str) -> List[str]:
        """Extract URLs from text content."""
        url_pattern = re.compile(r'https?://[^\s<>"{}|\\^`\[\]]+')
        urls = url_pattern.findall(text)
        return [url for url in urls if self._is_valid_url(url)]

    def _is_valid_url(self, url: str) -> bool:
        """Check if URL is valid."""
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except Exception:
            return False


class FallbackProcessor:
    """
    Manages fallback processing strategies.

    Provides automatic fallback to alternative processing methods
    when primary extraction methods fail.
    """

    def __init__(self):
        """Initialize fallback processor with default strategies."""
        self.strategies: List[FallbackStrategy] = [
            TitleExtractionFallback(),
            ContentExtractionFallback(),
            DateExtractionFallback(),
            URLExtractionFallback()
        ]
        self.retry_handler = RetryHandler()
        self.logger = logging.getLogger(f"atlas.core.{self.__class__.__name__}")

    def add_strategy(self, strategy: FallbackStrategy) -> None:
        """Add a custom fallback strategy."""
        self.strategies.append(strategy)

    def process_with_fallback(
        self,
        primary_func: Callable,
        data: Any,
        context: Optional[Dict[str, Any]] = None,
        max_fallback_attempts: int = 3
    ) -> Dict[str, Any]:
        """
        Process data with primary function and fallback strategies.

        Args:
            primary_func: Primary processing function
            data: Data to process
            context: Processing context
            max_fallback_attempts: Maximum fallback attempts

        Returns:
            Processed content item
        """
        if context is None:
            context = {}

        # Try primary function first
        try:
            result = primary_func(data)
            if result and isinstance(result, dict):
                result["processing_method"] = "primary"
                return result
        except Exception as e:
            self.logger.warning(
                f"Primary processing failed",
                error=str(e),
                error_type=type(e).__name__
            )

        # Try fallback strategies
        for strategy in self.strategies:
            try:
                if strategy.can_handle(e, context):
                    self.logger.info(f"Trying fallback strategy: {strategy.name}")

                    fallback_result = strategy.process(data, context)
                    if fallback_result:
                        fallback_result["processing_method"] = f"fallback_{strategy.name}"
                        fallback_result["fallback_reason"] = str(e)
                        return fallback_result

            except Exception as fallback_error:
                self.logger.warning(
                    f"Fallback strategy {strategy.name} failed",
                    error=str(fallback_error)
                )
                continue

        # Last resort: minimal content item
        self.logger.error("All processing methods failed, creating minimal content item")
        return self._create_minimal_content_item(data, str(e))

    def _create_minimal_content_item(self, data: Any, error: str) -> Dict[str, Any]:
        """Create minimal content item when all processing fails."""
        content_hash = hashlib.md5(str(data).encode()).hexdigest()[:8]
        timestamp = datetime.now().isoformat()

        return {
            "id": f"minimal-{content_hash}",
            "title": f"Failed Processing {content_hash}",
            "content": f"Content processing failed. Error: {error}",
            "date": timestamp,
            "ingested_at": timestamp,
            "source": "fallback",
            "type": "unknown",
            "processing_method": "minimal",
            "fallback_reason": error,
            "content_hash": content_hash
        }

    def get_fallback_stats(self) -> Dict[str, Any]:
        """Get statistics about fallback usage."""
        # This would be implemented with persistent storage in a real system
        return {
            "total_fallbacks": 0,
            "strategy_usage": {},
            "success_rate": 0.0
        }


# Global fallback processor instance
fallback_processor = FallbackProcessor()


def process_with_fallback(
    primary_func: Callable,
    data: Any,
    context: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Process data with fallback using global processor.

    Args:
        primary_func: Primary processing function
        data: Data to process
        context: Processing context

    Returns:
        Processed content item
    """
    return fallback_processor.process_with_fallback(primary_func, data, context)