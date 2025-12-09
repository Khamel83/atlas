"""
Robust Content Fetcher - "Never Fail" URL → Content System

This module provides a comprehensive content fetching system with cascading fallbacks:
1. Direct fetch (Trafilatura) - Fast, works for most sites
2. Fetch with browser cookies - For sites requiring login
3. Headless browser (Playwright) - For JS-rendered/paywall content
4. Archive.is lookup - For paywalled content
5. Wayback Machine lookup - For deleted/archived content
6. URL Resurrection - Parse slug, search for alternative sources

Output Format:
- metadata.json: Title, URL, dates, fetch method, status
- content.md: Clean markdown (searchable)
- article.html: Readability-cleaned HTML with images
- raw.html: Original HTML (backup)
- images/: Downloaded images with local references

Usage:
    from modules.ingest.robust_fetcher import RobustFetcher

    fetcher = RobustFetcher()
    result = fetcher.fetch("https://example.com/article")

    if result.success:
        print(f"Fetched via {result.method}: {result.title}")
        print(f"Content saved to: {result.output_dir}")
    else:
        print(f"Failed: {result.error}")
"""

import hashlib
import json
import logging
import os
import re
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
from urllib.parse import urlparse, urljoin, quote_plus

import requests
from bs4 import BeautifulSoup
import html2text
import trafilatura
from readability import Document

logger = logging.getLogger(__name__)

# Optional imports - gracefully handle missing dependencies
try:
    import waybackpy
    WAYBACK_AVAILABLE = True
except ImportError:
    WAYBACK_AVAILABLE = False
    logger.warning("waybackpy not installed - Wayback Machine fallback disabled")

try:
    from playwright.sync_api import sync_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    logger.warning("playwright not installed - headless browser fallback disabled")


@dataclass
class FetchResult:
    """Result of a content fetch operation."""
    success: bool
    url: str
    title: Optional[str] = None
    method: Optional[str] = None  # direct, cookies, playwright, archive_is, wayback, resurrected
    content_md: Optional[str] = None
    content_html: Optional[str] = None
    raw_html: Optional[str] = None
    images: List[Dict[str, str]] = field(default_factory=list)  # [{"url": ..., "local_path": ...}]
    metadata: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    attempts: List[Dict[str, Any]] = field(default_factory=list)  # Log of all attempts
    output_dir: Optional[Path] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "url": self.url,
            "title": self.title,
            "method": self.method,
            "error": self.error,
            "attempts": self.attempts,
            "metadata": self.metadata,
            "image_count": len(self.images),
        }


class RateLimiter:
    """Rate limiter for courteous web requests."""

    def __init__(self, min_delay: float = 1.0, max_delay: float = 2.0):
        self.min_delay = min_delay
        self.max_delay = max_delay
        self.last_request: Dict[str, float] = {}

    def wait(self, domain: str):
        """Wait appropriate time before next request to domain."""
        import random
        last = self.last_request.get(domain, 0)
        elapsed = time.time() - last
        delay = random.uniform(self.min_delay, self.max_delay)

        if elapsed < delay:
            time.sleep(delay - elapsed)

        self.last_request[domain] = time.time()


class ImageDownloader:
    """Downloads and stores images locally."""

    def __init__(self, session: requests.Session, output_dir: Path):
        self.session = session
        self.output_dir = output_dir
        self.images_dir = output_dir / "images"

    def download_images(self, html: str, base_url: str) -> Tuple[str, List[Dict[str, str]]]:
        """
        Download all images from HTML and update references.

        Returns:
            Tuple of (updated_html, list of image info dicts)
        """
        self.images_dir.mkdir(parents=True, exist_ok=True)

        soup = BeautifulSoup(html, 'lxml')
        images = []
        img_counter = 0

        for img in soup.find_all('img'):
            src = img.get('src') or img.get('data-src')
            if not src:
                continue

            # Resolve relative URLs
            if not src.startswith(('http://', 'https://', 'data:')):
                src = urljoin(base_url, src)

            # Skip data URIs
            if src.startswith('data:'):
                continue

            # Download image
            try:
                img_counter += 1
                ext = self._get_extension(src)
                local_filename = f"img_{img_counter:03d}{ext}"
                local_path = self.images_dir / local_filename

                response = self.session.get(src, timeout=15, stream=True)
                response.raise_for_status()

                with open(local_path, 'wb') as f:
                    for chunk in response.iter_content(8192):
                        f.write(chunk)

                # Update HTML reference
                img['src'] = f"images/{local_filename}"

                images.append({
                    "original_url": src,
                    "local_path": str(local_path),
                    "filename": local_filename,
                })

                logger.debug(f"Downloaded image: {src} -> {local_filename}")

            except Exception as e:
                logger.warning(f"Failed to download image {src}: {e}")
                continue

        return str(soup), images

    def _get_extension(self, url: str) -> str:
        """Extract file extension from URL."""
        path = urlparse(url).path.lower()
        for ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg']:
            if ext in path:
                return ext
        return '.jpg'  # Default


