"""
Generic Content Processor for Atlas

Unified processor that handles all content types (URLs, RSS, YouTube, documents)
with strategy pattern. Replaces 20+ specialized workers with one generic system.
"""

import abc
import asyncio
import time
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union, Type
from dataclasses import dataclass, asdict
import json
import hashlib
import re
from urllib.parse import urlparse

from .database import Content, get_database
from .config import get_config


@dataclass
class ProcessingResult:
    """Result of content processing"""
    success: bool
    content: Optional[Content] = None
    error: Optional[str] = None
    processing_time: float = 0.0
    stages_completed: List[int] = None

    def __post_init__(self):
        if self.stages_completed is None:
            self.stages_completed = []


@dataclass
class ProcessingContext:
    """Context for processing operations"""
    content_id: Optional[int] = None
    current_stage: int = 0
    metadata: Dict[str, Any] = None
    errors: List[str] = None
    start_time: float = 0.0

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
        if self.errors is None:
            self.errors = []


class ContentStrategy(abc.ABC):
    """Abstract base class for content processing strategies"""

    def __init__(self, name: str):
        self.name = name
        self.logger = logging.getLogger(f"{__name__}.{name}")

    @abc.abstractmethod
    def can_handle(self, input_data: Any) -> bool:
        """Check if this strategy can handle the input data"""
        pass

    @abc.abstractmethod
    async def extract_content(self, input_data: Any, context: ProcessingContext) -> ProcessingResult:
        """Extract raw content from input data"""
        pass

    @abc.abstractmethod
    async def process_content(self, content: Content, context: ProcessingContext) -> ProcessingResult:
        """Process extracted content through stages"""
        pass

    def _generate_content_hash(self, content: str) -> str:
        """Generate hash for content deduplication"""
        return hashlib.md5(content.encode()).hexdigest()


