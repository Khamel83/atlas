#!/usr/bin/env python3
"""
ntfy-to-Atlas Bridge
===================

Listens to ntfy.sh topic and forwards URLs to Atlas v3.

Flow:
1. Subscribe to ntfy.sh/atlas-ingest
2. Extract URLs from incoming messages
3. Send URLs to Atlas v3 ingest endpoint
4. Log successful processing

This runs continuously and handles connection failures gracefully.
"""

import requests
import time
import json
import re
import logging
import os
from datetime import datetime
from urllib.parse import urlparse

# Load environment
from dotenv import load_dotenv
load_dotenv('/home/ubuntu/dev/atlas/.env')

# Configuration
NTFY_TOPIC = os.getenv('NTFY_TOPIC', 'atlas-ingest')
NTFY_SERVER = os.getenv('NTFY_SERVER', 'https://ntfy.sh')
ATLAS_URL = os.getenv('ATLAS_URL', 'https://atlas.khamel.com')
ATLAS_INGEST_ENDPOINT = os.getenv('ATLAS_INGEST_ENDPOINT', '/ingest')

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/tmp/ntfy_atlas_bridge.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# URL extraction regex
URL_REGEX = re.compile(r'https?://\S+')

def send_to_atlas(url):
    """Send URL to Atlas v3 ingest endpoint"""
    try:
        atlas_endpoint = f"{ATLAS_URL.rstrip('/')}{ATLAS_INGEST_ENDPOINT}"

        response = requests.get(f"{atlas_endpoint}?url={url}", timeout=10)

        if response.status_code == 200:
            result = response.json()
            logger.info(f"✅ Sent to Atlas: {url} -> {result.get('unique_id', 'unknown')}")
            return True
        else:
            logger.error(f"❌ Atlas returned {response.status_code}: {response.text}")
            return False

    except Exception as e:
        logger.error(f"❌ Failed to send to Atlas: {url} - {e}")
        return False

def extract_urls(text):
    """Extract URLs from text"""
    if not text:
        return []

    urls = URL_REGEX.findall(text)
    return list(set(urls))  # Remove duplicates

def listen_to_ntfy():
    """Listen to ntfy.sh topic and process messages"""
    topic_url = f"{NTFY_SERVER.rstrip('/')}/{NTFY_TOPIC}/json"

    logger.info(f"🚀 Starting ntfy-to-Atlas bridge...")
    logger.info(f"📡 Listening to: {topic_url}")
    logger.info(f"🎯 Forwarding to: {ATLAS_URL}{ATLAS_INGEST_ENDPOINT}")

    while True:
        try:
            logger.info("🔗 Connecting to ntfy.sh...")

            # Stream messages from ntfy.sh
            response = requests.get(topic_url, stream=True, timeout=60)
            response.raise_for_status()

            logger.info("✅ Connected! Listening for messages...")

            for line in response.iter_lines():
                if line:
                    try:
                        message = json.loads(line.decode('utf-8'))

                        # Skip health/keepalive messages
                        if message.get('event') != 'message':
                            continue

                        # Extract message content
                        title = message.get('title', '')
                        message_text = message.get('message', '')
                        full_text = f"{title} {message_text}"

                        logger.info(f"📨 Received: {title[:50]}...")

                        # Extract URLs and send to Atlas
                        urls = extract_urls(full_text)

                        if urls:
                            logger.info(f"🔗 Found {len(urls)} URL(s)")
                            for url in urls:
                                send_to_atlas(url)
                        else:
                            logger.info("❌ No URLs found in message")

                    except json.JSONDecodeError as e:
                        logger.warning(f"⚠️  Failed to parse JSON: {e}")
                    except Exception as e:
                        logger.error(f"⚠️  Error processing message: {e}")

        except requests.exceptions.RequestException as e:
            logger.error(f"🔌 Connection error: {e}")
            logger.info("🔄 Reconnecting in 10 seconds...")
            time.sleep(10)

        except KeyboardInterrupt:
            logger.info("🛑 Shutting down ntfy-to-Atlas bridge...")
            break

        except Exception as e:
            logger.error(f"💥 Unexpected error: {e}")
            logger.info("🔄 Reconnecting in 30 seconds...")
            time.sleep(30)

if __name__ == "__main__":
    listen_to_ntfy()