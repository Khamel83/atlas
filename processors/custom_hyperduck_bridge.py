#!/usr/bin/env python3
"""
Custom Hyperduck Bridge
Mimics Hyperduck functionality but sends URLs to both Downie and Atlas

This acts as the middleman between Cyberduck and Downie/Atlas
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
import os
import platform

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(message)s',
    handlers=[logging.StreamHandler()]
)

class CustomHyperduckBridge:
    """Bridge between Cyberduck and Downie+Atlas"""

    def __init__(self):
        self.atlas_server = 'http://atlas.khamel.com:35555'
        self.system = platform.system()
        logging.info(f"🌉 Custom Hyperduck Bridge started on {self.system}")

    def send_to_downie(self, url):
        """Send URL to Downie using macOS system calls"""
        if self.system != 'Darwin':
            logging.warning("⚠️  Not on macOS - cannot open Downie")
            return False

        try:
            # Use macOS 'open' command to send URL to Downie
            cmd = ['open', '-a', 'Downie', url]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)

            if result.returncode == 0:
                logging.info(f"✅ Sent to Downie: {url}")
                return True
            else:
                logging.warning(f"⚠️  Downie failed: {result.stderr}")
                return False
        except Exception as e:
            logging.error(f"❌ Downie error: {e}")
            return False

    def send_to_atlas(self, url):
        """Send URL to Atlas server"""
        try:
            atlas_url = f"{self.atlas_server}/ingest?url={url}"
            response = requests.get(atlas_url, timeout=10)

            if response.status_code == 200:
                result = response.json()
                if result.get('status') == 'success':
                    logging.info(f"✅ Sent to Atlas: {url} (ID: {result.get('unique_id')})")
                    return True
                else:
                    logging.warning(f"⚠️  Atlas error: {result.get('message')}")
                    return False
            else:
                logging.warning(f"⚠️  Atlas HTTP error: {response.status_code}")
                return False
        except Exception as e:
            logging.error(f"❌ Atlas error: {e}")
            return False

    def process_url(self, url):
        """Process URL through both Downie and Atlas"""
        logging.info(f"🔗 Processing URL: {url}")

        # Send to both systems
        downie_success = self.send_to_downie(url)
        atlas_success = self.send_to_atlas(url)

        # Log results
        if downie_success and atlas_success:
            logging.info(f"🎯 SUCCESS: {url} sent to both Downie and Atlas")
        elif atlas_success:
            logging.info(f"✅ ATLAS SUCCESS: {url} sent to Atlas (Downie failed)")
        elif downie_success:
            logging.info(f"✅ DOWNIE SUCCESS: {url} sent to Downie (Atlas failed)")
        else:
            logging.error(f"❌ FAILED: {url} - neither system received it")

class BridgeHandler(BaseHTTPRequestHandler):
    """HTTP handler for receiving URLs from Cyberduck"""

    def __init__(self, *args, bridge=None, **kwargs):
        self.bridge = bridge or CustomHyperduckBridge()
        super().__init__(*args, **kwargs)

    def log_message(self, format, *args):
        pass  # Suppress default request logging

    def do_GET(self):
        """Handle GET requests from Cyberduck"""
        if self.path.startswith('/'):
            self.handle_request()

    def do_POST(self):
        """Handle POST requests from Cyberduck"""
        if self.path.startswith('/'):
            self.handle_request()

    def handle_request(self):
        """Handle URL processing request"""
        try:
            # Extract URL from various possible formats
            url = self.extract_url()

            if not url:
                self.send_error(400, "No URL found in request")
                return

            # Process through both systems
            self.bridge.process_url(url)

            # Send success response
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()

            response = {
                'status': 'success',
                'url': url,
                'message': 'URL processed by Custom Hyperduck Bridge'
            }

            self.wfile.write(json.dumps(response, indent=2).encode())

        except Exception as e:
            logging.error(f"Error handling request: {e}")
            self.send_error(500, str(e))

    def extract_url(self):
        """Extract URL from various request formats"""
        from urllib.parse import parse_qs, urlparse

        # Method 1: Query parameter
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)
        url = params.get('url', [None])[0]
        if url:
            return unquote(url)

        # Method 2: POST body
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length).decode('utf-8')

            if post_data:
                # Try JSON
                try:
                    data = json.loads(post_data)
                    if isinstance(data, dict) and 'url' in data:
                        return data['url']
                    elif isinstance(data, str):
                        return data
                except:
                    # Try form data
                    params = parse_qs(post_data)
                    url = params.get('url', [None])[0]
                    if url:
                        return unquote(url)
                    # Try raw URL
                    if post_data.startswith('http'):
                        return post_data.strip()
        except:
            pass

        return None

    def handle_status(self):
        """Show bridge status"""
        self.send_response(200)
        self.send_header('Content-Type', 'text/html')
        self.end_headers()

        html = """
        <!DOCTYPE html>
        <html>
        <head><title>Custom Hyperduck Bridge</title></head>
        <body>
            <h1>🌉 Custom Hyperduck Bridge</h1>
            <p><strong>Status:</strong> Running</p>
            <p><strong>Purpose:</strong> Bridge between Cyberduck and Downie+Atlas</p>
            <p><strong>Atlas Server:</strong> http://atlas.khamel.com:35555</p>
            <h3>How to use:</h3>
            <p>Configure Cyberduck to send URLs to this bridge instead of Hyperduck</p>
        </body>
        </html>
        """

        self.wfile.write(html.encode())

def create_handler(bridge):
    """Create handler with bridge dependency"""
    def handler(*args, **kwargs):
        return BridgeHandler(*args, bridge=bridge, **kwargs)
    return handler

def main():
    """Run the custom Hyperduck bridge"""
    print("🌉 Custom Hyperduck Bridge")
    print("=" * 40)
    print("Mimics Hyperduck but sends to both Downie and Atlas")

    # Initialize bridge
    bridge = CustomHyperduckBridge()

    # Start server on a different port to avoid conflicts
    port = 38888
    host = '0.0.0.0'  # Accept connections from anywhere
    handler = create_handler(bridge)
    server = HTTPServer((host, port), handler)

    print(f"🌐 Bridge running on http://atlas.khamel.com:{port}")
    print(f"📥 Configure Cyberduck to use: http://atlas.khamel.com:{port}")
    print(f"🎯 URLs will be sent to both Downie and Atlas")
    print("\nPress Ctrl+C to stop")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n🛑 Shutting down Custom Hyperduck Bridge")
        server.shutdown()

if __name__ == "__main__":
    main()