class ArchiveFetcher:
    """Fetch content from archive services (archive.is, Wayback Machine)."""

    def __init__(self, session: requests.Session, rate_limiter: RateLimiter):
        self.session = session
        self.rate_limiter = rate_limiter

    def fetch_archive_is(self, url: str) -> Optional[str]:
        """
        Fetch content from archive.is (archive.today).

        Archive.is is great for bypassing paywalls as it stores the full page.
        """
        self.rate_limiter.wait("archive.is")

        # Try to find existing archive
        search_url = f"https://archive.is/{url}"

        try:
            response = self.session.get(search_url, timeout=30, allow_redirects=True)

            # If we got redirected to an archive page
            if response.status_code == 200 and 'archive.is' in response.url:
                logger.info(f"Found archive.is version: {response.url}")
                return response.text

            # Try alternate format
            search_url2 = f"https://archive.today/{url}"
            response = self.session.get(search_url2, timeout=30, allow_redirects=True)
            if response.status_code == 200:
                return response.text

        except Exception as e:
            logger.debug(f"archive.is lookup failed: {e}")

        return None

    def fetch_wayback(self, url: str) -> Optional[str]:
        """
        Fetch content from Wayback Machine.

        Wayback stores historical snapshots of pages.
        """
        if not WAYBACK_AVAILABLE:
            return None

        self.rate_limiter.wait("web.archive.org")

        try:
            wayback = waybackpy.Url(url)

            # Try to get the newest archive
            try:
                archive = wayback.newest()
                logger.info(f"Found Wayback archive from {archive.timestamp}: {archive.archive_url}")

                response = self.session.get(archive.archive_url, timeout=30)
                if response.status_code == 200:
                    return response.text
            except waybackpy.exceptions.NoCDXRecordFound:
                logger.debug(f"No Wayback archive found for: {url}")

        except Exception as e:
            logger.debug(f"Wayback lookup failed: {e}")

        return None


class PlaywrightFetcher:
    """Fetch content using headless browser for JS-rendered pages."""

    def __init__(self, cookies_path: Optional[Path] = None):
        self.cookies_path = cookies_path

    def fetch(self, url: str, wait_time: int = 3000) -> Optional[str]:
        """
        Fetch page using Playwright headless browser.

        Args:
            url: URL to fetch
            wait_time: Time to wait for JS to render (ms)

        Returns:
            HTML content or None
        """
        if not PLAYWRIGHT_AVAILABLE:
            logger.warning("Playwright not available")
            return None

        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                context = browser.new_context(
                    user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                              "AppleWebKit/537.36 (KHTML, like Gecko) "
                              "Chrome/120.0.0.0 Safari/537.36"
                )

                # Load cookies if available
                if self.cookies_path and self.cookies_path.exists():
                    self._load_cookies(context)

                page = context.new_page()
                page.goto(url, wait_until="networkidle", timeout=30000)

                # Wait for content to render
                page.wait_for_timeout(wait_time)

                html = page.content()
                browser.close()

                logger.info(f"Fetched via Playwright: {url}")
                return html

        except Exception as e:
            logger.error(f"Playwright fetch failed: {e}")
            return None

    def _load_cookies(self, context):
        """Load cookies from file into browser context."""
        try:
            with open(self.cookies_path, 'r') as f:
                cookies = json.load(f)
                context.add_cookies(cookies)
                logger.debug(f"Loaded {len(cookies)} cookies")
        except Exception as e:
            logger.warning(f"Failed to load cookies: {e}")


