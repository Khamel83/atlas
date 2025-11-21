#!/usr/bin/env python3
"""
PODEMOS Private RSS Feed Server for Oracle OCI

Generates private RSS feeds for cleaned podcast episodes with authentication.
Target: Personal ad-free podcast feeds hosted on Oracle OCI.
"""

import os
import sys
import json
import asyncio
import hashlib
import secrets
from datetime import datetime, timezone
from typing import Dict, List

from fastapi import FastAPI, HTTPException
from fastapi.security import HTTPBearer
from fastapi.responses import Response
import sqlite3
from xml.dom import minidom
import xml.etree.ElementTree as ET

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from helpers.database_manager import DatabaseManager

class PodemosFeedAuth:
    """Authentication system for private RSS feeds"""

    def __init__(self, db_path: str = "data/podemos_auth.db"):
        self.db_path = db_path
        self._ensure_auth_db()

    def _ensure_auth_db(self):
        """Create authentication database if it doesn't exist"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS feed_tokens (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    feed_id TEXT NOT NULL,
                    token TEXT UNIQUE NOT NULL,
                    user_name TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    last_accessed TEXT,
                    access_count INTEGER DEFAULT 0,
                    active BOOLEAN DEFAULT 1
                )
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_tokens_token ON feed_tokens(token)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_tokens_feed ON feed_tokens(feed_id)
            """)

    def generate_feed_token(self, feed_id: str, user_name: str = "user") -> str:
        """Generate secure access token for feed"""
        token = secrets.token_urlsafe(32)

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO feed_tokens (feed_id, token, user_name)
                VALUES (?, ?, ?)
            """, (feed_id, token, user_name))

        return token

    def validate_token(self, token: str, feed_id: str) -> bool:
        """Validate access token for specific feed"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id FROM feed_tokens
                WHERE token = ? AND feed_id = ? AND active = 1
            """, (token, feed_id))

            if cursor.fetchone():
                # Update access tracking
                cursor.execute("""
                    UPDATE feed_tokens
                    SET last_accessed = CURRENT_TIMESTAMP,
                        access_count = access_count + 1
                    WHERE token = ? AND feed_id = ?
                """, (token, feed_id))
                return True

        return False

class RSSGenerator:
    """Generate RSS feeds for cleaned podcast episodes"""

    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager

    async def get_clean_episodes(self, podcast_name: str, limit: int = 50) -> List[Dict]:
        """Get clean episodes for podcast"""
        query = """
            SELECT
                title,
                url,
                content,
                created_at,
                metadata
            FROM content
            WHERE content_type = 'podcast_clean'
            AND (title LIKE ? OR metadata LIKE ?)
            ORDER BY created_at DESC
            LIMIT ?
        """

        search_pattern = f"%{podcast_name}%"
        results = await self.db.execute_query(
            query,
            (search_pattern, search_pattern, limit)
        )

        episodes = []
        for row in results:
            metadata = json.loads(row[4]) if row[4] else {}
            episodes.append({
                'title': row[0],
                'url': row[1],
                'content': row[2],
                'pub_date': row[3],
                'metadata': metadata,
                'clean_audio_url': metadata.get('clean_audio_url'),
                'duration': metadata.get('duration', '0:00:00'),
                'file_size': metadata.get('file_size', 0)
            })

        return episodes

    def generate_rss_feed(self, podcast_name: str, episodes: List[Dict],
                         base_url: str = "https://podemos.example.com") -> str:
        """Generate RSS 2.0 feed XML"""

        # Create RSS root
        rss = ET.Element("rss", version="2.0")
        rss.set("xmlns:itunes", "http://www.itunes.com/dtds/podcast-1.0.dtd")
        rss.set("xmlns:content", "http://purl.org/rss/1.0/modules/content/")

        # Channel element
        channel = ET.SubElement(rss, "channel")

        # Channel metadata
        ET.SubElement(channel, "title").text = f"{podcast_name} (Ad-Free)"
        ET.SubElement(channel, "description").text = f"Personal ad-free feed for {podcast_name}"
        ET.SubElement(channel, "link").text = base_url
        ET.SubElement(channel, "language").text = "en-us"
        ET.SubElement(channel, "generator").text = "PODEMOS RSS Server"
        ET.SubElement(channel, "lastBuildDate").text = datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S GMT")

        # iTunes-specific tags
        ET.SubElement(channel, "itunes:explicit").text = "false"
        ET.SubElement(channel, "itunes:author").text = "PODEMOS Clean Feed"

        # Add episodes
        for episode in episodes:
            if not episode['clean_audio_url']:
                continue

            item = ET.SubElement(channel, "item")

            ET.SubElement(item, "title").text = episode['title']
            ET.SubElement(item, "description").text = f"Clean version of: {episode['title']}"
            ET.SubElement(item, "link").text = episode['url']
            ET.SubElement(item, "guid").text = hashlib.md5(episode['url'].encode()).hexdigest()

            # Publication date
            if episode['pub_date']:
                try:
                    pub_date = datetime.fromisoformat(episode['pub_date'].replace('Z', '+00:00'))
                    ET.SubElement(item, "pubDate").text = pub_date.strftime("%a, %d %b %Y %H:%M:%S GMT")
                except Exception:
                    ET.SubElement(item, "pubDate").text = datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S GMT")

            # Audio enclosure
            enclosure = ET.SubElement(item, "enclosure")
            enclosure.set("url", episode['clean_audio_url'])
            enclosure.set("type", "audio/mpeg")
            enclosure.set("length", str(episode['file_size']))

            # iTunes tags
            ET.SubElement(item, "itunes:duration").text = episode['duration']
            ET.SubElement(item, "itunes:explicit").text = "false"

        # Format XML
        rough_string = ET.tostring(rss, 'unicode')
        reparsed = minidom.parseString(rough_string)
        return reparsed.toprettyxml(indent="  ")

class PodemosFeedServer:
    """Private RSS feed server for PODEMOS"""

    def __init__(self):
        self.app = FastAPI(title="PODEMOS RSS Server", version="1.0.0")
        self.auth = PodemosFeedAuth()
        self.db = DatabaseManager()
        self.rss_gen = RSSGenerator(self.db)
        self.security = HTTPBearer()
        self._setup_routes()

    def _setup_routes(self):
        """Setup FastAPI routes"""

        @self.app.get("/")
        async def root():
            return {"message": "PODEMOS Private RSS Server", "version": "1.0.0"}

        @self.app.post("/feeds/{feed_id}/generate_token")
        async def generate_token(feed_id: str, user_name: str = "user"):
            """Generate access token for feed"""
            token = self.auth.generate_feed_token(feed_id, user_name)
            return {
                "feed_id": feed_id,
                "token": token,
                "feed_url": f"/feeds/{feed_id}/rss?token={token}"
            }

        @self.app.get("/feeds/{feed_id}/rss")
        async def get_feed(feed_id: str, token: str, limit: int = 50):
            """Get RSS feed with authentication"""

            # Validate token
            if not self.auth.validate_token(token, feed_id):
                raise HTTPException(status_code=401, detail="Invalid or expired token")

            # Get clean episodes
            episodes = await self.rss_gen.get_clean_episodes(feed_id, limit)

            if not episodes:
                raise HTTPException(status_code=404, detail="No clean episodes found")

            # Generate RSS
            base_url = "https://podemos.example.com"  # TODO: Configure from env
            rss_xml = self.rss_gen.generate_rss_feed(feed_id, episodes, base_url)

            return Response(content=rss_xml, media_type="application/rss+xml")

        @self.app.get("/feeds/{feed_id}/episodes")
        async def list_episodes(feed_id: str, token: str, limit: int = 20):
            """List available clean episodes (JSON)"""

            if not self.auth.validate_token(token, feed_id):
                raise HTTPException(status_code=401, detail="Invalid token")

            episodes = await self.rss_gen.get_clean_episodes(feed_id, limit)
            return {
                "feed_id": feed_id,
                "episode_count": len(episodes),
                "episodes": episodes
            }

        @self.app.get("/status")
        async def server_status():
            """Server status and statistics"""

            # Count clean episodes
            clean_count_query = """
                SELECT COUNT(*) FROM content
                WHERE content_type = 'podcast_clean'
            """
            clean_count = await self.db.execute_query(clean_count_query)

            # Count active tokens
            with sqlite3.connect(self.auth.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM feed_tokens WHERE active = 1")
                active_tokens = cursor.fetchone()[0]

            return {
                "status": "running",
                "clean_episodes": clean_count[0][0] if clean_count else 0,
                "active_tokens": active_tokens,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

def create_oracle_deployment_config():
    """Create Oracle OCI deployment configuration"""

    config = {
        "deployment": {
            "platform": "Oracle OCI",
            "service_type": "Container Instance",
            "region": "us-ashburn-1",
            "memory": "1GB",
            "cpu": "0.5 OCPU",
            "storage": "10GB"
        },
        "networking": {
            "public_ip": True,
            "security_group": "podemos-rss-sg",
            "ingress_rules": [
                {"port": 8080, "protocol": "TCP", "source": "0.0.0.0/0"}
            ]
        },
        "environment": {
            "PORT": "8080",
            "DATABASE_PATH": "/data/atlas.db",
            "AUTH_DB_PATH": "/data/podemos_auth.db",
            "BASE_URL": "${OCI_PUBLIC_IP}:8080"
        },
        "volumes": [
            {
                "name": "atlas-data",
                "mount_path": "/data",
                "type": "persistent"
            }
        ]
    }

    # Save config
    config_path = "config/oracle_oci_deployment.json"
    os.makedirs(os.path.dirname(config_path), exist_ok=True)

    with open(config_path, 'w') as f:
        json.dump(config, f, indent=2)

    return config_path

async def main():
    """Main entry point"""
    if len(sys.argv) > 1:
        command = sys.argv[1]

        if command == "--create-deployment-config":
            config_path = create_oracle_deployment_config()
            print(f"✅ Oracle OCI deployment config created: {config_path}")
            return

        elif command == "--generate-token":
            if len(sys.argv) < 3:
                print("Usage: --generate-token <feed_id> [user_name]")
                return

            feed_id = sys.argv[2]
            user_name = sys.argv[3] if len(sys.argv) > 3 else "user"

            auth = PodemosFeedAuth()
            token = auth.generate_feed_token(feed_id, user_name)

            print(f"✅ Generated token for feed '{feed_id}':")
            print(f"   Token: {token}")
            print(f"   Feed URL: http://localhost:8080/feeds/{feed_id}/rss?token={token}")
            return

        elif command == "--test-feed":
            if len(sys.argv) < 3:
                print("Usage: --test-feed <feed_id>")
                return

            feed_id = sys.argv[2]

            # Generate test feed
            db = DatabaseManager()
            rss_gen = RSSGenerator(db)

            episodes = await rss_gen.get_clean_episodes(feed_id, 10)
            print(f"✅ Found {len(episodes)} clean episodes for '{feed_id}'")

            if episodes:
                rss_xml = rss_gen.generate_rss_feed(feed_id, episodes)
                print("✅ Generated RSS feed sample:")
                print(rss_xml[:500] + "..." if len(rss_xml) > 500 else rss_xml)

            return

    # Start server
    print("🎵 Starting PODEMOS RSS Server...")

    server = PodemosFeedServer()

    # Run with uvicorn
    import uvicorn
    uvicorn.run(
        server.app,
        host="0.0.0.0",
        port=8080,
        log_level="info"
    )

if __name__ == "__main__":
    asyncio.run(main())