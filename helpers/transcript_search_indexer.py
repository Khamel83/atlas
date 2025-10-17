#!/usr/bin/env python3
"""
Enhanced Search Indexer for Transcript Content
Indexes parsed transcript segments with speaker attribution, topic clustering,
and conversation-aware search capabilities.
"""

import json
import sqlite3
import logging
from typing import Dict, List, Any, Optional
from pathlib import Path
from collections import defaultdict


class TranscriptSearchIndexer:
    """Index transcript content for enhanced search capabilities."""

    def __init__(self, db_path: str = "data/atlas_search.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.logger = logging.getLogger(__name__)

        # Initialize database
        self._init_database()

    def _init_database(self):
        """Initialize database with transcript search schema."""
        try:
            # Read and execute schema
            schema_path = Path("migrations/add_transcript_segments.sql")
            if schema_path.exists():
                with open(schema_path, "r") as f:
                    schema_sql = f.read()

                conn = sqlite3.connect(self.db_path)

                # Use executescript for better multi-line statement handling
                # But first clean up comments and extra whitespace
                cleaned_sql_lines = []
                for line in schema_sql.split('\n'):
                    line = line.strip()
                    # Skip comment-only lines but preserve inline comments for context
                    if line and not line.startswith('--'):
                        cleaned_sql_lines.append(line)

                cleaned_sql = '\n'.join(cleaned_sql_lines)

                try:
                    conn.executescript(cleaned_sql)
                    conn.commit()
                    self.logger.info(
                        f"Initialized transcript search database: {self.db_path}"
                    )
                except sqlite3.Error as e:
                    self.logger.error(f"Error executing schema script: {e}")
                    # Fallback to creating basic tables without FTS/triggers
                    self._create_basic_tables(conn)

                conn.close()
            else:
                self.logger.warning(f"Schema file not found: {schema_path}")
                # Create basic tables without schema file
                conn = sqlite3.connect(self.db_path)
                self._create_basic_tables(conn)
                conn.close()

        except Exception as e:
            self.logger.error(f"Error initializing database: {e}")
            raise

    def _create_basic_tables(self, conn):
        """Create basic tables without advanced features if schema fails."""
        cursor = conn.cursor()

        # Basic transcript segments table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS transcript_segments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                episode_id INTEGER,
                content_uid TEXT NOT NULL,
                speaker TEXT,
                content TEXT NOT NULL,
                segment_id INTEGER,
                start_line INTEGER,
                end_line INTEGER,
                start_timestamp TEXT,
                end_timestamp TEXT,
                word_count INTEGER,
                segment_type TEXT,
                topic_tags TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Basic topic clusters table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS topic_clusters (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                topic_name TEXT UNIQUE NOT NULL,
                keywords TEXT,
                related_segments TEXT,
                episode_count INTEGER DEFAULT 0,
                content_count INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Basic speakers table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS transcript_speakers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                speaker_name TEXT NOT NULL,
                normalized_name TEXT NOT NULL,
                episode_count INTEGER DEFAULT 0,
                segment_count INTEGER DEFAULT 0,
                total_word_count INTEGER DEFAULT 0,
                first_appearance TIMESTAMP,
                last_appearance TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(normalized_name)
            )
        """)

        # Basic indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_transcript_segments_speaker ON transcript_segments(speaker)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_transcript_segments_content_uid ON transcript_segments(content_uid)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_topic_clusters_name ON topic_clusters(topic_name)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_transcript_speakers_name ON transcript_speakers(normalized_name)")

        conn.commit()
        self.logger.info("Created basic transcript search tables")

    def index_transcript_content(
        self,
        content_uid: str,
        parsed_transcript: Dict[str, Any],
        metadata: Dict[str, Any] = None,
    ) -> bool:
        """Index parsed transcript content for search."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Clear existing segments for this content
            cursor.execute(
                "DELETE FROM transcript_segments WHERE content_uid = ?", (content_uid,)
            )

            # Index segments
            segments_indexed = self._index_segments(
                cursor, content_uid, parsed_transcript, metadata
            )

            # Build topic clusters
            self._update_topic_clusters(cursor, parsed_transcript.get("topics", []))

            # Update speaker statistics
            self._update_speaker_stats(
                cursor,
                parsed_transcript.get("speakers", []),
                parsed_transcript.get("segments", []),
            )

            conn.commit()
            conn.close()

            self.logger.info(
                f"Indexed {segments_indexed} transcript segments for {content_uid}"
            )
            return True

        except Exception as e:
            self.logger.error(f"Error indexing transcript content {content_uid}: {e}")
            return False

    def _index_segments(
        self,
        cursor: sqlite3.Cursor,
        content_uid: str,
        parsed_transcript: Dict[str, Any],
        metadata: Dict[str, Any],
    ) -> int:
        """Index individual transcript segments."""
        segments = parsed_transcript.get("segments", [])
        indexed_count = 0

        # Get episode ID if available
        episode_id = self._get_episode_id(metadata) if metadata else None

        for segment in segments:
            try:
                # Extract topic tags for this segment
                topic_tags = self._extract_segment_topics(
                    segment, parsed_transcript.get("topics", [])
                )

                cursor.execute(
                    """
                    INSERT INTO transcript_segments (
                        episode_id, content_uid, speaker, content, segment_id,
                        start_line, end_line, start_timestamp, end_timestamp,
                        word_count, segment_type, topic_tags
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        episode_id,
                        content_uid,
                        segment.get("speaker"),
                        segment.get("content"),
                        segment.get("id"),
                        segment.get("start_line"),
                        segment.get("end_line"),
                        segment.get("timestamp"),
                        segment.get("end_timestamp"),
                        segment.get("word_count", 0),
                        segment.get("type", "discussion"),
                        json.dumps(topic_tags) if topic_tags else None,
                    ),
                )

                indexed_count += 1

            except Exception as e:
                self.logger.error(
                    f"Error indexing segment {segment.get('id', 'unknown')}: {e}"
                )
                continue

        return indexed_count

    def _extract_segment_topics(
        self, segment: Dict[str, Any], topics: List[Dict[str, Any]]
    ) -> List[str]:
        """Extract topic tags for a specific segment."""
        segment_id = segment.get("id")
        if not segment_id:
            return []

        segment_topics = []
        for topic in topics:
            if segment_id in topic.get("segments", []):
                segment_topics.append(topic.get("topic", ""))
                # Add keywords as well
                keywords = topic.get("keywords", [])
                segment_topics.extend(keywords[:3])  # Top 3 keywords

        return list(set(segment_topics))  # Remove duplicates

    def _get_episode_id(self, metadata: Dict[str, Any]) -> Optional[int]:
        """Extract episode ID from metadata if available."""
        # This would connect to the podcast database to get episode ID
        # For now, return None as it requires integration with podcast system
        return None

    def _update_topic_clusters(
        self, cursor: sqlite3.Cursor, topics: List[Dict[str, Any]]
    ):
        """Update topic clusters with new topics."""
        for topic in topics:
            topic_name = topic.get("topic", "").strip()
            if not topic_name:
                continue

            keywords = topic.get("keywords", [])
            segments = topic.get("segments", [])

            try:
                # Check if topic exists
                cursor.execute(
                    "SELECT id, content_count FROM topic_clusters WHERE topic_name = ?",
                    (topic_name,),
                )
                result = cursor.fetchone()

                if result:
                    # Update existing topic
                    topic_id, current_count = result
                    cursor.execute(
                        """
                        UPDATE topic_clusters
                        SET keywords = ?, content_count = ?, updated_at = CURRENT_TIMESTAMP
                        WHERE id = ?
                    """,
                        (json.dumps(keywords), current_count + 1, topic_id),
                    )
                else:
                    # Create new topic
                    cursor.execute(
                        """
                        INSERT INTO topic_clusters (topic_name, keywords, content_count)
                        VALUES (?, ?, ?)
                    """,
                        (topic_name, json.dumps(keywords), 1),
                    )

            except Exception as e:
                self.logger.error(f"Error updating topic cluster {topic_name}: {e}")
                continue

    def _update_speaker_stats(
        self,
        cursor: sqlite3.Cursor,
        speakers: List[str],
        segments: List[Dict[str, Any]],
    ):
        """Update speaker statistics."""
        speaker_stats = defaultdict(lambda: {"segment_count": 0, "word_count": 0})

        # Calculate stats from segments
        for segment in segments:
            speaker = segment.get("speaker")
            if not speaker:
                continue

            speaker_stats[speaker]["segment_count"] += 1
            speaker_stats[speaker]["word_count"] += segment.get("word_count", 0)

        # Update database
        for speaker, stats in speaker_stats.items():
            try:
                normalized_name = self._normalize_speaker_name(speaker)

                # Check if speaker exists
                cursor.execute(
                    "SELECT id, segment_count, total_word_count FROM transcript_speakers WHERE normalized_name = ?",
                    (normalized_name,),
                )
                result = cursor.fetchone()

                if result:
                    # Update existing speaker
                    speaker_id, current_segments, current_words = result
                    cursor.execute(
                        """
                        UPDATE transcript_speakers
                        SET segment_count = ?, total_word_count = ?, last_appearance = CURRENT_TIMESTAMP,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE id = ?
                    """,
                        (
                            current_segments + stats["segment_count"],
                            current_words + stats["word_count"],
                            speaker_id,
                        ),
                    )
                else:
                    # Create new speaker
                    cursor.execute(
                        """
                        INSERT INTO transcript_speakers (
                            speaker_name, normalized_name, segment_count, total_word_count,
                            first_appearance, last_appearance
                        ) VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                    """,
                        (
                            speaker,
                            normalized_name,
                            stats["segment_count"],
                            stats["word_count"],
                        ),
                    )

            except Exception as e:
                self.logger.error(f"Error updating speaker stats for {speaker}: {e}")
                continue

    def _normalize_speaker_name(self, speaker: str) -> str:
        """Normalize speaker name for consistent indexing."""
        if not speaker:
            return ""

        # Basic normalization
        normalized = speaker.strip().lower()
        normalized = normalized.replace(".", "").replace(",", "")

        return normalized

    def search_transcripts(
        self,
        query: str,
        speaker: str = None,
        topic: str = None,
        segment_type: str = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """Search transcript segments with filters."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Build search query
            base_query = """
                SELECT ts.*, tc.topic_name, tc.keywords
                FROM transcript_segments ts
                LEFT JOIN topic_clusters tc ON json_extract(ts.topic_tags, '$[0]') = tc.topic_name
                WHERE 1=1
            """

            params = []

            # Add text search
            if query:
                base_query += " AND ts.content MATCH ?"
                params.append(query)

            # Add filters
            if speaker:
                base_query += " AND LOWER(ts.speaker) LIKE ?"
                params.append(f"%{speaker.lower()}%")

            if topic:
                base_query += " AND ts.topic_tags LIKE ?"
                params.append(f"%{topic}%")

            if segment_type:
                base_query += " AND ts.segment_type = ?"
                params.append(segment_type)

            # Order by relevance and limit
            base_query += " ORDER BY ts.word_count DESC, ts.id DESC LIMIT ?"
            params.append(limit)

            cursor.execute(base_query, params)
            results = cursor.fetchall()

            # Convert to dictionaries
            columns = [desc[0] for desc in cursor.description]
            search_results = []

            for row in results:
                result = dict(zip(columns, row))
                # Parse JSON fields
                if result.get("topic_tags"):
                    try:
                        result["topic_tags"] = json.loads(result["topic_tags"])
                    except:
                        result["topic_tags"] = []
                if result.get("keywords"):
                    try:
                        result["keywords"] = json.loads(result["keywords"])
                    except:
                        result["keywords"] = []

                search_results.append(result)

            conn.close()

            self.logger.info(
                f"Search returned {len(search_results)} results for query: {query}"
            )
            return search_results

        except Exception as e:
            self.logger.error(f"Error searching transcripts: {e}")
            return []

    def get_speaker_topics(self, speaker_name: str) -> List[Dict[str, Any]]:
        """Get all topics discussed by a specific speaker."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT DISTINCT tc.topic_name, tc.keywords, COUNT(ts.id) as segment_count
                FROM transcript_segments ts
                JOIN topic_clusters tc ON json_extract(ts.topic_tags, '$[0]') = tc.topic_name
                WHERE LOWER(ts.speaker) LIKE ?
                GROUP BY tc.topic_name, tc.keywords
                ORDER BY segment_count DESC
            """,
                (f"%{speaker_name.lower()}%",),
            )

            results = cursor.fetchall()
            topics = []

            for row in results:
                topic_name, keywords_json, segment_count = row
                keywords = []
                if keywords_json:
                    try:
                        keywords = json.loads(keywords_json)
                    except:
                        pass

                topics.append(
                    {
                        "topic": topic_name,
                        "keywords": keywords,
                        "segment_count": segment_count,
                    }
                )

            conn.close()
            return topics

        except Exception as e:
            self.logger.error(f"Error getting speaker topics for {speaker_name}: {e}")
            return []

    def find_related_segments(
        self, segment_id: int, limit: int = 5
    ) -> List[Dict[str, Any]]:
        """Find segments related to a given segment by topic."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Get topics for the source segment
            cursor.execute(
                "SELECT topic_tags FROM transcript_segments WHERE id = ?", (segment_id,)
            )
            result = cursor.fetchone()

            if not result or not result[0]:
                return []

            try:
                source_topics = json.loads(result[0])
            except:
                return []

            if not source_topics:
                return []

            # Find segments with similar topics
            topic_placeholders = ",".join(["?" for _ in source_topics])
            cursor.execute(
                f"""
                SELECT ts.*, COUNT(*) as topic_overlap
                FROM transcript_segments ts
                WHERE ts.id != ?
                AND (
                    {' OR '.join(["ts.topic_tags LIKE ?" for _ in source_topics])}
                )
                GROUP BY ts.id
                ORDER BY topic_overlap DESC, ts.word_count DESC
                LIMIT ?
            """,
                [segment_id] + [f"%{topic}%" for topic in source_topics] + [limit],
            )

            results = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]

            related_segments = []
            for row in results:
                segment = dict(zip(columns, row))
                if segment.get("topic_tags"):
                    try:
                        segment["topic_tags"] = json.loads(segment["topic_tags"])
                    except:
                        segment["topic_tags"] = []
                related_segments.append(segment)

            conn.close()
            return related_segments

        except Exception as e:
            self.logger.error(f"Error finding related segments for {segment_id}: {e}")
            return []

    def get_search_stats(self) -> Dict[str, Any]:
        """Get search index statistics."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            stats = {}

            # Segment stats
            cursor.execute("SELECT COUNT(*) FROM transcript_segments")
            stats["total_segments"] = cursor.fetchone()[0]

            cursor.execute(
                "SELECT COUNT(DISTINCT speaker) FROM transcript_segments WHERE speaker IS NOT NULL"
            )
            stats["unique_speakers"] = cursor.fetchone()[0]

            cursor.execute(
                "SELECT COUNT(DISTINCT content_uid) FROM transcript_segments"
            )
            stats["indexed_content"] = cursor.fetchone()[0]

            # Topic stats
            cursor.execute("SELECT COUNT(*) FROM topic_clusters")
            stats["total_topics"] = cursor.fetchone()[0]

            # Speaker stats
            cursor.execute("SELECT COUNT(*) FROM transcript_speakers")
            stats["total_speakers"] = cursor.fetchone()[0]

            # Top speakers by content
            cursor.execute(
                """
                SELECT speaker_name, segment_count, total_word_count
                FROM transcript_speakers
                ORDER BY total_word_count DESC
                LIMIT 10
            """
            )
            stats["top_speakers"] = [
                {"name": row[0], "segments": row[1], "words": row[2]}
                for row in cursor.fetchall()
            ]

            # Top topics
            cursor.execute(
                """
                SELECT topic_name, content_count
                FROM topic_clusters
                ORDER BY content_count DESC
                LIMIT 10
            """
            )
            stats["top_topics"] = [
                {"topic": row[0], "content_count": row[1]} for row in cursor.fetchall()
            ]

            conn.close()
            return stats

        except Exception as e:
            self.logger.error(f"Error getting search stats: {e}")
            return {}


def main():
    """Test transcript search indexer."""
    indexer = TranscriptSearchIndexer()

    # Test with sample data
    sample_transcript = {
        "speakers": ["Lex Fridman", "Elon Musk"],
        "segments": [
            {
                "id": 1,
                "speaker": "Lex Fridman",
                "content": "Welcome to the podcast. Today we discuss AI safety.",
                "type": "question",
                "word_count": 10,
            },
            {
                "id": 2,
                "speaker": "Elon Musk",
                "content": "AI safety is crucial for the future of humanity.",
                "type": "answer",
                "word_count": 9,
            },
        ],
        "topics": [
            {
                "topic": "AI Safety",
                "keywords": ["safety", "artificial", "intelligence"],
                "segments": [1, 2],
            }
        ],
    }

    # Index sample content
    success = indexer.index_transcript_content("test-episode-1", sample_transcript)
    print(f"Indexing success: {success}")

    # Test search
    results = indexer.search_transcripts("AI safety")
    print(f"Search results: {len(results)}")

    # Test speaker topics
    topics = indexer.get_speaker_topics("Elon Musk")
    print(f"Elon Musk topics: {len(topics)}")

    # Get stats
    stats = indexer.get_search_stats()
    print(f"Search stats: {stats}")


if __name__ == "__main__":
    main()
