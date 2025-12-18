#!/usr/bin/env python3
"""
Crawl Dithering - Extract show notes and queue audio for Whisper.

Uses cookies from ~/.config/atlas/cookies/dithering.passport.online.json
Saves show notes to data/dithering/show_notes/
Extracts URLs and adds them to link queue
Queues audio for Mac Mini Whisper transcription

Stop condition: "Subscribe to Stratechery Plus..." text indicates paywall

Features:
- Cookie-based authentication for paywalled content
- Generates manifest first (all episodes pre-computed)
- Extracts URLs from show notes for ingestion
- Rate limited (5 second delay between fetches)
- Fully resumable (atomic saves after each fetch)

Usage:
    python scripts/crawl_dithering.py --generate-manifest
    python scripts/crawl_dithering.py --execute
    python scripts/crawl_dithering.py --execute --limit 50
    python scripts/crawl_dithering.py --status
    python scripts/crawl_dithering.py --extract-urls  # Extract URLs from saved show notes
"""

import argparse
import hashlib
import json
import logging
import os
import re
import sqlite3
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Set
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
MANIFEST_FILE = ATLAS_ROOT / "data/manifests/dithering_tasks.json"
OUTPUT_DIR = ATLAS_ROOT / "data/dithering/show_notes"
EXTRACTED_URLS_FILE = ATLAS_ROOT / "data/manifests/dithering_urls.json"
WHISPER_QUEUE_DIR = ATLAS_ROOT / "data/whisper_queue/audio"
LINK_QUEUE_DB = ATLAS_ROOT / "data/enrich/link_queue.db"
COOKIES_FILE = Path(os.path.expanduser("~/.config/atlas/cookies/dithering.passport.online.json"))

# Rate limiting
DELAY_BETWEEN_FETCHES = 5  # seconds

# Base URL
BASE_URL = "https://dithering.passport.online"

# User agent
USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"

# Paywall stop condition
PAYWALL_TEXT = "subscribe to stratechery plus"


def load_cookies() -> Dict[str, str]:
    """Load cookies from JSON file."""
    if not COOKIES_FILE.exists():
        logger.error(f"Cookie file not found: {COOKIES_FILE}")
        logger.error("Please export cookies from browser and save to:")
        logger.error(f"  {COOKIES_FILE}")
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
        session.cookies.set(name, value, domain='.dithering.passport.online')

    session.headers.update({
        'User-Agent': USER_AGENT,
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
    })

    return session


def discover_episodes(session: requests.Session) -> List[Dict[str, Any]]:
    """Discover all episode URLs from the site."""
    episodes = []
    task_id = 0
    seen_urls = set()

    # Start from main page and navigate
    urls_to_try = [
        f"{BASE_URL}/",
        f"{BASE_URL}/posts",
        f"{BASE_URL}/archive",
        f"{BASE_URL}/episodes",
    ]

    for url in urls_to_try:
        logger.info(f"Trying: {url}")
        try:
            response = session.get(url, timeout=30)
            if response.status_code != 200:
                logger.warning(f"  Status {response.status_code}")
                continue

            soup = BeautifulSoup(response.text, 'html.parser')

            # Check for paywall
            if PAYWALL_TEXT in soup.get_text().lower():
                logger.warning("  Paywall detected on this page")
                continue

            # Find all episode links
            for link in soup.find_all('a', href=True):
                href = link['href']

                # Normalize URL
                if href.startswith('/'):
                    full_url = urljoin(BASE_URL, href)
                elif href.startswith('http'):
                    full_url = href
                else:
                    continue

                # Skip non-episode URLs
                if any(skip in full_url for skip in ['/tag/', '/author/', '/login', '/subscribe', '#', '?', '/about']):
                    continue

                # Check if it looks like an episode
                parsed = urlparse(full_url)

                # Dithering episodes might be at /p/slug or similar
                if ('/p/' in parsed.path or
                    '/posts/' in parsed.path or
                    '/episodes/' in parsed.path or
                    re.search(r'/\d{4}/', parsed.path)):

                    if full_url not in seen_urls:
                        seen_urls.add(full_url)

                        title = link.get_text(strip=True) or parsed.path.split('/')[-1]
                        task_id += 1
                        url_hash = hashlib.md5(full_url.encode()).hexdigest()[:12]

                        episodes.append({
                            'id': f'dith-{task_id:05d}',
                            'url': full_url,
                            'url_hash': url_hash,
                            'title': title[:200],
                            'status': 'pending',
                            'fetched_at': None,
                            'show_notes_path': None,
                            'audio_queued': False,
                            'urls_extracted': 0,
                            'error': None,
                        })

        except Exception as e:
            logger.warning(f"  Error: {e}")
            continue

    logger.info(f"Discovered {len(episodes)} episodes")
    return episodes


