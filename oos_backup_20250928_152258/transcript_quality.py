#!/usr/bin/env python3

def is_real_transcript(content):
    """Simple check if content is a real transcript (not fake)"""
    if not content or len(content) < 5000:
        return False

    # Check for transcript-like patterns
    transcript_indicators = [
        "transcript", "speaker", "host", "guest",
        "[music]", "[applause]", "[laughter]",
        "welcome to", "today we", "our guest"
    ]

    content_lower = content.lower()
    indicators_found = sum(1 for indicator in transcript_indicators if indicator in content_lower)

    # Need at least 2 transcript indicators and 5k+ chars
    return indicators_found >= 2

def quality_filter(transcripts):
    """Filter list of transcripts to only real ones"""
    return [t for t in transcripts if is_real_transcript(t.get('content', ''))]

if __name__ == "__main__":
    import sqlite3

    conn = sqlite3.connect('data/atlas.db')

    # Check current quality
    transcripts = conn.execute('''
        SELECT title, content, LENGTH(content) as char_count
        FROM content
        WHERE content_type = 'podcast_transcript'
        ORDER BY char_count DESC
    ''').fetchall()

    print(f"📊 QUALITY CHECK OF {len(transcripts)} TRANSCRIPTS")
    print("=" * 50)

    real_count = 0
    fake_count = 0

    for title, content, char_count in transcripts:
        if is_real_transcript(content):
            real_count += 1
        else:
            fake_count += 1

    print(f"✅ Real transcripts: {real_count}")
    print(f"❌ Fake transcripts: {fake_count}")
    print(f"📈 Quality rate: {real_count/(real_count+fake_count)*100:.1f}%")

    conn.close()