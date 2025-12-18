#!/usr/bin/env python3
"""
Crawl Asianometry - Fetch transcripts using authentication cookies.

Uses cookies from ~/.config/atlas/cookies/asianometry.passport.online.json
Saves transcripts to data/asianometry/

Features:
- Cookie-based authentication for paywalled content
- Generates manifest first (all URLs pre-computed)
- Rate limited (5 second delay between fetches)
- Fully resumable (atomic saves after each fetch)

Usage:
    python scripts/crawl_asianometry.py --generate-manifest
    python scripts/crawl_asianometry.py --execute
    python scripts/crawl_asianometry.py --execute --limit 50
    python scripts/crawl_asianometry.py --status
"""

import argparse
import hashlib
import json
import logging
import os
import re
import sys
import time
from datetime import datetime
from http.cookiejar import CookieJar
from pathlib import Path
from typing import Dict, List, Any, Optional
from urllib.parse import urlparse, urljoin

import requests
from bs4 import BeautifulSoup

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Paths
ATLAS_ROOT = Path(__file__).parent.parent
MANIFEST_FILE = ATLAS_ROOT / "data/manifests/asianometry_tasks.json"
OUTPUT_DIR = ATLAS_ROOT / "data/asianometry"
COOKIES_FILE = Path(os.path.expanduser("~/.config/atlas/cookies/asianometry.passport.online.json"))

# Rate limiting
DELAY_BETWEEN_FETCHES = 5  # seconds

# Base URL
BASE_URL = "https://asianometry.passport.online"
MAIN_SITE = "https://asianometry.com"

# User agent
USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"


def load_cookies() -> Dict[str, str]:
    """Load cookies from JSON file."""
    if not COOKIES_FILE.exists():
        logger.error(f"Cookie file not found: {COOKIES_FILE}")
        return {}

    with open(COOKIES_FILE) as f:
        cookies_list = json.load(f)

    # Convert list format to dict for requests
    cookies = {}
    for cookie in cookies_list:
        cookies[cookie['name']] = cookie['value']

    return cookies


def load_manifest(path: Path) -> List[Dict[str, Any]]:
    """Load manifest from file."""
    if not path.exists():
        return []
    with open(path) as f:
        return json.load(f)


