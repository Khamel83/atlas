#!/usr/bin/env python3
"""
Simple Atlas URL Ingestion - BULLETPROOF VERSION
===============================================

Just takes URLs and stores them. No complexity, no crashes.
"""

from http.server import HTTPServer, BaseHTTPRequestHandler
import sqlite3
import json
import uuid
import urllib.parse
from datetime import datetime
import os

# Configuration
PORT = 35555
DB_PATH = '/home/ubuntu/dev/atlas/data/simple_atlas.db'

# Ensure data directory exists
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

# Initialize database
def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS urls (
            id TEXT PRIMARY KEY,
            url TEXT NOT NULL,
            created_at TEXT NOT NULL,
            source TEXT DEFAULT 'api'
        )
    ''')
    conn.commit()
    conn.close()

class SimpleIngestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path.startswith('/ingest'):
            # Parse URL parameter
            url_parts = urllib.parse.urlparse(self.path)
            params = urllib.parse.parse_qs(url_parts.query)

            url = params.get('url', [''])[0]

            if url:
                # Store URL
                unique_id = str(uuid.uuid4())
                timestamp = datetime.now().isoformat()

                try:
                    conn = sqlite3.connect(DB_PATH)
                    cursor = conn.cursor()
                    cursor.execute(
                        'INSERT INTO urls (id, url, created_at, source) VALUES (?, ?, ?, ?)',
                        (unique_id, url, timestamp, 'api')
                    )
                    conn.commit()
                    conn.close()

                    # Return success
                    response = {
                        "status": "success",
                        "unique_id": unique_id,
                        "url": url,
                        "message": "URL stored successfully"
                    }

                    self.send_response(200)
                    self.send_header('Content-type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps(response).encode('utf-8'))

                    print(f"✅ Stored: {url} -> {unique_id}")

                except Exception as e:
                    # Return error
                    self.send_response(500)
                    self.send_header('Content-type', 'application/json')
                    self.end_headers()
                    error_response = {"status": "error", "message": str(e)}
                    self.wfile.write(json.dumps(error_response).encode('utf-8'))
                    print(f"❌ Error storing {url}: {e}")
            else:
                # No URL provided
                self.send_response(400)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                error_response = {"status": "error", "message": "Missing 'url' parameter"}
                self.wfile.write(json.dumps(error_response).encode('utf-8'))
        else:
            # Status page
            try:
                conn = sqlite3.connect(DB_PATH)
                cursor = conn.cursor()
                cursor.execute('SELECT COUNT(*) FROM urls')
                count = cursor.fetchone()[0]
                conn.close()

                html = f"""
                <!DOCTYPE html>
                <html><head><title>Simple Atlas Ingest</title></head>
                <body>
                    <h1>Simple Atlas URL Ingestion</h1>
                    <p><strong>Status:</strong> Running</p>
                    <p><strong>Total URLs:</strong> {count}</p>
                    <p><strong>Endpoint:</strong> <code>/ingest?url=YOUR_URL</code></p>
                </body></html>
                """

                self.send_response(200)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                self.wfile.write(html.encode('utf-8'))

            except Exception as e:
                self.send_response(500)
                self.end_headers()
                print(f"❌ Status page error: {e}")

def main():
    # Initialize database
    init_db()

    # Start server
    print(f"🚀 Starting Simple Atlas Ingest on port {PORT}")
    print(f"📊 Database: {DB_PATH}")
    print(f"🔗 Endpoint: http://localhost:{PORT}/ingest?url=YOUR_URL")

    server = HTTPServer(('0.0.0.0', PORT), SimpleIngestHandler)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("🛑 Shutting down...")
        server.shutdown()

if __name__ == "__main__":
    main()