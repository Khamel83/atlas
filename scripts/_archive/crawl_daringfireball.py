#!/usr/bin/env python3
"""
Crawl Daring Fireball Archive - Full archive from 2013-present.

Fetches all articles from https://daringfireball.net/archive/
Saves as markdown to data/daringfireball/

Features:
- Generates manifest first (all URLs pre-computed)
- Rate limited (5 second delay between fetches)
- Fully resumable (atomic saves after each fetch)
- Progress tracking in manifest

Usage:
    python scripts/crawl_daringfireball.py --generate-manifest
    python scripts/crawl_daringfireball.py --execute
    python scripts/crawl_daringfireball.py --execute --limit 50
    python scripts/crawl_daringfireball.py --status
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
from pathlib import Path
from typing import Dict, List, Any, Optional
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Paths
ATLAS_ROOT = Path(__file__).parent.parent
MANIFEST_FILE = ATLAS_ROOT / "data/manifests/daringfireball_tasks.json"
OUTPUT_DIR = ATLAS_ROOT / "data/daringfireball"

# Rate limiting
DELAY_BETWEEN_FETCHES = 5  # seconds

# Archive URL
ARCHIVE_URL = "https://daringfireball.net/archive/"

# User agent
USER_AGENT = "Mozilla/5.0 (compatible; AtlasBot/1.0; +https://github.com/atlas)"


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


def extract_article_links() -> List[Dict[str, Any]]:
    """Extract all article links from the archive page."""
    logger.info(f"Fetching archive page: {ARCHIVE_URL}")

    response = requests.get(ARCHIVE_URL, headers={'User-Agent': USER_AGENT}, timeout=30)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, 'html.parser')

    articles = []
    task_id = 0

    # Find all article links - they follow pattern daringfireball.net/YYYY/MM/slug
    for link in soup.find_all('a', href=True):
        href = link['href']

        # Match DF article pattern: full URL or relative path
        # Full: https://daringfireball.net/2024/12/article_slug
        # Relative: /2024/12/article_slug
        match = re.match(r'^(?:https?://daringfireball\.net)?/(\d{4})/(\d{2})/([a-z0-9_-]+)$', href, re.IGNORECASE)
        if not match:
            continue

        year, month, slug = match.groups()
        full_url = f"https://daringfireball.net/{year}/{month}/{slug}"

        # Get title from link text
        title = link.get_text(strip=True)
        if not title:
            title = slug.replace('_', ' ').title()

        task_id += 1
        url_hash = hashlib.md5(full_url.encode()).hexdigest()[:12]

        articles.append({
            'id': f'df-{task_id:05d}',
            'url': full_url,
            'url_hash': url_hash,
            'title': title,
            'year': year,
            'month': month,
            'slug': slug,
            'status': 'pending',
            'fetched_at': None,
            'content_path': None,
            'error': None,
        })

    # Sort by date (newest first)
    articles.sort(key=lambda x: (x['year'], x['month'], x['slug']), reverse=True)

    # Re-number after sorting
    for i, article in enumerate(articles):
        article['id'] = f'df-{i+1:05d}'

    return articles


def fetch_article(url: str) -> Optional[Dict[str, Any]]:
    """Fetch a single article and extract content."""
    try:
        response = requests.get(url, headers={'User-Agent': USER_AGENT}, timeout=30)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')

        # Find the article content
        article = soup.find('div', class_='article')
        if not article:
            article = soup.find('article')
        if not article:
            # Fallback: main content area
            article = soup.find('div', id='Main')

        if not article:
            return {'error': 'Could not find article content'}

        # Get title
        title = None
        title_tag = soup.find('h1')
        if title_tag:
            title = title_tag.get_text(strip=True)

        # Get date
        date = None
        time_tag = soup.find('time')
        if time_tag:
            date = time_tag.get('datetime') or time_tag.get_text(strip=True)

        # Convert to markdown-ish text
        # Remove script and style tags
        for tag in article.find_all(['script', 'style', 'nav', 'aside']):
            tag.decompose()

        # Get text content preserving some structure
        content_parts = []

        for elem in article.descendants:
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
                    # Indent blockquotes
                    lines = text.split('\n')
                    quoted = '\n'.join(f"> {line}" for line in lines)
                    content_parts.append(f"\n{quoted}\n")
            elif elem.name == 'li':
                text = elem.get_text(strip=True)
                if text:
                    content_parts.append(f"- {text}\n")
            elif elem.name == 'a' and elem.string:
                # Keep links inline
                pass

        content = ''.join(content_parts)

        # Clean up excessive newlines
        content = re.sub(r'\n{3,}', '\n\n', content)

        return {
            'title': title,
            'date': date,
            'content': content.strip(),
            'html': str(article),
        }

    except requests.RequestException as e:
        return {'error': str(e)}
    except Exception as e:
        return {'error': str(e)}


def save_article(task: Dict[str, Any], article_data: Dict[str, Any]) -> str:
    """Save article to markdown file."""
    year = task['year']
    month = task['month']
    slug = task['slug']

    # Create directory structure: data/daringfireball/YYYY/MM/
    output_dir = OUTPUT_DIR / year / month
    output_dir.mkdir(parents=True, exist_ok=True)

    filename = f"{slug}.md"
    filepath = output_dir / filename

    # Build markdown content
    md_content = f"""---