def save_manifest(manifest: List[Dict[str, Any]], path: Path):
    """Save manifest to file (atomic write)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_suffix('.tmp')
    with open(temp_path, 'w') as f:
        json.dump(manifest, f, indent=2)
    temp_path.rename(path)


def get_session_with_cookies() -> requests.Session:
    """Create a session with authentication cookies."""
    session = requests.Session()
    cookies = load_cookies()

    for name, value in cookies.items():
        session.cookies.set(name, value, domain='.asianometry.passport.online')

    session.headers.update({
        'User-Agent': USER_AGENT,
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
    })

    return session


def discover_articles(session: requests.Session) -> List[Dict[str, Any]]:
    """Discover all article URLs from the site."""
    articles = []
    task_id = 0

    # Try multiple discovery methods
    urls_to_try = [
        f"{BASE_URL}/",
        f"{BASE_URL}/posts",
        f"{BASE_URL}/archive",
        f"{MAIN_SITE}/",
        f"{MAIN_SITE}/archive",
    ]

    seen_urls = set()

    for url in urls_to_try:
        logger.info(f"Trying: {url}")
        try:
            response = session.get(url, timeout=30)
            if response.status_code != 200:
                logger.warning(f"  Status {response.status_code}")
                continue

            soup = BeautifulSoup(response.text, 'html.parser')

            # Find all article links
            for link in soup.find_all('a', href=True):
                href = link['href']

                # Normalize URL
                if href.startswith('/'):
                    full_url = urljoin(url, href)
                elif href.startswith('http'):
                    full_url = href
                else:
                    continue

                # Skip non-article URLs
                if any(skip in full_url for skip in ['/tag/', '/author/', '/login', '/subscribe', '#', '?']):
                    continue

                # Check if it looks like an article
                parsed = urlparse(full_url)

                # Asianometry articles might be at /p/slug or /posts/slug
                if '/p/' in parsed.path or '/posts/' in parsed.path or re.search(r'/\d{4}/', parsed.path):
                    if full_url not in seen_urls:
                        seen_urls.add(full_url)

                        title = link.get_text(strip=True) or parsed.path.split('/')[-1]
                        task_id += 1
                        url_hash = hashlib.md5(full_url.encode()).hexdigest()[:12]

                        articles.append({
                            'id': f'asian-{task_id:05d}',
                            'url': full_url,
                            'url_hash': url_hash,
                            'title': title[:200],
                            'status': 'pending',
                            'fetched_at': None,
                            'content_path': None,
                            'error': None,
                        })

        except Exception as e:
            logger.warning(f"  Error: {e}")
            continue

    # Also try to find posts via RSS or sitemap
    for feed_url in [f"{MAIN_SITE}/rss/", f"{MAIN_SITE}/feed.xml", f"{MAIN_SITE}/sitemap.xml"]:
        try:
            response = session.get(feed_url, timeout=30)
            if response.status_code == 200:
                # Extract URLs from XML
                soup = BeautifulSoup(response.text, 'xml')
                for loc in soup.find_all(['loc', 'link', 'guid']):
                    url = loc.get_text(strip=True)
                    if url and url.startswith('http') and url not in seen_urls:
                        if '/p/' in url or '/posts/' in url:
                            seen_urls.add(url)
                            task_id += 1
                            url_hash = hashlib.md5(url.encode()).hexdigest()[:12]
                            articles.append({
                                'id': f'asian-{task_id:05d}',
                                'url': url,
                                'url_hash': url_hash,
                                'title': url.split('/')[-1].replace('-', ' ').title(),
                                'status': 'pending',
                                'fetched_at': None,
                                'content_path': None,
                                'error': None,
                            })
        except:
            pass

    logger.info(f"Discovered {len(articles)} articles")
    return articles


def fetch_article(session: requests.Session, url: str) -> Optional[Dict[str, Any]]:
    """Fetch a single article and extract content."""
    try:
        response = session.get(url, timeout=30)

        if response.status_code == 403:
            return {'error': 'Authentication required (403)'}
        if response.status_code == 404:
            return {'error': 'Not found (404)'}

        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')

        # Find the article content - try various selectors
        article = None
        for selector in [
            'article',
            '.post-content',
            '.entry-content',
            '.article-content',
            '.content',
            'main',
            '#content',
        ]:
            article = soup.select_one(selector)
            if article:
                break

        if not article:
            # Fallback: get body minus nav/footer
            article = soup.find('body')
            if article:
                for tag in article.find_all(['nav', 'footer', 'header', 'aside', 'script', 'style']):
                    tag.decompose()

        if not article:
            return {'error': 'Could not find article content'}

        # Get title
        title = None
        for selector in ['h1.post-title', 'h1.entry-title', 'h1', 'title']:
            title_tag = soup.select_one(selector)
            if title_tag:
                title = title_tag.get_text(strip=True)
                break

        # Get date
        date = None
        time_tag = soup.find('time')
        if time_tag:
            date = time_tag.get('datetime') or time_tag.get_text(strip=True)

        # Check for paywall indicator
        paywall_text = soup.get_text().lower()
        if 'subscribe to continue' in paywall_text or 'members only' in paywall_text:
            return {'error': 'Paywall detected - cookies may have expired'}

        # Convert to markdown
        content = html_to_markdown(article)

        return {
            'title': title,
            'date': date,
            'content': content,
        }

    except requests.RequestException as e:
        return {'error': str(e)}
    except Exception as e:
        return {'error': str(e)}


def html_to_markdown(element) -> str:
    """Convert HTML element to markdown-ish text."""
    content_parts = []

    for elem in element.descendants:
        if elem.name == 'h1':
            content_parts.append(f"\n# {elem.get_text(strip=True)}\n")
        elif elem.name == 'h2':
            content_parts.append(f"\n## {elem.get_text(strip=True)}\n")
        elif elem.name == 'h3':
            content_parts.append(f"\n### {elem.get_text(strip=True)}\n")
        elif elem.name == 'p':
            text = elem.get_text(strip=True)
            if text:
                content_parts.append(f"\n{text}\n")
        elif elem.name == 'blockquote':
            text = elem.get_text(strip=True)
            if text:
                lines = text.split('\n')
                quoted = '\n'.join(f"> {line}" for line in lines)
                content_parts.append(f"\n{quoted}\n")
        elif elem.name == 'li':
            text = elem.get_text(strip=True)
            if text:
                content_parts.append(f"- {text}\n")
        elif elem.name == 'pre' or elem.name == 'code':
            text = elem.get_text()
            if text:
                content_parts.append(f"\n```\n{text}\n```\n")

    content = ''.join(content_parts)
    content = re.sub(r'\n{3,}', '\n\n', content)
    return content.strip()


def save_article(task: Dict[str, Any], article_data: Dict[str, Any]) -> str:
    """Save article to markdown file."""
    # Create filename from URL
    parsed = urlparse(task['url'])
    slug = parsed.path.strip('/').replace('/', '_')
    if not slug:
        slug = task['url_hash']

    filename = f"{slug}.md"
    filepath = OUTPUT_DIR / filename

    # Build markdown content
    title = article_data.get('title', task['title']).replace('"', '\\"') if article_data.get('title') or task.get('title') else 'Untitled'
    md_content = f"""---
title: "{title}"
url: {task['url']}
date: {article_data.get('date', 'unknown')}
source: asianometry
fetched_at: {datetime.now().isoformat()}
---

