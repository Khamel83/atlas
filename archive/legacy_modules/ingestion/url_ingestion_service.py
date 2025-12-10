#!/usr/bin/env python3
"""
Universal URL Ingestion Service for Atlas
Integrates with Velja for intelligent content routing
"""

import sqlite3
import requests
import json
import logging
from datetime import datetime
from urllib.parse import urlparse, parse_qs
import re
import os
from typing import Dict, List, Tuple, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/url_ingestion.log'),
        logging.StreamHandler()
    ]
)

class URLClassifier:
    """Intelligent URL classification system"""

    def __init__(self):
        self.documentation_patterns = {
            'domains': [
                'github.com', 'medium.com', 'dev.to', 'stackoverflow.com',
                'developer.mozilla.org', 'docs.python.org', 'reactjs.org',
                'stackoverflow.blog', 'hackernoon.com', ' towardsdatascience.com',
                'freecodecamp.org', 'css-tricks.com', 'smashingmagazine.com'
            ],
            'path_patterns': [
                r'/docs?', r'/documentation', r'/guide', r'/tutorial',
                r'/blog/', r'/article/', r'/learn/', r'/how-?to',
                r'/reference', r'/api', r'/manual', r'/handbook'
            ],
            'file_extensions': ['.md', '.txt', '.rst', '.pdf']
        }

        self.media_patterns = {
            'domains': [
                'youtube.com', 'vimeo.com', 'twitter.com', 'instagram.com',
                'tiktok.com', 'facebook.com', 'reddit.com/r/videos',
                'twitch.tv', 'dailymotion.com'
            ],
            'path_patterns': [
                r'/watch', r'/video', r'/media', r'/stream', r'/clip',
                r'/movies', r'/tv', r'/v/', r'/videos/'
            ],
            'file_extensions': ['.mp4', '.avi', '.mov', '.wmv', '.flv', '.mkv']
        }

        self.podcast_patterns = {
            'domains': [
                'npr.org', 'bbc.co.uk', 'thestartup.chat', 'acquired.fm',
                'stratechery.com', 'atp.fm', 'omny.fm', 'simplecast.com',
                'megaphone.fm', 'transistor.fm', 'apple.com/podcasts',
                'spotify.com/show', 'stitcher.com'
            ],
            'path_patterns': [
                r'/podcast', r'/episode', r'/show', r'/listen', r'/audio'
            ]
        }

    def classify_url(self, url: str) -> Dict[str, any]:
        """Classify URL and determine routing"""
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            path = parsed.path.lower()

            # Extract file extension if present
            file_ext = os.path.splitext(path)[1].lower()

            classification = {
                'url': url,
                'domain': domain,
                'path': path,
                'file_extension': file_ext,
                'content_type': None,
                'confidence': 0.0,
                'routing_destination': None,
                'priority': 'normal',
                'metadata': {}
            }

            # Check patterns and calculate confidence
            scores = self._calculate_scores(domain, path, file_ext)

            # Determine classification based on highest score
            best_category = max(scores.items(), key=lambda x: x[1])
            classification['content_type'] = best_category[0]
            classification['confidence'] = best_category[1]

            # Set routing destination based on classification
            classification['routing_destination'] = self._determine_routing(
                classification['content_type'],
                classification['confidence']
            )

            # Add additional metadata
            classification['metadata'] = self._extract_metadata(url, parsed)

            return classification

        except Exception as e:
            logging.error(f"Error classifying URL {url}: {e}")
            return {
                'url': url,
                'content_type': 'unknown',
                'confidence': 0.0,
                'routing_destination': 'manual_review',
                'priority': 'normal',
                'metadata': {'error': str(e)}
            }

    def _calculate_scores(self, domain: str, path: str, file_ext: str) -> Dict[str, float]:
        """Calculate confidence scores for each content type"""
        scores = {
            'documentation': 0.0,
            'media': 0.0,
            'podcast': 0.0
        }

        # Documentation scoring
        if domain in self.documentation_patterns['domains']:
            scores['documentation'] += 0.7

        for pattern in self.documentation_patterns['path_patterns']:
            if re.search(pattern, path):
                scores['documentation'] += 0.5

        if file_ext in self.documentation_patterns['file_extensions']:
            scores['documentation'] += 0.8

        # Media scoring
        if domain in self.media_patterns['domains']:
            scores['media'] += 0.8

        for pattern in self.media_patterns['path_patterns']:
            if re.search(pattern, path):
                scores['media'] += 0.6

        if file_ext in self.media_patterns['file_extensions']:
            scores['media'] += 0.9

        # Podcast scoring
        if domain in self.podcast_patterns['domains']:
            scores['podcast'] += 0.8

        for pattern in self.podcast_patterns['path_patterns']:
            if re.search(pattern, path):
                scores['podcast'] += 0.6

        return scores

    def _determine_routing(self, content_type: str, confidence: float) -> str:
        """Determine where to route the content"""
        if confidence < 0.3:
            return 'manual_review'

        routing_map = {
            'documentation': 'atlas',
            'media': 'native_app',
            'podcast': 'atlas'
        }

        return routing_map.get(content_type, 'manual_review')

    def _extract_metadata(self, url: str, parsed) -> Dict[str, any]:
        """Extract additional metadata from URL"""
        metadata = {
            'scheme': parsed.scheme,
            'domain': parsed.netloc,
            'path': parsed.path,
            'query_params': parse_qs(parsed.query),
            'fragment': parsed.fragment,
            'timestamp': datetime.now().isoformat()
        }

        # Extract specific identifiers
        if 'youtube.com' in parsed.netloc:
            video_id = parse_qs(parsed.query).get('v', [None])[0]
            if video_id:
                metadata['video_id'] = video_id
                metadata['platform'] = 'youtube'

        elif 'github.com' in parsed.netloc:
            path_parts = parsed.path.strip('/').split('/')
            if len(path_parts) >= 2:
                metadata['repo_owner'] = path_parts[0]
                metadata['repo_name'] = path_parts[1]
                if len(path_parts) > 2:
                    metadata['content_type'] = path_parts[2]  # issues, pull, blob, etc.

        return metadata

