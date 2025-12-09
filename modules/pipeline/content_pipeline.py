"""
Unified Content Pipeline - Fetch, process, and store content.

This pipeline handles:
1. URL fetching with cascading fallbacks (direct, Playwright, archive, wayback)
2. Content extraction (articles, transcripts)
3. HTML to markdown conversion with image downloading
4. Content type detection
5. Deduplication
6. Storage to file-based system

Uses RobustFetcher for reliable content retrieval:
- Direct HTTP fetch (Trafilatura)
- Playwright (headless browser for JS/paywall)
- Archive.is lookup
- Wayback Machine lookup
- URL resurrection (parse slug, search archives)
"""

import time
import logging
import re
import html2text
import trafilatura
from pathlib import Path
from urllib.parse import urlparse
from typing import Optional, Dict, Any, Tuple
from datetime import datetime

import requests
from bs4 import BeautifulSoup

from modules.storage import FileStore, IndexManager, ContentItem, ContentType, SourceType
from modules.storage.content_types import ProcessingStatus

logger = logging.getLogger(__name__)

# Lazy imports to avoid circular dependency
RobustFetcher = None
FetchResult = None
should_skip_url = None


def _import_robust_fetcher():
    """Lazy import of robust_fetcher to avoid circular imports."""
    global RobustFetcher, FetchResult, should_skip_url
    if RobustFetcher is None:
        from modules.ingest.robust_fetcher import (
            RobustFetcher as _RobustFetcher,
            FetchResult as _FetchResult,
            should_skip_url as _should_skip_url,
        )
        RobustFetcher = _RobustFetcher
        FetchResult = _FetchResult
        should_skip_url = _should_skip_url


class RateLimiter:
    """Simple rate limiter for courteous web requests."""

    def __init__(self, min_delay: float = 2.0, max_delay: float = 3.0):
        self.min_delay = min_delay
        self.max_delay = max_delay
        self.last_request_time: Dict[str, float] = {}

    def wait(self, domain: Optional[str] = None):
        """Wait appropriate time before next request."""
        key = domain or "_global"
        last_time = self.last_request_time.get(key, 0)
        elapsed = time.time() - last_time

        # Use variable delay
        import random
        delay = random.uniform(self.min_delay, self.max_delay)

        if elapsed < delay:
            sleep_time = delay - elapsed
            logger.debug(f"Rate limiting: sleeping {sleep_time:.1f}s for {key}")
            time.sleep(sleep_time)

        self.last_request_time[key] = time.time()


class ContentFetcher:
    """Fetch and extract content from URLs."""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) "
                          "Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        })
        self.rate_limiter = RateLimiter()
        self.html2text = html2text.HTML2Text()
        self.html2text.ignore_links = False
        self.html2text.ignore_images = False
        self.html2text.body_width = 0  # Don't wrap

    def fetch_url(self, url: str) -> Tuple[Optional[str], Optional[Dict[str, Any]]]:
        """
        Fetch and extract content from a URL.

        Returns:
            Tuple of (markdown_content, metadata)
        """
        domain = urlparse(url).netloc
        self.rate_limiter.wait(domain)

        try:
            logger.info(f"Fetching: {url}")
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            html = response.text

            # Use trafilatura for article extraction (best results)
            extracted = trafilatura.extract(
                html,
                include_links=True,
                include_images=True,
                include_comments=False,
                output_format="markdown"
            )

            # Get metadata
            metadata = trafilatura.extract_metadata(html)
            meta_dict = {}
            if metadata:
                meta_dict = {
                    "title": metadata.title or "",
                    "author": metadata.author or "",
                    "description": metadata.description or "",
                    "date": metadata.date or "",
                    "sitename": metadata.sitename or "",
                }

            # Fallback to html2text if trafilatura fails
            if not extracted or len(extracted) < 200:
                logger.debug("Trafilatura extraction minimal, using html2text fallback")
                extracted = self._html2text_fallback(html)

                # Extract title from HTML if not in metadata
                if not meta_dict.get("title"):
                    soup = BeautifulSoup(html, "html.parser")
                    title_tag = soup.find("title")
                    if title_tag:
                        meta_dict["title"] = title_tag.get_text().strip()

            return extracted, meta_dict

        except requests.RequestException as e:
            logger.error(f"Error fetching {url}: {e}")
            return None, {"error": str(e)}
        except Exception as e:
            logger.error(f"Error processing {url}: {e}")
            return None, {"error": str(e)}

    def _html2text_fallback(self, html: str) -> str:
        """Convert HTML to markdown using html2text."""
        return self.html2text.handle(html)


