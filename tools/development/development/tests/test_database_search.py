#!/usr/bin/env python3
"""
Test database search functionality with real data
"""

import sqlite3
from helpers.simple_database import SimpleDatabase

def test_search():
    """Test basic search functionality"""
    db = SimpleDatabase()
    conn = db.get_connection()
    cursor = conn.cursor()

    # Check total records
    cursor.execute('SELECT COUNT(*) FROM content')
    total = cursor.fetchone()[0]
    print(f"📊 Total records: {total}")

    # Test search queries
    search_terms = ['Stratechery', 'technology', 'Apple', 'AI', 'bitcoin']

    for term in search_terms:
        # Simple text search
        cursor.execute("""
            SELECT title, content_type,
                   substr(content, 1, 100) as excerpt
            FROM content
            WHERE content LIKE ? OR title LIKE ?
            LIMIT 5
        """, (f'%{term}%', f'%{term}%'))

        results = cursor.fetchall()

        print(f"\n🔍 Search '{term}': {len(results)} results")
        for i, (title, content_type, excerpt) in enumerate(results[:3], 1):
            print(f"  {i}. [{content_type}] {title[:60]}...")
            print(f"     {excerpt.strip()[:80]}...")

    # Content type breakdown
    cursor.execute("""
        SELECT content_type, COUNT(*) as count
        FROM content
        GROUP BY content_type
        ORDER BY count DESC
    """)

    types = cursor.fetchall()
    print(f"\n📈 Content types:")
    for content_type, count in types:
        print(f"  {content_type}: {count}")

    conn.close()

if __name__ == "__main__":
    test_search()