class URLStrategy(ContentStrategy):
    """Strategy for processing URL content"""

    def __init__(self):
        super().__init__("url")
        self.supported_schemes = {'http', 'https'}

    def can_handle(self, input_data: Any) -> bool:
        """Check if input is a valid URL"""
        if isinstance(input_data, str):
            try:
                parsed = urlparse(input_data)
                return parsed.scheme in self.supported_schemes
            except Exception:
                return False
        return False

    async def extract_content(self, input_data: Any, context: ProcessingContext) -> ProcessingResult:
        """Extract content from URL"""
        start_time = time.time()
        url = str(input_data)

        try:
            # Import here to avoid circular dependencies
            from strategies.url_strategy import URLProcessor

            processor = URLProcessor()
            result = await processor.process_url(url)

            if result['success']:
                content = Content(
                    title=result['title'],
                    url=url,
                    content=result['content'],
                    content_type='article',
                    metadata={
                        'source_url': url,
                        'extracted_at': datetime.utcnow().isoformat(),
                        'word_count': len(result['content'].split()),
                        'extraction_method': 'url_strategy'
                    }
                )

                return ProcessingResult(
                    success=True,
                    content=content,
                    processing_time=time.time() - start_time,
                    stages_completed=[0, 50]
                )
            else:
                return ProcessingResult(
                    success=False,
                    error=result.get('error', 'Unknown URL processing error'),
                    processing_time=time.time() - start_time
                )

        except Exception as e:
            self.logger.error(f"URL extraction failed for {url}: {e}")
            return ProcessingResult(
                success=False,
                error=str(e),
                processing_time=time.time() - start_time
            )

    async def process_content(self, content: Content, context: ProcessingContext) -> ProcessingResult:
        """Process URL content through stages"""
        start_time = time.time()

        try:
            # Stage 100-150: Basic content processing
            await self._process_basic_content(content, context)

            # Stage 200-250: Content enhancement
            await self._enhance_content(content, context)

            # Stage 300: Final processing
            await self._finalize_content(content, context)

            return ProcessingResult(
                success=True,
                content=content,
                processing_time=time.time() - start_time,
                stages_completed=[100, 150, 200, 250, 300]
            )

        except Exception as e:
            self.logger.error(f"Content processing failed: {e}")
            return ProcessingResult(
                success=False,
                error=str(e),
                processing_time=time.time() - start_time
            )

    async def _process_basic_content(self, content: Content, context: ProcessingContext):
        """Basic content processing (stage 100-150)"""
        # Clean HTML content
        content.content = self._clean_html(content.content)

        # Extract basic metadata
        content.metadata['processed_at'] = datetime.utcnow().isoformat()
        content.metadata['content_length'] = len(content.content)

        # Update stage
        try:
            db = get_database()
            if content.id:
                db.update_content_stage(content.id, 100)
        except Exception as e:
            self.logger.warning(f"Failed to update stage: {e}")

    async def _enhance_content(self, content: Content, context: ProcessingContext):
        """Content enhancement (stage 200-250)"""
        # Extract keywords
        content.metadata['keywords'] = self._extract_keywords(content.content)

        # Generate summary (basic)
        if len(content.content) > 500:
            summary = self._generate_summary(content.content)
            if summary:
                content.ai_summary = summary

        # Update stage
        try:
            db = get_database()
            if content.id:
                db.update_content_stage(content.id, 200)
        except Exception as e:
            self.logger.warning(f"Failed to update stage: {e}")

    async def _finalize_content(self, content: Content, context: ProcessingContext):
        """Final processing (stage 300)"""
        # Mark as completed
        content.metadata['processing_complete'] = True
        content.metadata['completed_at'] = datetime.utcnow().isoformat()

        # Update stage
        try:
            db = get_database()
            if content.id:
                db.update_content_stage(content.id, 300)
        except Exception as e:
            self.logger.warning(f"Failed to update stage: {e}")

    def _clean_html(self, html_content: str) -> str:
        """Clean HTML content"""
        # Remove HTML tags
        clean_text = re.sub(r'<[^>]+>', '', html_content)
        # Normalize whitespace
        clean_text = re.sub(r'\s+', ' ', clean_text).strip()
        return clean_text

    def _extract_keywords(self, text: str) -> List[str]:
        """Extract simple keywords from text"""
        # Simple keyword extraction
        words = re.findall(r'\b[a-zA-Z]{3,}\b', text.lower())
        # Remove common stop words
        stop_words = {'the', 'and', 'for', 'are', 'but', 'not', 'you', 'all', 'can', 'had', 'her', 'was', 'one', 'our', 'out', 'day', 'get', 'has', 'him', 'his', 'how', 'its', 'may', 'new', 'now', 'old', 'see', 'two', 'way', 'who', 'boy', 'did', 'she', 'use', 'her', 'have', 'been', 'from', 'they', 'this', 'that', 'with', 'were', 'been'}
        keywords = [word for word in words if word not in stop_words]
        # Return most common
        return list(set(keywords))[:10]

    def _generate_summary(self, text: str) -> Optional[str]:
        """Generate basic summary"""
        sentences = text.split('.')
        if len(sentences) > 3:
            # Take first 3 sentences as summary
            return '. '.join(sentences[:3]) + '.'
        return None


