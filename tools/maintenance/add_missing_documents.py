#!/usr/bin/env python3
"""
Add all missing documents to Atlas v2 processing queue
"""

import sqlite3
import json
import hashlib
from pathlib import Path
from datetime import datetime
import re

def create_content_hash(url, title, source):
    """Create unique hash for content deduplication"""
    content_str = f"{url}|{title or ''}|{source or ''}"
    return hashlib.md5(content_str.encode()).hexdigest()

def create_content_id(url, title, source):
    """Create content ID from URL and metadata"""
    if not url:
        return f"content-{datetime.now().strftime('%Y%m%d%H%M%S')}"

    title_text = title or ''
    if not title_text:
        title_text = url.split('/')[-1] if '/' in url else url

    slug = re.sub(r'[^a-zA-Z0-9\s-]', '', title_text.lower())
    slug = re.sub(r'[-\s]+', '-', slug)[:30]

    date_str = datetime.now().strftime('%Y%m%d')
    return f"{source or 'unknown'}-{date_str}-{slug}"

def add_documents_to_queue():
    """Add all missing documents to the processing queue"""
    print("🚀 Adding all missing documents to Atlas v2 queue...")

    atlas_v1_path = Path("/home/ubuntu/dev/atlas/output")
    atlas_v2_db_path = "/home/ubuntu/dev/atlas/atlas_v2/data/atlas_v2.db"

    # Connect to Atlas v2 database
    v2_conn = sqlite3.connect(atlas_v2_db_path)

    # Get existing hashes to avoid duplicates
    existing_hashes = set()
    cursor = v2_conn.execute("SELECT source_url, metadata_json FROM processing_queue")
    for row in cursor.fetchall():
        url, metadata = row
        if url and metadata:
            try:
                meta = json.loads(metadata)
                title = meta.get('title', '')
                source = meta.get('source', 'document')
                existing_hashes.add(create_content_hash(url, title, source))
            except:
                pass

    print(f"📊 Found {len(existing_hashes)} existing items in queue")

    # Find all structured documents
    docs_dir = atlas_v1_path / "documents"
    structured_files = list(docs_dir.glob("**/*_structured.json"))
    print(f"📂 Found {len(structured_files)} structured documents")

    added_count = 0
    error_count = 0

    for i, doc_file in enumerate(structured_files):
        if i % 1000 == 0:
            print(f"📊 Processing document {i}/{len(structured_files)}...")

        try:
            with open(doc_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Create metadata
            metadata = {
                'document_id': doc_file.stem.replace('_structured', ''),
                'type': 'document',
                'file_path': str(doc_file.relative_to(atlas_v1_path)),
                'migration_timestamp': datetime.now().isoformat()
            }

            if isinstance(data, dict):
                metadata.update({k: v for k, v in data.items() if isinstance(v, (str, int, float, bool))})

            # Create URL and content ID
            file_url = f"file://{doc_file.relative_to(atlas_v1_path)}"
            content_id = create_content_id(file_url, metadata.get('document_id', ''), 'document')
            content_hash = create_content_hash(file_url, metadata.get('document_id', ''), 'document')

            # Skip if already exists
            if content_hash in existing_hashes:
                continue

            # Add to queue
            v2_conn.execute('''
                INSERT OR IGNORE INTO processing_queue
                (content_id, source_url, source_name, content_type, priority, metadata_json)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                content_id, file_url, 'documents', 'document', 'normal', json.dumps(metadata)
            ))

            added_count += 1

            if added_count % 1000 == 0:
                print(f"  ✅ Added {added_count} documents to queue...")

        except Exception as e:
            error_count += 1
            if error_count <= 10:  # Only print first 10 errors
                print(f"❌ Error processing {doc_file}: {e}")

    v2_conn.commit()
    v2_conn.close()

    print(f"\n🎯 Queue update complete!")
    print(f"✅ Added {added_count:,} documents to processing queue")
    print(f"❌ Errors: {error_count}")
    print(f"📊 Total queue size should now be: {added_count + 175} items")

    return added_count

if __name__ == "__main__":
    added = add_documents_to_queue()
    print(f"\n🚀 Atlas v2 now has {added:,} new documents to process!")