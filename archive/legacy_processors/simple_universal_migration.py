#!/usr/bin/env python3
"""
Simple Universal Migration - Everything from Atlas v1 to Atlas v2
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

    # Extract slug from title or URL
    title_text = title or ''
    if not title_text:
        title_text = url.split('/')[-1] if '/' in url else url

    slug = re.sub(r'[^a-zA-Z0-9\s-]', '', title_text.lower())
    slug = re.sub(r'[-\s]+', '-', slug)[:30]

    date_str = datetime.now().strftime('%Y%m%d')
    return f"{source or 'unknown'}-{date_str}-{slug}"

def migrate_everything():
    """Migrate everything from Atlas v1 to Atlas v2"""
    print("🚀 Starting universal migration of ALL Atlas content...")

    atlas_v1_path = Path("/home/ubuntu/dev/atlas/output")
    atlas_v2_db_path = "/home/ubuntu/dev/atlas/atlas_v2/data/atlas_v2.db"

    # Connect to Atlas v2 database
    v2_conn = sqlite3.connect(atlas_v2_db_path)

    # Create tables if they don't exist
    v2_conn.execute('''
        CREATE TABLE IF NOT EXISTS processing_queue (
            content_id TEXT PRIMARY KEY,
            source_url TEXT NOT NULL,
            source_name TEXT,
            content_type TEXT NOT NULL,
            status TEXT DEFAULT 'pending',
            priority TEXT DEFAULT 'normal',
            metadata_json TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    v2_conn.execute('''
        CREATE TABLE IF NOT EXISTS processed_content (
            content_id TEXT PRIMARY KEY,
            content_type TEXT NOT NULL,
            content TEXT,
            metadata_json TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Get existing content hashes
    existing_hashes = set()
    cursor = v2_conn.execute("SELECT source_url, metadata_json FROM processing_queue")
    for row in cursor.fetchall():
        url, metadata = row
        if url and metadata:
            try:
                meta = json.loads(metadata)
                title = meta.get('title', '')
                source = meta.get('source', 'podcast')
                existing_hashes.add(create_content_hash(url, title, source))
            except:
                pass

    print(f"📊 Found {len(existing_hashes)} existing items in Atlas v2")

    stats = {
        'queue_items': 0,
        'podcast_files': 0,
        'article_files': 0,
        'transcript_files': 0,
        'document_files': 0,
        'duplicates_skipped': 0,
        'errors': 0
    }

    # 1. Migrate queue items
    print("\n📋 Migrating queue items...")
    v1_queue_db = atlas_v1_path / "processing_queue.db"
    if v1_queue_db.exists():
        v1_conn = sqlite3.connect(v1_queue_db)
        cursor = v1_conn.execute("""
            SELECT episode_url, episode_title, podcast_name, created_at, status
            FROM processing_queue
            WHERE status IN ('pending', 'processing')
            ORDER BY created_at DESC
        """)

        for row in cursor.fetchall():
            episode_url, episode_title, podcast_name, created_at, status = row

            if not episode_url:
                continue

            content_hash = create_content_hash(episode_url, episode_title, podcast_name)
            if content_hash in existing_hashes:
                stats['duplicates_skipped'] += 1
                continue

            content_id = create_content_id(episode_url, episode_title, podcast_name)
            metadata = {
                'title': episode_title,
                'podcast_name': podcast_name,
                'source': 'atlas_v1_queue',
                'original_status': status,
                'migration_timestamp': datetime.now().isoformat()
            }

            try:
                v2_conn.execute('''
                    INSERT OR IGNORE INTO processing_queue
                    (content_id, source_url, source_name, content_type, priority, metadata_json, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    content_id, episode_url, podcast_name, 'podcast', 'high',
                    json.dumps(metadata), created_at or datetime.now().isoformat()
                ))
                stats['queue_items'] += 1
                existing_hashes.add(content_hash)

                if stats['queue_items'] % 50 == 0:
                    print(f"  📊 Migrated {stats['queue_items']} queue items...")

            except Exception as e:
                print(f"  ❌ Error migrating queue item {episode_title}: {e}")
                stats['errors'] += 1

        v1_conn.close()
        print(f"✅ Queue migration complete: {stats['queue_items']} items")

    # 2. Migrate podcast files
    print("\n🎙️ Migrating podcast files...")
    podcast_dir = atlas_v1_path / "podcasts"
    if podcast_dir.exists():
        json_files = list(podcast_dir.glob("**/*_rss_entry.json"))
        print(f"  📊 Found {len(json_files)} podcast files")

        for i, podcast_file in enumerate(json_files):
            if i % 100 == 0:
                print(f"  📊 Processing podcast file {i}/{len(json_files)}...")

            try:
                with open(podcast_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                if 'raw_data' in data:
                    raw = data['raw_data']
                    title = raw.get('title', '')
                    link = raw.get('link', '')
                    source = data.get('source', 'unknown')

                    if not link:
                        continue

                    content_hash = create_content_hash(link, title, source)
                    if content_hash in existing_hashes:
                        stats['duplicates_skipped'] += 1
                        continue

                    content_id = create_content_id(link, title, source)
                    metadata = {
                        'title': title,
                        'source': source,
                        'type': 'podcast_rss',
                        'authors': [author.get('name', '') for author in raw.get('authors', [])],
                        'published': raw.get('published', ''),
                        'itunes_duration': raw.get('itunes_duration', ''),
                        'summary': raw.get('summary', '')[:500] if raw.get('summary') else '',
                        'migration_file': str(podcast_file.relative_to(atlas_v1_path)),
                        'migration_timestamp': datetime.now().isoformat()
                    }

                    v2_conn.execute('''
                        INSERT OR IGNORE INTO processing_queue
                        (content_id, source_url, source_name, content_type, priority, metadata_json)
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', (
                        content_id, link, source, 'podcast', 'normal', json.dumps(metadata)
                    ))

                    stats['podcast_files'] += 1
                    existing_hashes.add(content_hash)

            except Exception as e:
                print(f"  ❌ Error processing {podcast_file}: {e}")
                stats['errors'] += 1

        print(f"✅ Podcast migration complete: {stats['podcast_files']} items")

    # 3. Migrate article files
    print("\n📰 Migrating article files...")
    articles_dir = atlas_v1_path / "articles"
    if articles_dir.exists():
        md_files = list(articles_dir.glob("**/*.md"))
        print(f"  📊 Found {len(md_files)} article files")

        for i, article_file in enumerate(md_files):
            if i % 200 == 0:
                print(f"  📊 Processing article file {i}/{len(md_files)}...")

            try:
                with open(article_file, 'r', encoding='utf-8') as f:
                    content = f.read()

                if len(content) < 100:
                    continue

                content_hash = hashlib.md5(content.encode()).hexdigest()
                if content_hash in existing_hashes:
                    stats['duplicates_skipped'] += 1
                    continue

                content_id = f"article-{article_file.stem}"

                # Extract title
                title = 'Untitled'
                lines = content.split('\n')
                for line in lines:
                    line = line.strip()
                    if line.startswith('# '):
                        title = line[2:].strip()
                        break

                metadata = {
                    'title': title,
                    'file_path': str(article_file.relative_to(atlas_v1_path)),
                    'content_length': len(content),
                    'word_count': len(content.split()),
                    'type': 'processed_article',
                    'migration_timestamp': datetime.now().isoformat()
                }

                v2_conn.execute('''
                    INSERT OR IGNORE INTO processed_content
                    (content_id, content_type, content, metadata_json)
                    VALUES (?, ?, ?, ?)
                ''', (content_id, 'article', content, json.dumps(metadata)))

                stats['article_files'] += 1
                existing_hashes.add(content_hash)

            except Exception as e:
                print(f"  ❌ Error processing {article_file}: {e}")
                stats['errors'] += 1

        print(f"✅ Article migration complete: {stats['article_files']} items")

    # 4. Migrate transcript files
    print("\n📄 Migrating transcript files...")
    output_dir = atlas_v1_path
    transcript_files = list(output_dir.glob("*.md")) + list(output_dir.glob("transcripts/*.md"))

    # Filter out non-transcript files
    exclude_files = ['.md', '403-Forbidden.md', 'wsj-com.md', 'nytimes-com.md', 'Attention-Required-Cloudflare.md', 'Origin-DNS-error-artifact-news-Cloudflare.md', 'Page-not-found-LAmag.md', 'Protected-page.md', 'RemovePaywall-Free-online-paywall-remover.md', 'TechCrunch-Startup-and-Technology-News.md', 'Yahoo-Finance-Stock-Market-Live-Quotes-Business-Finance-News.md', 'archive-md.md', 'BBC-Innovation-Technology-Health-Environment-AI.md', 'Forbidden-Fruit-by-Alexander-Sammon.md', 'Just-a-moment.md']
    transcript_files = [f for f in transcript_files if f.name not in exclude_files and len(f.read_text(encoding='utf-8', errors='ignore')) > 100]

    print(f"  📊 Found {len(transcript_files)} transcript files")

    for i, transcript_file in enumerate(transcript_files):
        if i % 50 == 0 and i > 0:
            print(f"  📊 Processing transcript file {i}/{len(transcript_files)}...")

        try:
            with open(transcript_file, 'r', encoding='utf-8') as f:
                content = f.read()

            if len(content) < 100:
                continue

            content_hash = hashlib.md5(content.encode()).hexdigest()
            if content_hash in existing_hashes:
                stats['duplicates_skipped'] += 1
                continue

            content_id = f"transcript-{transcript_file.stem}"

            # Extract title
            title = 'Untitled'
            lines = content.split('\n')
            for line in lines:
                line = line.strip()
                if line.startswith('# '):
                    title = line[2:].strip()
                    break

            metadata = {
                'title': title,
                'file_path': str(transcript_file.relative_to(atlas_v1_path)),
                'content_length': len(content),
                'word_count': len(content.split()),
                'type': 'transcript',
                'migration_timestamp': datetime.now().isoformat()
            }

            v2_conn.execute('''
                INSERT OR IGNORE INTO processed_content
                (content_id, content_type, content, metadata_json)
                VALUES (?, ?, ?, ?)
            ''', (content_id, 'transcript', content, json.dumps(metadata)))

            stats['transcript_files'] += 1
            existing_hashes.add(content_hash)

        except Exception as e:
            print(f"  ❌ Error processing {transcript_file}: {e}")
            stats['errors'] += 1

        if i % 100 == 0 and i > 0:
            print(f"  📊 Processed {i}/{len(transcript_files)} transcript files...")

    print(f"✅ Transcript migration complete: {stats['transcript_files']} items")

    # 5. Migrate document files
    print("\n📂 Migrating document files...")
    docs_dir = atlas_v1_path / "documents"
    if docs_dir.exists():
        doc_files = list(docs_dir.glob("**/*_structured.json")) + list(docs_dir.glob("**/*_metadata.json"))
        print(f"  📊 Found {len(doc_files)} document files")

        processed_docs = set()

        for i, doc_file in enumerate(doc_files):
            if i % 500 == 0:
                print(f"  📊 Processing document file {i}/{len(doc_files)}...")

            try:
                with open(doc_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                base_name = doc_file.stem.replace('_structured', '').replace('_metadata', '')
                if base_name in processed_docs:
                    continue

                content_hash = hashlib.md5(json.dumps(data, sort_keys=True).encode()).hexdigest()
                if content_hash in existing_hashes:
                    stats['duplicates_skipped'] += 1
                    continue

                content_id = f"document-{base_name}"
                metadata = {
                    'document_id': base_name,
                    'type': 'document',
                    'file_path': str(doc_file.relative_to(atlas_v1_path)),
                    'migration_timestamp': datetime.now().isoformat()
                }

                if isinstance(data, dict):
                    metadata.update({k: v for k, v in data.items() if k not in ['content', 'raw_content']})

                v2_conn.execute('''
                    INSERT OR IGNORE INTO processing_queue
                    (content_id, source_url, source_name, content_type, priority, metadata_json)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    content_id, f"file://{doc_file.relative_to(atlas_v1_path)}", 'documents',
                    'document', 'low', json.dumps(metadata)
                ))

                processed_docs.add(base_name)
                stats['document_files'] += 1
                existing_hashes.add(content_hash)

            except Exception as e:
                print(f"  ❌ Error processing {doc_file}: {e}")
                stats['errors'] += 1

        print(f"✅ Document migration complete: {stats['document_files']} items")

    # Commit everything
    v2_conn.commit()
    v2_conn.close()

    # Print final stats
    print("\n" + "="*60)
    print("🎯 UNIVERSAL MIGRATION COMPLETE")
    print("="*60)
    print(f"📋 Queue items migrated:     {stats['queue_items']:,}")
    print(f"🎙️ Podcast files migrated:   {stats['podcast_files']:,}")
    print(f"📰 Article files migrated:   {stats['article_files']:,}")
    print(f"📄 Transcript files migrated: {stats['transcript_files']:,}")
    print(f"📂 Document files migrated:   {stats['document_files']:,}")
    print(f"🔄 Duplicates skipped:       {stats['duplicates_skipped']:,}")
    print(f"❌ Errors:                   {stats['errors']:,}")

    total_migrated = sum([
        stats['queue_items'], stats['podcast_files'], stats['article_files'],
        stats['transcript_files'], stats['document_files']
    ])

    print("-"*60)
    print(f"📊 TOTAL ITEMS MIGRATED:     {total_migrated:,}")
    print("="*60)

    if total_migrated > 0:
        print(f"\n🚀 Atlas v2 now has {total_migrated:,} items to process!")
        print("📈 The aggressive 5-minute scheduler will start working through everything immediately.")

    return total_migrated

if __name__ == "__main__":
    total = migrate_everything()
    print(f"\n🎉 Migration complete! {total:,} items ready for processing.")