class RSSStrategy(ContentStrategy):
    """Strategy for processing RSS feeds"""

    def __init__(self):
        super().__init__("rss")

    def can_handle(self, input_data: Any) -> bool:
        """Check if input is RSS feed URL or RSS content"""
        if isinstance(input_data, str):
            return (input_data.endswith('.xml') or
                   input_data.endswith('.rss') or
                   'rss' in input_data.lower() or
                   'feed' in input_data.lower())
        return False

    async def extract_content(self, input_data: Any, context: ProcessingContext) -> ProcessingResult:
        """Extract content from RSS feed"""
        start_time = time.time()

        try:
            # Import here to avoid circular dependencies
            from strategies.rss_strategy import RSSProcessor

            processor = RSSProcessor()
            result = await processor.process_feed(str(input_data))

            if result['success']:
                # RSS feeds typically return multiple content items
                # For now, we'll process the first item as representative
                if result['entries']:
                    entry = result['entries'][0]
                    content = Content(
                        title=entry.get('title', 'RSS Entry'),
                        url=entry.get('link', ''),
                        content=entry.get('content', ''),
                        content_type='article',
                        metadata={
                            'feed_url': str(input_data),
                            'feed_title': result.get('feed_title', ''),
                            'entry_published': entry.get('published', ''),
                            'extraction_method': 'rss_strategy'
                        }
                    )

                    return ProcessingResult(
                        success=True,
                        content=content,
                        processing_time=time.time() - start_time,
                        stages_completed=[0, 75]
                    )
                else:
                    return ProcessingResult(
                        success=False,
                        error="No entries found in RSS feed",
                        processing_time=time.time() - start_time
                    )
            else:
                return ProcessingResult(
                    success=False,
                    error=result.get('error', 'Unknown RSS processing error'),
                    processing_time=time.time() - start_time
                )

        except Exception as e:
            self.logger.error(f"RSS extraction failed: {e}")
            return ProcessingResult(
                success=False,
                error=str(e),
                processing_time=time.time() - start_time
            )

    async def process_content(self, content: Content, context: ProcessingContext) -> ProcessingResult:
        """Process RSS content through stages"""
        # RSS content uses same processing as URL content
        return await URLStrategy().process_content(content, context)


class TextStrategy(ContentStrategy):
    """Strategy for processing plain text content"""

    def __init__(self):
        super().__init__("text")

    def can_handle(self, input_data: Any) -> bool:
        """Check if input is plain text"""
        if isinstance(input_data, str):
            # If it doesn't look like a URL, treat as text
            return not URLStrategy().can_handle(input_data)
        return False

    async def extract_content(self, input_data: Any, context: ProcessingContext) -> ProcessingResult:
        """Extract content from text input"""
        start_time = time.time()
        text = str(input_data)

        try:
            content = Content(
                title=f"Text Note - {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}",
                url="",  # No URL for text input
                content=text,
                content_type='note',
                metadata={
                    'source': 'direct_input',
                    'created_at': datetime.utcnow().isoformat(),
                    'char_count': len(text),
                    'word_count': len(text.split()),
                    'extraction_method': 'text_strategy'
                }
            )

            return ProcessingResult(
                success=True,
                content=content,
                processing_time=time.time() - start_time,
                stages_completed=[0, 25]
            )

        except Exception as e:
            self.logger.error(f"Text extraction failed: {e}")
            return ProcessingResult(
                success=False,
                error=str(e),
                processing_time=time.time() - start_time
            )

    async def process_content(self, content: Content, context: ProcessingContext) -> ProcessingResult:
        """Process text content through stages"""
        # Text content uses simplified processing
        start_time = time.time()

        try:
            # Basic processing (stage 100)
            content.metadata['processed_at'] = datetime.utcnow().isoformat()
            content.metadata['content_length'] = len(content.content)

            # Extract keywords
            content.metadata['keywords'] = URLStrategy._extract_keywords(self, content.content)

            # Generate summary if long enough
            if len(content.content) > 200:
                summary = URLStrategy._generate_summary(self, content.content)
                if summary:
                    content.ai_summary = summary

            # Final stage
            content.metadata['processing_complete'] = True
            content.metadata['completed_at'] = datetime.utcnow().isoformat()

            return ProcessingResult(
                success=True,
                content=content,
                processing_time=time.time() - start_time,
                stages_completed=[100, 200]
            )

        except Exception as e:
            self.logger.error(f"Text processing failed: {e}")
            return ProcessingResult(
                success=False,
                error=str(e),
                processing_time=time.time() - start_time
            )


