#!/usr/bin/env python3
"""
Process all Gmail Newsletter emails for Atlas
"""

from newsletter_processor import NewsletterProcessor
import time

def process_all_newsletters():
    """Process all newsletter emails"""
    print("🚀 STARTING FULL NEWSLETTER PROCESSING")
    print("=" * 60)
    print("This will process ALL 3,253 newsletter emails")
    print("This may take 30-60 minutes...")
    print()

    processor = NewsletterProcessor()

    # Check current database status
    import sqlite3
    try:
        conn = sqlite3.connect(processor.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM content WHERE content_type = 'newsletter'")
        existing_newsletters = cursor.fetchone()[0]
        conn.close()
        print(f"📊 Current newsletter count in Atlas: {existing_newsletters}")
    except:
        existing_newsletters = 0
        print(f"📊 Could not check existing newsletter count")

    print(f"📧 About to process up to 3,253 newsletter emails")

    # Start processing
    start_time = time.time()
    processor.process_newsletters()  # Process all emails
    end_time = time.time()

    # Final summary
    print(f"\n" + "=" * 60)
    print(f"🎉 FULL PROCESSING COMPLETE!")
    print(f"⏱️  Total time: {(end_time - start_time)/60:.1f} minutes")

    # Check final database status
    try:
        conn = sqlite3.connect(processor.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM content WHERE content_type = 'newsletter'")
        final_newsletters = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM content")
        total_content = cursor.fetchone()[0]
        conn.close()

        new_newsletters = final_newsletters - existing_newsletters
        print(f"📊 Final Summary:")
        print(f"   Newsletter content items: {final_newsletters}")
        print(f"   New newsletters added: {new_newsletters}")
        print(f"   Total Atlas content: {total_content}")
    except Exception as e:
        print(f"Could not generate final summary: {e}")

if __name__ == "__main__":
    response = input("Process all 3,253 newsletter emails? This will take 30-60 minutes. (y/N): ").strip().lower()
    if response == 'y':
        process_all_newsletters()
    else:
        print("Cancelled. Run again when ready to process all emails.")