# SIMPLE PODCAST FIX - QWEN CODE COMPATIBLE

## CURRENT STATUS: SUPERSEDED BY MAIN PIPELINE

This document outlines a simplified, proof-of-concept approach for podcast processing. The core functionality described here has been fully integrated and expanded upon in the main `SmartTranscriptionPipeline` (`helpers/smart_transcription_pipeline.py`).

For the complete and robust podcast ingestion and transcription system, please refer to `PODCAST_PROCESSING_MASTER_PLAN.md` and the `smart_transcription.py` script.

## THE PROBLEM
*(Note: These problems have been addressed by the main `SmartTranscriptionPipeline`.)*
- Database has 6 articles ABOUT podcasts, not actual episodes (now handles real episodes).
- No RSS feed ingestion exists (now integrated).
- Scheduler runs 3 minutes then exits (now continuous processing and queuing).

## SIMPLE 3-STEP FIX

### STEP 1: Create Simple RSS Importer

**File: `simple_rss_import.py`**
```python
#!/usr/bin/env python3
import feedparser
import sqlite3
import requests

# Simple RSS feed importer - run once to populate episodes
feeds = {
    "Acquired": "https://feeds.simplecast.com/7wT59F0l",
    "99% Invisible": "https://feeds.99percentinvisible.org/99percentinvisible",
    "This American Life": "https://feeds.thisamericanlife.org/talpodcast",
    "Radiolab": "https://feeds.feedburner.com/radiolab",
    "ATP": "https://atp.fm/rss"
}

def import_episodes():
    # Create table
    with sqlite3.connect("data/atlas.db") as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS podcast_episodes (
                id INTEGER PRIMARY KEY,
                title TEXT,
                audio_url TEXT UNIQUE,
                podcast_name TEXT,
                processed BOOLEAN DEFAULT 0
            )
        """)

        total = 0
        for name, url in feeds.items():
            print(f"Importing {name}...")
            feed = feedparser.parse(url)

            for entry in feed.entries[:10]:  # Only 10 per podcast for testing
                audio_url = None
                if hasattr(entry, 'enclosures'):
                    for enc in entry.enclosures:
                        if 'audio' in enc.type:
                            audio_url = enc.href
                            break

                if audio_url:
                    try:
                        conn.execute("""
                            INSERT OR IGNORE INTO podcast_episodes
                            (title, audio_url, podcast_name)
                            VALUES (?, ?, ?)
                        """, (entry.title, audio_url, name))
                        total += 1
                    except:
                        pass

        conn.commit()
        print(f"Imported {total} episodes")

if __name__ == "__main__":
    import_episodes()
```

### STEP 2: Create Simple Continuous Processor

**File: `simple_processor.py`**
```python
#!/usr/bin/env python3
import sqlite3
import time
import sys

def process_episodes():
    """Simple processing - just mark episodes as processed"""
    with sqlite3.connect("data/atlas.db") as conn:
        # Get unprocessed episodes
        episodes = conn.execute("""
            SELECT id, title, podcast_name
            FROM podcast_episodes
            WHERE processed = 0
            LIMIT 5
        """).fetchall()

        if not episodes:
            print("No episodes to process")
            return False

        for episode_id, title, podcast in episodes:
            print(f"Processing: {title[:50]}...")

            # Simulate processing - add to main content table
            conn.execute("""
                INSERT OR REPLACE INTO content
                (title, content, content_type, created_at)
                VALUES (?, ?, 'podcast_episode', CURRENT_TIMESTAMP)
            """, (f"[PODCAST] {title}", f"Transcript for {title} from {podcast}"))

            # Mark as processed
            conn.execute("""
                UPDATE podcast_episodes
                SET processed = 1
                WHERE id = ?
            """, (episode_id,))

        conn.commit()
        print(f"Processed {len(episodes)} episodes")
        return True

def run_continuous():
    """Run processor every 30 seconds"""
    print("Starting simple continuous processor...")

    try:
        while True:
            if process_episodes():
                print("Work done, sleeping 30 seconds...")
            else:
                print("No work, sleeping 30 seconds...")

            time.sleep(30)
    except KeyboardInterrupt:
        print("Stopping processor")

if __name__ == "__main__":
    if "--continuous" in sys.argv:
        run_continuous()
    else:
        process_episodes()
```

### STEP 3: Simple Start Script

**File: `start_simple.sh`**
```bash
#!/bin/bash
echo "Starting Simple Podcast System"

# Step 1: Import episodes once
python3 simple_rss_import.py

# Step 2: Start continuous processing in background
nohup python3 simple_processor.py --continuous > processor.log 2>&1 &
echo $! > processor.pid

echo "✅ Simple system started!"
echo "Check: tail -f processor.log"
echo "Test: sqlite3 data/atlas.db 'SELECT COUNT(*) FROM podcast_episodes;'"
```

## QWEN CODE EXECUTION STEPS

1. **Copy these 3 files** (simple_rss_import.py, simple_processor.py, start_simple.sh)

2. **Install dependency:**
   ```bash
   pip install feedparser
   ```

3. **Run the system:**
   ```bash
   chmod +x start_simple.sh
   ./start_simple.sh
   ```

4. **Verify working:**
   ```bash
   # Check episodes imported
   sqlite3 data/atlas.db "SELECT COUNT(*) FROM podcast_episodes;"

   # Check processing
   tail processor.log

   # Test search
   curl "http://localhost:7444/api/v1/search/?query=podcast&limit=3"
   ```

5. **Stop system:**
   ```bash
   kill $(cat processor.pid)
   ```

## WHAT THIS FIXES
*(Note: These points are now fully addressed by the main `SmartTranscriptionPipeline`.)*
- ✅ Gets real podcast episodes in database (50 episodes from 5 shows)
- ✅ Continuous processor that doesn't exit
- ✅ Searchable podcast content
- ✅ Simple to run and understand

## LIMITATIONS
*(Note: These limitations are overcome by the main `SmartTranscriptionPipeline`.)*
- No actual audio download/transcription (just placeholder text) - **Main system performs full audio download and transcription.**
- Only 5 podcast feeds (easy to add more) - **Main system uses `podcasts_prioritized_cleaned.csv` for a comprehensive list.**
- Basic processing (good enough for testing) - **Main system offers robust, configurable processing.**

**This simple version will work in qwen code and prove the concept works.**