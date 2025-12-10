#!/usr/bin/env python3
"""
Quick check for episodes since September 1, 2025
"""

import csv
import feedparser
from datetime import datetime
import concurrent.futures
import time

def check_podcast_episodes(podcast_name, rss_url):
    """Check episodes since Sep 1 for one podcast"""
    try:
        cutoff_date = datetime(2025, 9, 1)
        feed = feedparser.parse(rss_url)
        count = 0

        for entry in feed.entries:
            pub_date = entry.get('published_parsed')
            if pub_date:
                pub_datetime = datetime(*pub_date[:6])
                if pub_datetime >= cutoff_date:
                    count += 1

        return podcast_name, count, None
    except Exception as e:
        return podcast_name, 0, str(e)

def main():
    print("CHECKING EPISODES SINCE SEPTEMBER 1, 2025")
    print("=" * 50)

    # Load data
    rss_mappings = {}
    with open('config/podcast_rss_feeds.csv', 'r') as f:
        reader = csv.reader(f)
        for row in reader:
            if len(row) >= 2:
                rss_mappings[row[0].strip('\"')] = row[1].strip('\"')

    user_podcasts = []
    with open('config/podcast_config.csv', 'r') as f:
        reader = csv.reader(f)
        next(reader)
        for row in reader:
            if len(row) >= 6 and row[5] == '0':
                user_podcasts.append(row[1].strip('\"'))

    print(f"Checking {len(user_podcasts)} podcasts...")

    # Process in batches
    tasks = [(name, rss_mappings[name]) for name in user_podcasts if name in rss_mappings]

    total_episodes = 0
    podcasts_with_episodes = 0

    # Process in smaller batches
    batch_size = 10
    for i in range(0, len(tasks), batch_size):
        batch = tasks[i:i+batch_size]
        print(f"Processing batch {i//batch_size + 1}/{(len(tasks)-1)//batch_size + 1}")

        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(check_podcast_episodes, name, url) for name, url in batch]

            for future in concurrent.futures.as_completed(futures):
                podcast_name, count, error = future.result()

                if error:
                    print(f"  ❌ {podcast_name}: Error")
                elif count > 0:
                    print(f"  📅 {podcast_name}: {count} episodes")
                    total_episodes += count
                    podcasts_with_episodes += 1

        time.sleep(1)  # Delay between batches

    print(f"\n{'='*50}")
    print("RESULTS")
    print(f"{'='*50}")
    print(f"Podcasts with episodes since Sep 1: {podcasts_with_episodes}")
    print(f"Total episodes since Sep 1: {total_episodes:,}")

    if total_episodes > 0:
        print(f"Average episodes per podcast: {total_episodes/podcasts_with_episodes:.1f}")

if __name__ == "__main__":
    main()