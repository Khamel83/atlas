#!/usr/bin/env python3
"""
Add all missing documents to Atlas v2 processing queue - FIXED VERSION
"""

import sqlite3
import json
import hashlib
from pathlib import Path
from datetime import datetime
import re

def create_content_id(file_url, document_id):
    """Create unique content ID from file path and document ID"""
    content_str = f"{file_url}|{document_id}"
    hash_suffix = hashlib.md5(content_str.encode()).hexdigest()[:8]
    date_str = datetime.now().strftime("%Y%m%d")
    clean_doc_id = document_id.replace('_', '-')[:20]
    return f"document-{date_str}-{clean_doc_id}-{hash_suffix}"

def add_documents_to_queue():
    """Add all missing documents to the processing queue"""
    print("🚀 Adding all missing documents to Atlas v2 queue...")

    atlas_v1_path = Path("/home/ubuntu/dev/atlas/output")
    atlas_v2_db_path = "/home/ubuntu/dev/atlas/atlas_v2/data/atlas_v2.db"

    # Connect to Atlas v2 database
    v2_conn = sqlite3.connect(atlas_v2_db_path)
    cursor = v2_conn.cursor()

    # Get existing document URLs to avoid duplicates
    existing_urls = set()
    cursor.execute("SELECT source_url FROM processing_queue WHERE source_name = 'documents'")
    for row in cursor.fetchall():
        existing_urls.add(row[0])

    print(f"📊 Found {len(existing_urls)} existing documents in queue")

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
            document_id = doc_file.stem.replace('_structured', '')
            metadata = {
                'document_id': document_id,
                'type': 'document',
                'file_path': str(doc_file.relative_to(atlas_v1_path)),
                'migration_timestamp': datetime.now().isoformat()
            }

            if isinstance(data, dict):
                metadata.update({k: v for k, v in data.items() if isinstance(v, (str, int, float, bool))})

            # Create URL and content ID
            file_url = f"file://{doc_file.relative_to(atlas_v1_path)}"
            content_id = create_content_id(file_url, document_id)

            # Skip if already exists
            if file_url in existing_urls:
                continue

            # Insert into content_metadata first
            cursor.execute('''
                INSERT OR IGNORE INTO content_metadata
                (content_id, source_url, source_name, content_type, title, metadata_json, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                content_id, file_url, 'documents', 'document',
                metadata.get('document_id', ''), json.dumps(metadata),
                datetime.now().isoformat(), datetime.now().isoformat()
            ))

            # Then insert into processing_queue
            cursor.execute('''
                INSERT OR IGNORE INTO processing_queue
                (content_id, source_url, source_name, content_type, priority, metadata_json, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (content_id, file_url, 'documents', 'document', 'normal', json.dumps(metadata),
                  datetime.now().isoformat(), datetime.now().isoformat()))

            added_count += 1

            if added_count % 1000 == 0:
                print(f"  ✅ Added {added_count} documents to queue...")
                v2_conn.commit()  # Commit periodically

        except Exception as e:
            error_count += 1
            if error_count <= 10:  # Only print first 10 errors
                print(f"❌ Error processing {doc_file}: {e}")

    # Final commit
    v2_conn.commit()

    # Verify the results
    cursor.execute("SELECT COUNT(*) FROM processing_queue WHERE source_name = 'documents'")
    actual_doc_count = cursor.fetchone()[0]

    cursor.execute("SELECT status, COUNT(*) FROM processing_queue GROUP BY status")
    queue_status = dict(cursor.fetchall())

    v2_conn.close()

    print(f"\n🎯 Queue update complete!")
    print(f"✅ Added {added_count:,} new documents to processing queue")
    print(f"❌ Errors: {error_count}")
    print(f"📊 Actual documents in queue: {actual_doc_count:,}")
    print(f"📊 Queue status: {queue_status}")

    return added_count

if __name__ == "__main__":
    added = add_documents_to_queue()
    print(f"\n🚀 Atlas v2 now has {added:,} new documents to process!")