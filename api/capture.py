"""
Atlas Content Capture API
Simple API endpoint for receiving content from Apple devices
"""

import json
import uuid
import sqlite3
from datetime import datetime
from pathlib import Path
from flask import Flask, request, jsonify
import sys

# Add Atlas helpers to path
sys.path.append(str(Path(__file__).parent.parent))

from helpers.config import load_config

app = Flask(__name__)


class CaptureAPI:
    """Handle content capture from Apple devices"""

    def __init__(self, config=None):
        self.config = config or load_config()
        self.db_path = str(
            Path(__file__).parent.parent / "data" / "podcasts" / "atlas_podcasts.db"
        )
        self.inputs_dir = Path(__file__).parent.parent / "inputs"
        self.inputs_dir.mkdir(exist_ok=True)

        # Initialize capture queue table if not exists
        self._init_capture_database()

    def _init_capture_database(self):
        """Initialize capture tracking database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS capture_queue (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        capture_id TEXT UNIQUE NOT NULL,
                        content_type TEXT NOT NULL,
                        content TEXT NOT NULL,
                        metadata TEXT,
                        source_device TEXT,
                        captured_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        processed_at TIMESTAMP,
                        status TEXT DEFAULT 'queued',
                        error_message TEXT,
                        atlas_content_id TEXT
                    )
                """
                )

                conn.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_capture_queue_status
                    ON capture_queue(status)
                """
                )

                conn.commit()
        except Exception as e:
            print(f"Error initializing capture database: {e}")

    def capture_content(self, content_type, content, metadata=None, source_device=None):
        """
        Capture content and queue for processing

        Args:
            content_type: Type of content (url, text, voice)
            content: The actual content (URL, text, etc.)
            metadata: Optional metadata dict
            source_device: Source device identifier

        Returns:
            Dict with success status and capture_id
        """

        try:
            # Validate input
            if not content_type or not content:
                return {
                    "success": False,
                    "error": "content_type and content are required",
                }

            if content_type not in ["url", "text", "voice"]:
                return {
                    "success": False,
                    "error": "content_type must be: url, text, or voice",
                }

            # Generate unique capture ID
            capture_id = str(uuid.uuid4())

            # Prepare metadata
            metadata = metadata or {}
            metadata.update(
                {
                    "captured_timestamp": datetime.now().isoformat(),
                    "capture_id": capture_id,
                }
            )

            # Queue for processing
            success = self._queue_for_processing(
                capture_id, content_type, content, metadata, source_device
            )

            if success:
                return {
                    "success": True,
                    "capture_id": capture_id,
                    "message": "Content queued for processing",
                    "estimated_processing_time": "5-30 minutes",
                }
            else:
                return {
                    "success": False,
                    "error": "Failed to queue content for processing",
                }

        except Exception as e:
            return {"success": False, "error": f"Capture error: {str(e)}"}

    def _queue_for_processing(
        self, capture_id, content_type, content, metadata, source_device
    ):
        """Queue content for background processing"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    """
                    INSERT INTO capture_queue
                    (capture_id, content_type, content, metadata, source_device)
                    VALUES (?, ?, ?, ?, ?)
                """,
                    (
                        capture_id,
                        content_type,
                        content,
                        json.dumps(metadata),
                        source_device,
                    ),
                )
                conn.commit()

            # Also write to immediate processing file for faster pickup
            if content_type == "url":
                self._add_to_articles_txt(content, metadata)
            elif content_type == "text":
                self._save_text_content(content, metadata, capture_id)

            return True

        except Exception as e:
            print(f"Error queuing content: {e}")
            return False

    def _add_to_articles_txt(self, url, metadata):
        """Add URL to articles.txt for immediate processing"""
        try:
            articles_file = self.inputs_dir / "articles.txt"
            with open(articles_file, "a", encoding="utf-8") as f:
                # Add comment with metadata if present
                if metadata.get("notes"):
                    f.write(f"\n# {metadata['notes']}\n")
                f.write(f"{url}\n")
        except Exception as e:
            print(f"Error adding to articles.txt: {e}")

    def _save_text_content(self, text, metadata, capture_id):
        """Save text content to file"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"captured_text_{timestamp}_{capture_id[:8]}.txt"
            filepath = self.inputs_dir / filename

            with open(filepath, "w", encoding="utf-8") as f:
                if metadata.get("notes"):
                    f.write(f"# {metadata['notes']}\n\n")
                f.write(text)

        except Exception as e:
            print(f"Error saving text content: {e}")

    def get_capture_status(self, capture_id):
        """Get status of a capture request"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row

                result = conn.execute(
                    """
                    SELECT capture_id, content_type, status, captured_at,
                           processed_at, error_message, atlas_content_id
                    FROM capture_queue
                    WHERE capture_id = ?
                """,
                    (capture_id,),
                ).fetchone()

                if result:
                    return dict(result)
                else:
                    return {"error": "Capture ID not found"}

        except Exception as e:
            return {"error": f"Status check error: {str(e)}"}


# Initialize API instance
capture_api = CaptureAPI()


@app.route("/api/capture", methods=["POST"])
def capture_endpoint():
    """
    Main capture endpoint for content from Apple devices

    Expected JSON format:
    {
        "type": "url|text|voice",
        "content": "...",
        "metadata": {
            "notes": "optional notes",
            "source": "ios_share_extension",
            "app": "Safari"
        },
        "source_device": "iPhone"
    }
    """

    try:
        # Parse JSON request
        data = request.get_json()

        if not data:
            return (
                jsonify({"success": False, "error": "Invalid JSON or empty request"}),
                400,
            )

        # Extract parameters
        content_type = data.get("type")
        content = data.get("content")
        metadata = data.get("metadata", {})
        source_device = data.get("source_device", "unknown")

        # Capture content
        result = capture_api.capture_content(
            content_type=content_type,
            content=content,
            metadata=metadata,
            source_device=source_device,
        )

        # Return appropriate status code
        status_code = 200 if result.get("success") else 400
        return jsonify(result), status_code

    except Exception as e:
        return jsonify({"success": False, "error": f"Server error: {str(e)}"}), 500


@app.route("/api/capture/status/<capture_id>", methods=["GET"])
def capture_status_endpoint(capture_id):
    """Get status of a capture request"""

    try:
        result = capture_api.get_capture_status(capture_id)
        return jsonify(result)

    except Exception as e:
        return jsonify({"error": f"Status error: {str(e)}"}), 500


@app.route("/api/capture/health", methods=["GET"])
def health_endpoint():
    """Health check endpoint"""
    return jsonify(
        {
            "status": "healthy",
            "service": "Atlas Content Capture API",
            "timestamp": datetime.now().isoformat(),
        }
    )


@app.route("/api/capture/recent", methods=["GET"])
def recent_captures_endpoint():
    """Get recent capture requests (for debugging)"""

    try:
        limit = request.args.get("limit", 10, type=int)

        with sqlite3.connect(capture_api.db_path) as conn:
            conn.row_factory = sqlite3.Row

            results = conn.execute(
                """
                SELECT capture_id, content_type, status, captured_at,
                       processed_at, source_device
                FROM capture_queue
                ORDER BY captured_at DESC
                LIMIT ?
            """,
                (limit,),
            ).fetchall()

            return jsonify({"recent_captures": [dict(row) for row in results]})

    except Exception as e:
        return jsonify({"error": f"Recent captures error: {str(e)}"}), 500


def create_flask_app():
    """Create Flask app with capture API endpoints"""
    return app


if __name__ == "__main__":
    # Development server
    print("Starting Atlas Capture API...")
    print("Endpoints:")
    print("  POST /api/capture - Capture content")
    print("  GET  /api/capture/status/<id> - Check capture status")
    print("  GET  /api/capture/health - Health check")
    print("  GET  /api/capture/recent - Recent captures")

    app.run(host="0.0.0.0", port=5000, debug=True)
