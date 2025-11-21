#!/usr/bin/env python3
"""
Atlas Database Introspection Tool
Verifies database schema and provides detailed table information.
Exits with non-zero code if critical tables are missing.
"""

import sys
import sqlite3
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from helpers.database_config import get_database_path, get_database_connection


def introspect_database():
    """Introspect the Atlas database and verify schema."""
    try:
        db_path = get_database_path()
        print(f"📍 Database Path: {db_path}")
        print(f"📁 Database Exists: {db_path.exists()}")

        if not db_path.exists():
            print("❌ ERROR: Database file does not exist!")
            return False

        # Get database size
        size_mb = db_path.stat().st_size / (1024 * 1024)
        print(f"💾 Database Size: {size_mb:.1f} MB")
        print("")

        # Connect and introspect
        conn = get_database_connection()
        cursor = conn.cursor()

        # Get all tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        tables = [row[0] for row in cursor.fetchall()]

        print(f"📊 Tables Found: {len(tables)}")
        for table in tables:
            print(f"   • {table}")
        print("")

        # Check critical tables
        critical_tables = ['podcast_episodes', 'transcriptions']
        missing_tables = []

        for table in critical_tables:
            if table in tables:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
                print(f"✅ {table}: {count:,} rows")
            else:
                print(f"❌ {table}: MISSING")
                missing_tables.append(table)

        if missing_tables:
            print(f"\n🚨 ERROR: Critical tables missing: {missing_tables}")
            conn.close()
            return False

        # Show schema for critical tables
        print("\n📋 Schema Details:")
        for table in critical_tables:
            cursor.execute(f"PRAGMA table_info({table})")
            columns = cursor.fetchall()
            print(f"\n{table}:")
            for col in columns:
                print(f"   {col[1]} ({col[2]}) {'NOT NULL' if col[3] else 'NULL'}")

        # Check for recent activity
        print("\n🕐 Recent Activity:")
        try:
            cursor.execute("SELECT MAX(created_at) FROM transcriptions WHERE created_at IS NOT NULL")
            latest_transcription = cursor.fetchone()[0]
            if latest_transcription:
                print(f"   Latest transcription: {latest_transcription}")
            else:
                print("   No transcriptions found")

            cursor.execute("SELECT MAX(last_updated) FROM podcast_episodes WHERE last_updated IS NOT NULL")
            latest_episode = cursor.fetchone()[0]
            if latest_episode:
                print(f"   Latest episode update: {latest_episode}")

        except Exception as e:
            print(f"   ⚠️  Could not check timestamps: {e}")

        conn.close()
        print("\n✅ Database introspection complete")
        return True

    except Exception as e:
        print(f"❌ ERROR: Database introspection failed: {e}")
        return False


def main():
    """Main function."""
    print("🔍 Atlas Database Introspection")
    print("=" * 50)

    success = introspect_database()

    if not success:
        print("\n💡 To fix database issues:")
        print("   1. Check ATLAS_DB_PATH in .env")
        print("   2. Ensure database schema is initialized")
        print("   3. Check file permissions")
        sys.exit(1)
    else:
        print("\n🎉 Database is healthy!")
        sys.exit(0)


if __name__ == "__main__":
    main()