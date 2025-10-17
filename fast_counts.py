#!/usr/bin/env python3
"""
Fast episode count scanner - minimal processing
"""

import csv
import feedparser
import concurrent.futures
import time

def get_episode_count(podcast_name, rss_url):
    """Get episode count for a single podcast"""
    try:
        feed = feedparser.parse(rss_url)
        return len(feed.entries)
    except:
        return 0

def main():
    print("FAST EPISODE COUNT SCANNER")
    print("=" * 50)

    # Load data
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

    # Prepare tasks
    tasks = []
    for podcast_name, requested_count in user_podcasts:
        if podcast_name in rss_mappings:
            tasks.append((podcast_name, rss_mappings[podcast_name], requested_count))

    print(f"Processing {len(tasks)} podcasts with RSS feeds...")

    # Process in parallel with smaller batches
    results = []
    batch_size = 10

    for i in range(0, len(tasks), batch_size):
        batch = tasks[i:i+batch_size]
        print(f"Processing batch {i//batch_size + 1}/{(len(tasks)-1)//batch_size + 1}")

        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            future_to_podcast = {
                executor.submit(get_episode_count, name, url): (name, url, requested)
                for name, url, requested in batch
            }

            for future in concurrent.futures.as_completed(future_to_podcast):
                podcast_name, rss_url, requested_count = future_to_podcast[future]
                try:
                    available_count = future.result()
                    results.append({
                        'name': podcast_name,
                        'requested': requested_count,
                        'available': available_count,
                        'rss_url': rss_url
                    })
                    print(f"  {podcast_name}: {available_count} episodes")
                except Exception as e:
                    results.append({
                        'name': podcast_name,
                        'requested': requested_count,
                        'available': 0,
                        'rss_url': rss_url
                    })
                    print(f"  {podcast_name}: Error")

        time.sleep(1)  # Delay between batches

    # Calculate totals
    total_requested = sum(r['requested'] for r in results)
    total_available = sum(r['available'] for r in results)

    print(f"\n{'='*50}")
    print("FINAL COUNTS")
    print(f"{'='*50}")
    print(f"Podcasts with RSS: {len(results)}")
    print(f"Total episodes requested: {total_requested:,}")
    print(f"Total episodes available: {total_available:,}")

    # Expected to process
    expected_to_process = 0
    for r in results:
        if r['requested'] > 0:
            expected_to_process += min(r['requested'], r['available'])
        else:
            expected_to_process += r['available']

    print(f"Expected episodes to process: {expected_to_process:,}")

    # Top 10 podcasts
    print(f"\nTOP 10 PODCASTS:")
    sorted_results = sorted(results, key=lambda x: x['available'], reverse=True)[:10]
    for i, r in enumerate(sorted_results, 1):
        print(f"{i:2d}. {r['name']}: {r['available']:,} episodes")

if __name__ == "__main__":
    main()