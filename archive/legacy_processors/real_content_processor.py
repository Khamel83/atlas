#!/usr/bin/env python3
"""
Real Atlas v2 Content Processor
Actually processes structured documents into markdown content
"""

import sqlite3
import json
import os
import subprocess
import time
from datetime import datetime
from pathlib import Path
import hashlib

def convert_structured_to_markdown(structured_data, metadata):
    """Convert structured JSON to markdown format"""
    if not structured_data.get('structured_content'):
        return None

    content_lines = []
    content_lines.append(f"# {metadata.get('document_id', 'Untitled Document')}")
    content_lines.append("")

    # Add metadata header
    content_lines.append("## Document Information")
    content_lines.append(f"- **Source File**: {metadata.get('source_file', 'Unknown')}")
    content_lines.append(f"- **Document ID**: {metadata.get('uid', 'Unknown')}")
    content_lines.append(f"- **Processed**: {metadata.get('processing_timestamp', 'Unknown')}")
    content_lines.append("")

    # Process structured content
    for item in structured_data['structured_content']:
        item_type = item.get('type', '').lower()
        text = item.get('text', '').strip()

        if not text:
            continue

        if item_type == 'title':
            # Determine heading level based on text length and context
            if len(text) < 50 and not text.endswith('.'):
                content_lines.append(f"## {text}")
            else:
                content_lines.append(f"### {text}")
            content_lines.append("")

        elif item_type == 'narrativetext':
            content_lines.append(text)
            content_lines.append("")

        elif item_type == 'listitem':
            content_lines.append(f"- {text}")

        elif item_type == 'quote':
            content_lines.append(f"> {text}")
            content_lines.append("")

        else:
            # Default handling for other types
            content_lines.append(text)
            content_lines.append("")

    return '\n'.join(content_lines)

def process_content_batch(batch_size=20):
    """Actually process a batch of structured documents"""
    print(f"🔄 Processing {batch_size} structured documents at {datetime.now()}")

    conn = sqlite3.connect("/home/ubuntu/dev/atlas/atlas_v2/data/atlas_v2.db")
    cursor = conn.cursor()

    # Get pending documents
    cursor.execute('''
        SELECT content_id, source_url, metadata_json
        FROM processing_queue
        WHERE status = 'pending' AND source_name = 'documents'
        LIMIT ?
    ''', (batch_size,))

    items = cursor.fetchall()
    print(f"Found {len(items)} documents to process")

    processed_count = 0

    for content_id, source_url, metadata_json in items:
        try:
            # Update status to processing
            cursor.execute('''
                UPDATE processing_queue
                SET status = 'processing', updated_at = ?
                WHERE content_id = ?
            ''', (datetime.now().isoformat(), content_id))

            metadata = json.loads(metadata_json)
            file_path = metadata.get('file_path', '')

            if not file_path:
                print(f"❌ No file path for {content_id}")
                cursor.execute('''
                    UPDATE processing_queue
                    SET status = 'failed', updated_at = ?
                    WHERE content_id = ?
                ''', (datetime.now().isoformat(), content_id))
                continue

            # Read the structured document
            full_path = Path("/home/ubuntu/dev/atlas/output") / file_path
            if not full_path.exists():
                print(f"❌ File not found: {full_path}")
                cursor.execute('''
                    UPDATE processing_queue
                    SET status = 'failed', updated_at = ?
                    WHERE content_id = ?
                ''', (datetime.now().isoformat(), content_id))
                continue

            with open(full_path, 'r', encoding='utf-8') as f:
                structured_data = json.load(f)

            # Convert to markdown
            markdown_content = convert_structured_to_markdown(structured_data, metadata)

            if markdown_content:
                # Create output directory
                output_dir = Path("/home/ubuntu/dev/atlas/atlas_v2/content/markdown")
                output_dir.mkdir(parents=True, exist_ok=True)

                # Create filename from source URL
                filename = f"url_{source_url.replace('://', '_').replace('/', '_')}.md"
                filename = filename.replace('file://documents_', 'document_')[:200]  # Limit length
                output_file = output_dir / filename

                # Write markdown content
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(markdown_content)

                # Insert into content_metadata table
                cursor.execute('''
                    INSERT OR REPLACE INTO content_metadata
                    (content_id, source_url, source_name, content_type, title, metadata_json, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    content_id, source_url, 'documents', 'document',
                    metadata.get('document_id', content_id),
                    json.dumps(metadata),
                    datetime.now().isoformat(),
                    datetime.now().isoformat()
                ))

                print(f"✅ Processed: {content_id} -> {filename}")
                processed_count += 1

                # Update status to completed
                cursor.execute('''
                    UPDATE processing_queue
                    SET status = 'completed', updated_at = ?, completed_at = ?
                    WHERE content_id = ?
                ''', (datetime.now().isoformat(), datetime.now().isoformat(), content_id))
            else:
                print(f"❌ No content generated for {content_id}")
                cursor.execute('''
                    UPDATE processing_queue
                    SET status = 'failed', updated_at = ?
                    WHERE content_id = ?
                ''', (datetime.now().isoformat(), content_id))

        except Exception as e:
            print(f"❌ Error processing {content_id}: {e}")
            cursor.execute('''
                UPDATE processing_queue
                SET status = 'failed', updated_at = ?
                WHERE content_id = ?
            ''', (datetime.now().isoformat(), content_id))

    conn.commit()
    conn.close()

    print(f"✅ Batch complete: {processed_count}/{len(items)} documents processed")
    return processed_count

def continuous_real_processor():
    """Run continuous real processing"""
    print("🚀 Starting Atlas v2 Real Content Processor")
    print("Actually converting structured documents to markdown")
    print("Processing 20 documents every 2 minutes")
    print("Press Ctrl+C to stop")

    while True:
        try:
            conn = sqlite3.connect("/home/ubuntu/dev/atlas/atlas_v2/data/atlas_v2.db")
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM processing_queue WHERE status = 'pending' AND source_name = 'documents'")
            pending_count = cursor.fetchone()[0]
            conn.close()

            print(f"\n📊 Pending documents: {pending_count}")

            if pending_count > 0:
                processed = process_content_batch(20)
                if processed == 0:
                    print("⚠️ No documents processed, may be hitting errors")
            else:
                print("✅ All documents processed!")
                break

        except Exception as e:
            print(f"❌ Error in processing loop: {e}")

        print("⏰ Waiting 2 minutes...")
        time.sleep(120)

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Atlas v2 Real Content Processor')
    parser.add_argument('--run', action='store_true', help='Run continuous real processor')
    parser.add_argument('--once', action='store_true', help='Process one batch only')
    parser.add_argument('--batch-size', type=int, default=20, help='Batch size per run')

    args = parser.parse_args()

    if args.run:
        continuous_real_processor()
    elif args.once:
        process_content_batch(args.batch_size)
    else:
        print("Usage: python3 real_content_processor.py --run or --once [--batch-size N]")