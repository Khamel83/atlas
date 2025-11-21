#!/usr/bin/env python3
"""
Get REAL episode counts for all 68 user podcasts
"""

import csv
import feedparser
import time

def main():
    print("GETTING REAL EPISODE COUNTS FOR ALL 68 PODCASTS")
    print("=" * 70)

    # Load RSS mappings and user podcasts
    rss_mappings = {}
    with open('config/podcast_rss_feeds.csv', 'r') as f:
        reader = csv.reader(f)
        for row in reader:
            if len(row) >= 2:
                podcast_name = row[0].strip('"')
                rss_url = row[1].strip('"')
                rss_mappings[podcast_name] = rss_url

    user_podcasts = []
    with open('config/podcast_config.csv', 'r') as f:
        reader = csv.reader(f)
        next(reader)
        for row in reader:
            if len(row) >= 6 and row[5] == '0':
                podcast_name = row[1].strip('"')
                episode_count = int(row[2]) if row[2].isdigit() else 0
                user_podcasts.append((podcast_name, episode_count))

    print(f"Total user podcasts: {len(user_podcasts)}")
    print(f"RSS mappings available: {len(rss_mappings)}")
    print("=" * 70)

    # Track results
    results = []
    total_available = 0
    total_requested = 0
    podcasts_with_rss = 0

    for i, (podcast_name, requested_count) in enumerate(user_podcasts, 1):
        print(f"[{i:2d}/{len(user_podcasts)}] {podcast_name}")

        total_requested += requested_count

        if podcast_name not in rss_mappings:
            print(f"   ❌ No RSS feed found")
            results.append({
                'name': podcast_name,
                'requested': requested_count,
                'available': 0,
                'rss_url': None
            })
            continue

        podcasts_with_rss += 1
        rss_url = rss_mappings[podcast_name]
        print(f"   RSS: {rss_url}")

        try:
            # Parse RSS feed
            feed = feedparser.parse(rss_url)
            available_count = len(feed.entries)

            print(f"   ✅ {available_count} episodes available")

            total_available += available_count
            results.append({
                'name': podcast_name,
                'requested': requested_count,
                'available': available_count,
                'rss_url': rss_url
            })

        except Exception as e:
            print(f"   ❌ Error: {str(e)[:50]}...")
            results.append({
                'name': podcast_name,
                'requested': requested_count,
                'available': 0,
                'rss_url': rss_url
            })

        # Small delay to avoid overwhelming servers
        time.sleep(0.3)

    # Show summary
    print("\n" + "=" * 70)
    print("REAL COUNTS SUMMARY")
    print("=" * 70)
    print(f"Total user podcasts: {len(user_podcasts)}")
    print(f"Podcasts with RSS feeds: {podcasts_with_rss}")
    print(f"Podcasts without RSS: {len(user_podcasts) - podcasts_with_rss}")
    print(f"Total episodes requested: {total_requested:,}")
    print(f"Total episodes available: {total_available:,}")

    if total_requested > 0:
        coverage = (total_available / total_requested) * 100
        print(f"Coverage of requested: {coverage:.1f}%")

    # Show detailed breakdown
    print(f"\nDETAILED BREAKDOWN:")
    print("-" * 70)

    for result in results:
        status = "✅" if result['available'] > 0 else "❌"
        requested = result['requested']
        available = result['available']
        will_process = min(requested, available) if requested > 0 else available

        print(f"{status} {result['name']}")
        print(f"    Requested: {requested:,}, Available: {available:,}, Will process: {will_process:,}")

    # Show top 10 podcasts by episode count
    print(f"\nTOP 10 PODCASTS BY EPISODE COUNT:")
    sorted_results = sorted(results, key=lambda x: x['available'], reverse=True)[:10]
    for i, result in enumerate(sorted_results, 1):
        if result['available'] > 0:
            print(f"{i:2d}. {result['name']}: {result['available']:,} episodes")

    print(f"\n{'='*70}")
    print(f"EXPECTED TOTAL EPISODES TO PROCESS: {min(total_requested, total_available):,}")
    print("=" * 70)

if __name__ == "__main__":
    main()