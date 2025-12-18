#!/usr/bin/env python3
"""
Quick Podcast Content Extractor
Extract summaries and metadata from podcast JSON files for immediate indexing
"""

import json
import os
import sys
import sqlite3
from pathlib import Path
from datetime import datetime
import html

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

class PodcastExtractor:
    def __init__(self):
        self.db_path = "atlas.db"
        self.output_dir = Path("output/podcasts/metadata")
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def init_database(self):
        """Initialize database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS content (
                id INTEGER PRIMARY KEY,
                title TEXT,
                content TEXT,
                content_type TEXT,
                source_url TEXT,
                metadata TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        conn.close()

    def extract_podcast_content(self, json_path):
        """Extract all useful content from podcast metadata"""
        try:
            with open(json_path, 'r') as f:
                data = json.load(f)

            raw_data = data.get('raw_data', {})

            # Extract basic info
            title = raw_data.get('title', 'Unknown Podcast')
            summary = raw_data.get('summary', '')
            description = raw_data.get('description', '')
            link = raw_data.get('link', '')
            published = raw_data.get('published', '')
            author = raw_data.get('author', '')

            # Clean HTML from summary/description
            if summary:
                summary = html.unescape(summary)
                # Remove HTML tags (simple approach)
                import re
                summary = re.sub('<[^<]+?>', '', summary)
                summary = re.sub(r'\s+', ' ', summary).strip()

            if description:
                description = html.unescape(description)
                description = re.sub('<[^<]+?>', '', description)
                description = re.sub(r'\s+', ' ', description).strip()

            # Find audio URL
            audio_url = None
            links = raw_data.get('links', [])
            for link_obj in links:
                if link_obj.get('type', '').startswith('audio/'):
                    audio_url = link_obj.get('href')
                    break

            # Combine all text content
            full_content = []
            if title:
                full_content.append(f"Title: {title}")
            if author:
                full_content.append(f"Author: {author}")
            if published:
                full_content.append(f"Published: {published}")
            if summary:
                full_content.append(f"Summary: {summary}")
            if description and description != summary:
                full_content.append(f"Description: {description}")
            if audio_url:
                full_content.append(f"Audio: {audio_url}")

            content_text = "\n\n".join(full_content)

            # Create metadata
            metadata = {
                'podcast_id': Path(json_path).stem,
                'audio_url': audio_url,
                'published': published,
                'author': author,
                'source': 'podcast_rss'
            }

            return {
                'title': title,
                'content': content_text,
                'source_url': link or audio_url,
                'metadata': json.dumps(metadata)
            }

        except Exception as e:
            print(f"Error extracting {json_path}: {e}")
            return None

    def save_to_database(self, content_data):
        """Save content to database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO content (title, content, content_type, metadata)
                VALUES (?, ?, ?, ?)
            """, (
                content_data['title'],
                content_data['content'],
                'podcast',
                content_data['metadata']
            ))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Database save failed: {e}")
            return False

    def save_to_file(self, content_data, podcast_id):
        """Save content to markdown file"""
        try:
            file_path = self.output_dir / f"{podcast_id}_content.md"
            with open(file_path, 'w') as f:
                f.write(f"# {content_data['title']}\n\n")
                f.write(content_data['content'])
                f.write(f"\n\n---\nProcessed: {datetime.now().isoformat()}\n")
            return str(file_path)
        except Exception as e:
            print(f"File save failed: {e}")
            return None

    def process_all_podcasts(self):
        """Process all podcast metadata files"""
        self.init_database()

        podcast_files = list(Path("output/podcasts").glob("*_rss_entry.json"))
        print(f"Found {len(podcast_files)} podcast files")

        successful = 0
        failed = 0

        for i, podcast_file in enumerate(podcast_files, 1):
            print(f"[{i}/{len(podcast_files)}] Processing {podcast_file.name}")

            content_data = self.extract_podcast_content(podcast_file)
            if not content_data:
                failed += 1
                continue

            # Save to database
            if self.save_to_database(content_data):
                successful += 1
            else:
                failed += 1

            # Save to file
            podcast_id = podcast_file.stem
            self.save_to_file(content_data, podcast_id)

            # Progress update
            if i % 50 == 0:
                print(f"Progress: {i}/{len(podcast_files)} - Success: {successful}, Failed: {failed}")

        print(f"\n🎉 Content extraction complete!")
        print(f"✅ Successful: {successful}")
        print(f"❌ Failed: {failed}")
        print(f"📁 Content saved to database and {self.output_dir}")

        return successful

def main():
    """Main entry point"""
    extractor = PodcastExtractor()
    extractor.process_all_podcasts()

if __name__ == "__main__":
    main()