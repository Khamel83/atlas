#!/usr/bin/env python3
"""
Simple Email Ingestion Web Interface
===================================

Alternative to SMTP - provides a simple web form for URL submission
that can be bookmarked on your phone for easy sharing.

Access via: https://atlas.khamel.com/email-submit
"""

from http.server import HTTPServer, BaseHTTPRequestHandler
import urllib.parse
import json
import re
import requests
import logging
import os
import uuid
import cgi
import tempfile
from datetime import datetime

# Load environment
from dotenv import load_dotenv
load_dotenv('/home/ubuntu/dev/atlas/.env')

# Configuration
HTTP_PORT = 7446
ATLAS_URL = os.getenv('ATLAS_URL', 'https://atlas.khamel.com')
ATLAS_INGEST_ENDPOINT = os.getenv('ATLAS_INGEST_ENDPOINT', '/ingest')
ATTACHMENTS_DIR = '/home/ubuntu/dev/atlas/attachments'

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/tmp/simple_email_ingestion.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# URL extraction regex
URL_REGEX = re.compile(r'https?://\S+')

def send_to_atlas(url, source='web-form'):
    """Send URL to Atlas v3 ingest endpoint"""
    try:
        atlas_endpoint = f"{ATLAS_URL.rstrip('/')}{ATLAS_INGEST_ENDPOINT}"
        response = requests.get(f"{atlas_endpoint}?url={url}", timeout=10)

        if response.status_code == 200:
            result = response.json()
            unique_id = result.get('unique_id', 'unknown')
            logger.info(f"✅ Web→Atlas: {url} -> {unique_id}")
            return unique_id
        else:
            logger.error(f"❌ Atlas returned {response.status_code}: {response.text}")
            return None

    except Exception as e:
        logger.error(f"❌ Failed to send to Atlas: {url} - {e}")
        return None

def extract_urls(text):
    """Extract URLs from text"""
    if not text:
        return []
    urls = URL_REGEX.findall(text)
    return list(set(urls))  # Remove duplicates

def save_attachment(file_data, filename, content_type):
    """Save uploaded file to attachments directory"""
    try:
        # Generate unique filename
        file_id = str(uuid.uuid4())
        timestamp = datetime.now().isoformat()
        safe_filename = re.sub(r'[^a-zA-Z0-9._-]', '_', filename)
        stored_filename = f"{file_id}_{safe_filename}"

        # Save file
        file_path = os.path.join(ATTACHMENTS_DIR, stored_filename)
        with open(file_path, 'wb') as f:
            f.write(file_data)

        # Create metadata
        metadata = {
            'file_id': file_id,
            'original_filename': filename,
            'stored_filename': stored_filename,
            'content_type': content_type,
            'size': len(file_data),
            'uploaded_at': timestamp,
            'file_path': file_path
        }

        logger.info(f"📁 Saved attachment: {filename} -> {stored_filename} ({len(file_data)} bytes)")
        return metadata

    except Exception as e:
        logger.error(f"❌ Failed to save attachment {filename}: {e}")
        return None

