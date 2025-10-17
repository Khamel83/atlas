#!/usr/bin/env python3
"""
Clean up Low Quality Transcripts
Remove the 3 identified spam/fragment transcripts from database
"""

from helpers.database_config import get_database_connection

def main():
    # IDs of the 3 low-quality transcripts identified
    low_quality_ids = [37304, 37305, 173577]

    conn = get_database_connection()

    print("🧹 CLEANING UP LOW QUALITY TRANSCRIPTS")
    print("=" * 50)

    # First, show what we're about to delete
    for content_id in low_quality_ids:
        cursor = conn.execute(
            "SELECT title, length(content), content_type FROM content WHERE id = ?",
            (content_id,)
        )
        result = cursor.fetchone()
        if result:
            title, length, content_type = result
            print(f"Will delete ID {content_id}: {title[:50]} ({length} chars, {content_type})")
        else:
            print(f"ID {content_id} not found")

    print("\nProceeding with automatic cleanup...")

    # Automatically proceed
    deleted_count = 0
    for content_id in low_quality_ids:
        cursor = conn.execute("DELETE FROM content WHERE id = ?", (content_id,))
        if cursor.rowcount > 0:
            deleted_count += 1
            print(f"✅ Deleted transcript ID {content_id}")
        else:
            print(f"❌ Could not delete ID {content_id} (not found)")

    conn.commit()
    print(f"\n🎉 Successfully deleted {deleted_count} low-quality transcripts")

    # Verify cleanup
    cursor = conn.execute(
        "SELECT COUNT(*) FROM content WHERE content_type = 'podcast_transcript'"
    )
    remaining_count = cursor.fetchone()[0]
    print(f"📊 Remaining transcripts: {remaining_count}")

    conn.close()

if __name__ == "__main__":
    main()