class URLResurrector:
    """Resurrect dead URLs by finding archived/alternative versions."""

    def __init__(self, session: requests.Session, rate_limiter: RateLimiter):
        self.session = session
        self.rate_limiter = rate_limiter

    def resurrect(self, url: str) -> Optional[Tuple[str, str]]:
        """
        Try to find content for a dead URL.

        Strategy:
        1. Parse URL to extract keywords
        2. Search Wayback Machine CDX API
        3. Search Google for the title

        Returns:
            Tuple of (archive_url, html) or None
        """
        keywords = self._extract_keywords(url)
        if not keywords:
            return None

        logger.info(f"Resurrecting URL with keywords: {keywords}")

        # Try Wayback CDX search
        result = self._search_wayback_cdx(url)
        if result:
            return result

        # Could add Google search here in the future
        # For now, return None if CDX search fails

        return None

    def _extract_keywords(self, url: str) -> Optional[str]:
        """
        Extract searchable keywords from URL.

        Examples:
        - example.com/2023/05/tech-layoffs-analysis -> "tech layoffs analysis"
        - nytimes.com/article/climate-change-report -> "climate change report"
        """
        parsed = urlparse(url)
        path = parsed.path

        # Remove common path components
        path = re.sub(r'/\d{4}/\d{2}/\d{2}/', ' ', path)  # dates
        path = re.sub(r'/\d{4}/\d{2}/', ' ', path)
        path = re.sub(r'/article/', ' ', path)
        path = re.sub(r'/story/', ' ', path)
        path = re.sub(r'/news/', ' ', path)

        # Get the slug
        slug = path.rstrip('/').split('/')[-1]

        # Convert slug to words
        slug = re.sub(r'[-_]', ' ', slug)
        slug = re.sub(r'\.html?$', '', slug)

        # Clean up
        words = slug.split()
        words = [w for w in words if len(w) > 2 and not w.isdigit()]

        if words:
            # Add domain for context
            domain = parsed.netloc.replace('www.', '').split('.')[0]
            return f"{' '.join(words)} {domain}"

        return None

    def _search_wayback_cdx(self, url: str) -> Optional[Tuple[str, str]]:
        """Search Wayback CDX API for any archived versions."""
        if not WAYBACK_AVAILABLE:
            return None

        self.rate_limiter.wait("web.archive.org")

        try:
            cdx_url = f"https://web.archive.org/cdx/search/cdx?url={quote_plus(url)}&output=json&limit=5"
            response = self.session.get(cdx_url, timeout=15)

            if response.status_code == 200:
                data = response.json()
                if len(data) > 1:  # First row is headers
                    # Get most recent snapshot
                    row = data[-1]
                    timestamp = row[1]
                    archive_url = f"https://web.archive.org/web/{timestamp}/{url}"

                    # Fetch the archived page
                    html_response = self.session.get(archive_url, timeout=30)
                    if html_response.status_code == 200:
                        return (archive_url, html_response.text)

        except Exception as e:
            logger.debug(f"CDX search failed: {e}")

        return None