class EmailIngestionHandler(BaseHTTPRequestHandler):
    """HTTP handler for email/URL ingestion"""

    def do_GET(self):
        """Handle GET requests - show form or submit URL"""
        if self.path.startswith('/email-submit'):
            # Parse query parameters
            url_parts = urllib.parse.urlparse(self.path)
            params = urllib.parse.parse_qs(url_parts.query)

            url_param = params.get('url', [''])[0]

            if url_param:
                # Direct URL submission via GET
                urls = extract_urls(url_param)
                results = []

                for url in urls:
                    unique_id = send_to_atlas(url)
                    if unique_id:
                        results.append(f"✅ {url} → {unique_id}")
                    else:
                        results.append(f"❌ {url} → Failed")

                response_html = f"""
                <!DOCTYPE html>
                <html>
                <head>
                    <title>URL Submitted</title>
                    <meta name="viewport" content="width=device-width, initial-scale=1">
                </head>
                <body style="font-family: Arial; max-width: 600px; margin: 50px auto; padding: 20px;">
                    <h2>📧 URL Submitted to Atlas</h2>
                    {'<br>'.join(results)}
                    <br><br>
                    <a href="/email-submit">Submit Another URL</a>
                </body>
                </html>
                """
            else:
                # Show submission form
                response_html = """
                <!DOCTYPE html>
                <html>
                <head>
                    <title>Atlas Email Ingestion</title>
                    <meta name="viewport" content="width=device-width, initial-scale=1">
                </head>
                <body style="font-family: Arial; max-width: 600px; margin: 50px auto; padding: 20px;">
                    <h2>📧 Send URL to Atlas</h2>
                    <p>Paste or type any URL to add it to your Atlas knowledge base:</p>

                    <form method="POST" action="/email-submit" enctype="multipart/form-data">
                        <label for="url">📎 URL or Text:</label>
                        <input type="url" name="url" id="url" placeholder="https://example.com/article"
                               style="width: 100%; padding: 12px; font-size: 16px; border: 1px solid #ccc; border-radius: 4px; margin-bottom: 10px;">

                        <label for="text">💬 Or paste any text with URLs:</label>
                        <textarea name="text" id="text" placeholder="Paste article text, emails, or anything with URLs..."
                                  style="width: 100%; padding: 12px; font-size: 16px; border: 1px solid #ccc; border-radius: 4px; height: 100px; margin-bottom: 10px;"></textarea>

                        <label for="file">📁 Or upload files (PDFs, images, documents):</label>
                        <input type="file" name="file" id="file" multiple accept=".pdf,.doc,.docx,.txt,.jpg,.jpeg,.png,.gif"
                               style="width: 100%; padding: 12px; font-size: 16px; border: 1px solid #ccc; border-radius: 4px; margin-bottom: 15px;">

                        <button type="submit" style="background: #007cba; color: white; padding: 12px 24px; border: none; border-radius: 4px; font-size: 16px; cursor: pointer;">
                            📤 Send to Atlas
                        </button>
                    </form>

                    <h3>📱 Phone Setup</h3>
                    <p>Bookmark this page: <code>https://atlas.khamel.com/email-submit</code></p>
                    <p><strong>Workflow:</strong></p>
                    <ol>
                        <li>Find article in Safari/any app</li>
                        <li>Copy URL or Share → Copy Link</li>
                        <li>Open this bookmark</li>
                        <li>Paste URL and submit</li>
                    </ol>

                    <p><em>Alternative: Use URL like https://atlas.khamel.com/email-submit?url=YOUR_URL</em></p>
                </body>
                </html>
                """

            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(response_html.encode('utf-8'))

        else:
            # Default response for other paths
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        """Handle POST requests for form submission with file uploads"""
        if self.path.startswith('/email-submit'):
            try:
                # Parse multipart form data
                form = cgi.FieldStorage(
                    fp=self.rfile,
                    headers=self.headers,
                    environ={'REQUEST_METHOD': 'POST'}
                )

                results = []

                # Process URL field
                if 'url' in form and form['url'].value:
                    url = form['url'].value
                    urls = extract_urls(url)
                    for url in urls:
                        unique_id = send_to_atlas(url)
                        if unique_id:
                            results.append(f"✅ URL: {url} → {unique_id}")
                        else:
                            results.append(f"❌ URL: {url} → Failed")

                # Process text field
                if 'text' in form and form['text'].value:
                    text = form['text'].value
                    urls = extract_urls(text)
                    for url in urls:
                        unique_id = send_to_atlas(url)
                        if unique_id:
                            results.append(f"✅ Text URL: {url} → {unique_id}")
                        else:
                            results.append(f"❌ Text URL: {url} → Failed")

                # Process file uploads
                if 'file' in form:
                    files = form['file'] if isinstance(form['file'], list) else [form['file']]
                    for file_field in files:
                        if file_field.filename:
                            file_data = file_field.file.read()
                            content_type = file_field.type or 'application/octet-stream'

                            metadata = save_attachment(file_data, file_field.filename, content_type)
                            if metadata:
                                results.append(f"📁 File: {file_field.filename} → Saved ({metadata['size']} bytes)")

                                # Try to extract URLs from text files
                                if content_type.startswith('text/') or file_field.filename.endswith('.txt'):
                                    try:
                                        text_content = file_data.decode('utf-8', errors='ignore')
                                        urls = extract_urls(text_content)
                                        for url in urls:
                                            unique_id = send_to_atlas(url)
                                            if unique_id:
                                                results.append(f"✅ File URL: {url} → {unique_id}")
                                    except:
                                        pass
                            else:
                                results.append(f"❌ File: {file_field.filename} → Failed to save")

                if not results:
                    results.append("❌ No URLs or files found to process")

                response_html = f"""
                <!DOCTYPE html>
                <html>
                <head>
                    <title>Content Submitted to Atlas</title>
                    <meta name="viewport" content="width=device-width, initial-scale=1">
                </head>
                <body style="font-family: Arial; max-width: 600px; margin: 50px auto; padding: 20px;">
                    <h2>📧 Content Submitted to Atlas</h2>
                    {'<br>'.join(results)}
                    <br><br>
                    <a href="/email-submit">Submit More Content</a>
                </body>
                </html>
                """

                self.send_response(200)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                self.wfile.write(response_html.encode('utf-8'))

            except Exception as e:
                logger.error(f"❌ Error processing POST request: {e}")
                self.send_response(500)
                self.end_headers()

def main():
    """Start the web server"""
    logger.info(f"🚀 Starting Simple Email Ingestion Web Server...")
    logger.info(f"🌐 Access via: https://atlas.khamel.com/email-submit")
    logger.info(f"📧 Listening on port {HTTP_PORT}")
    logger.info(f"🎯 Forwarding to: {ATLAS_URL}{ATLAS_INGEST_ENDPOINT}")

    try:
        server = HTTPServer(('0.0.0.0', HTTP_PORT), EmailIngestionHandler)
        logger.info("✅ Web server started successfully!")
        server.serve_forever()

    except KeyboardInterrupt:
        logger.info("🛑 Shutting down web server...")
        server.shutdown()
    except Exception as e:
        logger.error(f"💥 Server error: {e}")

if __name__ == "__main__":
    main()