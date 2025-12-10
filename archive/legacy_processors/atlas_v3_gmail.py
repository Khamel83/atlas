#!/usr/bin/env python3
"""
Atlas v3 + Gmail - Simple URL Ingestion with Gmail Integration
UNIX Philosophy: Do one thing well - ingest URLs from multiple sources

Features:
- URL ingestion via HTTP API (original v3)
- Gmail webhook for real-time email processing
- Gmail watch for push notifications
- SQLite database with source tracking

Usage:
    python3 atlas_v3_gmail.py

Endpoints:
    POST/GET http://localhost:8080/ingest?url=<URL>
    POST http://localhost:8080/webhook/gmail (Gmail push notifications)

Database:
    Enhanced SQLite with Gmail message tracking
"""

import sqlite3
import logging
import json
import os
import asyncio
import base64
import hashlib
from datetime import datetime
from urllib.parse import urlparse, unquote
from http.server import HTTPServer, BaseHTTPRequestHandler
import uuid
import re
from typing import Dict, List, Optional

# Gmail API imports
try:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    GMAIL_AVAILABLE = True
except ImportError:
    GMAIL_AVAILABLE = False
    print("⚠️ Gmail libraries not available. Gmail features disabled.")

# Enhanced logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('logs/atlas_v3_gmail.log', encoding='utf-8')
    ]
)

# Ensure logs directory exists
os.makedirs('logs', exist_ok=True)

class AtlasV3GmailDatabase:
    """Enhanced database for URL and Gmail ingestion"""

    def __init__(self, db_path='data/atlas_v3_gmail.db'):
        self.db_path = db_path
        self.init_database()

    def init_database(self):
        """Create enhanced schema for Gmail integration"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Original URL ingestion table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ingested_urls (
                unique_id TEXT PRIMARY KEY,
                url TEXT NOT NULL,
                created_at TEXT NOT NULL,
                source TEXT DEFAULT 'manual',
                content_type TEXT DEFAULT 'unknown',
                gmail_message_id TEXT,
                gmail_sender TEXT,
                gmail_subject TEXT
            )
        """)

        # Gmail messages table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS gmail_messages (
                gmail_message_id TEXT PRIMARY KEY,
                gmail_thread_id TEXT,
                subject TEXT,
                sender_email TEXT,
                sender_name TEXT,
                urls TEXT,
                attachments TEXT,
                gmail_timestamp TEXT,
                processed_at TEXT,
                labels TEXT,
                message_hash TEXT
            )
        """)

        # Processing state table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS processing_state (
                key TEXT PRIMARY KEY,
                value TEXT,
                updated_at TEXT
            )
        """)

        # Failed messages table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS failed_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                gmail_message_id TEXT,
                error_message TEXT,
                error_type TEXT,
                retry_count INTEGER DEFAULT 0,
                created_at TEXT
            )
        """)

        # Indexes for performance
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_urls_created_at ON ingested_urls(created_at)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_urls_source ON ingested_urls(source)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_gmail_timestamp ON gmail_messages(gmail_timestamp)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_gmail_sender ON gmail_messages(sender_email)")

        conn.commit()
        conn.close()
        logging.info(f"✅ Database initialized: {self.db_path}")

    def ingest_url(self, url, source='manual', gmail_info=None):
        """Ingest URL with optional Gmail context"""
        try:
            unique_id = str(uuid.uuid4())
            timestamp = datetime.now().isoformat()

            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Extract Gmail info if provided
            gmail_message_id = gmail_info.get('message_id') if gmail_info else None
            gmail_sender = gmail_info.get('sender_email') if gmail_info else None
            gmail_subject = gmail_info.get('subject') if gmail_info else None

            cursor.execute("""
                INSERT INTO ingested_urls
                (unique_id, url, created_at, source, content_type, gmail_message_id, gmail_sender, gmail_subject)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (unique_id, url, timestamp, source, 'unknown', gmail_message_id, gmail_sender, gmail_subject))

            conn.commit()
            conn.close()

            logging.info(f"✅ Ingested: {unique_id} -> {url} (source: {source})")
            return {'success': True, 'unique_id': unique_id}

        except Exception as e:
            logging.error(f"❌ Failed to ingest {url}: {e}")
            return {'success': False, 'error': str(e)}

    def store_gmail_message(self, message_data):
        """Store Gmail message data"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("""
                INSERT OR REPLACE INTO gmail_messages
                (gmail_message_id, gmail_thread_id, subject, sender_email, sender_name,
                 urls, attachments, gmail_timestamp, processed_at, labels, message_hash)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                message_data['message_id'],
                message_data['thread_id'],
                message_data['subject'],
                message_data['sender_email'],
                message_data['sender_name'],
                json.dumps(message_data['urls']),
                json.dumps(message_data['attachments']),
                message_data['gmail_timestamp'],
                datetime.now().isoformat(),
                json.dumps(message_data['labels']),
                message_data['message_hash']
            ))

            conn.commit()
            conn.close()

            logging.info(f"✅ Stored Gmail message: {message_data['message_id']}")
            return {'success': True}

        except Exception as e:
            logging.error(f"❌ Failed to store Gmail message: {e}")
            return {'success': False, 'error': str(e)}

    def get_processing_state(self, key):
        """Get processing state value"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM processing_state WHERE key = ?", (key,))
        result = cursor.fetchone()
        conn.close()
        return result[0] if result else None

    def set_processing_state(self, key, value):
        """Set processing state value"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO processing_state (key, value, updated_at)
            VALUES (?, ?, ?)
        """, (key, value, datetime.now().isoformat()))
        conn.commit()
        conn.close()

    def get_count(self):
        """Get total ingested count"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM ingested_urls")
        count = cursor.fetchone()[0]
        conn.close()
        return count

