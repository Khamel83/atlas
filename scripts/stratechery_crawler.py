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
BASE_DELAY = 5.0  # 5 seconds between requests
MAX_DELAY = 300.0  # 5 minutes max backoff
DELAY_MULTIPLIER = 2.0

# Output directories
OUTPUT_BASE = Path("data/stratechery")
PODCASTS_DIR = OUTPUT_BASE / "podcasts"
ARTICLES_DIR = OUTPUT_BASE / "articles"
PROGRESS_FILE = OUTPUT_BASE / "crawl_progress.json"


class StrategyCrawler:
    """Crawler for Stratechery content with careful rate limiting"""

    def __init__(self, cookies: Dict[str, str] = None):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Atlas-Stratechery/1.0 (personal archive)",
            "Accept": "text/html,application/xhtml+xml",
        })
        self.cookies = cookies or load_cookies_for_domain("stratechery.com")
        self.current_delay = BASE_DELAY
        self.request_count = 0
        self.crawled_urls: Set[str] = set()
        self.progress = self._load_progress()

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
        """Fetch URL with rate limiting and backoff"""
        if url in self.crawled_urls:
            logger.debug(f"Skipping already crawled: {url}")
            return None

        # Rate limit
        time.sleep(self.current_delay)
        self.request_count += 1

        try:
            response = self.session.get(
                url,
                cookies=self.cookies,
                timeout=30,
                allow_redirects=True
            )
            response.raise_for_status()

            # Success - reset delay
            self.current_delay = BASE_DELAY
            self.crawled_urls.add(url)

            logger.info(f"[{self.request_count}] Fetched: {url[:80]}...")
            return response.text

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 429:
                # Rate limited - back off
                self.current_delay = min(self.current_delay * DELAY_MULTIPLIER, MAX_DELAY)
                logger.warning(f"Rate limited. Backing off to {self.current_delay}s")
                time.sleep(self.current_delay)
                return self._fetch(url)  # Retry
            elif e.response.status_code in (401, 403):
                logger.error(f"Auth error on {url} - cookies may have expired")
                self.progress["failed_urls"].append({"url": url, "error": "auth"})
            else:
                logger.error(f"HTTP {e.response.status_code} for {url}")
                self.progress["failed_urls"].append({"url": url, "error": str(e)})

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
        """Get list of article/podcast URLs from archive pages"""
        urls = []

        # Archive pages to crawl
        archive_pages = []

        if content_type in ("all", "articles"):
            archive_pages.append("https://stratechery.com/category/articles/")
            archive_pages.append("https://stratechery.com/category/daily-email/")

        if content_type in ("all", "podcasts"):
            archive_pages.append("https://stratechery.com/category/podcasts/")
            archive_pages.append("https://stratechery.com/category/sharp-tech/")
            archive_pages.append("https://stratechery.com/category/dithering/")

        for archive_url in archive_pages:
            page = 1
            while True:
                if page == 1:
                    url = archive_url
                else:
                    url = f"{archive_url}page/{page}/"

                html = self._fetch(url)
                if not html:
                    break

                soup = BeautifulSoup(html, "html.parser")

                # Find article links
                article_links = soup.select("article a[href*='stratechery.com/20'], h2 a[href*='stratechery.com/20']")
                if not article_links:
                    break

                for link in article_links:
                    href = link.get("href", "")
                    if href and "stratechery.com/20" in href:
                        # Filter by date if specified
                        if since:
                            # Extract year from URL (e.g., stratechery.com/2024/...)
                            match = re.search(r"/(\d{4})/", href)
                            if match:
                                year = int(match.group(1))
                                since_year = int(since[:4])
                                if year < since_year:
                                    continue

                        if href not in urls:
                            urls.append(href)

                logger.info(f"Found {len(urls)} URLs from {url}")

                # Check for next page
                next_page = soup.select_one("a.next, .nav-next a, a[rel='next']")
                if not next_page:
                    break
                page += 1

                # Extra delay between archive pages
                time.sleep(2)

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