class GenericContentProcessor:
    """Unified processor for all content types"""

    def __init__(self):
        self.strategies: List[ContentStrategy] = []
        self.logger = logging.getLogger(__name__)
        self._load_strategies()

    def _load_strategies(self):
        """Load all content processing strategies"""
        self.strategies = [
            URLStrategy(),
            RSSStrategy(),
            TextStrategy(),
            # YouTubeStrategy(),  # Will be added later
            # DocumentStrategy(), # Will be added later
        ]

    def register_strategy(self, strategy: ContentStrategy):
        """Register a new processing strategy"""
        self.strategies.append(strategy)
        self.logger.info(f"Registered strategy: {strategy.name}")

    def select_strategy(self, input_data: Any) -> Optional[ContentStrategy]:
        """Select appropriate strategy for input data"""
        for strategy in self.strategies:
            if strategy.can_handle(input_data):
                return strategy
        return None

    async def process(self, input_data: Any, title: str = None) -> ProcessingResult:
        """Process input data with automatic strategy selection"""
        context = ProcessingContext(start_time=time.time())

        try:
            # Select strategy
            strategy = self.select_strategy(input_data)
            if not strategy:
                return ProcessingResult(
                    success=False,
                    error=f"No strategy found for input: {type(input_data)}"
                )

            self.logger.info(f"Processing with strategy: {strategy.name}")

            # Extract content
            extract_result = await strategy.extract_content(input_data, context)
            if not extract_result.success:
                return extract_result

            # Set custom title if provided
            if title and extract_result.content:
                extract_result.content.title = title

            # Store in database
            db = get_database()
            content_id = db.store_content(extract_result.content)
            extract_result.content.id = content_id

            # Process content through stages
            process_result = await strategy.process_content(extract_result.content, context)

            # Update final content in database
            if process_result.success:
                db.update_content(process_result.content)

            return process_result

        except Exception as e:
            self.logger.error(f"Processing failed: {e}")
            return ProcessingResult(
                success=False,
                error=str(e),
                processing_time=time.time() - context.start_time
            )

    async def process_batch(self, items: List[Any]) -> List[ProcessingResult]:
        """Process multiple items concurrently"""
        tasks = []
        for item in items:
            task = self.process(item)
            tasks.append(task)

        return await asyncio.gather(*tasks, return_exceptions=True)

    def get_capabilities(self) -> Dict[str, Any]:
        """Get processor capabilities"""
        return {
            'strategies': [strategy.name for strategy in self.strategies],
            'total_strategies': len(self.strategies),
            'supported_types': [
                'URLs (http/https)',
                'RSS feeds',
                'Plain text',
                # 'YouTube videos',
                # 'Documents'
            ]
        }

    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on processor"""
        healthy_strategies = 0
        errors = []

        for strategy in self.strategies:
            try:
                # Basic health check for each strategy
                test_input = self._get_test_input_for_strategy(strategy)
                if test_input:
                    result = await strategy.extract_content(test_input, ProcessingContext())
                    if result.success:
                        healthy_strategies += 1
                    else:
                        errors.append(f"{strategy.name}: {result.error}")
                else:
                    healthy_strategies += 1  # Strategy without test input
            except Exception as e:
                errors.append(f"{strategy.name}: {str(e)}")

        return {
            'status': 'healthy' if healthy_strategies == len(self.strategies) else 'degraded',
            'healthy_strategies': healthy_strategies,
            'total_strategies': len(self.strategies),
            'errors': errors
        }

    def _get_test_input_for_strategy(self, strategy: ContentStrategy) -> Any:
        """Get test input for strategy health check"""
        if isinstance(strategy, URLStrategy):
            return "https://example.com"
        elif isinstance(strategy, RSSStrategy):
            return "https://example.com/feed.xml"
        elif isinstance(strategy, TextStrategy):
            return "Test content"
        return None

    async def close(self):
        """Close all strategy sessions and cleanup resources"""
        for strategy in self.strategies:
            try:
                if hasattr(strategy, 'close'):
                    await strategy.close()
            except Exception as e:
                self.logger.warning(f"Failed to close {strategy.name} strategy: {e}")

    def __del__(self):
        """Cleanup when processor is destroyed"""
        # Ensure sessions are closed
        try:
            import asyncio
            loop = asyncio.get_event_loop()
            if loop.is_running():
                loop.create_task(self.close())
        except Exception:
            pass


# Singleton instance for easy import
processor_instance = None

def get_processor() -> GenericContentProcessor:
    """Get singleton processor instance"""
    global processor_instance
    if processor_instance is None:
        processor_instance = GenericContentProcessor()
    return processor_instance