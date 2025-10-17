#!/usr/bin/env python3
"""
Universal Atlas Content Migration Script
Finds and processes EVERYTHING from Atlas v1 into Atlas v2
"""

import os
import sqlite3
import json
import hashlib
from pathlib import Path
from datetime import datetime
import re
import sys

class UniversalMigrator:
    def __init__(self):
        self.atlas_v1_path = Path("/home/ubuntu/dev/atlas/output")
        self.atlas_v2_db_path = "/home/ubuntu/dev/atlas/atlas_v2/data/atlas_v2.db"
        self.processed_hashes = set()
        self.migration_stats = {
            'queue_items': 0,
            'podcast_files': 0,
            'article_files': 0,
            'transcript_files': 0,
            'document_files': 0,
            'duplicates_skipped': 0,
            'errors': 0
        }

    async def migrate_everything(self):
        """Migrate all content from Atlas v1 to Atlas v2"""
        print("🚀 Starting universal migration of ALL Atlas content...")

        # Initialize Atlas v2 database
        await self.atlas_v2_db.init_database()

        # Get existing hashes to avoid duplicates
        await self.load_existing_hashes()

        # Process all content types
        await self.migrate_queue_items()
        await self.migrate_podcast_files()
        await self.migrate_article_files()
        await self.migrate_transcript_files()
        await self.migrate_document_files()

        # Print final stats
        self.print_migration_summary()

    async def load_existing_hashes(self):
        """Load existing content hashes from Atlas v2"""
        try:
            existing_content = await self.atlas_v2_db.get_all_content()
            for content in existing_content:
                if 'content_hash' in content:
                    self.processed_hashes.add(content['content_hash'])
            print(f"📊 Loaded {len(self.processed_hashes)} existing content hashes")
        except Exception as e:
            print(f"⚠️ Could not load existing hashes: {e}")

    async def migrate_queue_items(self):
        """Migrate items from Atlas v1 processing queue"""
        print("\n📋 Migrating queue items...")

        v1_queue_db = self.atlas_v1_path / "processing_queue.db"
        if not v1_queue_db.exists():
            print("❌ No queue database found")
            return

        conn = sqlite3.connect(v1_queue_db)
        cursor = conn.execute("""
            SELECT episode_url, episode_title, podcast_name, created_at, status
            FROM processing_queue
            WHERE status IN ('pending', 'processing')
            ORDER BY created_at DESC
        """)

        for row in cursor.fetchall():
            episode_url, episode_title, podcast_name, created_at, status = row

            if not episode_url:
                continue

            # Create content hash
            content_hash = self.create_content_hash(episode_url, episode_title, podcast_name)

            if content_hash in self.processed_hashes:
                self.migration_stats['duplicates_skipped'] += 1
                continue

            # Create content ID
            content_id = self.create_content_id(episode_url, episode_title, podcast_name)

            # Add to Atlas v2 queue
            metadata = {
                'title': episode_title,
                'podcast_name': podcast_name,
                'source': 'atlas_v1_queue',
                'original_status': status,
                'migration_timestamp': datetime.now().isoformat()
            }

            try:
                await self.atlas_v2_db.add_to_queue(
                    content_id=content_id,
                    url=episode_url,
                    content_type='podcast',
                    metadata=metadata
                )
                self.migration_stats['queue_items'] += 1
                self.processed_hashes.add(content_hash)

                if self.migration_stats['queue_items'] % 50 == 0:
                    print(f"  📊 Migrated {self.migration_stats['queue_items']} queue items...")

            except Exception as e:
                print(f"  ❌ Error migrating queue item {episode_title}: {e}")
                self.migration_stats['errors'] += 1

        conn.close()
        print(f"✅ Queue migration complete: {self.migration_stats['queue_items']} items")

    async def migrate_podcast_files(self):
        """Migrate podcast RSS entry files"""
        print("\n🎙️ Migrating podcast files...")

        podcast_dir = self.atlas_v1_path / "podcasts"
        if not podcast_dir.exists():
            print("❌ No podcast directory found")
            return

        json_files = list(podcast_dir.glob("**/*_rss_entry.json"))
        print(f"  📊 Found {len(json_files)} podcast files")

        for i, podcast_file in enumerate(json_files):
            if i % 100 == 0:
                print(f"  📊 Processing podcast file {i}/{len(json_files)}...")

            try:
                with open(podcast_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                # Extract key info
                if 'raw_data' in data:
                    raw = data['raw_data']
                    title = raw.get('title', '')
                    link = raw.get('link', '')
                    source = data.get('source', 'unknown')

                    if not link:
                        continue

                    # Create hash and check for duplicates
                    content_hash = self.create_content_hash(link, title, source)
                    if content_hash in self.processed_hashes:
                        self.migration_stats['duplicates_skipped'] += 1
                        continue

                    # Create content ID
                    content_id = self.create_content_id(link, title, source)

                    # Create metadata
                    metadata = {
                        'title': title,
                        'source': source,
                        'type': 'podcast_rss',
                        'authors': [author.get('name', '') for author in raw.get('authors', [])],
                        'published': raw.get('published', ''),
                        'itunes_duration': raw.get('itunes_duration', ''),
                        'summary': raw.get('summary', '')[:500] if raw.get('summary') else '',
                        'migration_file': str(podcast_file.relative_to(self.atlas_v1_path)),
                        'migration_timestamp': datetime.now().isoformat()
                    }

                    # Add to Atlas v2 queue
                    await self.atlas_v2_db.add_to_queue(
                        content_id=content_id,
                        url=link,
                        content_type='podcast',
                        metadata=metadata
                    )

                    self.migration_stats['podcast_files'] += 1
                    self.processed_hashes.add(content_hash)

            except Exception as e:
                print(f"  ❌ Error processing {podcast_file}: {e}")
                self.migration_stats['errors'] += 1

        print(f"✅ Podcast migration complete: {self.migration_stats['podcast_files']} items")

    async def migrate_article_files(self):
        """Migrate processed article files"""
        print("\n📰 Migrating article files...")

        articles_dir = self.atlas_v1_path / "articles"
        if not articles_dir.exists():
            print("❌ No articles directory found")
            return

        md_files = list(articles_dir.glob("**/*.md"))
        print(f"  📊 Found {len(md_files)} article files")

        for i, article_file in enumerate(md_files):
            if i % 200 == 0:
                print(f"  📊 Processing article file {i}/{len(md_files)}...")

            try:
                with open(article_file, 'r', encoding='utf-8') as f:
                    content = f.read()

                # Create hash from content
                content_hash = hashlib.md5(content.encode()).hexdigest()
                if content_hash in self.processed_hashes:
                    self.migration_stats['duplicates_skipped'] += 1
                    continue

                # Create content ID from filename
                content_id = f"article-{article_file.stem}"

                # Create metadata
                metadata = {
                    'title': self.extract_title_from_md(content),
                    'file_path': str(article_file.relative_to(self.atlas_v1_path)),
                    'content_length': len(content),
                    'word_count': len(content.split()),
                    'type': 'processed_article',
                    'migration_timestamp': datetime.now().isoformat()
                }

                # Add as completed content (already processed)
                await self.atlas_v2_db.add_completed_content(
                    content_id=content_id,
                    content_type='article',
                    content=content,
                    metadata=metadata
                )

                self.migration_stats['article_files'] += 1
                self.processed_hashes.add(content_hash)

            except Exception as e:
                print(f"  ❌ Error processing {article_file}: {e}")
                self.migration_stats['errors'] += 1

        print(f"✅ Article migration complete: {self.migration_stats['article_files']} items")

    async def migrate_transcript_files(self):
        """Migrate transcript files from output directory"""
        print("\n📄 Migrating transcript files...")

        output_dir = self.atlas_v1_path
        transcript_files = list(output_dir.glob("*.md")) + list(output_dir.glob("transcripts/*.md"))

        # Filter out non-transcript files
        transcript_files = [f for f in transcript_files if f.name not in ['.md', '403-Forbidden.md', 'wsj-com.md', 'nytimes-com.md']]

        print(f"  📊 Found {len(transcript_files)} transcript files")

        for i, transcript_file in enumerate(transcript_files):
            if i % 50 == 0 and i > 0:
                print(f"  📊 Processing transcript file {i}/{len(transcript_files)}...")

            try:
                with open(transcript_file, 'r', encoding='utf-8') as f:
                    content = f.read()

                if len(content) < 100:  # Skip very short files
                    continue

                # Create hash
                content_hash = hashlib.md5(content.encode()).hexdigest()
                if content_hash in self.processed_hashes:
                    self.migration_stats['duplicates_skipped'] += 1
                    continue

                # Create content ID
                content_id = f"transcript-{transcript_file.stem}"

                # Create metadata
                metadata = {
                    'title': self.extract_title_from_md(content),
                    'file_path': str(transcript_file.relative_to(self.atlas_v1_path)),
                    'content_length': len(content),
                    'word_count': len(content.split()),
                    'type': 'transcript',
                    'migration_timestamp': datetime.now().isoformat()
                }

                # Add as completed content
                await self.atlas_v2_db.add_completed_content(
                    content_id=content_id,
                    content_type='transcript',
                    content=content,
                    metadata=metadata
                )

                self.migration_stats['transcript_files'] += 1
                self.processed_hashes.add(content_hash)

            except Exception as e:
                print(f"  ❌ Error processing {transcript_file}: {e}")
                self.migration_stats['errors'] += 1

        print(f"✅ Transcript migration complete: {self.migration_stats['transcript_files']} items")

    async def migrate_document_files(self):
        """Migrate structured document files"""
        print("\n📂 Migrating document files...")

        docs_dir = self.atlas_v1_path / "documents"
        if not docs_dir.exists():
            print("❌ No documents directory found")
            return

        # Focus on structured and metadata files
        doc_files = list(docs_dir.glob("**/*_structured.json")) + list(docs_dir.glob("**/*_metadata.json"))
        print(f"  📊 Found {len(doc_files)} document files")

        processed_docs = set()

        for i, doc_file in enumerate(doc_files):
            if i % 500 == 0:
                print(f"  📊 Processing document file {i}/{len(doc_files)}...")

            try:
                with open(doc_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                # Extract base name (without _structured or _metadata suffix)
                base_name = doc_file.stem.replace('_structured', '').replace('_metadata', '')
                if base_name in processed_docs:
                    continue

                # Create hash from the data
                content_hash = hashlib.md5(json.dumps(data, sort_keys=True).encode()).hexdigest()
                if content_hash in self.processed_hashes:
                    self.migration_stats['duplicates_skipped'] += 1
                    continue

                # Create content ID
                content_id = f"document-{base_name}"

                # Create metadata
                metadata = {
                    'document_id': base_name,
                    'type': 'document',
                    'file_path': str(doc_file.relative_to(self.atlas_v1_path)),
                    'migration_timestamp': datetime.now().isoformat()
                }

                # Merge document metadata
                if isinstance(data, dict):
                    metadata.update({k: v for k, v in data.items() if k not in ['content', 'raw_content']})

                # Add to queue for processing (raw documents need processing)
                await self.atlas_v2_db.add_to_queue(
                    content_id=content_id,
                    url=f"file://{doc_file.relative_to(self.atlas_v1_path)}",
                    content_type='document',
                    metadata=metadata
                )

                processed_docs.add(base_name)
                self.migration_stats['document_files'] += 1
                self.processed_hashes.add(content_hash)

            except Exception as e:
                print(f"  ❌ Error processing {doc_file}: {e}")
                self.migration_stats['errors'] += 1

        print(f"✅ Document migration complete: {self.migration_stats['document_files']} items")

    def create_content_hash(self, url, title, source):
        """Create unique hash for content deduplication"""
        content_str = f"{url}|{title or ''}|{source or ''}"
        return hashlib.md5(content_str.encode()).hexdigest()

    def create_content_id(self, url, title, source):
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

    def extract_title_from_md(self, content):
        """Extract title from markdown content"""
        lines = content.split('\n')
        for line in lines:
            line = line.strip()
            if line.startswith('# '):
                return line[2:].strip()

        # If no header found, return first non-empty line
        for line in lines:
            if line.strip():
                return line.strip()[:100]

        return 'Untitled'

    def print_migration_summary(self):
        """Print final migration statistics"""
        print("\n" + "="*60)
        print("🎯 UNIVERSAL MIGRATION COMPLETE")
        print("="*60)
        print(f"📋 Queue items migrated:     {self.migration_stats['queue_items']:,}")
        print(f"🎙️ Podcast files migrated:   {self.migration_stats['podcast_files']:,}")
        print(f"📰 Article files migrated:   {self.migration_stats['article_files']:,}")
        print(f"📄 Transcript files migrated: {self.migration_stats['transcript_files']:,}")
        print(f"📂 Document files migrated:   {self.migration_stats['document_files']:,}")
        print(f"🔄 Duplicates skipped:       {self.migration_stats['duplicates_skipped']:,}")
        print(f"❌ Errors:                   {self.migration_stats['errors']:,}")

        total_migrated = sum([
            self.migration_stats['queue_items'],
            self.migration_stats['podcast_files'],
            self.migration_stats['article_files'],
            self.migration_stats['transcript_files'],
            self.migration_stats['document_files']
        ])

        print("-"*60)
        print(f"📊 TOTAL ITEMS MIGRATED:     {total_migrated:,}")
        print("="*60)

        if total_migrated > 0:
            print(f"\n🚀 Atlas v2 now has {total_migrated:,} items to process!")
            print("📈 The aggressive 5-minute scheduler will start working through everything immediately.")

async def main():
    """Run the universal migration"""
    migrator = UniversalMigrator()
    await migrator.migrate_everything()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())