class ContentTypeDetector:
    """Detect content type from URL or content."""

    YOUTUBE_PATTERNS = [
        r"youtube\.com/watch",
        r"youtu\.be/",
        r"youtube\.com/shorts",
    ]

    PODCAST_PATTERNS = [
        r"podcasts?\.apple\.com",
        r"open\.spotify\.com/episode",
        r"overcast\.fm",
        r"pocketcasts\.com",
        r"castro\.fm",
    ]

    NEWSLETTER_PATTERNS = [
        r"substack\.com",
        r"buttondown\.email",
        r"revue\.co",
        r"beehiiv\.com",
        r"convertkit\.com",
        r"mailchimp\.com",
    ]

    @classmethod
    def detect_from_url(cls, url: str) -> ContentType:
        """Detect content type from URL patterns."""
        url_lower = url.lower()

        for pattern in cls.YOUTUBE_PATTERNS:
            if re.search(pattern, url_lower):
                return ContentType.YOUTUBE

        for pattern in cls.PODCAST_PATTERNS:
            if re.search(pattern, url_lower):
                return ContentType.PODCAST

        for pattern in cls.NEWSLETTER_PATTERNS:
            if re.search(pattern, url_lower):
                return ContentType.NEWSLETTER

        return ContentType.ARTICLE


class ContentPipeline:
    """Main content processing pipeline using robust fallback fetcher."""

    def __init__(self, base_dir: str = ".", cookies_path: str = None, use_robust: bool = True):
        """
        Initialize the content pipeline.

        Args:
            base_dir: Base directory for storage
            cookies_path: Path to browser cookies JSON for authenticated fetching
            use_robust: Use RobustFetcher with fallbacks (default True)
        """
        self.file_store = FileStore("data/content")
        self.index_manager = IndexManager("data/indexes/atlas_index.db")
        self.use_robust = use_robust

        if use_robust:
            _import_robust_fetcher()  # Lazy import
            self.fetcher = RobustFetcher(
                output_base=Path("data/content"),
                cookies_path=Path(cookies_path) if cookies_path else None,
                download_images=True,
            )
        else:
            self.fetcher = ContentFetcher()

        self.stats = {
            "processed": 0,
            "skipped_duplicate": 0,
            "skipped_non_content": 0,
            "failed": 0,
            "by_method": {},  # Track success by fetch method
        }

    def process_url(
        self,
        url: str,
        source_type: SourceType = SourceType.MANUAL,
        force: bool = False,
        extra: Optional[Dict[str, Any]] = None,
    ) -> Optional[ContentItem]:
        """
        Process a URL through the pipeline with robust fallbacks.

        Args:
            url: URL to process
            source_type: How this URL was discovered
            force: Process even if duplicate exists
            extra: Additional metadata to store

        Returns:
            ContentItem if processed successfully, None otherwise
        """
        # Check if URL should be skipped (marketing, tracking, etc.)
        if self.use_robust:
            _import_robust_fetcher()
            skip, reason = should_skip_url(url)
        else:
            skip, reason = False, ""

        if skip:
            logger.info(f"Skipping non-content URL: {reason}")
            self.stats["skipped_non_content"] += 1
            return None

        # Check for duplicate
        content_id = ContentItem.generate_id(source_url=url)
        if not force and self.file_store.exists(content_id):
            logger.info(f"Skipping duplicate: {url}")
            self.stats["skipped_duplicate"] += 1
            return None

        # Detect content type
        content_type = ContentTypeDetector.detect_from_url(url)

        # Fetch content using appropriate fetcher
        if self.use_robust:
            result = self._fetch_robust(url, content_type)
            content = result.content_md if result else None
            metadata = result.metadata if result else {}
            fetch_method = result.method if result else None
            fetch_success = result.success if result else False
            fetch_error = result.error if result else "Unknown error"
        else:
            content, metadata = self.fetcher.fetch_url(url)
            fetch_method = "direct"
            fetch_success = content is not None
            fetch_error = metadata.get("error", "Unknown error") if not fetch_success else None

        if not fetch_success:
            logger.error(f"Failed to fetch: {url}")
            self.stats["failed"] += 1

            # Still create a record for tracking
            item = ContentItem(
                content_id=content_id,
                content_type=content_type,
                source_type=source_type,
                title=f"Failed: {url[:50]}",
                source_url=url,
                status=ProcessingStatus.FAILED,
                error_message=fetch_error,
                extra=extra or {},
            )
            item_dir = self.file_store.save(item)
            self.index_manager.index_item(item, str(item_dir))
            return item

        # Extract metadata
        title = metadata.get("title", "") or url[:100]
        author = metadata.get("author", "")
        description = metadata.get("description", "")

        # Parse date
        created_at = datetime.utcnow()
        date_str = metadata.get("date")
        if date_str:
            try:
                from dateutil.parser import parse as parse_date
                created_at = parse_date(str(date_str))
            except Exception:
                pass

        # Create content item
        item = ContentItem(
            content_id=content_id,
            content_type=content_type,
            source_type=source_type,
            title=title,
            source_url=url,
            author=author,
            description=description[:500] if description else "",
            created_at=created_at,
            status=ProcessingStatus.COMPLETED,
            extra={
                **(extra or {}),
                "sitename": metadata.get("sitename", ""),
                "word_count": len(content.split()) if content else 0,
                "fetch_method": fetch_method,
                "archived_from": metadata.get("archived_from"),
                "resurrected_from": metadata.get("resurrected_from"),
            },
        )

        # Save to storage (RobustFetcher already saves files, but we still need index)
        if self.use_robust and result.output_dir:
            # RobustFetcher already saved files, just update the index
            self.index_manager.index_item(item, str(result.output_dir), search_text=content)
            item_dir = result.output_dir
        else:
            item_dir = self.file_store.save(item, content=content)
            self.index_manager.index_item(item, str(item_dir), search_text=content)

        logger.info(f"Processed via {fetch_method}: {title[:50]}... ({len(content)} chars)")
        self.stats["processed"] += 1

        # Track by method
        if fetch_method:
            self.stats["by_method"][fetch_method] = self.stats["by_method"].get(fetch_method, 0) + 1

        return item

    def _fetch_robust(self, url: str, content_type: ContentType) -> Optional[FetchResult]:
        """Fetch using RobustFetcher with all fallbacks."""
        return self.fetcher.fetch(url, content_type=content_type.value)

    def process_pending_items(self, limit: int = 50) -> Dict[str, int]:
        """Process items that need fetching (from inbox, etc.)."""
        pending = self.index_manager.list_by_type(
            ContentType.ARTICLE,
            status=ProcessingStatus.PENDING,
            limit=limit
        )

        for item_data in pending:
            url = item_data.get("source_url")
            if url and item_data.get("extra", {}).get("needs_fetch"):
                self.process_url(url, force=True)

        return self.stats

    def get_stats(self) -> Dict[str, int]:
        """Get pipeline statistics."""
        return self.stats.copy()