title: "{article_data.get('title', task['title']).replace('"', '\\"')}"
url: {task['url']}
date: {article_data.get('date', f'{year}-{month}')}
source: daringfireball
fetched_at: {datetime.now().isoformat()}
---

{article_data.get('content', '')}
"""

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(md_content)

    return str(filepath)


def generate_manifest():
    """Generate manifest from archive page."""
    logger.info("Generating Daring Fireball manifest...")

    articles = extract_article_links()

    logger.info(f"Found {len(articles)} articles")

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

    print(f"\n=== Daring Fireball Manifest ===")
    print(f"Total articles: {len(articles)}")
    print(f"Pending:        {pending}")
    print(f"Fetched:        {fetched}")
    print(f"Failed:         {failed}")
    print(f"\nManifest saved to: {MANIFEST_FILE}")

    # Year breakdown
    from collections import Counter
    years = Counter(a['year'] for a in articles)
    print(f"\nBy year:")
    for year, count in sorted(years.items(), reverse=True):
        print(f"  {year}: {count}")


def execute_manifest(limit: int = 0, dry_run: bool = False):
    """Execute the manifest - fetch pending articles."""
    manifest = load_manifest(MANIFEST_FILE)

    if not manifest:
        logger.error("No manifest found. Run with --generate-manifest first.")
        return

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
        result = fetch_article(task['url'])

        if result.get('error'):
            manifest[task_index]['status'] = 'failed'
            manifest[task_index]['error'] = result['error']
            logger.warning(f"  FAILED: {result['error']}")
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
            logger.debug(f"  Waiting {DELAY_BETWEEN_FETCHES}s...")
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

    print(f"\n=== Daring Fireball Status ===")
    print(f"Total:   {total}")
    print(f"Pending: {pending} ({100*pending/total:.1f}%)")
    print(f"Fetched: {fetched} ({100*fetched/total:.1f}%)")
    print(f"Failed:  {failed} ({100*failed/total:.1f}%)")

    if fetched > 0:
        # Estimate time remaining
        avg_time = DELAY_BETWEEN_FETCHES + 2  # fetch + delay
        remaining_seconds = pending * avg_time
        remaining_hours = remaining_seconds / 3600
        print(f"\nEstimated time remaining: {remaining_hours:.1f} hours")


def main():
    parser = argparse.ArgumentParser(description='Crawl Daring Fireball archive')
    parser.add_argument('--generate-manifest', action='store_true',
                       help='Generate manifest from archive page')
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