class RobustFetcher:
    """
    Main robust content fetcher with cascading fallbacks.

    Fetching order:
    1. Direct fetch (trafilatura)
    2. Direct fetch with cookies
    3. Playwright (headless browser)
    4. Archive.is
    5. Wayback Machine
    6. URL Resurrection

    Storage format:
    - metadata.json
    - content.md
    - article.html
    - raw.html
    - images/
    """

    def __init__(
        self,
        output_base: Path = Path("data/content"),
        cookies_path: Optional[Path] = None,
        download_images: bool = True,
    ):
        self.output_base = Path(output_base)
        self.cookies_path = cookies_path
        self.download_images = download_images

        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) "
                          "Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        })

        # Load cookies if path provided
        if cookies_path and cookies_path.exists():
            self._load_request_cookies(cookies_path)

        self.rate_limiter = RateLimiter()
        self.archive_fetcher = ArchiveFetcher(self.session, self.rate_limiter)
        self.playwright_fetcher = PlaywrightFetcher(cookies_path)
        self.resurrector = URLResurrector(self.session, self.rate_limiter)

        self.html2text = html2text.HTML2Text()
        self.html2text.ignore_links = False
        self.html2text.ignore_images = False
        self.html2text.body_width = 0

    def _load_request_cookies(self, cookies_path: Path):
        """Load cookies into requests session."""
        try:
            with open(cookies_path, 'r') as f:
                cookies = json.load(f)
                for cookie in cookies:
                    self.session.cookies.set(
                        cookie.get('name'),
                        cookie.get('value'),
                        domain=cookie.get('domain', ''),
                    )
                logger.info(f"Loaded {len(cookies)} cookies for requests")
        except Exception as e:
            logger.warning(f"Failed to load cookies: {e}")

    def fetch(self, url: str, content_type: str = "article") -> FetchResult:
        """
        Fetch content from URL using all available strategies.

        Args:
            url: URL to fetch
            content_type: Type of content (article, newsletter, etc.)

        Returns:
            FetchResult with content and metadata
        """
        result = FetchResult(success=False, url=url)
        domain = urlparse(url).netloc

        # Strategy 1: Direct fetch with trafilatura
        logger.info(f"Attempting direct fetch: {url}")
        self.rate_limiter.wait(domain)
        html = self._direct_fetch(url)

        if html:
            content_md, content_html, meta = self._extract_content(html, url)
            if content_md and len(content_md) > 500:
                result.success = True
                result.method = "direct"
                result.raw_html = html
                result.content_md = content_md
                result.content_html = content_html
                result.title = meta.get('title')
                result.metadata = meta
                result.attempts.append({"method": "direct", "success": True})
                return self._finalize_result(result, url, content_type)

        result.attempts.append({"method": "direct", "success": False, "error": "No content or blocked"})

        # Strategy 2: Playwright (headless browser)
        if PLAYWRIGHT_AVAILABLE:
            logger.info(f"Attempting Playwright fetch: {url}")
            html = self.playwright_fetcher.fetch(url)

            if html:
                content_md, content_html, meta = self._extract_content(html, url)
                if content_md and len(content_md) > 500:
                    result.success = True
                    result.method = "playwright"
                    result.raw_html = html
                    result.content_md = content_md
                    result.content_html = content_html
                    result.title = meta.get('title')
                    result.metadata = meta
                    result.attempts.append({"method": "playwright", "success": True})
                    return self._finalize_result(result, url, content_type)

            result.attempts.append({"method": "playwright", "success": False})

        # Strategy 3: Archive.is
        logger.info(f"Attempting archive.is lookup: {url}")
        html = self.archive_fetcher.fetch_archive_is(url)

        if html:
            content_md, content_html, meta = self._extract_content(html, url)
            if content_md and len(content_md) > 500:
                result.success = True
                result.method = "archive_is"
                result.raw_html = html
                result.content_md = content_md
                result.content_html = content_html
                result.title = meta.get('title')
                result.metadata = meta
                result.metadata['archived_from'] = 'archive.is'
                result.attempts.append({"method": "archive_is", "success": True})
                return self._finalize_result(result, url, content_type)

        result.attempts.append({"method": "archive_is", "success": False})

        # Strategy 4: Wayback Machine
        logger.info(f"Attempting Wayback lookup: {url}")
        html = self.archive_fetcher.fetch_wayback(url)

        if html:
            content_md, content_html, meta = self._extract_content(html, url)
            if content_md and len(content_md) > 500:
                result.success = True
                result.method = "wayback"
                result.raw_html = html
                result.content_md = content_md
                result.content_html = content_html
                result.title = meta.get('title')
                result.metadata = meta
                result.metadata['archived_from'] = 'wayback'
                result.attempts.append({"method": "wayback", "success": True})
                return self._finalize_result(result, url, content_type)

        result.attempts.append({"method": "wayback", "success": False})

        # Strategy 5: URL Resurrection
        logger.info(f"Attempting URL resurrection: {url}")
        resurrection_result = self.resurrector.resurrect(url)

        if resurrection_result:
            archive_url, html = resurrection_result
            content_md, content_html, meta = self._extract_content(html, url)
            if content_md and len(content_md) > 200:
                result.success = True
                result.method = "resurrected"
                result.raw_html = html
                result.content_md = content_md
                result.content_html = content_html
                result.title = meta.get('title')
                result.metadata = meta
                result.metadata['resurrected_from'] = archive_url
                result.attempts.append({"method": "resurrected", "success": True, "source": archive_url})
                return self._finalize_result(result, url, content_type)

        result.attempts.append({"method": "resurrected", "success": False})

        # All strategies failed
        result.error = f"All {len(result.attempts)} fetch strategies failed"
        logger.warning(f"Failed to fetch {url} after all attempts")

        return result

    def _direct_fetch(self, url: str) -> Optional[str]:
        """Direct HTTP fetch."""
        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            return response.text
        except requests.exceptions.HTTPError as e:
            logger.debug(f"HTTP error: {e}")
        except Exception as e:
            logger.debug(f"Fetch error: {e}")
        return None

    def _extract_content(self, html: str, url: str) -> Tuple[Optional[str], Optional[str], Dict[str, Any]]:
        """
        Extract clean content from HTML.

        Returns:
            Tuple of (markdown, clean_html, metadata)
        """
        metadata = {}

        # Use trafilatura for extraction (best quality)
        extracted_md = trafilatura.extract(
            html,
            include_links=True,
            include_images=True,
            include_comments=False,
            output_format="markdown"
        )

        # Get metadata
        traf_meta = trafilatura.extract_metadata(html)
        if traf_meta:
            metadata = {
                'title': traf_meta.title,
                'author': traf_meta.author,
                'description': traf_meta.description,
                'sitename': traf_meta.sitename,
                'date': str(traf_meta.date) if traf_meta.date else None,
            }

        # Use readability for clean HTML
        try:
            doc = Document(html)
            clean_html = doc.summary()
            if not metadata.get('title'):
                metadata['title'] = doc.title()
        except Exception:
            clean_html = None

        # Fallback to html2text if trafilatura fails
        if not extracted_md and clean_html:
            extracted_md = self.html2text.handle(clean_html)

        return extracted_md, clean_html, metadata

    def _finalize_result(self, result: FetchResult, url: str, content_type: str) -> FetchResult:
        """Finalize result: download images, save files."""
        # Generate content ID
        content_id = hashlib.sha256(url.encode()).hexdigest()[:16]

        # Create output directory
        date_path = datetime.now().strftime("%Y/%m/%d")
        output_dir = self.output_base / content_type / date_path / content_id
        output_dir.mkdir(parents=True, exist_ok=True)
        result.output_dir = output_dir

        # Download images if enabled
        if self.download_images and result.content_html:
            downloader = ImageDownloader(self.session, output_dir)
            updated_html, images = downloader.download_images(result.content_html, url)
            result.content_html = updated_html
            result.images = images

        # Save files
        self._save_files(result)

        return result

    def _save_files(self, result: FetchResult):
        """Save all content files."""
        if not result.output_dir:
            return

        # Save raw HTML
        if result.raw_html:
            raw_path = result.output_dir / "raw.html"
            with open(raw_path, 'w', encoding='utf-8') as f:
                f.write(result.raw_html)

        # Save clean HTML
        if result.content_html:
            html_path = result.output_dir / "article.html"
            with open(html_path, 'w', encoding='utf-8') as f:
                f.write(result.content_html)

        # Save markdown
        if result.content_md:
            md_path = result.output_dir / "content.md"
            with open(md_path, 'w', encoding='utf-8') as f:
                f.write(result.content_md)

        # Save metadata
        meta = {
            "url": result.url,
            "title": result.title,
            "method": result.method,
            "fetched_at": datetime.now().isoformat(),
            "success": result.success,
            "attempts": result.attempts,
            "image_count": len(result.images),
            **result.metadata,
        }

        meta_path = result.output_dir / "metadata.json"
        with open(meta_path, 'w', encoding='utf-8') as f:
            json.dump(meta, f, indent=2)

        logger.info(f"Saved content to: {result.output_dir}")