class AtlasIngestionService:
    """Main ingestion service for Atlas integration"""

    def __init__(self, db_path: str = 'data/atlas.db'):
        self.db_path = db_path
        self.classifier = URLClassifier()
        self.ensure_database()

    def ensure_database(self):
        """Ensure ingestion database exists"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Create ingestion queue table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ingestion_queue (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url TEXT NOT NULL UNIQUE,
                classification JSON,
                status TEXT DEFAULT 'pending',
                routing_destination TEXT,
                source TEXT DEFAULT 'manual',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                processing_started_at TEXT,
                processing_completed_at TEXT,
                result_id TEXT,
                error_message TEXT,
                retry_count INTEGER DEFAULT 0,
                priority TEXT DEFAULT 'normal'
            )
        """)

        # Create index for performance
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_ingestion_status ON ingestion_queue(status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_ingestion_created ON ingestion_queue(created_at)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_ingestion_routing ON ingestion_queue(routing_destination)")

        conn.commit()
        conn.close()

    def ingest_url(self, url: str, source: str = 'manual', priority: str = 'normal') -> Dict[str, any]:
        """Ingest a URL into the system"""
        try:
            # Classify the URL
            classification = self.classifier.classify_url(url)

            # Store in database
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("""
                INSERT OR REPLACE INTO ingestion_queue
                (url, classification, routing_destination, priority, source, updated_at)
                VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (
                url,
                json.dumps(classification),
                classification['routing_destination'],
                priority,
                source
            ))

            ingestion_id = cursor.lastrowid
            conn.commit()
            conn.close()

            logging.info(f"URL ingested: {url} -> {classification['routing_destination']} (confidence: {classification['confidence']:.2f})")

            return {
                'success': True,
                'ingestion_id': ingestion_id,
                'classification': classification,
                'status': 'queued',
                'message': 'URL successfully ingested'
            }

        except Exception as e:
            logging.error(f"Error ingesting URL {url}: {e}")
            return {
                'success': False,
                'error': str(e),
                'message': 'Failed to ingest URL'
            }

    def process_pending_batch(self, batch_size: int = 10) -> Dict[str, any]:
        """Process a batch of pending URLs"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Get pending URLs
        cursor.execute("""
            SELECT id, url, classification, routing_destination, priority
            FROM ingestion_queue
            WHERE status = 'pending'
            ORDER BY
                CASE priority
                    WHEN 'high' THEN 1
                    WHEN 'normal' THEN 2
                    WHEN 'low' THEN 3
                END,
                created_at ASC
            LIMIT ?
        """, (batch_size,))

        pending_items = cursor.fetchall()

        if not pending_items:
            conn.close()
            return {'processed': 0, 'success': 0, 'failed': 0}

        results = {'processed': 0, 'success': 0, 'failed': 0}

        for item_id, url, classification_json, routing_destination, priority in pending_items:
            try:
                # Mark as processing
                cursor.execute("""
                    UPDATE ingestion_queue
                    SET status = 'processing', processing_started_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (item_id,))

                conn.commit()

                # Process based on routing destination
                result = self._process_by_routing(url, routing_destination, json.loads(classification_json))

                # Update status based on result
                if result['success']:
                    cursor.execute("""
                        UPDATE ingestion_queue
                        SET status = 'completed',
                            processing_completed_at = CURRENT_TIMESTAMP,
                            result_id = ?,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE id = ?
                    """, (result.get('result_id'), item_id))
                    results['success'] += 1
                else:
                    cursor.execute("""
                        UPDATE ingestion_queue
                        SET status = 'failed',
                            error_message = ?,
                            processing_completed_at = CURRENT_TIMESTAMP,
                            updated_at = CURRENT_TIMESTAMP,
                            retry_count = retry_count + 1
                        WHERE id = ?
                    """, (result.get('error'), item_id))
                    results['failed'] += 1

                conn.commit()
                results['processed'] += 1

            except Exception as e:
                logging.error(f"Error processing item {item_id}: {e}")
                cursor.execute("""
                    UPDATE ingestion_queue
                    SET status = 'failed',
                        error_message = ?,
                        processing_completed_at = CURRENT_TIMESTAMP,
                        updated_at = CURRENT_TIMESTAMP,
                        retry_count = retry_count + 1
                    WHERE id = ?
                """, (str(e), item_id))
                conn.commit()
                results['failed'] += 1
                results['processed'] += 1

        conn.close()
        logging.info(f"Batch processing complete: {results}")
        return results

    def _process_by_routing(self, url: str, routing_destination: str, classification: Dict) -> Dict[str, any]:
        """Process URL based on routing destination"""
        if routing_destination == 'atlas':
            return self._process_with_atlas(url, classification)
        elif routing_destination == 'native_app':
            return self._process_with_native_app(url, classification)
        elif routing_destination == 'manual_review':
            return self._flag_for_review(url, classification)
        else:
            return {'success': False, 'error': f'Unknown routing destination: {routing_destination}'}

    def _process_with_atlas(self, url: str, classification: Dict) -> Dict[str, any]:
        """Process URL with Atlas (documentation/podcast content)"""
        try:
            # Import here to avoid circular imports
            from single_episode_processor import process_episode

            # For now, handle as generic content extraction
            # This will be enhanced based on content type
            if classification['content_type'] == 'podcast':
                # Use existing podcast processing
                result = process_episode(1, url, classification.get('metadata', {}).get('domain', 'Unknown'))
                return {
                    'success': result,
                    'result_id': f"podcast_{url}" if result else None,
                    'method': 'podcast_processor'
                }
            else:
                # Generic content extraction for documentation
                return self._extract_documentation(url, classification)

        except Exception as e:
            return {'success': False, 'error': str(e)}

    def _extract_documentation(self, url: str, classification: Dict) -> Dict[str, any]:
        """Extract documentation content from URL"""
        try:
            import requests
            from bs4 import BeautifulSoup

            # Fetch content
            response = requests.get(url, timeout=30, headers={
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
            })

            if response.status_code != 200:
                return {'success': False, 'error': f'HTTP {response.status_code}'}

            soup = BeautifulSoup(response.content, 'html.parser')

            # Extract main content
            content_selectors = [
                'article', 'main', '.content', '.documentation',
                '.markdown-body', '.post-content', '.entry-content'
            ]

            content = None
            for selector in content_selectors:
                element = soup.select_one(selector)
                if element:
                    text = element.get_text(separator=' ', strip=True)
                    if len(text) > 500:  # Minimum content length
                        content = text
                        break

            if not content:
                # Fallback to largest text block
                text_blocks = []
                for elem in soup.find_all(['div', 'section', 'article']):
                    text = elem.get_text(separator=' ', strip=True)
                    if len(text) > 500:
                        text_blocks.append((len(text), text))

                if text_blocks:
                    text_blocks.sort(reverse=True)
                    content = text_blocks[0][1]

            if content:
                # Store in Atlas database
                conn = sqlite3.connect('data/atlas.db')
                cursor = conn.cursor()

                cursor.execute("""
                    INSERT INTO content (title, url, content, content_type, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    f"Documentation: {classification.get('metadata', {}).get('domain', 'Unknown')}",
                    url,
                    content,
                    'documentation',
                    datetime.now().isoformat(),
                    datetime.now().isoformat()
                ))

                result_id = str(cursor.lastrowid)
                conn.commit()
                conn.close()

                return {
                    'success': True,
                    'result_id': result_id,
                    'content_length': len(content),
                    'method': 'documentation_extraction'
                }
            else:
                return {'success': False, 'error': 'No extractable content found'}

        except Exception as e:
            return {'success': False, 'error': str(e)}

    def _process_with_native_app(self, url: str, classification: Dict) -> Dict[str, any]:
        """Process URL with native app (media content)"""
        # This will be implemented with AppleScript or URL schemes
        # For now, just flag for manual processing
        return {
            'success': False,
            'error': 'Native app integration not yet implemented',
            'suggestion': 'Please process manually with your video downloader'
        }

    def _flag_for_review(self, url: str, classification: Dict) -> Dict[str, any]:
        """Flag URL for manual review"""
        return {
            'success': False,
            'error': 'Requires manual review',
            'confidence': classification.get('confidence', 0),
            'reason': 'Low confidence classification'
        }

    def get_queue_status(self) -> Dict[str, any]:
        """Get current queue status"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT status, COUNT(*) as count
            FROM ingestion_queue
            GROUP BY status
        """)

        status_counts = dict(cursor.fetchall())

        cursor.execute("SELECT COUNT(*) FROM ingestion_queue")
        total = cursor.fetchone()[0]

        conn.close()

        return {
            'total': total,
            'status_counts': status_counts,
            'pending': status_counts.get('pending', 0),
            'processing': status_counts.get('processing', 0),
            'completed': status_counts.get('completed', 0),
            'failed': status_counts.get('failed', 0)
        }

def main():
    """CLI interface for the ingestion service"""
    if len(sys.argv) < 2:
        print("Usage: python3 url_ingestion_service.py <command> [args]")
        print("Commands:")
        print("  ingest <url> [source] [priority] - Ingest a URL")
        print("  process [batch_size] - Process pending URLs")
        print("  status - Show queue status")
        sys.exit(1)

    service = AtlasIngestionService()
    command = sys.argv[1]

    if command == 'ingest':
        if len(sys.argv) < 3:
            print("Error: ingest command requires a URL")
            sys.exit(1)

        url = sys.argv[2]
        source = sys.argv[3] if len(sys.argv) > 3 else 'manual'
        priority = sys.argv[4] if len(sys.argv) > 4 else 'normal'

        result = service.ingest_url(url, source, priority)
        print(f"Result: {result}")

    elif command == 'process':
        batch_size = int(sys.argv[2]) if len(sys.argv) > 2 else 10
        result = service.process_pending_batch(batch_size)
        print(f"Processing result: {result}")

    elif command == 'status':
        status = service.get_queue_status()
        print(f"Queue status: {status}")

    else:
        print(f"Unknown command: {command}")
        sys.exit(1)

if __name__ == "__main__":
    import sys
    main()