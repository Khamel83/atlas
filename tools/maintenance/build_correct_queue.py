#!/usr/bin/env python3
"""
Build CORRECT queue based on user's actual requests
"""

import csv
import feedparser
import sqlite3
from datetime import datetime
import time

def main():
    print("BUILDING CORRECT QUEUE BASED ON YOUR ACTUAL REQUESTS")
    print("=" * 70)

    # Connect to database
    conn = sqlite3.connect('data/atlas.db')
    cursor = conn.cursor()

    # Clear existing queue
    cursor.execute("DELETE FROM episode_queue")
    conn.commit()
    print("Cleared existing queue")

    # Load user's actual requests
    user_requests = []
    with open('config/podcast_config.csv', 'r') as f:
        reader = csv.reader(f)
        next(reader)  # Skip header
        for row in reader:
            if len(row) >= 6 and row[5] == '0':  # Not excluded
                podcast_name = row[1].strip('"')
                count = int(row[2]) if row[2].isdigit() else 0
                future = row[3] == '1'
                transcript_only = row[4] == '1'
                user_requests.append((podcast_name, count, future, transcript_only))

    # Load RSS mappings
    rss_mappings = {}
    with open('config/podcast_rss_feeds.csv', 'r') as f:
        reader = csv.reader(f)
        for row in reader:
            if len(row) >= 2:
                podcast_name = row[0].strip('"')
                rss_url = row[1].strip('"')
                rss_mappings[podcast_name] = rss_url

    print(f"Found {len(user_requests)} podcasts you want")

    # Calculate what we should process
    total_to_process = 0
    queue_plan = []

    for podcast_name, count, future, transcript_only in user_requests:
        if podcast_name not in rss_mappings:
            print(f"❌ No RSS feed for {podcast_name}")
            continue

        if count > 0:
            episodes_to_process = count
            queue_plan.append((podcast_name, rss_mappings[podcast_name], episodes_to_process, f"Count: {count}"))
            total_to_process += episodes_to_process
        else:
            # For 0 count, assume we want all available episodes
            queue_plan.append((podcast_name, rss_mappings[podcast_name], "ALL", f"Count: 0 (all available)"))

    print(f"Will process {total_to_process} episodes with specific counts + all episodes for 0-count podcasts")

    # Now build the queue
    added_count = 0
    processed_podcasts = 0

    for i, (podcast_name, rss_url, target_count, description) in enumerate(queue_plan, 1):
        print(f"\n[{i}/{len(queue_plan)}] {podcast_name}")
        print(f"   {description}")
        print(f"   RSS: {rss_url}")

        try:
            # Parse RSS feed
            feed = feedparser.parse(rss_url)

            if not feed.entries:
                print(f"   ❌ No episodes found in RSS")
                continue

            available = len(feed.entries)
            print(f"   Found {available} episodes in RSS")

            # Determine how many to add
            if target_count == "ALL":
                episodes_to_add = available
                print(f"   Will add ALL {available} episodes")
            else:
                episodes_to_add = min(target_count, available)
                print(f"   Will add {episodes_to_add} episodes (target: {target_count})")

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

                if j % 100 == 0 and j > 0:  # Progress update every 100 episodes
                    print(f"   Added {podcast_added}/{episodes_to_add} episodes...")

            conn.commit()
            processed_podcasts += 1
            print(f"   ✅ Added {podcast_added} episodes for {podcast_name}")

            # Small delay between podcasts
            time.sleep(0.3)

        except Exception as e:
            print(f"   ❌ Error processing {podcast_name}: {e}")

    # Final verification
    final_count = cursor.execute("SELECT COUNT(*) FROM episode_queue").fetchone()[0]
    distinct_podcasts = cursor.execute("SELECT COUNT(DISTINCT podcast_name) FROM episode_queue").fetchone()[0]

    print(f"\n{'='*70}")
    print("CORRECT QUEUE POPULATION COMPLETE")
    print(f"{'='*70}")
    print(f"Processed podcasts: {processed_podcasts}")
    print(f"Episodes added: {added_count}")
    print(f"Verified in database: {final_count}")
    print(f"Distinct podcasts: {distinct_podcasts}")

    if final_count == added_count:
        print(f"✅ SUCCESS: Queue built correctly!")

    # Show top podcasts by episode count
    print(f"\nTOP PODCASTS IN QUEUE:")
    cursor.execute("""
        SELECT podcast_name, COUNT(*) as episode_count
        FROM episode_queue
        GROUP BY podcast_name
        ORDER BY episode_count DESC
        LIMIT 15
    """)

    for podcast, count in cursor.fetchall():
        print(f"  {podcast}: {count} episodes")

    conn.close()

if __name__ == "__main__":
    main()