def fetch_episode(session: requests.Session, url: str) -> Optional[Dict[str, Any]]:
    """Fetch a single episode and extract show notes."""
    try:
        response = session.get(url, timeout=30)

        if response.status_code == 403:
            return {'error': 'Authentication required (403)'}
        if response.status_code == 404:
            return {'error': 'Not found (404)'}

        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')

        # Check for paywall
        page_text = soup.get_text().lower()
        if PAYWALL_TEXT in page_text:
            return {'error': 'Paywall - no access (need subscription)', 'is_paywall': True}

        # Find the episode content
        content = None
        for selector in [
            'article',
            '.post-content',
            '.entry-content',
            '.episode-content',
            '.show-notes',
            'main',
        ]:
            content = soup.select_one(selector)
            if content:
                break

        if not content:
            content = soup.find('body')
            if content:
                for tag in content.find_all(['nav', 'footer', 'header', 'aside', 'script', 'style']):
                    tag.decompose()

        if not content:
            return {'error': 'Could not find episode content'}

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

        # Extract all URLs from show notes
        urls = []
        for link in content.find_all('a', href=True):
            href = link['href']
            if href.startswith('http') and 'dithering' not in href.lower():
                anchor = link.get_text(strip=True)
                urls.append({
                    'url': href,
                    'anchor': anchor[:100] if anchor else '',
                })

        # Find audio URL if present
        audio_url = None
        audio_tag = soup.find('audio')
        if audio_tag:
            source = audio_tag.find('source')
            if source:
                audio_url = source.get('src')
            else:
                audio_url = audio_tag.get('src')

        # Also look for enclosure or download links
        if not audio_url:
            for link in soup.find_all('a', href=True):
                href = link['href']
                if any(ext in href.lower() for ext in ['.mp3', '.m4a', '.wav']):
                    audio_url = href
                    break

        # Convert to markdown
        show_notes = html_to_markdown(content)

        return {
            'title': title,
            'date': date,
            'show_notes': show_notes,
            'urls': urls,
            'audio_url': audio_url,
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
        elif elem.name == 'a' and elem.get('href'):
            text = elem.get_text(strip=True)
            href = elem.get('href')
            if text and href.startswith('http'):
                content_parts.append(f"[{text}]({href})")

    content = ''.join(content_parts)
    content = re.sub(r'\n{3,}', '\n\n', content)
    return content.strip()


def save_show_notes(task: Dict[str, Any], episode_data: Dict[str, Any]) -> str:
    """Save show notes to markdown file."""
    # Create filename from URL
    parsed = urlparse(task['url'])
    slug = parsed.path.strip('/').replace('/', '_')
    if not slug:
        slug = task['url_hash']

    filename = f"{slug}.md"
    filepath = OUTPUT_DIR / filename

    # Build markdown content with URL list
    title = episode_data.get('title', task['title']) or 'Untitled'
    title = title.replace('"', '\\"')

    urls_section = ""
    if episode_data.get('urls'):
        urls_section = "\n\n## Links from this episode\n\n"
        for url_info in episode_data['urls']:
            anchor = url_info.get('anchor', '')
            url = url_info['url']
            if anchor:
                urls_section += f"- [{anchor}]({url})\n"
            else:
                urls_section += f"- {url}\n"

    md_content = f"""---
title: "{title}"
url: {task['url']}
date: {episode_data.get('date', 'unknown')}
source: dithering
audio_url: {episode_data.get('audio_url', 'none')}
urls_count: {len(episode_data.get('urls', []))}
fetched_at: {datetime.now().isoformat()}
---

{episode_data.get('show_notes', '')}
{urls_section}
"""

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(md_content)

    return str(filepath)


def add_urls_to_queue(urls: List[Dict[str, str]], source_episode: str):
    """Add extracted URLs to the link queue database."""
    if not urls:
        return 0

    LINK_QUEUE_DB.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(LINK_QUEUE_DB)
    cursor = conn.cursor()

    # Ensure table exists
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS extracted_links (
            id INTEGER PRIMARY KEY,
            url TEXT NOT NULL,
            domain TEXT,
            anchor TEXT,
            score REAL DEFAULT 0.5,
            category TEXT DEFAULT 'article',
            status TEXT DEFAULT 'pending',
            source_content_id TEXT,
            source_path TEXT,
            created_at TEXT,
            UNIQUE(url)
        )
    """)

    added = 0
    for url_info in urls:
        url = url_info['url']
        anchor = url_info.get('anchor', '')

        # Skip internal/tracking URLs
        if any(skip in url.lower() for skip in ['dithering.', 'passport.online', 'twitter.com', 'facebook.com']):
            continue

        parsed = urlparse(url)
        domain = parsed.netloc.lower().replace('www.', '')

        try:
            cursor.execute("""
                INSERT OR IGNORE INTO extracted_links
                (url, domain, anchor, score, category, status, source_content_id, source_path, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                url,
                domain,
                anchor,
                0.75,  # Higher score for podcast show notes URLs
                'article',
                'pending',
                f'dithering:{source_episode}',
                f'data/dithering/show_notes/{source_episode}.md',
                datetime.now().isoformat(),
            ))
            if cursor.rowcount > 0:
                added += 1
        except sqlite3.Error as e:
            logger.debug(f"Could not add URL: {e}")

    conn.commit()
    conn.close()

    return added


