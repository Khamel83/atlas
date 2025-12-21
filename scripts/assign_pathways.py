#!/usr/bin/env python3
"""
Assign transcript pathways to all podcasts.

Philosophy: Whisper (local transcription) should be the LAST RESORT.
We should always prefer public sources in this order:

1. WEBSITE - Direct from podcast website (best quality)
2. NETWORK - NPR/Slate/WNYC official transcripts
3. NYT - New York Times transcript pages
4. PODSCRIPTS - Podscripts.co AI transcripts (covers most shows)
5. YOUTUBE - YouTube auto-captions (needs VPN)
6. WHISPER - Local transcription (only when no public source exists)

Usage:
    python scripts/assign_pathways.py              # Dry run
    python scripts/assign_pathways.py --apply      # Apply changes
    python scripts/assign_pathways.py --verify     # Just verify podscripts coverage
"""

import argparse
import sqlite3
import requests
import time
import sys
from pathlib import Path

# Known sources by podcast
WEBSITE_DIRECT = {
    'stratechery',
    'acquired',
    'lex-fridman-podcast',
    'conversations-with-tyler',
}

NETWORK_PODCASTS = {
    'planet-money', 'the-indicator', 'the-indicator-from-planet-money',
    'code-switch', 'throughline', 'fresh-air', 'hidden-brain',
    'ted-radio-hour', 'embedded', 'how-i-built-this',
    'the-npr-politics-podcast', 'pop-culture-happy-hour',
    'wait-wait-donapost-tell-me',
}

NYT_PODCASTS = {
    'hard-fork',
    'the-ezra-klein-show',
}

# Podcasts we KNOW are paywalled with no public transcripts
TRULY_PAYWALLED = {
    # Add podcasts here only after verifying they have NO public source
    # Currently empty - we found all our 'local' podcasts have podscripts!
}


def check_podscripts(slug: str, cache: dict) -> bool:
    """Check if a podcast exists on podscripts.co"""
    if slug in cache:
        return cache[slug]

    try:
        # Try the slug directly
        resp = requests.head(
            f'https://podscripts.co/podcasts/{slug}',
            timeout=5,
            allow_redirects=True
        )
        exists = resp.status_code == 200
        cache[slug] = exists
        time.sleep(0.3)  # Be polite
        return exists
    except Exception as e:
        print(f"  Warning: Failed to check {slug}: {e}")
        cache[slug] = False
        return False


def assign_pathway(slug: str, rss_url: str, podscripts_cache: dict) -> tuple[str, str]:
    """
    Determine the best pathway for a podcast.
    Returns (pathway, reason).
    """
    rss = rss_url or ''

    # 1. Known website sources (highest quality)
    if slug in WEBSITE_DIRECT:
        return 'website', 'Known website source'

    # 2. Network podcasts (official transcripts)
    if slug in NETWORK_PODCASTS:
        return 'network', 'NPR/Slate/WNYC network'

    # Check RSS domain for network hints
    if any(domain in rss for domain in ['npr.org', 'prx.org']):
        return 'network', 'NPR/PRX RSS feed'

    # 3. NYT podcasts
    if slug in NYT_PODCASTS:
        return 'nyt', 'NYT transcript page'

    if 'nytimes.com' in rss or 'nyt.com' in rss:
        return 'nyt', 'NYT RSS feed'

    # 4. Check podscripts.co (covers most shows)
    if check_podscripts(slug, podscripts_cache):
        return 'podscripts', 'Found on podscripts.co'

    # 5. Check for YouTube hints
    if 'youtube' in rss:
        return 'youtube', 'YouTube RSS feed'

    # 6. Known paywalled
    if slug in TRULY_PAYWALLED:
        return 'whisper', 'Confirmed paywalled'

    # 7. Default to whisper (but flag for review)
    return 'whisper', 'No public source found - VERIFY'


