#!/usr/bin/env python3
"""
Bulk crawl Tyler transcripts directly from conversationswithtyler.com
Bypasses resolver chain - directly scrapes transcript pages.
"""
import subprocess
import re
import time
import sys
from pathlib import Path
from bs4 import BeautifulSoup
from datetime import datetime

def get_episode_urls():
    """Get all episode URLs from the episodes page."""
    result = subprocess.run(
        ['curl', '-s', '-A', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)',
         'https://conversationswithtyler.com/episodes/'],
        capture_output=True, text=True
    )
    urls = re.findall(r'href="(/episodes/[^/]+/)"', result.stdout)
    unique = list(set(urls))
    # Filter out feed and special pages
    return [u for u in unique if 'feed' not in u]

def download_transcript(url: str, output_dir: Path) -> bool:
    """Download transcript for a single episode."""
    slug = url.strip('/').split('/')[-1]
    out_file = output_dir / f'{slug}.md'

    if out_file.exists() and out_file.stat().st_size > 1000:
        return None  # Skip existing

    full_url = f'https://conversationswithtyler.com{url}'

    try:
        result = subprocess.run(
            ['curl', '-s', '-A', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)', full_url],
            capture_output=True, text=True, timeout=30
        )
        soup = BeautifulSoup(result.stdout, 'html.parser')

        # Extract transcript content - try multiple selectors
        content = None
        for sel in ['.generic__content', '.transcript', '.entry-content', 'article .content']:
            elem = soup.select_one(sel)
            if elem:
                text = elem.get_text(separator='\n').strip()
                if len(text) > 500:
                    content = text
                    break

        if not content:
            return False

        # Get title
        title_elem = soup.select_one('h1, .entry-title, title')
        title = title_elem.get_text().strip() if title_elem else slug.replace('-', ' ').title()

        # Write markdown
        out_file.write_text(f'# {title}\n\nSource: {full_url}\nDate: {datetime.now().isoformat()}\n\n---\n\n{content}')
        return True

    except Exception as e:
        print(f'  Error {slug}: {e}', file=sys.stderr)
        return False

def main():
    output_dir = Path('data/podcasts/conversations-with-tyler/transcripts')
    output_dir.mkdir(parents=True, exist_ok=True)

    print('Getting episode list...')
    urls = get_episode_urls()
    print(f'Found {len(urls)} episodes')

    success = 0
    skipped = 0
    failed = 0

    for i, url in enumerate(urls):
        result = download_transcript(url, output_dir)
        slug = url.strip('/').split('/')[-1]

        if result is None:
            skipped += 1
        elif result:
            success += 1
            print(f'[{i+1}/{len(urls)}] ✅ {slug}')
        else:
            failed += 1
            print(f'[{i+1}/{len(urls)}] ❌ {slug}')

        if result is not None:
            time.sleep(1)  # Rate limit

        if (i + 1) % 20 == 0:
            print(f'\nProgress: {success} downloaded, {skipped} skipped, {failed} failed\n')

    print(f'\n=== COMPLETE ===')
    print(f'Downloaded: {success}')
    print(f'Skipped (already exist): {skipped}')
    print(f'Failed: {failed}')

if __name__ == '__main__':
    main()
