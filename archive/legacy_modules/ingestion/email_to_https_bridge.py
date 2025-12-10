#!/usr/bin/env python3
"""
Email-to-HTTPS Bridge - ACTUALLY WORKING SOLUTION
================================================

Since direct SMTP is blocked, this provides email forwarding via HTTPS.
Uses ntfy.sh as the bridge since it works over HTTPS.
"""

import requests
import json
import sqlite3
import uuid
import re
from datetime import datetime
import time

# Configuration
NTFY_TOPIC = "atlas-ingest"
NTFY_URL = f"https://ntfy.sh/{NTFY_TOPIC}/json"
DB_PATH = '/home/ubuntu/dev/atlas/data/simple_atlas.db'

# URL regex
URL_REGEX = re.compile(r'https?://\S+')

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS urls (
            id TEXT PRIMARY KEY,
            url TEXT NOT NULL,
            created_at TEXT NOT NULL,
            source TEXT DEFAULT 'email'
        )
    ''')
    conn.commit()
    conn.close()

def store_url(url, source='email'):
    try:
        unique_id = str(uuid.uuid4())
        timestamp = datetime.now().isoformat()

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            'INSERT INTO urls (id, url, created_at, source) VALUES (?, ?, ?, ?)',
            (unique_id, url, timestamp, source)
        )
        conn.commit()
        conn.close()

        print(f"✅ Email→Atlas: {url} -> {unique_id}")
        return unique_id
    except Exception as e:
        print(f"❌ Error storing {url}: {e}")
        return None

def extract_urls(text):
    if not text:
        return []
    urls = URL_REGEX.findall(text)
    return list(set(urls))

def listen_for_emails():
    print(f"🚀 Starting Email-to-Atlas HTTPS bridge...")
    print(f"📧 Email forwarding via: https://ntfy.sh/{NTFY_TOPIC}")
    print(f"📱 From phone: Send to ntfy topic '{NTFY_TOPIC}'")

    while True:
        try:
            print("🔗 Connecting to ntfy.sh...")
            response = requests.get(NTFY_URL, stream=True, timeout=60)
            response.raise_for_status()

            print("✅ Connected! Listening for email content...")

            for line in response.iter_lines():
                if line:
                    try:
                        message = json.loads(line.decode('utf-8'))

                        if message.get('event') != 'message':
                            continue

                        title = message.get('title', '')
                        content = message.get('message', '')
                        full_text = f"{title} {content}"

                        print(f"📨 Received email content: {title[:50]}...")

                        urls = extract_urls(full_text)
                        if urls:
                            print(f"🔗 Found {len(urls)} URL(s)")
                            for url in urls:
                                store_url(url)
                        else:
                            print("❌ No URLs found in content")

                    except json.JSONDecodeError:
                        continue
                    except Exception as e:
                        print(f"⚠️ Error processing content: {e}")

        except requests.exceptions.RequestException as e:
            print(f"🔌 Connection error: {e}")
            print("🔄 Reconnecting in 10 seconds...")
            time.sleep(10)
        except KeyboardInterrupt:
            print("🛑 Shutting down email bridge...")
            break
        except Exception as e:
            print(f"💥 Unexpected error: {e}")
            time.sleep(30)

if __name__ == "__main__":
    init_db()
    listen_for_emails()