def main():
    parser = argparse.ArgumentParser(description='Assign transcript pathways to podcasts')
    parser.add_argument('--apply', action='store_true', help='Apply changes to database')
    parser.add_argument('--verify', action='store_true', help='Just verify podscripts coverage')
    args = parser.parse_args()

    db_path = Path(__file__).parent.parent / 'data/podcasts/atlas_podcasts.db'
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # Get all podcasts with pending episodes
    cur.execute('''
        SELECT p.id, p.slug, p.name, p.rss_url, p.pathway,
               COUNT(CASE WHEN e.transcript_status IN ('unknown', 'local') THEN 1 END) as pending,
               COUNT(CASE WHEN e.transcript_status = 'local' THEN 1 END) as local_count,
               COUNT(*) as total
        FROM podcasts p
        LEFT JOIN episodes e ON p.id = e.podcast_id
        GROUP BY p.id
        ORDER BY pending DESC
    ''')

    podcasts = cur.fetchall()
    podscripts_cache = {}

    print("PATHWAY ASSIGNMENT")
    print("=" * 80)
    print()

    if args.verify:
        print("Verification mode - checking podscripts coverage only")
        print()

    changes = []
    by_pathway = {}

    for pid, slug, name, rss_url, current_pathway, pending, local_count, total in podcasts:
        if pending == 0 and not args.verify:
            continue  # Skip podcasts with no pending work

        pathway, reason = assign_pathway(slug, rss_url, podscripts_cache)

        if pathway not in by_pathway:
            by_pathway[pathway] = []
        by_pathway[pathway].append({
            'id': pid,
            'slug': slug,
            'pending': pending,
            'local': local_count,
            'pathway': pathway,
            'reason': reason,
            'current': current_pathway
        })

        # Track changes
        if current_pathway != pathway:
            changes.append({
                'id': pid,
                'slug': slug,
                'from': current_pathway,
                'to': pathway,
                'reason': reason,
                'local_count': local_count
            })

    # Summary by pathway
    print("PODCASTS BY PATHWAY:")
    print("-" * 80)

    for pathway in ['website', 'network', 'nyt', 'podscripts', 'youtube', 'whisper', 'unknown']:
        pods = by_pathway.get(pathway, [])
        if not pods:
            continue

        total_pending = sum(p['pending'] for p in pods)
        total_local = sum(p['local'] for p in pods)

        icon = {
            'website': '🌐',
            'network': '📻',
            'nyt': '📰',
            'podscripts': '🤖',
            'youtube': '📺',
            'whisper': '🎙️',
            'unknown': '❓'
        }.get(pathway, '?')

        print(f"\n{icon} {pathway.upper()} ({len(pods)} podcasts, {total_pending} pending)")

        for p in sorted(pods, key=lambda x: -x['pending'])[:10]:
            local_note = f" [was local: {p['local']}]" if p['local'] > 0 else ""
            print(f"   {p['slug']:<40} {p['pending']:>4} pending{local_note}")

        if len(pods) > 10:
            print(f"   ... and {len(pods) - 10} more")

    # Changes summary
    print()
    print("=" * 80)
    print("CHANGES TO APPLY:")
    print("-" * 80)

    if not changes:
        print("No pathway changes needed.")
    else:
        recoverable = [c for c in changes if c['local_count'] > 0 and c['to'] != 'whisper']

        if recoverable:
            print(f"\n🎉 RECOVERED FROM WHISPER: {len(recoverable)} podcasts can use public sources!")
            for c in recoverable:
                print(f"   {c['slug']}: local({c['local_count']}) → {c['to']} ({c['reason']})")

        other_changes = [c for c in changes if c not in recoverable]
        if other_changes:
            print(f"\nOther pathway updates: {len(other_changes)}")
            for c in other_changes[:20]:
                print(f"   {c['slug']}: {c['from']} → {c['to']} ({c['reason']})")

    # Apply changes
    if args.apply and changes:
        print()
        print("=" * 80)
        print("APPLYING CHANGES...")

        for c in changes:
            # Update pathway
            cur.execute('UPDATE podcasts SET pathway = ? WHERE id = ?', (c['to'], c['id']))

            # If recovering from local, change episode status back to 'unknown'
            if c['local_count'] > 0 and c['to'] != 'whisper':
                cur.execute('''
                    UPDATE episodes
                    SET transcript_status = 'unknown'
                    WHERE podcast_id = ? AND transcript_status = 'local'
                ''', (c['id'],))
                print(f"  ✅ {c['slug']}: pathway={c['to']}, {c['local_count']} episodes reset to 'unknown'")

        conn.commit()
        print()
        print(f"Applied {len(changes)} pathway changes.")
        print("Run `python -m modules.podcasts.cli fetch-transcripts --all` to fetch using new pathways.")

    elif changes and not args.apply:
        print()
        print("DRY RUN - use --apply to make changes")

    conn.close()


if __name__ == '__main__':
    main()
