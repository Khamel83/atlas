#!/usr/bin/env python3
"""
Simple and efficient episode queue builder
"""

import csv
import feedparser
import sqlite3
from datetime import datetime
import time

def main():
    print("SIMPLE EPISODE QUEUE BUILDER")
    print("=" * 60)

    # Connect to database
    conn = sqlite3.connect('data/atlas.db')
    cursor = conn.cursor()

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

    print(f"Found {len(user_podcasts)} user podcasts")
    print(f"Found {len(rss_mappings)} RSS mappings")

    # Build queue
    total_episodes = 0
    processed_podcasts = 0

    for i, (podcast_name, requested_count) in enumerate(user_podcasts):
        if podcast_name not in rss_mappings:
            continue

        print(f"\n[{i+1}/{len(user_podcasts)}] {podcast_name}")

        try:
            # Parse RSS feed
            feed = feedparser.parse(rss_mappings[podcast_name])

            if not feed.entries:
                print("  ❌ No episodes found")
                continue

            print(f"  Found {len(feed.entries)} episodes")

            # Determine how many episodes to add
            episodes_to_add = feed.entries
            if requested_count > 0:
                episodes_to_add = feed.entries[:requested_count]
                print(f"  Limited to {len(episodes_to_add)} episodes (requested)")

            # Add episodes to database
            added = 0
            for entry in episodes_to_add:
                episode_url = entry.get('link', '')
                if not episode_url:
                    continue

                title = entry.get('title', 'Untitled Episode')

                # Check if already exists
                existing = cursor.execute(
                    "SELECT id FROM episode_queue WHERE episode_url = ?",
                    (episode_url,)
                ).fetchone()

                if existing:
                    continue

                # Add to queue
                cursor.execute("""
                    INSERT INTO episode_queue
                    (podcast_name, episode_title, episode_url, rss_url, status, created_at, updated_at)
                    VALUES (?, ?, ?, ?, 'pending', ?, ?)
                """, (
                    podcast_name,
                    title,
                    episode_url,
                    rss_mappings[podcast_name],
                    datetime.now().isoformat(),
                    datetime.now().isoformat()
                ))
                added += 1

            total_episodes += added
            processed_podcasts += 1
            print(f"  ✅ Added {added} episodes")

            # Small delay
            time.sleep(0.5)

        except Exception as e:
            print(f"  ❌ Error: {e}")

    # Commit and show results
    conn.commit()

    print(f"\n{'='*60}")
    print("QUEUE BUILDING COMPLETE")
    print(f"{'='*60}")
    print(f"Processed podcasts: {processed_podcasts}")
    print(f"Total episodes in queue: {total_episodes:,}")

    # Show top 10 podcasts by episode count
    print(f"\nTOP 10 PODCASTS BY EPISODES:")
    cursor.execute("""
        SELECT podcast_name, COUNT(*) as episode_count
        FROM episode_queue
        GROUP BY podcast_name
        ORDER BY episode_count DESC
        LIMIT 10
    """)
    for row in cursor.fetchall():
        print(f"  {row[0]}: {row[1]} episodes")

    conn.close()

if __name__ == "__main__":
    main()