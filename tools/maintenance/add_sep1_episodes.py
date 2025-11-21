#!/usr/bin/env python3
"""
Add all episodes since September 1, 2025 to the queue
"""

import csv
import feedparser
import sqlite3
from datetime import datetime
import time

def main():
    print("ADDING EPISODES SINCE SEPTEMBER 1, 2025")
    print("=" * 60)

    # Connect to database
    conn = sqlite3.connect('data/atlas.db')
    cursor = conn.cursor()

    # Load user podcasts and RSS mappings
    user_podcasts = []
    with open('config/podcast_config.csv', 'r') as f:
        reader = csv.reader(f)
        next(reader)  # Skip header
        for row in reader:
            if len(row) >= 6 and row[5] == '0':  # Not excluded
                podcast_name = row[1].strip('\"')
                future = row[3] == '1'
                user_podcasts.append((podcast_name, future))

    rss_mappings = {}
    with open('config/podcast_rss_feeds.csv', 'r') as f:
        reader = csv.reader(f)
        for row in reader:
            if len(row) >= 2:
                podcast_name = row[0].strip('\"')
                rss_url = row[1].strip('\"')
                rss_mappings[podcast_name] = rss_url

    print(f"Processing {len(user_podcasts)} user podcasts")
    print(f"RSS mappings available: {len(rss_mappings)}")

    # Define cutoff date
    cutoff_date = datetime(2025, 9, 1)
    print(f"Finding episodes since: {cutoff_date.strftime('%Y-%m-%d')}")

    # Track what we'll add
    total_to_add = 0
    episodes_to_add = []

    # First pass: count episodes since Sep 1
    print("\nCOUNTING EPISODES SINCE SEPTEMBER 1, 2025")
    print("-" * 50)

    for podcast_name, future in user_podcasts:
        if podcast_name not in rss_mappings:
            continue

        rss_url = rss_mappings[podcast_name]

        try:
            feed = feedparser.parse(rss_url)
            podcast_count = 0

            for entry in feed.entries:
                pub_date = entry.get('published_parsed')
                if pub_date:
                    pub_datetime = datetime(*pub_date[:6])

                    if pub_datetime >= cutoff_date:
                        episode_url = entry.get('link', '')
                        if episode_url:
                            podcast_count += 1
                            episodes_to_add.append({
                                'podcast_name': podcast_name,
                                'episode_title': entry.get('title', 'Untitled Episode'),
                                'episode_url': episode_url,
                                'rss_url': rss_url,
                                'pub_date': pub_datetime
                            })

            if podcast_count > 0:
                print(f"  {podcast_name}: {podcast_count} episodes")
                total_to_add += podcast_count

        except Exception as e:
            print(f"  ❌ Error counting {podcast_name}: {e}")

    print(f"\nTotal episodes to add: {total_to_add:,}")

    # Check what's already in queue to avoid duplicates
    print("\nCHECKING FOR EXISTING QUEUE ITEMS")
    print("-" * 40)

    existing_urls = set()
    cursor.execute("SELECT episode_url FROM episode_queue")
    for row in cursor.fetchall():
        existing_urls.add(row[0])

    # Also check already processed content
    cursor.execute("SELECT url FROM content WHERE content_type = 'podcast_transcript'")
    for row in cursor.fetchall():
        existing_urls.add(row[0])

    print(f"Existing URLs in queue/database: {len(existing_urls):,}")

    # Filter out duplicates
    new_episodes = [ep for ep in episodes_to_add if ep['episode_url'] not in existing_urls]
    duplicates = len(episodes_to_add) - len(new_episodes)

    print(f"New episodes to add: {len(new_episodes):,}")
    print(f"Duplicate episodes: {duplicates:,}")

    if len(new_episodes) == 0:
        print("No new episodes to add!")
        conn.close()
        return

    # Add to queue
    print(f"\nADDING {len(new_episodes)} EPISODES TO QUEUE")
    print("-" * 50)

    added_count = 0
    for i, episode in enumerate(new_episodes):
        try:
            cursor.execute("""
                INSERT INTO episode_queue
                (podcast_name, episode_title, episode_url, rss_url, status, created_at, updated_at)
                VALUES (?, ?, ?, ?, 'pending', ?, ?)
            """, (
                episode['podcast_name'],
                episode['episode_title'],
                episode['episode_url'],
                episode['rss_url'],
                datetime.now().isoformat(),
                datetime.now().isoformat()
            ))

            added_count += 1

            if added_count % 100 == 0:
                print(f"  Added {added_count}/{len(new_episodes)} episodes...")

        except Exception as e:
            print(f"  ❌ Error adding episode: {e}")

    conn.commit()

    # Final verification
    final_count = cursor.execute("SELECT COUNT(*) FROM episode_queue WHERE status = 'pending'").fetchone()[0]

    print(f"\n{'='*60}")
    print("SEPTEMBER 1, 2025 EPISODES ADDED")
    print(f"{'='*60}")
    print(f"Episodes added: {added_count:,}")
    print(f"Total pending in queue: {final_count:,}")

    # Show top podcasts by episode count
    print(f"\nTOP PODCASTS BY NEW EPISODES:")
    cursor.execute("""
        SELECT podcast_name, COUNT(*) as episode_count
        FROM episode_queue
        WHERE status = 'pending'
        GROUP BY podcast_name
        ORDER BY episode_count DESC
        LIMIT 15
    """)

    for podcast, count in cursor.fetchall():
        print(f"  {podcast}: {count} episodes")

    conn.close()

if __name__ == "__main__":
    main()