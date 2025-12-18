
import sqlite3
import shutil
import argparse
from pathlib import Path
from datetime import datetime

def get_db_path():
    """Gets the path to the database."""
    # This is a placeholder. In a real application, this would be read from a config file.
    return Path("data/atlas.db")

def backup_database(db_path):
    """Creates a backup of the database."""
    backup_dir = Path("backups")
    backup_dir.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = backup_dir / f"{db_path.name}.{timestamp}.bak"
    shutil.copy2(db_path, backup_path)
    print(f"Database backed up to {backup_path}")
    return backup_path

def cleanup_duplicates(cursor, dry_run=True):
    """Removes duplicate entries from the content table."""
    print("\n--- Cleaning up duplicates ---")
    cursor.execute("""
        SELECT url, COUNT(*), GROUP_CONCAT(id)
        FROM content
        GROUP BY url
        HAVING COUNT(*) > 1
    """)
    duplicates = cursor.fetchall()
    total_deleted = 0
    for url, count, ids in duplicates:
        ids_to_delete = ids.split(",")[1:]
        print(f"  - URL: {url}, Count: {count}, Deleting {len(ids_to_delete)} entries.")
        if not dry_run:
            cursor.execute(f"DELETE FROM content WHERE id IN ({','.join(ids_to_delete)})")
        total_deleted += len(ids_to_delete)
    print(f"Total duplicate entries to be deleted: {total_deleted}")
    return total_deleted

def cleanup_phantom_entries(cursor, dry_run=True):
    """Removes phantom entries (NULL or empty content)."""
    print("\n--- Cleaning up phantom entries ---")
    cursor.execute("SELECT id FROM content WHERE content IS NULL OR content = ''")
    phantom_ids = [row[0] for row in cursor.fetchall()]
    print(f"Found {len(phantom_ids)} phantom entries to be deleted.")
    if not dry_run and phantom_ids:
        cursor.execute(f"DELETE FROM content WHERE id IN ({','.join(map(str, phantom_ids))})")
    return len(phantom_ids)

def cleanup_low_quality_entries(cursor, dry_run=True):
    """Removes low-quality entries (content length < 100 chars)."""
    print("\n--- Cleaning up low-quality entries ---")
    cursor.execute("SELECT id FROM content WHERE LENGTH(content) < 100")
    low_quality_ids = [row[0] for row in cursor.fetchall()]
    print(f"Found {len(low_quality_ids)} low-quality entries to be deleted.")
    if not dry_run and low_quality_ids:
        cursor.execute(f"DELETE FROM content WHERE id IN ({','.join(map(str, low_quality_ids))})")
    return len(low_quality_ids)

def main():
    parser = argparse.ArgumentParser(description="Clean up the Atlas database.")
    parser.add_argument("--dry-run", action="store_true", help="Perform a dry run without deleting any data.")
    parser.add_argument("--no-backup", action="store_true", help="Do not create a backup of the database.")
    args = parser.parse_args()

    db_path = get_db_path()
    if not db_path.exists():
        print(f"Database not found at {db_path}")
        return

    if not args.no_backup:
        backup_database(db_path)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    duplicates_deleted = cleanup_duplicates(cursor, args.dry_run)
    phantom_deleted = cleanup_phantom_entries(cursor, args.dry_run)
    low_quality_deleted = cleanup_low_quality_entries(cursor, args.dry_run)

    if not args.dry_run:
        conn.commit()

    conn.close()

    print("\n--- Cleanup Complete ---")
    if args.dry_run:
        print("This was a dry run. No data was deleted.")
    else:
        print(f"Deleted {duplicates_deleted} duplicate entries.")
        print(f"Deleted {phantom_deleted} phantom entries.")
        print(f"Deleted {low_quality_deleted} low-quality entries.")

if __name__ == "__main__":
    main()
