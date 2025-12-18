#!/usr/bin/env python3
"""
Stratechery Full Archive Crawler

Crawls the entire Stratechery archive (podcasts + articles) with careful rate limiting.
Uses authenticated session to access subscriber content.

Rate limiting strategy:
- 5 second delay between requests (very conservative)
- Exponential backoff on errors
- Saves progress so can resume

Content types:
- Daily Updates (articles)
- Weekly Articles
- Podcasts (Sharp Tech, Dithering excerpts)
- Interviews

Usage:
    python scripts/stratechery_crawler.py --type all --limit 100
    python scripts/stratechery_crawler.py --type podcasts --resume
    python scripts/stratechery_crawler.py --type articles --since 2024-01-01
"""

import argparse
import asyncio
import json
import logging
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from modules.podcasts.resolvers.generic_html import load_cookies_for_domain

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Rate limiting - VERY conservative for Stratechery
import random
BASE_DELAY = 6.0  # Base delay
MAX_DELAY = 300.0  # 5 minutes max backoff
DELAY_MULTIPLIER = 2.0
DELAY_JITTER = 0.5  # +/- 50% randomization

# Output directories
OUTPUT_BASE = Path("data/stratechery")
PODCASTS_DIR = OUTPUT_BASE / "podcasts"
ARTICLES_DIR = OUTPUT_BASE / "articles"
PROGRESS_FILE = OUTPUT_BASE / "crawl_progress.json"


