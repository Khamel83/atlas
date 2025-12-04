#!/usr/bin/env python3
"""
Atlas Content Processor - Simple file-based processing
Processes all content files without external dependencies
"""

import os
import json
import hashlib
from pathlib import Path
from datetime import datetime
import time

class AtlasSimpleProcessor:
    """Simple processor that works with existing content"""

    def __init__(self):
        self.start_time = datetime.now()
        self.base_dir = Path(".")
        self.processed_count = 0
        self.error_count = 0
        self.content_types = {
            'markdown': 0,
            'html': 0,
            'json': 0,
            'other': 0
        }

    def scan_content(self):
        """Scan all content files"""
        print("🔍 SCANNING ATLAS CONTENT...")

        # Find all content files
        markdown_files = list(self.base_dir.rglob("*.md"))
        html_files = list(self.base_dir.rglob("*.html"))
        json_files = list(self.base_dir.rglob("*.json"))

        total_files = len(markdown_files) + len(html_files) + len(json_files)

        print(f"📊 CONTENT OVERVIEW:")
        print(f"   📄 Markdown files: {len(markdown_files):,}")
        print(f"   🌐 HTML files: {len(html_files):,}")
        print(f"   📋 JSON files: {len(json_files):,}")
        print(f"   📁 TOTAL CONTENT FILES: {total_files:,}")

        return {
            'markdown': markdown_files,
            'html': html_files,
            'json': json_files,
            'total': total_files
        }

    def process_markdown_file(self, file_path):
        """Process a single markdown file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Extract metadata from frontmatter if present
            metadata = self.extract_metadata(content, file_path)

            # Create content hash
            content_hash = hashlib.md5(content.encode()).hexdigest()[:16]

            # Update content tracker
            self.update_content_tracker(file_path, metadata, content_hash, 'markdown')

            return True

        except Exception as e:
            print(f"❌ Error processing {file_path}: {e}")
            return False

    def extract_metadata(self, content, file_path):
        """Extract metadata from content"""
        metadata = {
            'file_path': str(file_path),
            'file_size': len(content),
            'word_count': len(content.split()),
            'line_count': content.count('\n'),
            'has_frontmatter': content.startswith('---'),
            'processed_at': datetime.now().isoformat()
        }

        # Extract title if present
        lines = content.split('\n')
        for line in lines[:10]:  # Check first 10 lines
            line = line.strip()
            if line.startswith('# '):
                metadata['title'] = line[2:].strip()
                break
            elif line.startswith('title:'):
                metadata['title'] = line.split(':', 1)[1].strip()
                break

        return metadata

    def update_content_tracker(self, file_path, metadata, content_hash, content_type):
        """Update content tracking"""
        tracker_file = self.base_dir / "content_tracker.json"

        # Load existing tracker
        if tracker_file.exists():
            try:
                with open(tracker_file, 'r') as f:
                    tracker = json.load(f)
            except:
                tracker = {}
        else:
            tracker = {}

        # Add entry
        file_key = str(file_path.relative_to(self.base_dir))
        tracker[file_key] = {
            'uid': f"content_{content_hash}",
            'content_hash': content_hash,
            'content_type': content_type,
            'metadata': metadata,
            'status': 'processed'
        }

        # Save tracker
        try:
            with open(tracker_file, 'w') as f:
                json.dump(tracker, f, indent=2)
        except Exception as e:
            print(f"⚠️  Error saving tracker: {e}")

    def process_all_content(self):
        """Process all content files"""
        content = self.scan_content()

        if content['total'] == 0:
            print("⚠️  No content files found!")
            return

        print(f"\n🚀 PROCESSING {content['total']:,} CONTENT FILES...")
        print("=" * 60)

        # Process markdown files
        for i, file_path in enumerate(content['markdown']):
            if i % 1000 == 0:
                print(f"📄 Processing markdown: {i:,}/{len(content['markdown']):,}")

            if self.process_markdown_file(file_path):
                self.processed_count += 1
            else:
                self.error_count += 1

            self.content_types['markdown'] += 1

        # Process HTML files (basic processing)
        for i, file_path in enumerate(content['html']):
            if i % 1000 == 0:
                print(f"🌐 Processing HTML: {i:,}/{len(content['html']):,}")

            # Basic processing for HTML files
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    html_content = f.read()

                content_hash = hashlib.md5(html_content.encode()).hexdigest()[:16]
                metadata = {
                    'file_path': str(file_path),
                    'file_size': len(html_content),
                    'content_type': 'html',
                    'processed_at': datetime.now().isoformat()
                }

                self.update_content_tracker(file_path, metadata, content_hash, 'html')
                self.processed_count += 1
                self.content_types['html'] += 1

            except Exception as e:
                print(f"❌ Error processing HTML {file_path}: {e}")
                self.error_count += 1

        # Process JSON files (analysis reports, etc.)
        for i, file_path in enumerate(content['json']):
            if i % 500 == 0:
                print(f"📋 Processing JSON: {i:,}/{len(content['json']):,}")

            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    json_content = json.load(f)

                content_hash = hashlib.md5(str(json_content).encode()).hexdigest()[:16]
                metadata = {
                    'file_path': str(file_path),
                    'file_size': len(str(json_content)),
                    'content_type': 'json',
                    'processed_at': datetime.now().isoformat()
                }

                self.update_content_tracker(file_path, metadata, content_hash, 'json')
                self.processed_count += 1
                self.content_types['json'] += 1

            except Exception as e:
                print(f"❌ Error processing JSON {file_path}: {e}")
                self.error_count += 1

        # Show final statistics
        self.show_final_statistics()

    def show_final_statistics(self):
        """Show processing statistics"""
        runtime = datetime.now() - self.start_time

        print("\n" + "=" * 60)
        print("🎯 ATLAS CONTENT PROCESSING COMPLETE!")
        print("=" * 60)
        print(f"⏱️  Total Runtime: {runtime}")
        print(f"✅ Successfully Processed: {self.processed_count:,}")
        print(f"❌ Processing Errors: {self.error_count:,}")
        print(f"📊 Content Types:")
        print(f"   📄 Markdown: {self.content_types['markdown']:,}")
        print(f"   🌐 HTML: {self.content_types['html']:,}")
        print(f"   📋 JSON: {self.content_types['json']:,}")
        print(f"📁 Content tracker updated: content_tracker.json")
        print(f"\n🚀 Atlas content is now fully indexed and tracked!")

if __name__ == "__main__":
    processor = AtlasSimpleProcessor()
    processor.process_all_content()