# Convenience function for CLI usage
def fetch_url(url: str, output_base: str = "data/content", cookies_path: str = None) -> FetchResult:
    """
    Fetch a URL using the robust fetcher.

    Args:
        url: URL to fetch
        output_base: Base directory for output
        cookies_path: Optional path to cookies JSON file

    Returns:
        FetchResult with content and metadata
    """
    fetcher = RobustFetcher(
        output_base=Path(output_base),
        cookies_path=Path(cookies_path) if cookies_path else None,
    )
    return fetcher.fetch(url)


if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.INFO)

    if len(sys.argv) < 2:
        print("Usage: python -m modules.ingest.robust_fetcher <url>")
        print("Example: python -m modules.ingest.robust_fetcher https://example.com/article")
        sys.exit(1)

    url = sys.argv[1]
    result = fetch_url(url)

    print(f"\n{'='*60}")
    print(f"URL: {result.url}")
    print(f"Success: {result.success}")
    print(f"Method: {result.method}")
    print(f"Title: {result.title}")
    print(f"Images: {len(result.images)}")
    print(f"Output: {result.output_dir}")
    print(f"Attempts: {len(result.attempts)}")

    if result.error:
        print(f"Error: {result.error}")

    for i, attempt in enumerate(result.attempts):
        status = "✅" if attempt.get("success") else "❌"
        print(f"  {i+1}. {attempt['method']}: {status}")

    print(f"{'='*60}\n")
