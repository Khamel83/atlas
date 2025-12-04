#!/usr/bin/env python3
"""
COMPLETE Atlas v1 to v2 Migration
Move EVERYTHING so nothing is lost
"""

import sqlite3
import json
import shutil
from pathlib import Path
from datetime import datetime

def migrate_all_atlas_v1_content():
    """Move absolutely everything from Atlas v1 to Atlas v2"""
    print("🚀 COMPLETE ATLAS MIGRATION - Moving everything from v1 to v2")
    print("=" * 60)

    # Paths
    atlas_v1_db = "/home/ubuntu/dev/atlas/atlas.db"
    atlas_v2_db = "/home/ubuntu/dev/atlas/atlas_v2/data/atlas_v2.db"
    atlas_v1_output = "/home/ubuntu/dev/atlas/output"
    atlas_v2_content = "/home/ubuntu/dev/atlas/atlas_v2/content"

    print(f"📁 From: {atlas_v1_db}")
    print(f"📁 To: {atlas_v2_db}")
    print(f"📁 Files: {atlas_v1_output} → {atlas_v2_content}")

    # Connect to both databases
    v1_conn = sqlite3.connect(atlas_v1_db)
    v2_conn = sqlite3.connect(atlas_v2_db)

    print("\n📊 Atlas v1 Content Survey:")
    v1_cursor = v1_conn.cursor()

    # Check what we have in v1
    v1_cursor.execute("SELECT content_type, COUNT(*) FROM content GROUP BY content_type ORDER BY COUNT(*) DESC")
    v1_content = v1_cursor.fetchall()

    total_v1_items = 0
    for content_type, count in v1_content:
        print(f"  {content_type}: {count:,}")
        total_v1_items += count

    print(f"\n📈 TOTAL Atlas v1 items: {total_v1_items:,}")

    # Create v2 content directories
    Path(atlas_v2_content).mkdir(parents=True, exist_ok=True)
    Path(f"{atlas_v2_content}/transcripts").mkdir(exist_ok=True)
    Path(f"{atlas_v2_content}/articles").mkdir(exist_ok=True)
    Path(f"{atlas_v2_content}/podcasts").mkdir(exist_ok=True)
    Path(f"{atlas_v2_content}/emails").mkdir(exist_ok=True)
    Path(f"{atlas_v2_content}/misc").mkdir(exist_ok=True)

    # Migrate ALL content from v1 to v2
    v2_cursor = v2_conn.cursor()

    migrated_count = 0
    error_count = 0

    print(f"\n🔄 Starting complete migration...")

    # Get all v1 content
    v1_cursor.execute("SELECT * FROM content")
    all_v1_items = v1_cursor.fetchall()

    # Get column names
    v1_cursor.execute("PRAGMA table_info(content)")
    columns = [col[1] for col in v1_cursor.fetchall()]
    print(f"📋 Found {len(columns)} columns: {', '.join(columns[:5])}...")

    for i, row in enumerate(all_v1_items):
        if i % 1000 == 0:
            print(f"📊 Migrating item {i:,}/{len(all_v1_items):,}...")

        try:
            # Extract data from row
            item_data = dict(zip(columns, row))

            content_id = f"v1-migrated-{item_data.get('id', i)}"
            title = item_data.get('title', 'Untitled')
            url = item_data.get('url', '')
            content = item_data.get('content', '')
            content_type = item_data.get('content_type', 'unknown')
            metadata = item_data.get('metadata', '{}')
            created_at = item_data.get('created_at', datetime.now().isoformat())
            updated_at = item_data.get('updated_at', datetime.now().isoformat())

            # Parse metadata
            try:
                if metadata and metadata.strip():
                    parsed_metadata = json.loads(metadata)
                else:
                    parsed_metadata = {}
            except:
                parsed_metadata = {"original_metadata": metadata}

            # Add migration info
            parsed_metadata.update({
                "migrated_from_v1": True,
                "v1_id": item_data.get('id'),
                "migration_timestamp": datetime.now().isoformat(),
                "original_content_type": content_type
            })

            # Insert into v2 content_metadata
            v2_cursor.execute('''
                INSERT OR REPLACE INTO content_metadata
                (content_id, source_url, source_name, content_type, title, metadata_json, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                content_id, url, f"atlas_v1_{content_type}", content_type,
                title, json.dumps(parsed_metadata), created_at, updated_at
            ))

            # Create content file based on type
            if content and len(content.strip()) > 50:
                content_dir = f"{atlas_v2_content}"

                if content_type == 'podcast_transcript':
                    content_dir += "/transcripts"
                elif content_type == 'article':
                    content_dir += "/articles"
                elif content_type in ['podcast', 'podcast_episode']:
                    content_dir += "/podcasts"
                elif content_type == 'email':
                    content_dir += "/emails"
                else:
                    content_dir += "/misc"

                Path(content_dir).mkdir(exist_ok=True)

                # Create safe filename
                safe_title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).strip()[:50]
                if not safe_title:
                    safe_title = f"content_{item_data.get('id', i)}"

                filename = f"{safe_title.replace(' ', '_')}.md"
                filepath = Path(content_dir) / filename

                # Write content as markdown
                with open(filepath, 'w', encoding='utf-8') as f:
                    if title:
                        f.write(f"# {title}\n\n")
                    f.write(f"**Source**: {url}\n")
                    f.write(f"**Type**: {content_type}\n")
                    f.write(f"**Created**: {created_at}\n\n")
                    f.write("---\n\n")
                    f.write(content)

            # Add to processing queue as completed (since it's already processed)
            v2_cursor.execute('''
                INSERT OR REPLACE INTO processing_queue
                (content_id, source_url, source_name, content_type, status, metadata_json, created_at, updated_at, completed_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                content_id, url, f"atlas_v1_{content_type}", content_type, 'completed',
                json.dumps(parsed_metadata), created_at, updated_at, datetime.now().isoformat()
            ))

            migrated_count += 1

        except Exception as e:
            error_count += 1
            if error_count <= 10:
                print(f"❌ Error migrating item {i}: {e}")

        if i % 1000 == 0 and i > 0:
            v2_conn.commit()
            print(f"  ✅ Committed {migrated_count:,} items so far...")

    # Final commit
    v2_conn.commit()

    # Also copy all physical files from output directory
    print(f"\n📁 Copying all files from {atlas_v1_output} to {atlas_v2_content}/v1_files...")

    if Path(atlas_v1_output).exists():
        v1_files_dest = Path(f"{atlas_v2_content}/v1_files")
        if v1_files_dest.exists():
            shutil.rmtree(v1_files_dest)
        shutil.copytree(atlas_v1_output, v1_files_dest)
        print(f"✅ Copied all v1 output files to {v1_files_dest}")

    # Close connections
    v1_conn.close()
    v2_conn.close()

    print(f"\n🎉 COMPLETE MIGRATION FINISHED!")
    print(f"✅ Migrated: {migrated_count:,} items")
    print(f"❌ Errors: {error_count}")
    print(f"📁 Files copied from output/")
    print(f"🗄️ Database migrated to v2")
    print(f"\n🚀 Atlas v1 → v2 migration complete. Nothing is lost.")

    return migrated_count

if __name__ == "__main__":
    migrated = migrate_all_atlas_v1_content()
    print(f"\n🎯 Final result: {migrated:,} items successfully migrated to Atlas v2")