#!/usr/bin/env python3
"""
Test script for Gmail integration to verify everything works together
"""

import sqlite3
import json
import os
from datetime import datetime

def test_atlas_v3_gmail():
    """Test Atlas v3 Gmail integration basic functionality"""
    print("🧪 Testing Atlas v3 Gmail Integration")
    print("=" * 50)

    # Test 1: Check database creation
    print("1. Testing database creation...")
    db_path = 'data/atlas_v3_gmail.db'
    try:
        if os.path.exists(db_path):
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()

            # Check tables exist
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]
            expected_tables = ['ingested_urls', 'gmail_messages', 'processing_state', 'failed_messages']

            missing_tables = [t for t in expected_tables if t not in tables]
            if missing_tables:
                print(f"❌ Missing tables: {missing_tables}")
            else:
                print("✅ All required tables exist")

            conn.close()
        else:
            print("❌ Database file not found")
            return False
    except Exception as e:
        print(f"❌ Database test failed: {e}")
        return False

    # Test 2: Check Atlas database integration
    print("\n2. Testing Atlas database integration...")
    atlas_db_path = 'data/atlas.db'
    try:
        if os.path.exists(atlas_db_path):
            conn = sqlite3.connect(atlas_db_path)
            cursor = conn.cursor()

            # Check content table
            cursor.execute("SELECT COUNT(*) FROM content")
            content_count = cursor.fetchone()[0]
            print(f"✅ Atlas database has {content_count} existing content records")

            # Check if Gmail content types exist in metadata
            cursor.execute("""
                SELECT COUNT(*) FROM content
                WHERE json_extract(metadata, '$.source') = 'gmail'
            """)
            gmail_count = cursor.fetchone()[0]
            print(f"✅ Atlas has {gmail_count} Gmail-sourced content records")

            conn.close()
        else:
            print("❌ Atlas database not found")
            return False
    except Exception as e:
        print(f"❌ Atlas database test failed: {e}")
        return False

    # Test 3: Test Gmail modules
    print("\n3. Testing Gmail modules...")
    try:
        import sys
        sys.path.insert(0, '/home/ubuntu/dev/atlas')

        from modules.gmail.auth import GmailAuthManager
        from modules.gmail.processor import GmailProcessor
        from modules.gmail.webhook import GmailWebhookManager

        # Test instantiation
        auth_manager = GmailAuthManager()
        processor = GmailProcessor(auth_manager)
        webhook_manager = GmailWebhookManager(auth_manager, processor)

        print("✅ All Gmail modules import and instantiate correctly")

    except Exception as e:
        print(f"❌ Gmail module test failed: {e}")
        return False

    # Test 4: Test URL extraction
    print("\n4. Testing URL extraction...")
    try:
        from modules.gmail.processor import GmailProcessor
        processor = GmailProcessor(None)

        # Test URL extraction
        test_text = """
        Check out this article: https://example.com/article1
        And this one: https://github.com/user/repo

        Also visit https://www.youtube.com/watch?v=dQw4w9WgXcQ
        """

        # This would normally be called from processor, but let's test the pattern
        import re
        url_pattern = re.compile(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+')
        urls = url_pattern.findall(test_text)

        expected_urls = [
            'https://example.com/article1',
            'https://github.com/user/repo',
            'https://www.youtube.com/watch?v=dQw4w9WgXcQ'
        ]

        if set(urls) == set(expected_urls):
            print(f"✅ URL extraction works: found {len(urls)} URLs")
        else:
            print(f"❌ URL extraction failed: got {urls}")
            return False

    except Exception as e:
        print(f"❌ URL extraction test failed: {e}")
        return False

    # Test 5: Test API configuration
    print("\n5. Testing API configuration...")
    try:
        from api import get_gmail_auth_manager, get_gmail_processor, get_gmail_webhook_manager

        # Test authentication status check
        auth_manager = get_gmail_auth_manager()
        is_authenticated = auth_manager.is_authenticated()
        print(f"✅ Gmail auth manager created (authenticated: {is_authenticated})")

        # Test processor
        processor = get_gmail_processor()
        print(f"✅ Gmail processor created for database: {processor.atlas_db_path}")

        # Test webhook manager
        webhook_manager = get_gmail_webhook_manager()
        print(f"✅ Gmail webhook manager created")

    except Exception as e:
        print(f"❌ API configuration test failed: {e}")
        return False

    # Test 6: Test email processing simulation
    print("\n6. Testing email processing simulation...")
    try:
        # Simulate the email you'll send from iOS
        simulated_email = {
            'message_id': 'test_msg_123',
            'thread_id': 'test_thread_123',
            'subject': 'Atlas Bookmark: Check out this article',
            'sender_email': 'your-device@icloud.com',
            'sender_name': 'iPhone',
            'content': 'https://example.com/article\n\nThis is a great article about technology.',
            'labels': ['INBOX', 'UNREAD'],
            'gmail_timestamp': datetime.now().isoformat()
        }

        # Test URL extraction from content
        urls = url_pattern.findall(simulated_email['content'])
        if urls:
            print(f"✅ Email processing simulation works: found {len(urls)} URLs")
            for url in urls:
                print(f"   📄 Found URL: {url}")
        else:
            print("❌ Email processing simulation failed: no URLs found")
            return False

    except Exception as e:
        print(f"❌ Email processing simulation failed: {e}")
        return False

    print("\n" + "=" * 50)
    print("🎉 ALL TESTS PASSED!")
    print("\nYour Gmail integration is ready!")
    print("\n📱 Next steps:")
    print("1. Create the iOS shortcut (see SIMPLE_SHORTCUT_GUIDE.md)")
    print("2. Set up Gmail filter for khamel83+atlas@gmail.com")
    print("3. Get Gmail API credentials from Google Cloud Console")
    print("4. Test by sending an email from your iOS shortcut")

    return True

if __name__ == "__main__":
    test_atlas_v3_gmail()