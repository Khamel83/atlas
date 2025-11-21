import sqlite3
from pathlib import Path
import os

# Define the path to the data directory and atlas.db
data_dir = Path(__file__).parent.parent / "output"
data_dir.mkdir(parents=True, exist_ok=True) # Ensure data directory exists
db_path = data_dir / "atlas.db"

def init_atlas_db():
    conn = None
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Create the content table if it doesn't exist
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS content (
                url TEXT PRIMARY KEY,
                title TEXT,
                content TEXT,
                content_type TEXT,
                metadata TEXT,
                created_at TEXT,
                updated_at TEXT
            )
        """)
        conn.commit()
        print(f"Successfully initialized Atlas database at {db_path}")
    except sqlite3.Error as e:
        print(f"Error initializing Atlas database: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    init_atlas_db()