class GmailProcessor:
    """Gmail message processing for Atlas v3"""

    def __init__(self, database: AtlasV3GmailDatabase):
        self.database = database
        self.credentials_path = 'config/gmail_credentials.json'
        self.token_path = 'config/gmail_token.json'
        self.scopes = ['https://www.googleapis.com/auth/gmail.readonly', 'https://www.googleapis.com/auth/gmail.modify']
        self.service = None

        if not GMAIL_AVAILABLE:
            logging.warning("⚠️ Gmail libraries not available. Gmail processing disabled.")

    async def authenticate(self):
        """Authenticate with Gmail API"""
        if not GMAIL_AVAILABLE:
            return False

        try:
            creds = None
            if os.path.exists(self.token_path):
                creds = Credentials.from_authorized_user_file(self.token_path, self.scopes)

            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                else:
                    if not os.path.exists(self.credentials_path):
                        logging.error("❌ Gmail credentials file not found")
                        return False

                    flow = InstalledAppFlow.from_client_secrets_file(self.credentials_path, self.scopes)
                    creds = flow.run_local_server(port=0)

                with open(self.token_path, 'w') as token:
                    token.write(creds.to_json())

            self.service = build('gmail', 'v1', credentials=creds)
            logging.info("✅ Gmail authenticated successfully")
            return True

        except Exception as e:
            logging.error(f"❌ Gmail authentication failed: {e}")
            return False

    def extract_urls_from_message(self, message):
        """Extract URLs from Gmail message content"""
        urls = set()
        url_pattern = re.compile(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+')

        # Extract from payload parts
        def extract_from_parts(parts):
            for part in parts:
                if part.get('mimeType', '').startswith('text/'):
                    if 'data' in part.get('body', {}):
                        try:
                            import base64
                            data = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8', errors='ignore')
                            urls.update(url_pattern.findall(data))
                        except:
                            pass
                elif 'parts' in part:
                    extract_from_parts(part['parts'])

        payload = message.get('payload', {})
        if 'parts' in payload:
            extract_from_parts(payload['parts'])
        elif 'data' in payload.get('body', {}):
            try:
                import base64
                data = base64.urlsafe_b64decode(payload['body']['data']).decode('utf-8', errors='ignore')
                urls.update(url_pattern.findall(data))
            except:
                pass

        return list(urls)

    def extract_attachments_info(self, message):
        """Extract attachment information"""
        attachments = []
        payload = message.get('payload', {})

        def extract_from_parts(parts):
            for part in parts:
                if part.get('filename'):
                    attachment_info = {
                        'filename': part['filename'],
                        'size': part.get('body', {}).get('size', 0),
                        'mime_type': part.get('mimeType', 'application/octet-stream')
                    }
                    attachments.append(attachment_info)
                elif 'parts' in part:
                    extract_from_parts(part['parts'])

        if 'parts' in payload:
            extract_from_parts(payload['parts'])

        return attachments

    async def process_gmail_message(self, message_id):
        """Process a single Gmail message"""
        if not self.service:
            logging.error("❌ Gmail service not initialized")
            return {'success': False, 'error': 'Gmail service not initialized'}

        try:
            message = self.service.users().messages().get(
                userId='me', id=message_id, format='full'
            ).execute()

            # Extract message data
            headers = {h['name']: h['value'] for h in message['payload'].get('headers', [])}
            from_header = headers.get('From', '')

            # Parse sender
            sender_email = ''
            sender_name = ''
            if '<' in from_header:
                sender_name = from_header.split('<')[0].strip().strip('"')
                sender_email = from_header.split('<')[1].split('>')[0].strip()
            else:
                sender_email = from_header.strip()

            # Extract URLs and attachments
            urls = self.extract_urls_from_message(message)
            attachments = self.extract_attachments_info(message)

            # Create message hash for deduplication
            message_content = f"{headers.get('Subject', '')}{sender_email}{sorted(urls)}"
            message_hash = hashlib.sha256(message_content.encode()).hexdigest()

            # Store Gmail message
            message_data = {
                'message_id': message['id'],
                'thread_id': message['threadId'],
                'subject': headers.get('Subject', ''),
                'sender_email': sender_email,
                'sender_name': sender_name,
                'urls': urls,
                'attachments': attachments,
                'gmail_timestamp': datetime.fromtimestamp(int(message['internalDate']) / 1000).isoformat(),
                'labels': message.get('labelIds', []),
                'message_hash': message_hash
            }

            result = self.database.store_gmail_message(message_data)
            if not result['success']:
                return result

            # Ingest URLs
            gmail_info = {
                'message_id': message['id'],
                'sender_email': sender_email,
                'subject': headers.get('Subject', '')
            }

            for url in urls:
                self.database.ingest_url(url, source='gmail', gmail_info=gmail_info)

            logging.info(f"✅ Processed Gmail message: {message_id} ({len(urls)} URLs, {len(attachments)} attachments)")
            return {'success': True, 'urls_count': len(urls), 'attachments_count': len(attachments)}

        except HttpError as e:
            logging.error(f"❌ Gmail API error processing {message_id}: {e}")
            return {'success': False, 'error': f'Gmail API error: {e}'}
        except Exception as e:
            logging.error(f"❌ Error processing Gmail message {message_id}: {e}")
            return {'success': False, 'error': str(e)}

    def parse_webhook_message(self, body):
        """Parse Gmail webhook message"""
        try:
            data = json.loads(body.decode('utf-8'))
            if 'message' not in data:
                return None

            message = data['message']
            message_data = base64.b64decode(message['data']).decode('utf-8')
            notification = json.loads(message_data)

            return {
                'email_address': data.get('emailAddress'),
                'history_id': notification.get('historyId'),
                'message_id': notification.get('messageId'),
                'raw_data': notification
            }

        except Exception as e:
            logging.error(f"❌ Failed to parse webhook message: {e}")
            return None

class AtlasV3GmailHandler(BaseHTTPRequestHandler):
    """Enhanced HTTP handler with Gmail webhook support"""

    def __init__(self, *args, database=None, gmail_processor=None, **kwargs):
        self.database = database
        self.gmail_processor = gmail_processor
        super().__init__(*args, **kwargs)

    def do_GET(self):
        """Handle GET requests"""
        if self.path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            response = {
                'service': 'Atlas v3 + Gmail',
                'status': 'running',
                'endpoints': {
                    'ingest': '/ingest?url=<URL>',
                    'gmail_webhook': '/webhook/gmail',
                    'stats': '/stats'
                }
            }
            self.wfile.write(json.dumps(response, indent=2).encode())

        elif self.path == '/stats':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()

            count = self.database.get_count()
            gmail_count = 0

            try:
                conn = sqlite3.connect(self.database.db_path)
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM gmail_messages")
                gmail_count = cursor.fetchone()[0]
                conn.close()
            except:
                pass

            stats = {
                'total_urls': count,
                'gmail_messages': gmail_count,
                'gmail_enabled': GMAIL_AVAILABLE and self.gmail_processor.service is not None
            }
            self.wfile.write(json.dumps(stats, indent=2).encode())

        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        """Handle POST requests"""
        if self.path.startswith('/ingest'):
            # URL ingestion (original v3 functionality)
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)

            try:
                data = json.loads(post_data.decode('utf-8'))
                url = data.get('url') or ''
            except:
                # Fallback to URL parameter
                query = self.path.split('?')[-1] if '?' in self.path else ''
                url = ''
                for param in query.split('&'):
                    if param.startswith('url='):
                        url = unquote(param[4:])
                        break

            if url:
                result = self.database.ingest_url(url, source='api')
                self.send_response(200 if result['success'] else 400)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(result).encode())
            else:
                self.send_response(400)
                self.end_headers()

        elif self.path == '/webhook/gmail':
            # Gmail webhook
            content_length = int(self.headers['Content-Length'])
            body = self.rfile.read(content_length)

            if self.gmail_processor:
                # Parse webhook message
                notification = self.gmail_processor.parse_webhook_message(body)
                if notification:
                    # Process message asynchronously
                    if notification.get('message_id'):
                        asyncio.create_task(self.gmail_processor.process_gmail_message(notification['message_id']))

                    self.send_response(200)
                    self.send_header('Content-type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps({'status': 'received'}).encode())
                else:
                    self.send_response(400)
                    self.end_headers()
            else:
                self.send_response(503)
                self.end_headers()

        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        """Override to prevent default logging"""
        pass

class AtlasV3GmailServer:
    """Main Atlas v3 + Gmail server"""

    def __init__(self, host='localhost', port=8080):
        self.host = host
        self.port = port
        self.database = AtlasV3GmailDatabase()
        self.gmail_processor = GmailProcessor(self.database) if GMAIL_AVAILABLE else None

    async def start_gmail_services(self):
        """Start Gmail background services"""
        if self.gmail_processor:
            success = await self.gmail_processor.authenticate()
            if success:
                logging.info("✅ Gmail services started")
            else:
                logging.warning("⚠️ Gmail services failed to start")

    def run(self):
        """Start the server"""
        # Start Gmail services
        if self.gmail_processor:
            asyncio.run(self.start_gmail_services())

        # Custom handler with database and Gmail processor
        handler = lambda *args, **kwargs: AtlasV3GmailHandler(
            *args, database=self.database, gmail_processor=self.gmail_processor, **kwargs
        )

        server = HTTPServer((self.host, self.port), handler)
        logging.info(f"🚀 Atlas v3 + Gmail server running on http://{self.host}:{self.port}")
        logging.info(f"📊 Current URL count: {self.database.get_count()}")

        try:
            server.serve_forever()
        except KeyboardInterrupt:
            logging.info("🛑 Server stopped")
            server.shutdown()

if __name__ == '__main__':
    # Create config directory if it doesn't exist
    os.makedirs('config', exist_ok=True)

    # Start server
    server = AtlasV3GmailServer()
    server.run()