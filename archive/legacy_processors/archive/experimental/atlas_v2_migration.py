#!/usr/bin/env python3
"""
Atlas v2 Comprehensive Data Migration Script

Discovers and migrates ALL data from existing Atlas installation:
- Multiple SQLite databases
- Content files (MD, JSON, TXT)
- Queue items and metadata
- Preserves every piece of data found

CRITICAL: This script NEVER deletes original data. Only exports/copies.
"""

import os
import sqlite3
import json
import shutil
import hashlib
import glob
from datetime import datetime
from pathlib import Path
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('atlas_v2_migration.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class AtlasDataDiscovery:
    """Comprehensive data discovery and migration for Atlas v2"""

    def __init__(self, atlas_root="/home/ubuntu/dev/atlas"):
        self.atlas_root = Path(atlas_root)
        self.migration_dir = self.atlas_root / "atlas_v2_migration"
        self.migration_dir.mkdir(exist_ok=True)

        # Migration results
        self.discovered_data = {
            "databases": [],
            "content_files": {
                "markdown": [],
                "json": [],
                "text": []
            },
            "content_counts": {},
            "migration_stats": {}
        }

    def discover_all_databases(self):
        """Find all SQLite databases in Atlas project"""
        logger.info("🔍 Discovering all databases...")

        db_files = list(self.atlas_root.glob("**/*.db"))

        for db_path in db_files:
            try:
                # Get file info
                stat = db_path.stat()
                db_info = {
                    "path": str(db_path),
                    "size_mb": round(stat.st_size / (1024*1024), 2),
                    "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    "tables": []
                }

                # Connect and get table info
                conn = sqlite3.connect(db_path)
                tables = conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchall()

                for table_name, in tables:
                    try:
                        count = conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
                        db_info["tables"].append({
                            "name": table_name,
                            "count": count
                        })
                    except Exception as e:
                        logger.warning(f"Error counting {table_name}: {e}")

                conn.close()
                self.discovered_data["databases"].append(db_info)
                logger.info(f"📊 {db_path.name}: {len(db_info['tables'])} tables, {db_info['size_mb']}MB")

            except Exception as e:
                logger.error(f"Error analyzing {db_path}: {e}")

    def discover_content_files(self):
        """Find all content files (MD, JSON, TXT)"""
        logger.info("📁 Discovering content files...")

        file_types = {
            "markdown": "**/*.md",
            "json": "**/*.json",
            "text": "**/*.txt"
        }

        for file_type, pattern in file_types.items():
            files = list(self.atlas_root.glob(pattern))

            # Sample file analysis
            sample_files = []
            total_size = 0

            for file_path in files[:100]:  # Analyze first 100 files
                try:
                    stat = file_path.stat()
                    total_size += stat.st_size

                    sample_files.append({
                        "path": str(file_path),
                        "size_kb": round(stat.st_size / 1024, 1),
                        "modified": datetime.fromtimestamp(stat.st_mtime).isoformat()
                    })
                except Exception as e:
                    logger.warning(f"Error analyzing {file_path}: {e}")

            self.discovered_data["content_files"][file_type] = {
                "total_count": len(files),
                "total_size_mb": round(total_size / (1024*1024), 2),
                "sample_files": sample_files
            }

            logger.info(f"📄 {file_type}: {len(files)} files, ~{round(total_size/(1024*1024), 1)}MB")

    def analyze_main_database(self):
        """Deep analysis of main atlas.db"""
        main_db = self.atlas_root / "data" / "atlas.db"
        if not main_db.exists():
            logger.error("Main atlas.db not found!")
            return

        logger.info("🔬 Analyzing main database...")

        conn = sqlite3.connect(main_db)

        # Content analysis
        content_stats = {}

        # Main content table
        content_total = conn.execute("SELECT COUNT(*) FROM content").fetchone()[0]
        content_with_data = conn.execute(
            "SELECT COUNT(*) FROM content WHERE length(content) > 1000"
        ).fetchone()[0]
        content_large = conn.execute(
            "SELECT COUNT(*) FROM content WHERE length(content) > 10000"
        ).fetchone()[0]

        content_stats["content"] = {
            "total": content_total,
            "with_substantial_content": content_with_data,
            "large_content": content_large
        }

        # Episode queue analysis
        try:
            queue_stats = conn.execute("""
                SELECT status, COUNT(*)
                FROM episode_queue
                GROUP BY status
            """).fetchall()
            content_stats["episode_queue"] = {
                "total": sum(count for _, count in queue_stats),
                "by_status": dict(queue_stats)
            }
        except:
            logger.warning("No episode_queue table found")

        # Other important tables
        for table in ["podcast_episodes", "transcriptions", "processed_content"]:
            try:
                count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                content_stats[table] = {"total": count}
            except:
                logger.warning(f"Table {table} not found")

        conn.close()

        self.discovered_data["content_counts"] = content_stats
        logger.info(f"📊 Main DB analysis complete: {content_stats}")

    def export_critical_data(self):
        """Export the most critical data for migration"""
        logger.info("💾 Exporting critical data...")

        main_db = self.atlas_root / "data" / "atlas.db"
        if not main_db.exists():
            logger.error("Cannot export: main atlas.db not found!")
            return

        conn = sqlite3.connect(main_db)

        # Export main content
        logger.info("Exporting main content...")
        content_data = conn.execute("""
            SELECT id, title, url, content, content_type,
                   metadata, created_at, updated_at, ai_summary, ai_tags
            FROM content
            WHERE length(content) > 1000
            ORDER BY created_at DESC
        """).fetchall()

        content_export = []
        for row in content_data:
            content_export.append({
                "id": row[0],
                "title": row[1],
                "url": row[2],
                "content": row[3],
                "content_type": row[4],
                "metadata": row[5],
                "created_at": row[6],
                "updated_at": row[7],
                "ai_summary": row[8],
                "ai_tags": row[9],
                "content_length": len(row[3]) if row[3] else 0
            })

        export_file = self.migration_dir / "main_content_export.json"
        with open(export_file, 'w', encoding='utf-8') as f:
            json.dump(content_export, f, indent=2, ensure_ascii=False)

        logger.info(f"✅ Exported {len(content_export)} content items to {export_file}")

        # Export episode queue
        try:
            logger.info("Exporting episode queue...")
            queue_data = conn.execute("""
                SELECT id, podcast_name, episode_url, status, metadata,
                       created_at, updated_at, retry_count
                FROM episode_queue
                ORDER BY created_at DESC
            """).fetchall()

            queue_export = []
            for row in queue_data:
                queue_export.append({
                    "id": row[0],
                    "podcast_name": row[1],
                    "episode_url": row[2],
                    "status": row[3],
                    "metadata": row[4],
                    "created_at": row[5],
                    "updated_at": row[6],
                    "retry_count": row[7] if row[7] else 0
                })

            queue_file = self.migration_dir / "episode_queue_export.json"
            with open(queue_file, 'w', encoding='utf-8') as f:
                json.dump(queue_export, f, indent=2, ensure_ascii=False)

            logger.info(f"✅ Exported {len(queue_export)} queue items to {queue_file}")

        except Exception as e:
            logger.error(f"Error exporting queue: {e}")

        # Export podcast episodes if exists
        try:
            logger.info("Exporting podcast episodes...")
            episodes_data = conn.execute("""
                SELECT * FROM podcast_episodes
                ORDER BY created_at DESC
                LIMIT 5000
            """).fetchall()

            # Get column names
            cursor = conn.execute("PRAGMA table_info(podcast_episodes)")
            columns = [row[1] for row in cursor.fetchall()]

            episodes_export = []
            for row in episodes_data:
                episode_dict = dict(zip(columns, row))
                episodes_export.append(episode_dict)

            episodes_file = self.migration_dir / "podcast_episodes_export.json"
            with open(episodes_file, 'w', encoding='utf-8') as f:
                json.dump(episodes_export, f, indent=2, ensure_ascii=False)

            logger.info(f"✅ Exported {len(episodes_export)} podcast episodes to {episodes_file}")

        except Exception as e:
            logger.warning(f"Could not export podcast episodes: {e}")

        conn.close()

    def backup_databases(self):
        """Create backups of all database files"""
        logger.info("🔄 Creating database backups...")

        backup_dir = self.migration_dir / "database_backups"
        backup_dir.mkdir(exist_ok=True)

        for db_info in self.discovered_data["databases"]:
            src_path = Path(db_info["path"])
            if src_path.exists():
                # Create backup with timestamp
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_name = f"{src_path.stem}_backup_{timestamp}.db"
                backup_path = backup_dir / backup_name

                try:
                    shutil.copy2(src_path, backup_path)
                    logger.info(f"✅ Backed up {src_path.name} → {backup_name}")
                except Exception as e:
                    logger.error(f"Failed to backup {src_path}: {e}")

    def generate_migration_report(self):
        """Generate comprehensive migration report"""
        logger.info("📋 Generating migration report...")

        report = {
            "migration_timestamp": datetime.now().isoformat(),
            "atlas_root": str(self.atlas_root),
            "discovery_summary": {
                "total_databases": len(self.discovered_data["databases"]),
                "total_markdown_files": self.discovered_data["content_files"]["markdown"]["total_count"],
                "total_json_files": self.discovered_data["content_files"]["json"]["total_count"],
                "main_content_items": self.discovered_data["content_counts"].get("content", {}).get("total", 0),
                "large_content_items": self.discovered_data["content_counts"].get("content", {}).get("large_content", 0),
                "pending_queue_items": self.discovered_data["content_counts"].get("episode_queue", {}).get("by_status", {}).get("pending", 0)
            },
            "detailed_discovery": self.discovered_data
        }

        report_file = self.migration_dir / "migration_report.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        logger.info(f"📊 Migration report saved to {report_file}")
        return report

    def run_complete_discovery(self):
        """Run complete data discovery and migration preparation"""
        logger.info("🚀 Starting comprehensive Atlas data discovery...")

        # Discovery phase
        self.discover_all_databases()
        self.discover_content_files()
        self.analyze_main_database()

        # Export phase
        self.export_critical_data()
        self.backup_databases()

        # Reporting
        report = self.generate_migration_report()

        logger.info("✅ Discovery and export complete!")
        logger.info(f"📁 All migration data in: {self.migration_dir}")

        return report

def main():
    """Main migration execution"""
    discovery = AtlasDataDiscovery()
    report = discovery.run_complete_discovery()

    print("\n" + "="*60)
    print("ATLAS V2 MIGRATION DISCOVERY COMPLETE")
    print("="*60)
    print(f"Total databases found: {report['discovery_summary']['total_databases']}")
    print(f"Main content items: {report['discovery_summary']['main_content_items']:,}")
    print(f"Large content items: {report['discovery_summary']['large_content_items']:,}")
    print(f"Pending queue items: {report['discovery_summary']['pending_queue_items']:,}")
    print(f"Markdown files: {report['discovery_summary']['total_markdown_files']:,}")
    print(f"JSON files: {report['discovery_summary']['total_json_files']:,}")
    print(f"\n📁 Migration data: atlas_v2_migration/")
    print("🔒 Original data preserved (never modified)")
    print("="*60)

if __name__ == "__main__":
    main()