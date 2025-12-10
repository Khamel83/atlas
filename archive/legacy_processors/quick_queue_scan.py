#!/usr/bin/env python3
"""
Quick scan to identify podcasts with RSS feeds and estimate episode counts
"""

import csv
import feedparser
import time

def main():
    print("QUICK PODCAST RSS SCAN")
    print("=" * 50)

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

    print(f"User podcasts: {len(user_podcasts)}")
    print(f"RSS mappings: {len(rss_mappings)}")

    # Quick scan of first 20 podcasts
    podcast_stats = []
    matched_count = 0

    for i, (podcast_name, requested_count) in enumerate(user_podcasts[:20]):
        if podcast_name not in rss_mappings:
            print(f"{i+1:2d}. {podcast_name[:30]:<30} ❌ No RSS")
            continue

        matched_count += 1
        rss_url = rss_mappings[podcast_name]

        try:
            # Quick feed parse with timeout
            feed = feedparser.parse(rss_url)
            episode_count = len(feed.entries)

            print(f"{i+1:2d}. {podcast_name[:30]:<30} ✅ {episode_count:4d} episodes")

            podcast_stats.append({
                'name': podcast_name,
                'requested': requested_count,
                'available': episode_count,
                'rss_url': rss_url
            })

        except Exception as e:
            print(f"{i+1:2d}. {podcast_name[:30]:<30} ❌ Error: {str(e)[:30]}")

        time.sleep(0.2)  # Small delay

    # Show summary
    print(f"\n{'='*50}")
    print(f"First 20 podcasts summary:")
    print(f"RSS feeds found: {matched_count}/20")
    print(f"Total episodes available: {sum(s['available'] for s in podcast_stats):,}")

    # Estimate full scale
    print(f"\nEstimated full scale (68 podcasts):")
    print(f"If similar ratio: ~{(68 * matched_count // 20)} podcasts with RSS")
    print(f"Potential episodes: ~{(68 * sum(s['available'] for s in podcast_stats) // 20):,}")

if __name__ == "__main__":
    main()