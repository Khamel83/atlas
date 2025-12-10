#!/usr/bin/env python3
"""
Atlas v3 Dual Ingestion System
- Atlas v3: Ingests all URLs (text, articles, podcasts)
- Video Downloader: Attempts video downloads (best effort)
- Smart Filtering: Routes content based on type detection
"""

import sqlite3
import logging
import json
import subprocess
import requests
from datetime import datetime
from urllib.parse import urlparse, unquote
from http.server import HTTPServer, BaseHTTPRequestHandler
import uuid
import re
import os

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(message)s',
    handlers=[logging.StreamHandler()]
)

class ContentDetector:
    """Detect content type from URL"""

    VIDEO_DOMAINS = {
        'youtube.com', 'youtu.be', 'vimeo.com', 'twitch.tv',
        'dailymotion.com', 'metacafe.com', 'vevo.com',
        'tiktok.com', 'instagram.com', 'facebook.com',
        'twitter.com', 'x.com'
    }

    VIDEO_EXTENSIONS = {
        '.mp4', '.avi', '.mov', '.wmv', '.flv', '.webm',
        '.mkv', '.m4v', '.3gp', '.ogv', '.ts'
    }

    @classmethod
    def is_video_url(cls, url):
        """Check if URL points to video content"""
        parsed = urlparse(url.lower())
        domain = parsed.netloc.replace('www.', '')

        # Check video domains
        for video_domain in cls.VIDEO_DOMAINS:
            if video_domain in domain:
                return True

        # Check video extensions
        for ext in cls.VIDEO_EXTENSIONS:
            if url.lower().endswith(ext):
                return True

        # Check path patterns for video
        path_patterns = ['/video/', '/watch', '/embed/', '/player/']
        if any(pattern in parsed.path.lower() for pattern in path_patterns):
            return True

        return False

    @classmethod
    def get_content_type(cls, url):
        """Categorize content type"""
        if cls.is_video_url(url):
            return 'video'

        # Check for common content types
        parsed = urlparse(url.lower())
        domain = parsed.netloc.replace('www.', '')

        # Podcast/audio
        if any(x in domain for x in ['spotify.com', 'soundcloud.com', 'podcast', 'anchor.fm']):
            return 'audio'

        # Social media
        if any(x in domain for x in ['twitter.com', 'x.com', 'instagram.com', 'facebook.com']):
            return 'social'

        # News/articles
        if any(x in domain for x in ['news', 'article', 'blog', 'medium.com', 'substack.com']):
            return 'article'

        return 'web'