def run_pipeline():
    """CLI entry point."""
    import argparse
    import logging

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s"
    )

    parser = argparse.ArgumentParser(description="Atlas Content Pipeline")
    parser.add_argument("urls", nargs="*", help="URLs to process")
    parser.add_argument("--pending", action="store_true", help="Process pending items")
    parser.add_argument("--limit", type=int, default=50, help="Limit for pending processing")
    parser.add_argument("--no-robust", action="store_true", help="Disable robust fetcher (use simple HTTP)")
    parser.add_argument("--cookies", type=str, help="Path to browser cookies JSON")
    args = parser.parse_args()

    pipeline = ContentPipeline(
        cookies_path=args.cookies,
        use_robust=not args.no_robust,
    )

    if args.pending:
        stats = pipeline.process_pending_items(limit=args.limit)
    elif args.urls:
        for url in args.urls:
            pipeline.process_url(url)
        stats = pipeline.get_stats()
    else:
        print("Usage: python -m modules.pipeline.content_pipeline [URLs...] [--pending]")
        print("\nOptions:")
        print("  --no-robust  Disable cascading fallbacks (faster but less reliable)")
        print("  --cookies    Path to browser cookies JSON for authenticated fetching")
        print("  --pending    Process pending items from inbox")
        print("  --limit N    Limit number of pending items to process")
        return

    print("\n" + "=" * 50)
    print("PIPELINE COMPLETE")
    print("=" * 50)
    print(f"Processed:     {stats['processed']}")
    print(f"Duplicates:    {stats['skipped_duplicate']}")
    print(f"Non-content:   {stats.get('skipped_non_content', 0)}")
    print(f"Failed:        {stats['failed']}")

    # Show method breakdown
    by_method = stats.get('by_method', {})
    if by_method:
        print("-" * 30)
        print("By fetch method:")
        for method, count in sorted(by_method.items(), key=lambda x: -x[1]):
            print(f"  {method}: {count}")

    print("=" * 50)


if __name__ == "__main__":
    run_pipeline()