class StrategyCrawler:
    """Crawler for Stratechery content with careful rate limiting.

    Uses Playwright for browser-based fetching to handle OAuth redirects properly.
    """

    def __init__(self, cookies: Dict[str, str] = None):
        self.cookies = cookies or load_cookies_for_domain("stratechery.com")
        self.current_delay = BASE_DELAY
        self.request_count = 0
        self.crawled_urls: Set[str] = set()
        self.progress = self._load_progress()
        self.browser = None
        self.page = None

    def _init_browser(self):
        """Initialize Playwright browser with cookies"""
        if self.browser:
            return

        from playwright.sync_api import sync_playwright
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(headless=True)
        self.context = self.browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        )

        # Load cookies into browser context
        cookie_list = []
        for name, value in self.cookies.items():
            cookie_list.append({
                "name": name,
                "value": value,
                "domain": "stratechery.com",
                "path": "/"
            })
        self.context.add_cookies(cookie_list)
        self.page = self.context.new_page()
        logger.info("Playwright browser initialized with cookies")

    def _close_browser(self):
        """Close Playwright browser"""
        if self.browser:
            self.browser.close()
            self.playwright.stop()
            self.browser = None

    def _load_progress(self) -> Dict:
        """Load crawl progress from disk"""
        if PROGRESS_FILE.exists():
            try:
                with open(PROGRESS_FILE) as f:
                    return json.load(f)
            except:
                pass
        return {
            "crawled_urls": [],
            "failed_urls": [],
            "last_run": None,
            "stats": {"articles": 0, "podcasts": 0, "errors": 0}
        }

    def _save_progress(self):
        """Save crawl progress to disk"""
        PROGRESS_FILE.parent.mkdir(parents=True, exist_ok=True)
        self.progress["last_run"] = datetime.now().isoformat()
        self.progress["crawled_urls"] = list(self.crawled_urls)
        with open(PROGRESS_FILE, "w") as f:
            json.dump(self.progress, f, indent=2)

    def _fetch(self, url: str) -> Optional[str]:
        """Fetch URL with Playwright browser (handles OAuth redirects)"""
        if url in self.crawled_urls:
            logger.debug(f"Skipping already crawled: {url}")
            return None

        # Initialize browser on first fetch
        self._init_browser()

        # Rate limit with random jitter (looks more human)
        jitter = random.uniform(1 - DELAY_JITTER, 1 + DELAY_JITTER)
        delay = self.current_delay * jitter
        time.sleep(delay)
        self.request_count += 1

        try:
            self.page.goto(url, wait_until="networkidle", timeout=60000)

            # Check if we got redirected to login
            if "passport" in self.page.url and "login" in self.page.url:
                logger.error(f"Redirected to login - cookies expired")
                self.progress["failed_urls"].append({"url": url, "error": "auth"})
                return None

            html = self.page.content()

            # Success - reset delay
            self.current_delay = BASE_DELAY
            self.crawled_urls.add(url)

            logger.info(f"[{self.request_count}] Fetched: {url[:80]}...")
            return html

        except Exception as e:
            logger.error(f"Error fetching {url}: {e}")
            self.progress["failed_urls"].append({"url": url, "error": str(e)})
            self.progress["stats"]["errors"] += 1

        return None

    def _extract_article_content(self, html: str, url: str) -> Dict:
        """Extract article content from HTML"""
        soup = BeautifulSoup(html, "html.parser")

        # Get title
        title_el = soup.select_one("h1.post-title, h1.entry-title, article h1")
        title = title_el.get_text(strip=True) if title_el else "Untitled"

        # Get date
        date_el = soup.select_one("time, .post-date, .entry-date")
        date_str = date_el.get("datetime", "") if date_el else ""
        if not date_str and date_el:
            date_str = date_el.get_text(strip=True)

        # Get content
        content_el = soup.select_one(".post-content, .entry-content, article")
        content = ""
        if content_el:
            # Remove scripts, styles, etc
            for tag in content_el.select("script, style, nav, .share-buttons"):
                tag.decompose()
            content = content_el.get_text(separator="\n", strip=True)

        # Check for audio (podcast)
        is_podcast = bool(soup.select("audio, .podcast-player, iframe[src*='player']"))

        # Get category
        category_el = soup.select_one(".category, .post-category a")
        category = category_el.get_text(strip=True) if category_el else "article"

        return {
            "url": url,
            "title": title,
            "date": date_str,
            "content": content,
            "is_podcast": is_podcast,
            "category": category,
            "word_count": len(content.split()),
            "crawled_at": datetime.now().isoformat()
        }

    def _save_content(self, data: Dict, content_type: str):
        """Save content to disk"""
        if content_type == "podcast":
            output_dir = PODCASTS_DIR
        else:
            output_dir = ARTICLES_DIR

        output_dir.mkdir(parents=True, exist_ok=True)

        # Create filename from date and title
        date_prefix = data.get("date", "")[:10] or datetime.now().strftime("%Y-%m-%d")
        title_slug = re.sub(r"[^\w\s-]", "", data["title"].lower())
        title_slug = re.sub(r"[\s_]+", "-", title_slug)[:60]
        filename = f"{date_prefix}_{title_slug}.md"

        filepath = output_dir / filename

        # Write markdown
        md_content = f"""# {data['title']}

**URL:** {data['url']}
**Date:** {data['date']}
**Category:** {data['category']}
**Word Count:** {data['word_count']}

---

{data['content']}
"""

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(md_content)

        logger.info(f"Saved: {filepath}")
        return filepath

    def get_archive_urls(self, content_type: str = "all", since: str = None) -> List[str]:
        """Get list of article/podcast URLs from year-based archive pages.

        Stratechery uses year-based archives like /2024/, /2023/, etc. with pagination.
        This is more reliable than category pages which have inconsistent pagination.
        """
        urls = []
        seen_urls = set()

        # Determine year range
        current_year = datetime.now().year
        start_year = 2013  # Stratechery started in 2013

        if since:
            start_year = max(start_year, int(since[:4]))

        # Crawl each year from most recent to oldest
        for year in range(current_year, start_year - 1, -1):
            page = 1
            consecutive_empty = 0

            while True:
                if page == 1:
                    url = f"https://stratechery.com/{year}/"
                else:
                    url = f"https://stratechery.com/{year}/page/{page}/"

                html = self._fetch(url)
                if not html:
                    # 404 or error - move to next year
                    break

                soup = BeautifulSoup(html, "html.parser")

                # Find all article links on the page
                # Look for links in article titles, entry titles, post titles
                found_on_page = 0
                for link in soup.find_all("a", href=True):
                    href = link.get("href", "")
                    # Match article URLs like stratechery.com/2024/article-slug/
                    if re.match(rf"https?://stratechery\.com/{year}/[a-z0-9-]+/?$", href):
                        # Skip category/tag/page URLs
                        if any(x in href for x in ["/category/", "/tag/", "/page/", "/author/"]):
                            continue
                        if href not in seen_urls:
                            seen_urls.add(href)
                            urls.append(href)
                            found_on_page += 1

                logger.info(f"Found {found_on_page} new URLs from {url} (total: {len(urls)})")

                if found_on_page == 0:
                    consecutive_empty += 1
                    if consecutive_empty >= 2:
                        # Two empty pages in a row - done with this year
                        break
                else:
                    consecutive_empty = 0

                # Check for next page link
                next_link = soup.select_one("a.next, .nav-next a, a[rel='next'], .pagination a.next")
                if not next_link:
                    # No explicit next link - try a few more pages anyway
                    if page < 3 or found_on_page > 0:
                        page += 1
                        time.sleep(2)
                        continue
                    break

                page += 1

                # Extra delay between archive pages
                time.sleep(2)

                # Safety limit per year
                if page > 100:
                    logger.warning(f"Hit page limit for year {year}")
                    break

            logger.info(f"Year {year} complete: {len(urls)} total URLs so far")

        return urls

    def crawl(self, content_type: str = "all", limit: int = None, since: str = None, resume: bool = True):
        """Main crawl function"""
        logger.info(f"Starting Stratechery crawl: type={content_type}, limit={limit}, since={since}")

        # Load previously crawled URLs
        if resume:
            self.crawled_urls = set(self.progress.get("crawled_urls", []))
            logger.info(f"Resuming with {len(self.crawled_urls)} already crawled")

        # Get URLs to crawl
        urls = self.get_archive_urls(content_type, since)
        logger.info(f"Found {len(urls)} total URLs to process")

        # Filter out already crawled
        urls = [u for u in urls if u not in self.crawled_urls]
        logger.info(f"{len(urls)} URLs remaining after filtering")

        if limit:
            urls = urls[:limit]

        # Crawl each URL
        for i, url in enumerate(urls):
            logger.info(f"Processing {i+1}/{len(urls)}: {url}")

            html = self._fetch(url)
            if not html:
                continue

            # Extract content
            data = self._extract_article_content(html, url)

            # Determine type and save
            if data["is_podcast"]:
                self._save_content(data, "podcast")
                self.progress["stats"]["podcasts"] += 1
            else:
                self._save_content(data, "article")
                self.progress["stats"]["articles"] += 1

            # Save progress periodically
            if i % 10 == 0:
                self._save_progress()

        # Final save
        self._save_progress()

        logger.info(f"""
Crawl complete!
  Articles: {self.progress['stats']['articles']}
  Podcasts: {self.progress['stats']['podcasts']}
  Errors: {self.progress['stats']['errors']}
  Total crawled: {len(self.crawled_urls)}
""")