def queue_audio_for_whisper(task: Dict[str, Any], audio_url: str) -> bool:
    """Queue audio file for Mac Mini Whisper transcription."""
    if not audio_url:
        return False

    WHISPER_QUEUE_DIR.mkdir(parents=True, exist_ok=True)

    # Create filename
    slug = task['url_hash']
    title_part = re.sub(r'[^\w\s-]', '', task.get('title', '')[:50]).strip().replace(' ', '_')
    filename = f"dithering_{slug}_{title_part}.mp3"
    output_path = WHISPER_QUEUE_DIR / filename

    if output_path.exists():
        logger.info(f"  Audio already queued: {filename}")
        return True

    # Download audio
    logger.info(f"  Downloading audio: {audio_url[:60]}...")
    try:
        response = requests.get(audio_url, timeout=600, stream=True)
        response.raise_for_status()

        with open(output_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

        size_mb = output_path.stat().st_size / 1024 / 1024
        logger.info(f"  Downloaded: {size_mb:.1f} MB")
        return True

    except Exception as e:
        logger.warning(f"  Audio download failed: {e}")
        return False


def generate_manifest():
    """Generate manifest from discovered episodes."""
    logger.info("Generating Dithering manifest...")

    session = get_session_with_cookies()
    if not session.cookies:
        logger.error("No cookies loaded. Please save cookies first.")
        return

    episodes = discover_episodes(session)

    if not episodes:
        logger.error("No episodes discovered. Check cookies and site access.")
        return

    # Check for existing manifest to preserve status
    existing = load_manifest(MANIFEST_FILE)
    existing_by_hash = {a['url_hash']: a for a in existing}

    # Merge with existing status
    for episode in episodes:
        if episode['url_hash'] in existing_by_hash:
            old = existing_by_hash[episode['url_hash']]
            episode['status'] = old['status']
            episode['fetched_at'] = old.get('fetched_at')
            episode['show_notes_path'] = old.get('show_notes_path')
            episode['audio_queued'] = old.get('audio_queued', False)
            episode['urls_extracted'] = old.get('urls_extracted', 0)
            episode['error'] = old.get('error')

    save_manifest(episodes, MANIFEST_FILE)

    # Stats
    pending = sum(1 for a in episodes if a['status'] == 'pending')
    fetched = sum(1 for a in episodes if a['status'] == 'fetched')
    failed = sum(1 for a in episodes if a['status'] == 'failed')

    print(f"\n=== Dithering Manifest ===")
    print(f"Total episodes: {len(episodes)}")
    print(f"Pending:        {pending}")
    print(f"Fetched:        {fetched}")
    print(f"Failed:         {failed}")
    print(f"\nManifest saved to: {MANIFEST_FILE}")


def execute_manifest(limit: int = 0, dry_run: bool = False, skip_audio: bool = False):
    """Execute the manifest - fetch pending episodes."""
    manifest = load_manifest(MANIFEST_FILE)

    if not manifest:
        logger.error("No manifest found. Run with --generate-manifest first.")
        return

    session = get_session_with_cookies()

    # Filter to pending
    pending = [e for e in manifest if e['status'] == 'pending']

    if limit > 0:
        pending = pending[:limit]

    logger.info(f"Processing {len(pending)} pending episodes")

    if dry_run:
        for task in pending[:10]:
            print(f"[DRY RUN] Would fetch: {task['url']}")
        if len(pending) > 10:
            print(f"... and {len(pending) - 10} more")
        return

    total_urls_added = 0

    for i, task in enumerate(pending):
        task_index = next(j for j, t in enumerate(manifest) if t['id'] == task['id'])

        logger.info(f"[{i+1}/{len(pending)}] Fetching: {task['url'][:70]}...")

        # Fetch episode
        result = fetch_episode(session, task['url'])

        if result.get('error'):
            manifest[task_index]['status'] = 'failed'
            manifest[task_index]['error'] = result['error']
            logger.warning(f"  FAILED: {result['error']}")

            # If paywall, we've hit the limit
            if result.get('is_paywall'):
                logger.warning("Hit paywall - stopping. These episodes need subscription.")
                save_manifest(manifest, MANIFEST_FILE)
                break

            # If auth error, stop
            if '403' in result['error']:
                logger.error("Authentication error - stopping. Refresh cookies.")
                save_manifest(manifest, MANIFEST_FILE)
                return
        else:
            # Save show notes
            show_notes_path = save_show_notes(task, result)
            manifest[task_index]['status'] = 'fetched'
            manifest[task_index]['fetched_at'] = datetime.now().isoformat()
            manifest[task_index]['show_notes_path'] = show_notes_path

            # Extract and queue URLs
            urls = result.get('urls', [])
            if urls:
                added = add_urls_to_queue(urls, task['url_hash'])
                manifest[task_index]['urls_extracted'] = added
                total_urls_added += added
                logger.info(f"  Added {added} URLs to queue")

            # Queue audio for Whisper
            if not skip_audio and result.get('audio_url'):
                audio_queued = queue_audio_for_whisper(task, result['audio_url'])
                manifest[task_index]['audio_queued'] = audio_queued

            logger.info(f"  Saved: {show_notes_path}")

        # Atomic save after each
        save_manifest(manifest, MANIFEST_FILE)

        # Rate limit
        if i < len(pending) - 1:
            time.sleep(DELAY_BETWEEN_FETCHES)

    # Final stats
    print(f"\nTotal URLs added to queue: {total_urls_added}")
    print_status(manifest)


def print_status(manifest: List[Dict[str, Any]] = None):
    """Print current status."""
    if manifest is None:
        manifest = load_manifest(MANIFEST_FILE)

    if not manifest:
        print("No manifest found. Run with --generate-manifest first.")
        return

    total = len(manifest)
    pending = sum(1 for e in manifest if e['status'] == 'pending')
    fetched = sum(1 for e in manifest if e['status'] == 'fetched')
    failed = sum(1 for e in manifest if e['status'] == 'failed')
    audio_queued = sum(1 for e in manifest if e.get('audio_queued'))
    urls_extracted = sum(e.get('urls_extracted', 0) for e in manifest)

    print(f"\n=== Dithering Status ===")
    print(f"Total:          {total}")
    print(f"Pending:        {pending} ({100*pending/total:.1f}%)" if total > 0 else "Pending: 0")
    print(f"Fetched:        {fetched} ({100*fetched/total:.1f}%)" if total > 0 else "Fetched: 0")
    print(f"Failed:         {failed} ({100*failed/total:.1f}%)" if total > 0 else "Failed: 0")
    print(f"Audio queued:   {audio_queued}")
    print(f"URLs extracted: {urls_extracted}")


def main():
    parser = argparse.ArgumentParser(description='Crawl Dithering with cookies')
    parser.add_argument('--generate-manifest', action='store_true',
                       help='Generate manifest by discovering episodes')
    parser.add_argument('--execute', action='store_true',
                       help='Execute manifest (fetch pending episodes)')
    parser.add_argument('--limit', '-l', type=int, default=0,
                       help='Limit number of episodes to fetch')
    parser.add_argument('--dry-run', action='store_true',
                       help='Show what would be done without fetching')
    parser.add_argument('--skip-audio', action='store_true',
                       help='Skip downloading audio files')
    parser.add_argument('--status', action='store_true',
                       help='Show current status')
    args = parser.parse_args()

    # Ensure output directory exists
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    MANIFEST_FILE.parent.mkdir(parents=True, exist_ok=True)

    if args.generate_manifest:
        generate_manifest()
    elif args.execute:
        execute_manifest(limit=args.limit, dry_run=args.dry_run, skip_audio=args.skip_audio)
    elif args.status:
        print_status()
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
