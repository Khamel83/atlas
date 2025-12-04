#!/usr/bin/env python3
"""
Atlas v3 - Simple URL Ingestion
UNIX Philosophy: Do one thing well - ingest URLs with unique IDs

Usage:
    python3 atlas_v3.py

Endpoint:
    POST/GET http://localhost:8080/ingest?url=<URL>

Database:
    SQLite with unique_id for each URL
"""

import sqlite3
import logging
import json
from datetime import datetime
from urllib.parse import urlparse, unquote
from http.server import HTTPServer, BaseHTTPRequestHandler
import uuid

# Simple logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(message)s',
    handlers=[logging.StreamHandler()]
)

class AtlasV3Database:
    """Simple database for URL ingestion"""

    def __init__(self, db_path='data/atlas_v3.db'):
        self.db_path = db_path
        self.init_database()

    def init_database(self):
        """Create the simplest possible schema"""
        import os
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Single table - just what we need
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ingested_urls (
                unique_id TEXT PRIMARY KEY,
                url TEXT NOT NULL,
                created_at TEXT NOT NULL,
                source TEXT DEFAULT 'velja',
                content_type TEXT DEFAULT 'unknown'
            )
        """)

        # Index for performance
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_created_at ON ingested_urls(created_at)")

        conn.commit()
        conn.close()
        logging.info(f"Database initialized: {self.db_path}")

    def ingest_url(self, url, source='velja'):
        """Ingest URL with unique ID - the core function"""
        try:
            # Generate unique ID
            unique_id = str(uuid.uuid4())
            timestamp = datetime.now().isoformat()

            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Simple insert
            cursor.execute("""
                INSERT INTO ingested_urls (unique_id, url, created_at, source, content_type)
                VALUES (?, ?, ?, ?, ?)
            """, (unique_id, url, timestamp, source, 'unknown'))

            conn.commit()
            conn.close()

            logging.info(f"✅ Ingested: {unique_id} -> {url}")
            return {'success': True, 'unique_id': unique_id}

        except Exception as e:
            logging.error(f"❌ Failed to ingest {url}: {e}")
            return {'success': False, 'error': str(e)}

    def get_count(self):
        """Get total ingested count"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM ingested_urls")
        count = cursor.fetchone()[0]
        conn.close()
        return count

class AtlasV3Handler(BaseHTTPRequestHandler):
    """Simple HTTP handler for URL ingestion"""

    def __init__(self, *args, database=None, **kwargs):
        self.database = database
        super().__init__(*args, **kwargs)

    def log_message(self, format, *args):
        """Suppress default request logging"""
        pass

    def do_GET(self):
        """Handle GET requests for /ingest"""
        if self.path.startswith('/ingest'):
            self.handle_ingest()
        elif self.path == '/':
            self.handle_status()
        else:
            self.send_error(404)

    def do_POST(self):
        """Handle POST requests for /ingest"""
        if self.path.startswith('/ingest'):
            self.handle_ingest()
        else:
            self.send_error(404)

    def handle_ingest(self):
        """Handle URL ingestion"""
        try:
            # Extract URL from query params
            from urllib.parse import parse_qs, urlparse
            parsed = urlparse(self.path)
            params = parse_qs(parsed.query)

            url = params.get('url', [None])[0]
            if not url:
                self.send_error(400, "Missing 'url' parameter")
                return

            # URL decode
            url = unquote(url)

            # Validate URL
            if not url.startswith(('http://', 'https://')):
                self.send_error(400, "Invalid URL - must start with http:// or https://")
                return

            # Ingest the URL
            result = self.database.ingest_url(url)

            # Send response
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()

            response = {
                'status': 'success' if result['success'] else 'error',
                'unique_id': result.get('unique_id'),
                'url': url,
                'message': 'URL ingested successfully' if result['success'] else result.get('error')
            }

            self.wfile.write(json.dumps(response, indent=2).encode())

        except Exception as e:
            logging.error(f"Error handling request: {e}")
            self.send_error(500, str(e))

    def handle_status(self):
        """Show simple status page"""
        count = self.database.get_count()

        self.send_response(200)
        self.send_header('Content-Type', 'text/html')
        self.end_headers()

        html = f"""
        <!DOCTYPE html>
        <html>
        <head><title>Atlas v3 - Simple Ingestion</title></head>
        <body>
            <h1>Atlas v3 - URL Ingestion Service</h1>
            <p><strong>Status:</strong> Running</p>
            <p><strong>Total URLs Ingested:</strong> {count}</p>
            <p><strong>Endpoint:</strong> <code>/ingest?url=&lt;URL&gt;</code></p>
            <h3>Test:</h3>
            <p><a href="/ingest?url=https://example.com">Ingest https://example.com</a></p>
        </body>
        </html>
        """

        self.wfile.write(html.encode())

def create_handler(database):
    """Create handler with database dependency"""
    def handler(*args, **kwargs):
        return AtlasV3Handler(*args, database=database, **kwargs)
    return handler

def main():
    """Run Atlas v3 ingestion server"""
    print("🚀 Atlas v3 - Simple URL Ingestion")
    print("=" * 40)

    # Initialize database
    database = AtlasV3Database()
    count = database.get_count()
    print(f"📊 Current database: {count} URLs")

    # Start server - use fixed port for testing
    port = 35555
    handler = create_handler(database)
    server = HTTPServer(('localhost', port), handler)

    print(f"🌐 Server running on http://localhost:{port}")
    print(f"📥 Ingestion endpoint: http://localhost:{port}/ingest?url=<URL>")
    print(f"💡 Test: curl 'http://localhost:{port}/ingest?url=https://example.com'")
    print("\nPress Ctrl+C to stop")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n🛑 Shutting down Atlas v3")
        server.shutdown()

if __name__ == "__main__":
    main()