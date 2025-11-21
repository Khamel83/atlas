#!/usr/bin/env python3
"""
Build exact queue with 3,529 episodes based on user's requested counts
"""

import csv
import feedparser
import sqlite3
from datetime import datetime
import time

def main():
    print("BUILDING EXACT QUEUE - 3,529 EPISODES")
    print("=" * 60)

    # Connect to database
    conn = sqlite3.connect('data/atlas.db')
    cursor = conn.cursor()

    # Clear existing queue to start fresh
    cursor.execute("DELETE FROM episode_queue")
    conn.commit()
    print("Cleared existing queue")

    # Load user podcasts and their requested counts
    user_podcasts = []
    with open('config/podcast_config.csv', 'r') as f:
        reader = csv.reader(f)
        next(reader)
        for row in reader:
            if len(row) >= 6 and row[5] == '0':
                podcast_name = row[1].strip('"')
                requested_count = int(row[2]) if row[2].isdigit() else 0
                user_podcasts.append((podcast_name, requested_count))

    # Load RSS mappings
    rss_mappings = {}
    with open('config/podcast_rss_feeds.csv', 'r') as f:
        reader = csv.reader(f)
        for row in reader:
            if len(row) >= 2:
                podcast_name = row[0].strip('"')
                rss_url = row[1].strip('"')
                rss_mappings[podcast_name] = rss_url

    print(f"Processing {len(user_podcasts)} user podcasts")
    print(f"RSS mappings available: {len(rss_mappings)}")

    # Track what we'll add to queue
    queue_plan = []
    total_to_add = 0

    # Build the exact plan
    for podcast_name, requested_count in user_podcasts:
        if podcast_name not in rss_mappings:
            continue

        rss_url = rss_mappings[podcast_name]
        if requested_count > 0:
            episodes_to_add = requested_count
        else:
            episodes_to_add = 50  # Default for unlimited

        queue_plan.append((podcast_name, rss_url, episodes_to_add))
        total_to_add += episodes_to_add

    print(f"Will add {total_to_add} episodes to queue")

    # Now populate the queue
    added_count = 0
    processed_podcasts = 0

    for i, (podcast_name, rss_url, episodes_to_add) in enumerate(queue_plan, 1):
        print(f"\n[{i}/{len(queue_plan)}] {podcast_name}")
        print(f"   Target: {episodes_to_add} episodes")

        try:
            # Parse RSS feed
            feed = feedparser.parse(rss_url)

            if not feed.entries:
                print(f"   ❌ No episodes found in RSS")
                continue

            print(f"   Found {len(feed.entries)} episodes in RSS")

            # Add episodes to queue
            podcast_added = 0
            for j, entry in enumerate(feed.entries):
                if podcast_added >= episodes_to_add:
                    break

                episode_url = entry.get('link', '')
                if not episode_url:
                    continue

                title = entry.get('title', 'Untitled Episode')

                # Add to queue
                cursor.execute("""
                    INSERT INTO episode_queue
                    (podcast_name, episode_title, episode_url, rss_url, status, created_at, updated_at)
                    VALUES (?, ?, ?, ?, 'pending', ?, ?)
                """, (
                    podcast_name,
                    title,
                    episode_url,
                    rss_url,
                    datetime.now().isoformat(),
                    datetime.now().isoformat()
                ))

                podcast_added += 1
                added_count += 1

                if j % 50 == 0:  # Progress update every 50 episodes
                    print(f"   Added {podcast_added}/{episodes_to_add} episodes...")

            conn.commit()
            processed_podcasts += 1
            print(f"   ✅ Added {podcast_added} episodes for {podcast_name}")

            # Small delay between podcasts
            time.sleep(0.5)

        except Exception as e:
            print(f"   ❌ Error processing {podcast_name}: {e}")

    # Final verification
    final_count = cursor.execute("SELECT COUNT(*) FROM episode_queue").fetchone()[0]
    distinct_podcasts = cursor.execute("SELECT COUNT(DISTINCT podcast_name) FROM episode_queue").fetchone()[0]

    print(f"\n{'='*60}")
    print("QUEUE POPULATION COMPLETE")
    print(f"{'='*60}")
    print(f"Target: {total_to_add} episodes")
    print(f"Added: {added_count} episodes")
    print(f"Verified in database: {final_count} episodes")
    print(f"Processed podcasts: {processed_podcasts}")
    print(f"Distinct podcasts in queue: {distinct_podcasts}")

    if final_count == total_to_add:
        print(f"✅ SUCCESS: Exact target reached!")
    else:
        print(f"⚠️  Difference: {total_to_add - final_count} episodes")

    # Show queue summary by podcast
    print(f"\nQUEUE SUMMARY BY PODCAST:")
    cursor.execute("""
        SELECT podcast_name, COUNT(*) as episode_count
        FROM episode_queue
        GROUP BY podcast_name
        ORDER BY episode_count DESC
    """)

    results = cursor.fetchall()
    for podcast, count in results[:20]:  # Show top 20
        print(f"  {podcast}: {count} episodes")

    if len(results) > 20:
        print(f"  ... and {len(results) - 20} more podcasts")

    conn.close()

if __name__ == "__main__":
    main()