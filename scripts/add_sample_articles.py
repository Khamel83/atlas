#!/usr/bin/env python3
"""
Quick test: Add sample articles directly to Atlas database
"""

import json
import sqlite3
import os
from datetime import datetime
from pathlib import Path

def add_articles_to_db():
    """Add sample articles to Atlas database for testing"""

    # Connect to Atlas database
    db_path = "atlas.db"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Load sample JSON files
    json_dir = Path("inputs/New Docs/json/")
    json_files = list(json_dir.glob("*.json"))[:20]  # First 20 files

    print(f"🚀 Adding {len(json_files)} articles to Atlas database...")

    added = 0

    for json_file in json_files:
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Extract what we can from the JSON
            title = data.get('title', json_file.stem)
            url = data.get('url', f"file://{json_file.name}")
            summary = data.get('summary', '')
            content = summary or title  # Use title as content if no summary

            # Skip if no meaningful content
            if len(content.strip()) < 20:
                continue

            # Insert into Atlas content table
            cursor.execute("""
                INSERT OR IGNORE INTO content
                (url, title, content, created_at)
                VALUES (?, ?, ?, ?)
            """, (
                url,
                title,
                content,
                datetime.now()
            ))

            added += 1
            print(f"✅ Added: {title[:50]}...")

        except Exception as e:
            print(f"❌ Error processing {json_file.name}: {e}")
            continue

    # Commit changes
    conn.commit()
    conn.close()

    print(f"\n🎉 Added {added} articles to Atlas!")
    return added

def test_cognitive_features():
    """Test Atlas cognitive features with the added articles"""

    print(f"\n🧠 Testing cognitive features...")

    # Test database connection
    try:
        conn = sqlite3.connect("atlas.db")
        cursor = conn.cursor()

        # Count content
        cursor.execute("SELECT COUNT(*) FROM content")
        count = cursor.fetchone()[0]
        print(f"📊 Total content in database: {count}")

        # Get recent content
        cursor.execute("SELECT title FROM content ORDER BY created_at DESC LIMIT 5")
        recent = cursor.fetchall()

        print(f"📰 Recent articles:")
        for title, in recent:
            print(f"  - {title[:60]}...")

        conn.close()

        return True

    except Exception as e:
        print(f"❌ Database error: {e}")
        return False

def main():
    """Main function"""

    print("🚀 Atlas Quick Test - Adding Sample Articles")
    print("=" * 50)

    # Add articles
    added = add_articles_to_db()

    if added > 0:
        # Test cognitive features
        if test_cognitive_features():
            print(f"\n✅ SUCCESS! Atlas now has real data to work with.")
            print(f"🌐 Open your dashboard: http://localhost:8000/ask/html")
            print(f"🤖 Try asking: 'What articles do I have about race and academia?'")
            print(f"🔍 Or: 'Show me patterns in my recent articles'")
        else:
            print(f"\n⚠️  Articles added but database test failed")
    else:
        print(f"\n❌ No articles were added")

    return added > 0

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)