def main():
    parser = argparse.ArgumentParser(description="Crawl Stratechery archive")
    parser.add_argument("--type", choices=["all", "articles", "podcasts"], default="all",
                        help="Content type to crawl")
    parser.add_argument("--limit", type=int, help="Maximum URLs to crawl")
    parser.add_argument("--since", help="Only crawl content since date (YYYY-MM-DD)")
    parser.add_argument("--resume", action="store_true", default=True,
                        help="Resume from previous crawl")
    parser.add_argument("--no-resume", action="store_true",
                        help="Start fresh crawl")
    parser.add_argument("--delay", type=float, default=5.0,
                        help="Delay between requests in seconds")

    args = parser.parse_args()

    global BASE_DELAY
    BASE_DELAY = args.delay

    crawler = StrategyCrawler()

    if args.no_resume:
        crawler.crawled_urls = set()
        crawler.progress = {"crawled_urls": [], "failed_urls": [], "stats": {"articles": 0, "podcasts": 0, "errors": 0}}

    try:
        crawler.crawl(
            content_type=args.type,
            limit=args.limit,
            since=args.since,
            resume=not args.no_resume
        )
    except KeyboardInterrupt:
        logger.info("Interrupted - saving progress...")
        crawler._save_progress()


if __name__ == "__main__":
    main()