{article_data.get('content', '')}
"""

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(md_content)

    return str(filepath)


def generate_manifest():
    """Generate manifest from discovered articles."""
    logger.info("Generating Asianometry manifest...")

    session = get_session_with_cookies()
    articles = discover_articles(session)

    if not articles:
        logger.error("No articles discovered. Check cookies and site access.")
        return

    # Check for existing manifest to preserve status
    existing = load_manifest(MANIFEST_FILE)
    existing_by_hash = {a['url_hash']: a for a in existing}

    # Merge with existing status
    for article in articles:
        if article['url_hash'] in existing_by_hash:
            old = existing_by_hash[article['url_hash']]
            article['status'] = old['status']
            article['fetched_at'] = old.get('fetched_at')
            article['content_path'] = old.get('content_path')
            article['error'] = old.get('error')

    save_manifest(articles, MANIFEST_FILE)

    # Stats
    pending = sum(1 for a in articles if a['status'] == 'pending')
    fetched = sum(1 for a in articles if a['status'] == 'fetched')
    failed = sum(1 for a in articles if a['status'] == 'failed')

    print(f"\n=== Asianometry Manifest ===")
    print(f"Total articles: {len(articles)}")
    print(f"Pending:        {pending}")
    print(f"Fetched:        {fetched}")
    print(f"Failed:         {failed}")
    print(f"\nManifest saved to: {MANIFEST_FILE}")


def execute_manifest(limit: int = 0, dry_run: bool = False):
    """Execute the manifest - fetch pending articles."""
    manifest = load_manifest(MANIFEST_FILE)

    if not manifest:
        logger.error("No manifest found. Run with --generate-manifest first.")
        return

    session = get_session_with_cookies()

    # Filter to pending
    pending = [a for a in manifest if a['status'] == 'pending']

    if limit > 0:
        pending = pending[:limit]

    logger.info(f"Processing {len(pending)} pending articles")

    if dry_run:
        for task in pending[:10]:
            print(f"[DRY RUN] Would fetch: {task['url']}")
        if len(pending) > 10:
            print(f"... and {len(pending) - 10} more")
        return

    for i, task in enumerate(pending):
        task_index = next(j for j, t in enumerate(manifest) if t['id'] == task['id'])

        logger.info(f"[{i+1}/{len(pending)}] Fetching: {task['url'][:70]}...")

        # Fetch article
        result = fetch_article(session, task['url'])

        if result.get('error'):
            manifest[task_index]['status'] = 'failed'
            manifest[task_index]['error'] = result['error']
            logger.warning(f"  FAILED: {result['error']}")

            # If auth error, stop
            if '403' in result['error'] or 'expired' in result['error']:
                logger.error("Authentication error - stopping. Refresh cookies.")
                save_manifest(manifest, MANIFEST_FILE)
                return
        else:
            # Save article
            content_path = save_article(task, result)
            manifest[task_index]['status'] = 'fetched'
            manifest[task_index]['fetched_at'] = datetime.now().isoformat()
            manifest[task_index]['content_path'] = content_path
            logger.info(f"  Saved: {content_path}")

        # Atomic save after each
        save_manifest(manifest, MANIFEST_FILE)

        # Rate limit
        if i < len(pending) - 1:
            time.sleep(DELAY_BETWEEN_FETCHES)

    # Final stats
    print_status(manifest)


def print_status(manifest: List[Dict[str, Any]] = None):
    """Print current status."""
    if manifest is None:
        manifest = load_manifest(MANIFEST_FILE)

    if not manifest:
        print("No manifest found. Run with --generate-manifest first.")
        return

    total = len(manifest)
    pending = sum(1 for a in manifest if a['status'] == 'pending')
    fetched = sum(1 for a in manifest if a['status'] == 'fetched')
    failed = sum(1 for a in manifest if a['status'] == 'failed')

    print(f"\n=== Asianometry Status ===")
    print(f"Total:   {total}")
    print(f"Pending: {pending} ({100*pending/total:.1f}%)" if total > 0 else "Pending: 0")
    print(f"Fetched: {fetched} ({100*fetched/total:.1f}%)" if total > 0 else "Fetched: 0")
    print(f"Failed:  {failed} ({100*failed/total:.1f}%)" if total > 0 else "Failed: 0")


def main():
    parser = argparse.ArgumentParser(description='Crawl Asianometry with cookies')
    parser.add_argument('--generate-manifest', action='store_true',
                       help='Generate manifest by discovering articles')
    parser.add_argument('--execute', action='store_true',
                       help='Execute manifest (fetch pending articles)')
    parser.add_argument('--limit', '-l', type=int, default=0,
                       help='Limit number of articles to fetch')
    parser.add_argument('--dry-run', action='store_true',
                       help='Show what would be done without fetching')
    parser.add_argument('--status', action='store_true',
                       help='Show current status')
    args = parser.parse_args()

    # Ensure output directory exists
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    MANIFEST_FILE.parent.mkdir(parents=True, exist_ok=True)

    if args.generate_manifest:
        generate_manifest()
    elif args.execute:
        execute_manifest(limit=args.limit, dry_run=args.dry_run)
    elif args.status:
        print_status()
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
