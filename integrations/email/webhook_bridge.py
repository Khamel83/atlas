#!/usr/bin/env python3
"""
Webhook Email Bridge - ACTUALLY WORKING EMAIL SOLUTION
=====================================================

Receives emails via HTTP webhooks from services like Zapier, IFTTT, etc.
This bypasses SMTP port blocking completely.
"""

from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import sqlite3
import uuid
import re
import urllib.parse
from datetime import datetime
import os

# Configuration
PORT = 7447
DB_PATH = '/home/ubuntu/dev/atlas/data/simple_atlas.db'

# URL regex
URL_REGEX = re.compile(r'https?://\S+')

def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
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

class WebhookHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        """Handle webhook POST requests from email services"""
        try:
            # Read POST data
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)

            print(f"📧 Received webhook: {len(post_data)} bytes")

            # Try to parse as JSON first
            try:
                data = json.loads(post_data.decode('utf-8'))

                # Handle direct URL from bookmarklet
                if 'url' in data and data['url']:
                    direct_url = data['url']
                    unique_id = store_url(direct_url, 'bookmarklet')
                    if unique_id:
                        results = [f"✅ {direct_url} -> {unique_id}"]
                    else:
                        results = [f"❌ {direct_url} -> Failed"]

                    response = {"status": "success", "message": "Bookmarklet processed", "results": results}
                    self.send_response(200)
                    self.send_header('Content-type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps(response).encode('utf-8'))
                    return

                # Extract text from common webhook formats
                text_fields = ['body', 'text', 'message', 'content', 'subject', 'email_body']
                full_text = ""

                for field in text_fields:
                    if field in data and data[field]:
                        full_text += str(data[field]) + " "

                print(f"📝 Extracted text: {full_text[:100]}...")

            except json.JSONDecodeError:
                # Try as form data
                try:
                    form_data = urllib.parse.parse_qs(post_data.decode('utf-8'))
                    full_text = ""
                    for key, values in form_data.items():
                        if values:
                            full_text += " ".join(values) + " "
                    print(f"📝 Form data: {full_text[:100]}...")
                except:
                    # Last resort - treat as plain text
                    full_text = post_data.decode('utf-8', errors='ignore')
                    print(f"📝 Plain text: {full_text[:100]}...")

            # Extract and store URLs
            urls = extract_urls(full_text)
            results = []

            if urls:
                print(f"🔗 Found {len(urls)} URL(s)")
                for url in urls:
                    unique_id = store_url(url)
                    if unique_id:
                        results.append(f"✅ {url} -> {unique_id}")
                    else:
                        results.append(f"❌ {url} -> Failed")
            else:
                results.append("❌ No URLs found")
                print("❌ No URLs found in webhook data")

            # Return success response
            response = {
                "status": "success",
                "message": "Email processed",
                "results": results
            }

            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(response).encode('utf-8'))

        except Exception as e:
            print(f"❌ Error processing webhook: {e}")
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            error_response = {"status": "error", "message": str(e)}
            self.wfile.write(json.dumps(error_response).encode('utf-8'))

    def do_GET(self):
        """Handle GET requests - test endpoint"""
        if self.path.startswith('/test'):
            # Test with URL parameter
            url_parts = urllib.parse.urlparse(self.path)
            params = urllib.parse.parse_qs(url_parts.query)
            test_url = params.get('url', [''])[0]

            if test_url:
                unique_id = store_url(test_url, 'test')
                response = f"✅ Test URL stored: {test_url} -> {unique_id}"
            else:
                response = "❌ No URL provided. Use: /test?url=YOUR_URL"

            self.send_response(200)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(response.encode('utf-8'))
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
                <html><head><title>Email Webhook Bridge</title></head>
                <body>
                    <h1>📧 Email Webhook Bridge</h1>
                    <p><strong>Status:</strong> Running</p>
                    <p><strong>Total URLs:</strong> {count}</p>
                    <p><strong>Webhook Endpoint:</strong> <code>POST /</code></p>
                    <p><strong>Test Endpoint:</strong> <code>GET /test?url=YOUR_URL</code></p>
                    <h3>📱 Phone Email Setup:</h3>
                    <p>1. Set up email forwarding service (Zapier, IFTTT, etc.)</p>
                    <p>2. Point it to: <code>https://atlas.khamel.com/email-webhook</code></p>
                    <p>3. Send emails with URLs - they'll be stored automatically!</p>
                </body></html>
                """

                self.send_response(200)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                self.wfile.write(html.encode('utf-8'))

            except Exception as e:
                self.send_response(500)
                self.end_headers()

def main():
    init_db()
    print(f"🚀 Starting Email Webhook Bridge on port {PORT}")
    print(f"📧 Webhook URL: https://atlas.khamel.com/email-webhook")
    print(f"📊 Database: {DB_PATH}")

    server = HTTPServer(('0.0.0.0', PORT), WebhookHandler)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("🛑 Shutting down...")
        server.shutdown()

if __name__ == "__main__":
    main()