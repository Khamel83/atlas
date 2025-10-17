#!/usr/bin/env python3
"""
Archon Telegram Ingest Service
==============================

FastAPI webhook service that receives Telegram messages and forwards URLs to Atlas.

Flow:
1. Telegram bot receives shared URL from iOS
2. Telegram sends webhook to this service
3. Service extracts URLs from message
4. Service POSTs URLs to Atlas ingest API

Author: Archon Project
"""

import os
import re
import json
import logging
from datetime import datetime
from typing import Optional, Dict, Any, List

import requests
from fastapi import FastAPI, Request, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ATLAS_URL = os.getenv("ATLAS_URL", "https://atlas.khamel.com")
ATLAS_INGEST_ENDPOINT = os.getenv("ATLAS_INGEST_ENDPOINT", "/ingest")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "")
ALLOWED_USER_ID = os.getenv("ALLOWED_USER_ID", "")

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# URL extraction regex
URL_REGEX = re.compile(r'https?://\S+')

# FastAPI app
app = FastAPI(
    title="Archon Telegram Ingest",
    description="Telegram webhook service for Atlas content ingestion",
    version="1.0.0"
)

class TelegramUpdate(BaseModel):
    """Telegram webhook update structure"""
    update_id: Optional[int] = None
    message: Optional[Dict[str, Any]] = None
    channel_post: Optional[Dict[str, Any]] = None

def extract_urls_from_message(message: Dict[str, Any]) -> List[str]:
    """Extract URLs from Telegram message"""
    urls = []
    text = (message.get("text", "") or message.get("caption", "")).strip()

    # Extract URLs from entities (preferred method)
    for entity in (message.get("entities", []) + message.get("caption_entities", [])):
        if entity.get("type") == "url":
            offset = entity["offset"]
            length = entity["length"]
            urls.append(text[offset:offset + length])
        elif entity.get("type") == "text_link":
            url = entity.get("url")
            if url:
                urls.append(url)

    # Fallback: regex extraction if no entities found
    if not urls and text:
        urls = URL_REGEX.findall(text)

    return list(set(urls))  # Remove duplicates

def send_to_atlas(url: str) -> bool:
    """Send URL to Atlas ingest API"""
    try:
        atlas_endpoint = f"{ATLAS_URL.rstrip('/')}{ATLAS_INGEST_ENDPOINT}"

        payload = {
            "url": url,
            "source": "telegram",
            "timestamp": datetime.now().isoformat()
        }

        response = requests.post(
            atlas_endpoint,
            params={"url": url},  # Atlas expects URL as query param
            json=payload,
            timeout=10,
            headers={"Content-Type": "application/json"}
        )

        if response.status_code == 200:
            logger.info(f"✅ Successfully sent to Atlas: {url}")
            return True
        else:
            logger.error(f"❌ Atlas returned {response.status_code}: {url}")
            return False

    except requests.exceptions.RequestException as e:
        logger.error(f"❌ Failed to send to Atlas: {url} - {e}")
        return False

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "archon-telegram-ingest",
        "timestamp": datetime.now().isoformat()
    }

@app.post(f"/telegram/{WEBHOOK_SECRET}")
async def telegram_webhook(request: Request):
    """Handle Telegram webhook"""
    try:
        # Parse JSON payload
        data = await request.json()
        update = TelegramUpdate(**data)

        # Get message (regular message or channel post)
        message = update.message or update.channel_post
        if not message:
            return {"ok": True}

        # Check if user is allowed (if whitelist is configured)
        if ALLOWED_USER_ID:
            user_id = str((message.get("from", {}) or {}).get("id", ""))
            if user_id != str(ALLOWED_USER_ID):
                logger.warning(f"🚫 Unauthorized user attempted access: {user_id}")
                return {"ok": True}

        # Extract URLs from message
        urls = extract_urls_from_message(message)

        if not urls:
            logger.info("📭 No URLs found in message")
            return {"ok": True}

        # Send each URL to Atlas
        success_count = 0
        for url in urls:
            if send_to_atlas(url):
                success_count += 1

        logger.info(f"📤 Processed {success_count}/{len(urls)} URLs successfully")

        return {"ok": True, "processed": success_count, "total": len(urls)}

    except Exception as e:
        logger.error(f"❌ Webhook error: {e}")
        return {"ok": True}  # Always return ok to Telegram

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "Archon Telegram Ingest",
        "status": "running",
        "endpoints": ["/health", f"/telegram/{WEBHOOK_SECRET}"]
    }

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("SERVICE_PORT", 8081))
    uvicorn.run(app, host="127.0.0.1", port=port)