class VideoDownloader:
    """Handles video download attempts"""

    def __init__(self, download_dir='downloads'):
        self.download_dir = download_dir
        os.makedirs(download_dir, exist_ok=True)

    def download_yt_dlp(self, url):
        """Try to download with yt-dlp"""
        try:
            # Check if yt-dlp is available
            subprocess.run(['yt-dlp', '--version'], capture_output=True, check=True)

            # Generate output filename
            safe_title = f"video_{uuid.uuid4().hex[:8]}"
            output_path = os.path.join(self.download_dir, f"{safe_title}.%(ext)s")

            # Download command
            cmd = [
                'yt-dlp',
                '--no-warnings',
                '--simulate',  # Don't actually download, just get info
                '--print-json',
                url
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

            if result.returncode == 0:
                info = json.loads(result.stdout)
                return {
                    'success': True,
                    'method': 'yt-dlp',
                    'title': info.get('title', 'Unknown'),
                    'duration': info.get('duration'),
                    'uploader': info.get('uploader')
                }
            else:
                return {'success': False, 'error': result.stderr}

        except FileNotFoundError:
            return {'success': False, 'error': 'yt-dlp not found'}
        except subprocess.TimeoutExpired:
            return {'success': False, 'error': 'Download timeout'}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def attempt_download(self, url):
        """Try to download video content (best effort)"""
        if not ContentDetector.is_video_url(url):
            return {'success': False, 'error': 'Not a video URL'}

        # Try yt-dlp first
        result = self.download_yt_dlp(url)
        if result['success']:
            logging.info(f"✅ Video detected: {result.get('title', 'Unknown')}")

        return result

class AtlasV3Database:
    """Enhanced database for dual ingestion"""

    def __init__(self, db_path='data/atlas_v3.db'):
        self.db_path = db_path
        self.init_database()

    def init_database(self):
        """Create enhanced schema"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Main ingestion table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ingested_urls (
                unique_id TEXT PRIMARY KEY,
                url TEXT NOT NULL,
                content_type TEXT NOT NULL,
                created_at TEXT NOT NULL,
                source TEXT DEFAULT 'velja',
                video_info TEXT,
                atlas_success BOOLEAN DEFAULT 1,
                video_success BOOLEAN DEFAULT 0
            )
        """)

        # Indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_created_at ON ingested_urls(created_at)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_content_type ON ingested_urls(content_type)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_source ON ingested_urls(source)")

        conn.commit()
        conn.close()
        logging.info(f"Enhanced database initialized: {self.db_path}")

    def ingest_url(self, url, content_type='web', source='velja', video_info=None):
        """Ingest URL with enhanced metadata"""
        try:
            unique_id = str(uuid.uuid4())
            timestamp = datetime.now().isoformat()

            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO ingested_urls
                (unique_id, url, content_type, created_at, source, video_info, atlas_success, video_success)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                unique_id, url, content_type, timestamp, source,
                json.dumps(video_info) if video_info else None,
                True,  # Atlas always succeeds
                bool(video_info and video_info.get('success'))
            ))

            conn.commit()
            conn.close()

            logging.info(f"✅ Ingested: {unique_id} -> {url} ({content_type})")
            return {'success': True, 'unique_id': unique_id, 'content_type': content_type}

        except Exception as e:
            logging.error(f"❌ Failed to ingest {url}: {e}")
            return {'success': False, 'error': str(e)}

    def get_stats(self):
        """Get ingestion statistics"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Total count
        cursor.execute("SELECT COUNT(*) FROM ingested_urls")
        total = cursor.fetchone()[0]

        # By content type
        cursor.execute("SELECT content_type, COUNT(*) FROM ingested_urls GROUP BY content_type")
        by_type = dict(cursor.fetchall())

        # Video success rate
        cursor.execute("""
            SELECT
                COUNT(*) as total_videos,
                SUM(CASE WHEN video_success = 1 THEN 1 ELSE 0 END) as successful_videos
            FROM ingested_urls
            WHERE content_type = 'video'
        """)
        video_stats = cursor.fetchone()
        video_success_rate = (video_stats[1] / video_stats[0] * 100) if video_stats[0] > 0 else 0

        conn.close()

        return {
            'total': total,
            'by_type': by_type,
            'video_stats': {
                'total': video_stats[0],
                'successful': video_stats[1],
                'success_rate': round(video_success_rate, 1)
            }
        }

class AtlasV3DualHandler(BaseHTTPRequestHandler):
    """Enhanced HTTP handler for dual ingestion"""

    def __init__(self, *args, database=None, video_downloader=None, **kwargs):
        self.database = database
        self.video_downloader = video_downloader
        super().__init__(*args, **kwargs)

    def log_message(self, format, *args):
        pass

    def do_GET(self):
        if self.path.startswith('/ingest'):
            self.handle_ingest()
        elif self.path == '/':
            self.handle_status()
        elif self.path == '/stats':
            self.handle_stats()
        else:
            self.send_error(404)

    def do_POST(self):
        if self.path.startswith('/ingest'):
            self.handle_ingest()
        else:
            self.send_error(404)

    def handle_ingest(self):
        """Handle dual ingestion"""
        try:
            # Extract URL
            from urllib.parse import parse_qs, urlparse
            parsed = urlparse(self.path)
            params = parse_qs(parsed.query)

            url = params.get('url', [None])[0]
            if not url:
                self.send_error(400, "Missing 'url' parameter")
                return

            url = unquote(url)

            # Validate URL
            if not url.startswith(('http://', 'https://')):
                self.send_error(400, "Invalid URL")
                return

            # Detect content type
            content_type = ContentDetector.get_content_type(url)
            logging.info(f"🔍 Detected content type: {content_type} for {url}")

            # Step 1: Atlas v3 ingestion (always succeeds)
            atlas_result = self.database.ingest_url(url, content_type)

            # Step 2: Video download attempt (best effort)
            video_result = None
            if content_type == 'video':
                video_result = self.video_downloader.attempt_download(url)
                if video_result.get('success'):
                    logging.info(f"📹 Video info: {video_result}")
                else:
                    logging.info(f"📹 Video attempt failed: {video_result.get('error', 'Unknown error')}")

            # Send response
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()

            response = {
                'status': 'success',
                'unique_id': atlas_result.get('unique_id'),
                'url': url,
                'content_type': content_type,
                'atlas_success': True,
                'video_attempt': video_result is not None,
                'video_success': video_result.get('success') if video_result else False,
                'video_info': video_result if video_result else None,
                'message': f'URL ingested as {content_type}'
            }

            self.wfile.write(json.dumps(response, indent=2).encode())

        except Exception as e:
            logging.error(f"Error handling request: {e}")
            self.send_error(500, str(e))

    def handle_status(self):
        """Show enhanced status page"""
        stats = self.database.get_stats()

        self.send_response(200)
        self.send_header('Content-Type', 'text/html')
        self.end_headers()

        html = f"""
        <!DOCTYPE html>
        <html>
        <head><title>Atlas v3 - Dual Ingestion</title></head>
        <body>
            <h1>Atlas v3 - Dual Ingestion System</h1>
            <p><strong>Status:</strong> Running</p>
            <p><strong>Total URLs Ingested:</strong> {stats['total']}</p>

            <h3>By Content Type:</h3>
            <ul>
        """

        for content_type, count in stats['by_type'].items():
            html += f"                <li>{content_type}: {count}</li>\n"

        html += f"""
            </ul>

            <h3>Video Processing:</h3>
            <p>Total Videos: {stats['video_stats']['total']}</p>
            <p>Successfully Identified: {stats['video_stats']['successful']}</p>
            <p>Success Rate: {stats['video_stats']['success_rate']}%</p>

            <h3>Endpoints:</h3>
            <p><code>/ingest?url=&lt;URL&gt;</code> - Ingest URL</p>
            <p><code>/stats</code> - View statistics</p>

            <h3>Test:</h3>
            <p><a href="/ingest?url=https://example.com">Ingest https://example.com</a></p>
            <p><a href="/ingest?url=https://youtube.com/watch?v=dQw4w9WgXcQ">Ingest YouTube video</a></p>
        </body>
        </html>
        """

        self.wfile.write(html.encode())

    def handle_stats(self):
        """Return JSON statistics"""
        stats = self.database.get_stats()

        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()

        self.wfile.write(json.dumps(stats, indent=2).encode())

def create_handler(database, video_downloader):
    """Create handler with dependencies"""
    def handler(*args, **kwargs):
        return AtlasV3DualHandler(*args, database=database, video_downloader=video_downloader, **kwargs)
    return handler

def main():
    """Run Atlas v3 dual ingestion server"""
    print("🚀 Atlas v3 - Dual Ingestion System")
    print("=" * 50)

    # Initialize components
    database = AtlasV3Database()
    video_downloader = VideoDownloader()

    # Show stats
    stats = database.get_stats()
    print(f"📊 Current database: {stats['total']} URLs")
    print(f"📹 Video success rate: {stats['video_stats']['success_rate']}%")

    # Start server - bind to all interfaces for external access
    port = 8001
    host = '0.0.0.0'  # Bind to all interfaces
    handler = create_handler(database, video_downloader)
    server = HTTPServer((host, port), handler)

    print(f"🌐 Server running on http://atlas.khamel.com:{port}")
    print(f"📥 Ingestion: http://atlas.khamel.com:{port}/ingest?url=<URL>")
    print(f"📊 Statistics: http://atlas.khamel.com:{port}/stats")
    print(f"💡 Test: curl 'http://localhost:{port}/ingest?url=https://example.com'")
    print("\nPress Ctrl+C to stop")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n🛑 Shutting down Atlas v3")
        server.shutdown()

if __name__ == "__main__":
    main()