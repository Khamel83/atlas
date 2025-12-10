#!/usr/bin/env python3
"""
Validate Podcast Transcript Sources

For each podcast with pending episodes, checks if we can actually fetch transcripts.
Tests one episode per podcast to verify the source works.

Usage:
    python scripts/validate_podcast_sources.py
    python scripts/validate_podcast_sources.py --slug acquired
    python scripts/validate_podcast_sources.py --fix  # Update config with findings
"""

import argparse
import sys
import sqlite3
import requests
import re
import json
from pathlib import Path
from urllib.parse import urlparse
from bs4 import BeautifulSoup

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from modules.podcasts.matchers import load_mapping_config


def get_pending_podcasts(db_path: str) -> list:
    """Get podcasts with pending episodes"""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    results = conn.execute("""
        SELECT p.slug, p.name, p.rss_url, p.site_url, COUNT(*) as pending_count
        FROM episodes e
        JOIN podcasts p ON e.podcast_id = p.id
        WHERE e.transcript_status IN ('unknown', 'failed')
        GROUP BY p.slug
        ORDER BY pending_count DESC
    """).fetchall()

    conn.close()
    return [dict(r) for r in results]


def get_sample_episode(db_path: str, slug: str) -> dict:
    """Get one pending episode for a podcast"""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    result = conn.execute("""
        SELECT e.title, e.url, e.guid
        FROM episodes e
        JOIN podcasts p ON e.podcast_id = p.id
        WHERE p.slug = ? AND e.transcript_status IN ('unknown', 'failed')
        ORDER BY e.publish_date DESC
        LIMIT 1
    """, (slug,)).fetchone()

    conn.close()
    return dict(result) if result else None


def check_website_transcript(url: str, selectors: list) -> dict:
    """Check if a website URL has transcript content"""
    result = {
        'reachable': False,
        'has_transcript': False,
        'content_length': 0,
        'selector_matched': None,
        'error': None
    }

    try:
        resp = requests.get(url, timeout=15, headers={'User-Agent': 'Atlas-Validator/1.0'})
        result['reachable'] = resp.status_code == 200

        if not result['reachable']:
            result['error'] = f"HTTP {resp.status_code}"
            return result

        soup = BeautifulSoup(resp.text, 'html.parser')

        for selector in selectors:
            elem = soup.select_one(selector)
            if elem:
                text = elem.get_text(strip=True)
                if len(text) > 500:  # Minimum for a transcript
                    result['has_transcript'] = True
                    result['content_length'] = len(text)
                    result['selector_matched'] = selector
                    break

        if not result['has_transcript']:
            # Check for common transcript patterns
            for selector in ['.transcript', '#transcript', '[class*="transcript"]', '.post-content', '.entry-content']:
                elem = soup.select_one(selector)
                if elem:
                    text = elem.get_text(strip=True)
                    if len(text) > 500:
                        result['has_transcript'] = True
                        result['content_length'] = len(text)
                        result['selector_matched'] = selector
                        break

    except Exception as e:
        result['error'] = str(e)[:100]

    return result


def check_youtube_availability(title: str, podcast_name: str) -> dict:
    """Check if episode is likely on YouTube"""
    result = {
        'searchable': True,
        'likely_available': False,
        'notes': None
    }

    # Podcasts known to be on YouTube
    youtube_podcasts = [
        'acquired', 'acq2-by-acquired', 'lex-fridman', 'huberman-lab',
        'dwarkesh-podcast', 'conversations-with-tyler', 'hard-fork',
        'all-in', 'asianometry', 'against-the-rules'
    ]

    slug = podcast_name.lower().replace(' ', '-')
    if any(yt in slug for yt in youtube_podcasts):
        result['likely_available'] = True
        result['notes'] = "Podcast known to be on YouTube"

    return result


def check_podscripts(podcast_slug: str) -> dict:
    """Check if podcast is on podscripts.co"""
    result = {
        'available': False,
        'url': None,
        'error': None
    }

    try:
        # Podscripts uses podcast slugs
        url = f"https://podscripts.co/podcasts/{podcast_slug}"
        resp = requests.head(url, timeout=10, allow_redirects=True)
        if resp.status_code == 200:
            result['available'] = True
            result['url'] = url
    except Exception as e:
        result['error'] = str(e)[:50]

    return result


def validate_podcast(podcast: dict, config: dict, db_path: str) -> dict:
    """Validate transcript sources for a podcast"""
    slug = podcast['slug']
    podcast_config = config.get(slug, {})

    validation = {
        'slug': slug,
        'name': podcast['name'],
        'pending': podcast['pending_count'],
        'configured_resolver': podcast_config.get('resolver', 'none'),
        'site_url': podcast.get('site_url') or podcast_config.get('site_url'),
        'sources': {
            'website': {'status': 'unknown'},
            'youtube': {'status': 'unknown'},
            'podscripts': {'status': 'unknown'}
        },
        'recommendation': None,
        'can_fetch': False
    }

    # Get sample episode
    sample = get_sample_episode(db_path, slug)
    if not sample:
        validation['recommendation'] = "No pending episodes"
        return validation

    validation['sample_episode'] = sample['title'][:60]
    validation['sample_url'] = sample['url']

    # Check website
    site_url = validation['site_url']
    if site_url:
        # Try to construct episode URL
        selectors = podcast_config.get('transcript_selector', '').split(',')
        selectors = [s.strip() for s in selectors if s.strip()]

        # If episode URL is already the website
        if site_url and site_url.split('/')[2] in sample['url']:
            website_result = check_website_transcript(sample['url'], selectors)
        else:
            website_result = {'reachable': False, 'has_transcript': False, 'error': 'Episode URL not on website'}

        validation['sources']['website'] = website_result
        if website_result.get('has_transcript'):
            validation['sources']['website']['status'] = 'available'
            validation['can_fetch'] = True
        elif website_result.get('reachable'):
            validation['sources']['website']['status'] = 'no_transcript'
        else:
            validation['sources']['website']['status'] = 'unreachable'

    # Check YouTube
    yt_result = check_youtube_availability(sample['title'], podcast['name'])
    validation['sources']['youtube'] = yt_result
    if yt_result.get('likely_available'):
        validation['sources']['youtube']['status'] = 'likely'
        validation['can_fetch'] = True

    # Check Podscripts
    ps_result = check_podscripts(slug)
    validation['sources']['podscripts'] = ps_result
    if ps_result.get('available'):
        validation['sources']['podscripts']['status'] = 'available'
        validation['can_fetch'] = True

    # Generate recommendation
    if validation['sources']['website'].get('has_transcript'):
        validation['recommendation'] = f"✅ Website has transcripts (selector: {validation['sources']['website'].get('selector_matched')})"
    elif validation['sources']['podscripts'].get('available'):
        validation['recommendation'] = "✅ Available on Podscripts"
    elif validation['sources']['youtube'].get('likely_available'):
        validation['recommendation'] = "✅ Likely on YouTube - use YouTube resolver"
    elif validation['sources']['website'].get('reachable'):
        validation['recommendation'] = "⚠️ Website reachable but no transcript found - check selectors"
    else:
        validation['recommendation'] = "❌ No known transcript source"
        validation['can_fetch'] = False

    return validation


def main():
    parser = argparse.ArgumentParser(description='Validate podcast transcript sources')
    parser.add_argument('--slug', help='Validate specific podcast')
    parser.add_argument('--db', default='data/podcasts/atlas_podcasts.db', help='Database path')
    parser.add_argument('--limit', type=int, default=50, help='Max podcasts to check')
    parser.add_argument('--json', action='store_true', help='Output as JSON')
    args = parser.parse_args()

    # Load config
    try:
        config = load_mapping_config('config/mapping.yml')
    except:
        config = {}

    # Get pending podcasts
    podcasts = get_pending_podcasts(args.db)

    if args.slug:
        podcasts = [p for p in podcasts if p['slug'] == args.slug]
    else:
        podcasts = podcasts[:args.limit]

    if not podcasts:
        print("No pending podcasts found")
        return

    results = []

    print(f"\n{'='*80}")
    print(f"PODCAST TRANSCRIPT SOURCE VALIDATION")
    print(f"{'='*80}\n")

    for i, podcast in enumerate(podcasts):
        print(f"[{i+1}/{len(podcasts)}] Checking {podcast['slug']}...", end=' ', flush=True)

        validation = validate_podcast(podcast, config, args.db)
        results.append(validation)

        status = "✅" if validation['can_fetch'] else "❌"
        print(f"{status}")

    # Summary
    print(f"\n{'='*80}")
    print("RESULTS SUMMARY")
    print(f"{'='*80}\n")

    can_fetch = [r for r in results if r['can_fetch']]
    cannot_fetch = [r for r in results if not r['can_fetch']]

    total_pending = sum(r['pending'] for r in results)
    fetchable_pending = sum(r['pending'] for r in can_fetch)

    print(f"Podcasts checked: {len(results)}")
    print(f"Can fetch: {len(can_fetch)} ({fetchable_pending} episodes)")
    print(f"Cannot fetch: {len(cannot_fetch)} ({total_pending - fetchable_pending} episodes)")
    print(f"\nFetchable: {fetchable_pending}/{total_pending} ({100*fetchable_pending/total_pending:.1f}%)")

    print(f"\n{'─'*80}")
    print("DETAILED RESULTS")
    print(f"{'─'*80}\n")

    for r in results:
        status = "✅" if r['can_fetch'] else "❌"
        print(f"{status} {r['slug']} ({r['pending']} pending)")
        print(f"   {r['recommendation']}")
        if r.get('sample_url'):
            print(f"   Sample URL: {r['sample_url'][:70]}...")
        print()

    if args.json:
        print("\n" + json.dumps(results, indent=2))

    # Show podcasts that need attention
    if cannot_fetch:
        print(f"\n{'='*80}")
        print("PODCASTS NEEDING ATTENTION")
        print(f"{'='*80}\n")
        for r in cannot_fetch:
            print(f"  • {r['slug']} ({r['pending']} episodes)")


if __name__ == '__main__':
    main()
