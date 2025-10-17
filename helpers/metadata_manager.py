"""
Metadata Manager Module

This module provides standardized metadata structures and management utilities
for all Atlas ingestors, ensuring consistent metadata handling across the system.
"""

import json
import os
from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, TypedDict

from helpers.dedupe import link_uid
from helpers.utils import calculate_hash


class ContentType(Enum):
    """Supported content types in Atlas."""

    ARTICLE = "article"
    PODCAST = "podcast"
    YOUTUBE = "youtube"
    INSTAPAPER = "instapaper"
    DOCUMENT = "document"


class ProcessingStatus(Enum):
    """Processing status for content items."""

    PENDING = "pending"
    STARTED = "started"
    SUCCESS = "success"
    ERROR = "error"
    RETRY = "retry"
    SKIPPED = "skipped"


@dataclass
class FetchAttempt:
    """Represents a single fetch attempt."""

    method: str
    timestamp: str
    result: str  # "success", "failed", "pending"
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class FetchDetails:
    """Detailed information about fetch attempts."""

    attempts: List[FetchAttempt] = field(default_factory=list)
    successful_method: Optional[str] = None
    is_truncated: bool = False
    total_attempts: int = 0
    fetch_time: Optional[float] = None

    def add_attempt(
        self,
        method: str,
        result: str,
        error: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """Add a new fetch attempt."""
        attempt = FetchAttempt(
            method=method,
            timestamp=datetime.now().isoformat(),
            result=result,
            error=error,
            metadata=metadata or {},
        )
        self.attempts.append(attempt)
        self.total_attempts += 1

        if result == "success":
            self.successful_method = method


@dataclass
class ContentMetadata:
    """Standardized metadata structure for all content types."""

    # Core identification
    uid: str
    content_type: ContentType
    source: str  # URL or source identifier
    title: Optional[str] = None

    # Processing information
    status: ProcessingStatus = ProcessingStatus.PENDING
    date: str = field(default_factory=lambda: datetime.now().isoformat())
    error: Optional[str] = None

    # File paths (relative to data directory)
    content_path: Optional[str] = None
    html_path: Optional[str] = None
    audio_path: Optional[str] = None
    transcript_path: Optional[str] = None

    # Content analysis
    tags: List[str] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)

    # Fetch details
    fetch_method: str = "unknown"
    fetch_details: FetchDetails = field(default_factory=FetchDetails)

    # Categorization metadata
    category_version: Optional[str] = None
    last_tagged_at: Optional[str] = None
    source_hash: Optional[str] = None

    # Type-specific metadata
    type_specific: Dict[str, Any] = field(default_factory=dict)

    # Processing timestamps
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def update_timestamp(self):
        """Update the updated_at timestamp."""
        self.updated_at = datetime.now().isoformat()

    def add_tag(self, tag: str):
        """Add a tag if not already present."""
        if tag not in self.tags:
            self.tags.append(tag)
            self.update_timestamp()

    def add_note(self, note: str):
        """Add a note."""
        self.notes.append(note)
        self.update_timestamp()

    def set_success(self, content_path: Optional[str] = None):
        """Mark content as successfully processed."""
        self.status = ProcessingStatus.SUCCESS
        self.error = None
        if content_path:
            self.content_path = content_path
        self.update_timestamp()

    def set_error(self, error_message: str):
        """Mark content as failed with error."""
        self.status = ProcessingStatus.ERROR
        self.error = error_message
        self.update_timestamp()

    def set_retry(self, error_message: str):
        """Mark content for retry."""
        self.status = ProcessingStatus.RETRY
        self.error = error_message
        self.update_timestamp()

    def get(self, key: str, default=None):
        """Dict-like get method for compatibility."""
        if hasattr(self, key):
            attr = getattr(self, key)
            # Handle enum values
            if hasattr(attr, 'value'):
                return attr.value
            return attr
        return default

    def __getitem__(self, key: str):
        """Dict-like item access."""
        if hasattr(self, key):
            attr = getattr(self, key)
            # Handle enum values
            if hasattr(attr, 'value'):
                return attr.value
            return attr
        raise KeyError(key)

    def __contains__(self, key: str):
        """Dict-like contains check."""
        return hasattr(self, key)

    def keys(self):
        """Dict-like keys method."""
        return [field.name for field in self.__dataclass_fields__]

    def values(self):
        """Dict-like values method."""
        for key in self.keys():
            yield self.get(key)

    def items(self):
        """Dict-like items method."""
        for key in self.keys():
            yield key, self.get(key)

    def __iter__(self):
        """Make object iterable for dict() constructor and ** operator."""
        return iter(self.keys())

    def __len__(self):
        """Return number of fields."""
        return len(self.__dataclass_fields__)


    def to_dict(self):
        """Convert to dictionary with enum handling."""
        result = {}
        for key, value in asdict(self).items():
            if hasattr(value, 'value'):  # Handle enum values
                result[key] = value.value
            else:
                result[key] = value
        return result


class ForgottenItem(TypedDict):
    metadata: ContentMetadata
    staleness_score: float
    relevance_score: float
    combined_score: float


class RecallCandidate(TypedDict):
    metadata: ContentMetadata
    priority: float
    days_overdue: int
    review_interval: int


class TagPatterns(TypedDict):
    tag_frequencies: Dict[str, int]
    total_tags: int
    total_occurrences: int
    tag_source_analysis: Dict[str, Dict[str, Any]]
    tag_cooccurrences: Dict[str, Dict[str, int]]
    trending_tags: List[Dict[str, Any]]
    source_tag_distribution: Dict[str, List[str]]


class MetadataManager:
    """Manager for content metadata operations."""

    def __init__(self, config: Optional[Dict[str, Any]] = None, metadata_dir: Optional[str] = None):
        # Support both config dict and direct metadata_dir for test compatibility
        if config is not None:
            self.config = config
            self.data_directory = config.get("data_directory", "output")
        else:
            self.config = {}
            self.data_directory = metadata_dir or "output"
        # For test compatibility
        self.metadata_dir = self.data_directory
        self.metadata_cache: Dict[str, ContentMetadata] = {}
        self.categories: List[str] = []

    def create_metadata(
        self, content_type: ContentType, source: str, title: Optional[str] = None, **kwargs
    ) -> ContentMetadata:
        """Create new metadata for content."""
        uid = link_uid(source)

        metadata = ContentMetadata(
            uid=uid, content_type=content_type, source=source, title=title, **kwargs
        )

        return metadata

    def load_metadata(
        self, content_type: ContentType, uid: str
    ) -> Optional[ContentMetadata]:
        """Load existing metadata from file."""
        metadata_path = self.get_metadata_path(content_type, uid)

        if not os.path.exists(metadata_path):
            return None

        try:
            with open(metadata_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            # Convert back to proper types
            data["content_type"] = ContentType(data["content_type"])
            data["status"] = ProcessingStatus(data["status"])

            # Reconstruct FetchDetails
            if "fetch_details" in data:
                fetch_data = data["fetch_details"]
                attempts = [
                    FetchAttempt(**attempt)
                    for attempt in fetch_data.get("attempts", [])
                ]
                data["fetch_details"] = FetchDetails(
                    attempts=attempts,
                    successful_method=fetch_data.get("successful_method"),
                    is_truncated=fetch_data.get("is_truncated", False),
                    total_attempts=fetch_data.get("total_attempts", 0),
                    fetch_time=fetch_data.get("fetch_time"),
                )

            return ContentMetadata(**data)

        except (json.JSONDecodeError, KeyError, ValueError):
            # Handle corrupted metadata gracefully
            return None

    def save_metadata(self, metadata: ContentMetadata) -> bool:
        """Save metadata to file."""
        try:
            metadata_path = self.get_metadata_path(metadata.content_type, metadata.uid)
            os.makedirs(os.path.dirname(metadata_path), exist_ok=True)

            # Convert to dict for JSON serialization
            data = asdict(metadata)

            # Convert enums to strings
            data["content_type"] = metadata.content_type.value
            data["status"] = metadata.status.value

            with open(metadata_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            return True

        except Exception:
            return False

    def get_metadata_path(self, content_type: ContentType, uid: str) -> str:
        """Get the metadata file path for given content type and UID."""
        type_dir = self.get_type_directory(content_type)
        return os.path.join(type_dir, "metadata", f"{uid}.json")

    def get_type_directory(self, content_type: ContentType) -> str:
        """Get the base directory for a content type."""
        type_mapping = {
            ContentType.ARTICLE: self.config.get(
                "article_output_path", os.path.join(self.data_directory, "articles")
            ),
            ContentType.PODCAST: self.config.get(
                "podcast_output_path", os.path.join(self.data_directory, "podcasts")
            ),
            ContentType.YOUTUBE: self.config.get(
                "youtube_output_path", os.path.join(self.data_directory, "youtube")
            ),
            ContentType.INSTAPAPER: self.config.get(
                "article_output_path", os.path.join(self.data_directory, "articles")
            ),
            ContentType.DOCUMENT: self.config.get(
                "document_output_path", os.path.join(self.data_directory, "documents")
            ),
        }
        return type_mapping[content_type]

    def exists(self, content_type: ContentType, uid: str) -> bool:
        """Check if metadata exists for given content."""
        metadata_path = self.get_metadata_path(content_type, uid)
        return os.path.exists(metadata_path)

    def get_content_paths(self, content_type: ContentType, uid: str) -> Dict[str, str]:
        """Get standard file paths for content type."""
        type_dir = self.get_type_directory(content_type)

        paths = {
            "metadata": os.path.join(type_dir, "metadata", f"{uid}.json"),
            "markdown": os.path.join(type_dir, "markdown", f"{uid}.md"),
            "log": os.path.join(type_dir, "ingest.log"),
        }

        # Add type-specific paths
        if content_type == ContentType.ARTICLE:
            paths["html"] = os.path.join(type_dir, "html", f"{uid}.html")
        elif content_type == ContentType.PODCAST:
            paths["audio"] = os.path.join(type_dir, "audio", f"{uid}.mp3")
            paths["transcript"] = os.path.join(type_dir, "transcripts", f"{uid}.txt")
        elif content_type == ContentType.YOUTUBE:
            paths["video"] = os.path.join(type_dir, "videos", f"{uid}.mp4")
            paths["transcript"] = os.path.join(type_dir, "transcripts", f"{uid}.txt")

        return paths

    def update_categorization(
        self,
        metadata: ContentMetadata,
        tier_1_categories: List[str],
        tier_2_sub_tags: List[str],
        category_version: str = "v1.0",
    ) -> bool:
        """Update categorization metadata."""
        # Clear existing tags and add new ones
        metadata.tags = []
        metadata.tags.extend(tier_1_categories)
        metadata.tags.extend(tier_2_sub_tags)

        # Update categorization metadata
        metadata.category_version = category_version
        metadata.last_tagged_at = datetime.now().isoformat()

        # Calculate source hash if content path exists
        if metadata.content_path and os.path.exists(metadata.content_path):
            metadata.source_hash = calculate_hash(metadata.content_path)

        metadata.update_timestamp()
        return self.save_metadata(metadata)

    def get_all_metadata(self, filters: Optional[Dict[str, Any]] = None) -> List[ContentMetadata]:
        """
        Get all metadata across all content types with optional filtering.

        Args:
            filters: Optional dictionary of filters:
                - content_type: ContentType or str to filter by type
                - category: str to filter by category (in tags)
                - status: ProcessingStatus or str to filter by status
                - date_from: str (ISO format) for date range filtering
                - date_to: str (ISO format) for date range filtering
                - source: str to filter by source
                - tags: List[str] to filter by tags (must contain all)

        Returns:
            List of ContentMetadata matching filters
        """
        from datetime import datetime

        all_metadata = []

        # Get all metadata from all content types
        for content_type in ContentType:
            type_dir = self.get_type_directory(content_type)
            metadata_dir = os.path.join(type_dir, "metadata")

            if not os.path.exists(metadata_dir):
                continue

            for filename in os.listdir(metadata_dir):
                if filename.endswith(".json"):
                    uid = filename[:-5]  # Remove .json extension
                    metadata = self.load_metadata(content_type, uid)
                    if metadata:
                        all_metadata.append(metadata)

        # Apply filters if provided
        if not filters:
            return all_metadata

        filtered_metadata = []
        for metadata in all_metadata:
            # Apply content_type filter
            if "content_type" in filters:
                filter_type = filters["content_type"]
                if isinstance(filter_type, str):
                    filter_type = ContentType(filter_type)
                if metadata.content_type != filter_type:
                    continue

            # Apply category filter (check if category is in tags)
            if "category" in filters:
                if filters["category"] not in metadata.tags:
                    continue

            # Apply status filter
            if "status" in filters:
                filter_status = filters["status"]
                if isinstance(filter_status, str):
                    filter_status = ProcessingStatus(filter_status)
                if metadata.status != filter_status:
                    continue

            # Apply source filter
            if "source" in filters:
                if filters["source"] not in metadata.source:
                    continue

            # Apply tags filter (must contain all specified tags)
            if "tags" in filters:
                required_tags = (
                    filters["tags"]
                    if isinstance(filters["tags"], list)
                    else [filters["tags"]]
                )
                if not all(tag in metadata.tags for tag in required_tags):
                    continue

            # Apply date range filters
            try:
                metadata_date = datetime.fromisoformat(
                    metadata.created_at.replace("Z", "+00:00")
                )

                if "date_from" in filters:
                    date_from = datetime.fromisoformat(
                        filters["date_from"].replace("Z", "+00:00")
                    )
                    if metadata_date < date_from:
                        continue

                if "date_to" in filters:
                    date_to = datetime.fromisoformat(
                        filters["date_to"].replace("Z", "+00:00")
                    )
                    if metadata_date > date_to:
                        continue

            except (ValueError, AttributeError):
                # Skip items with invalid dates if date filtering is requested
                if "date_from" in filters or "date_to" in filters:
                    continue

            filtered_metadata.append(metadata)

        return filtered_metadata

    def bulk_import_metadata_to_database(self, db_path: str = "data/atlas.db") -> Dict[str, int]:
        """
        Bulk import all metadata to the main Atlas database.

        Args:
            db_path: Path to the database file

        Returns:
            Dictionary with import statistics
        """
        import sqlite3

        # Get all metadata
        all_metadata = self.get_all_metadata()

        success_count = 0
        error_count = 0

        try:
            with sqlite3.connect(db_path) as conn:
                # Create content table if it doesn't exist
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS content (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        uid TEXT UNIQUE,
                        content_type TEXT,
                        source TEXT,
                        title TEXT,
                        status TEXT,
                        created_at TEXT,
                        updated_at TEXT,
                        error TEXT,
                        tags TEXT,
                        metadata TEXT
                    )
                ''')

                # Create indexes for performance
                conn.execute('CREATE INDEX IF NOT EXISTS idx_content_uid ON content (uid)')
                conn.execute('CREATE INDEX IF NOT EXISTS idx_content_type ON content (content_type)')
                conn.execute('CREATE INDEX IF NOT EXISTS idx_content_status ON content (status)')

                # Insert all metadata
                for metadata in all_metadata:
                    try:
                        # Convert metadata to database format
                        uid = metadata.uid
                        content_type = metadata.content_type.value if hasattr(metadata.content_type, 'value') else str(metadata.content_type)
                        source = metadata.source
                        title = metadata.title or ""
                        status = metadata.status.value if hasattr(metadata.status, 'value') else str(metadata.status)
                        created_at = metadata.created_at
                        updated_at = metadata.updated_at
                        error = metadata.error or ""
                        tags = json.dumps(metadata.tags)
                        metadata_json = json.dumps(asdict(metadata))

                        # Insert or replace content
                        conn.execute('''
                            INSERT OR REPLACE INTO content
                            (uid, content_type, source, title, status, created_at, updated_at, error, tags, metadata)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ''', (uid, content_type, source, title, status, created_at, updated_at, error, tags, metadata_json))

                        success_count += 1
                    except Exception as e:
                        print(f"Error importing metadata for {metadata.uid}: {e}")
                        error_count += 1

                conn.commit()

        except Exception as e:
            print(f"Error during bulk import: {e}")
            error_count = len(all_metadata)

        # Return statistics
        return {
            "total_processed": len(all_metadata),
            "success_count": success_count,
            "error_count": error_count
        }

    def get_all_metadata_by_type(
        self, content_type: ContentType
    ) -> List[ContentMetadata]:
        """Get all metadata for a specific content type (legacy method)."""
        return self.get_all_metadata({"content_type": content_type})

    def get_failed_items(self, content_type: ContentType) -> List[ContentMetadata]:
        """Get all failed items for a content type."""
        all_metadata = self.get_all_metadata_by_type(content_type)
        return [m for m in all_metadata if m.status == ProcessingStatus.ERROR]

    def get_retry_items(self, content_type: ContentType) -> List[ContentMetadata]:
        """Get all items marked for retry."""
        all_metadata = self.get_all_metadata_by_type(content_type)
        return [m for m in all_metadata if m.status == ProcessingStatus.RETRY]

    def cleanup_old_metadata(self, content_type: ContentType, days_old: int = 30):
        """Clean up metadata older than specified days."""
        from datetime import datetime, timedelta

        cutoff_date = datetime.now() - timedelta(days=days_old)
        all_metadata = self.get_all_metadata_by_type(content_type)

        for metadata in all_metadata:
            created_date = datetime.fromisoformat(
                metadata.created_at.replace("Z", "+00:00")
            )
            if created_date < cutoff_date and metadata.status == ProcessingStatus.ERROR:
                # Remove old failed items
                metadata_path = self.get_metadata_path(content_type, metadata.uid)
                try:
                    os.remove(metadata_path)
                except OSError:
                    pass

    def get_forgotten_content(self, threshold_days: int = 30) -> List[ContentMetadata]:
        """
        Query content not accessed in threshold_days with relevance ranking.

        Args:
            threshold_days: Number of days to consider content "forgotten"

        Returns:
            List of ContentMetadata sorted by staleness and relevance
        """
        from datetime import datetime, timedelta

        cutoff = datetime.now() - timedelta(days=threshold_days)
        forgotten: List[ForgottenItem] = []

        # Get all metadata across all content types
        all_metadata = self.get_all_metadata()

        for metadata in all_metadata:
            try:
                updated = datetime.fromisoformat(
                    metadata.updated_at.replace("Z", "+00:00")
                )
                if updated < cutoff:
                    # Calculate staleness score (higher = more stale)
                    days_stale = (datetime.now() - updated).days
                    staleness_score = min(days_stale / 365.0, 1.0)  # Normalize to 0-1

                    # Calculate relevance score based on tags and content type
                    relevance_score = (
                        len(metadata.tags) * 0.1
                    )  # More tags = more relevant
                    if metadata.content_type == ContentType.ARTICLE:
                        relevance_score += 0.5
                    elif metadata.content_type == ContentType.YOUTUBE:
                        relevance_score += 0.3

                    # Combined score prioritizes stale but relevant content
                    combined_score = staleness_score + (1.0 - relevance_score)

                    forgotten.append(
                        {
                            "metadata": metadata,
                            "staleness_score": staleness_score,
                            "relevance_score": relevance_score,
                            "combined_score": combined_score,
                        }
                    )

            except (ValueError, AttributeError):
                continue

        # Sort by combined score (highest first = most stale + relevant)
        forgotten.sort(key=lambda x: float(x["combined_score"]), reverse=True)

        # Return just the metadata objects
        return [item["metadata"] for item in forgotten]  # type: ignore

    def get_tag_patterns(self, min_frequency: int = 2) -> TagPatterns:
        """
        Analyze tag usage patterns and frequencies for content organization insights.

        Args:
            min_frequency: Minimum frequency for tags to be included

        Returns:
            Dictionary with tag analysis including frequencies and co-occurrence
        """
        from collections import Counter, defaultdict

        all_metadata = self.get_all_metadata()

        # Collect all tags and their metadata
        tag_frequencies: Counter[str] = Counter()
        tag_sources: defaultdict[str, set] = defaultdict(set)
        tag_content_types: defaultdict[str, set] = defaultdict(set)
        tag_cooccurrences: defaultdict[str, Counter[str]] = defaultdict(Counter)

        for metadata in all_metadata:
            for tag in metadata.tags:
                tag_frequencies[tag] += 1
                tag_sources[tag].add(metadata.source)
                tag_content_types[tag].add(metadata.content_type.value)

                # Track co-occurrences with other tags
                for other_tag in metadata.tags:
                    if tag != other_tag:
                        tag_cooccurrences[tag][other_tag] += 1

        # Filter by minimum frequency
        filtered_tags = {
            tag: freq for tag, freq in tag_frequencies.items() if freq >= min_frequency
        }

        # Build patterns analysis
        patterns: TagPatterns = {
            "tag_frequencies": filtered_tags,
            "total_tags": len(filtered_tags),
            "total_occurrences": sum(filtered_tags.values()),
            "tag_source_analysis": {},
            "tag_cooccurrences": {},
            "trending_tags": [],
            "source_tag_distribution": defaultdict(list),
        }

        # Analyze each tag
        for tag, frequency in filtered_tags.items():
            patterns["tag_source_analysis"][tag] = {
                "frequency": frequency,
                "unique_sources": len(tag_sources[tag]),
                "content_types": list(tag_content_types[tag]),
                "average_usage": (
                    frequency / len(tag_sources[tag]) if tag_sources[tag] else 0
                ),
            }

            # Get top co-occurring tags
            top_cooccurrences = tag_cooccurrences[tag].most_common(5)
            patterns["tag_cooccurrences"][tag] = dict(top_cooccurrences)

        # Identify trending tags (high frequency, diverse sources)
        for tag, analysis in patterns["tag_source_analysis"].items():
            if analysis["frequency"] >= 3 and analysis["unique_sources"] >= 2:
                patterns["trending_tags"].append(
                    {
                        "tag": tag,
                        "frequency": analysis["frequency"],
                        "diversity_score": analysis["unique_sources"]
                        / analysis["frequency"],
                    }
                )

        patterns["trending_tags"].sort(key=lambda x: x["frequency"], reverse=True)

        return patterns

    def get_temporal_patterns(self, time_window: str = "month") -> Dict[str, Any]:
        """
        Analyze time-based content relationships and ingestion patterns.

        Args:
            time_window: Time window for analysis ('day', 'week', 'month')

        Returns:
            Dictionary with temporal analysis and patterns
        """
        from collections import defaultdict
        from datetime import datetime, timedelta

        all_metadata = self.get_all_metadata()

        # Time window mapping
        window_deltas = {
            "day": timedelta(days=1),
            "week": timedelta(weeks=1),
            "month": timedelta(days=30),
        }

        if time_window not in window_deltas:
            time_window = "month"

        # Group content by time windows
        time_groups: defaultdict[str, list] = defaultdict(list)
        content_volume: defaultdict[str, int] = defaultdict(int)
        tag_trends: defaultdict[str, defaultdict[str, int]] = defaultdict(lambda: defaultdict(int))
        content_type_trends: defaultdict[str, defaultdict[str, int]] = defaultdict(lambda: defaultdict(int))

        for metadata in all_metadata:
            try:
                created_date = datetime.fromisoformat(
                    metadata.created_at.replace("Z", "+00:00")
                )

                # Create time window key
                if time_window == "day":
                    window_key = created_date.strftime("%Y-%m-%d")
                elif time_window == "week":
                    # Get start of week
                    start_of_week = created_date - timedelta(
                        days=created_date.weekday()
                    )
                    window_key = start_of_week.strftime("%Y-W%U")
                else:  # month
                    window_key = created_date.strftime("%Y-%m")

                time_groups[window_key].append(metadata)
                content_volume[window_key] += 1

                # Track tag trends
                for tag in metadata.tags:
                    tag_trends[window_key][tag] += 1

                # Track content type trends
                content_type_trends[window_key][metadata.content_type.value] += 1

            except (ValueError, AttributeError):
                continue

        # Calculate patterns
        patterns = {
            "time_window": time_window,
            "content_volume": dict(content_volume),
            "tag_trends": dict(tag_trends),
            "content_type_trends": dict(content_type_trends),
            "volume_stats": {},
            "seasonal_patterns": {},
            "growth_analysis": {},
        }

        # Volume statistics
        volumes = list(content_volume.values())
        if volumes:
            patterns["volume_stats"] = {
                "average": sum(volumes) / len(volumes),
                "max": max(volumes),
                "min": min(volumes),
                "total_periods": len(volumes),
                "total_content": sum(volumes),
            }

        # Growth analysis (compare recent vs older periods)
        sorted_periods = sorted(content_volume.keys())
        if len(sorted_periods) >= 2:
            recent_periods = sorted_periods[-3:]  # Last 3 periods
            older_periods = (
                sorted_periods[:-3] if len(sorted_periods) > 3 else sorted_periods[:1]
            )

            recent_avg = sum(content_volume[p] for p in recent_periods) / len(
                recent_periods
            )
            older_avg = sum(content_volume[p] for p in older_periods) / len(
                older_periods
            )

            growth_rate = (
                ((recent_avg - older_avg) / older_avg * 100) if older_avg > 0 else 0
            )

            patterns["growth_analysis"] = {
                "recent_average": recent_avg,
                "older_average": older_avg,
                "growth_rate_percent": growth_rate,
                "trend": (
                    "growing"
                    if growth_rate > 10
                    else "declining" if growth_rate < -10 else "stable"
                ),
            }

        return patterns

    def get_recall_items(self, limit: int = 10) -> List[ContentMetadata]:
        """
        Generate spaced repetition schedule for knowledge retention optimization.

        Args:
            limit: Maximum number of items to return

        Returns:
            List of ContentMetadata due for review
        """
        from datetime import datetime

        all_metadata = self.get_all_metadata()
        recall_candidates: List[RecallCandidate] = []

        for metadata in all_metadata:
            try:
                created_date = datetime.fromisoformat(
                    metadata.created_at.replace("Z", "+00:00")
                )
                updated_date = datetime.fromisoformat(
                    metadata.updated_at.replace("Z", "+00:00")
                )

                # Calculate days since creation and last update
                days_since_created = (datetime.now() - created_date).days
                days_since_updated = (datetime.now() - updated_date).days

                # Simple spaced repetition algorithm
                # Review intervals: 1, 3, 7, 14, 30, 60, 120 days
                review_intervals = [1, 3, 7, 14, 30, 60, 120]

                # Determine current interval based on how many times it might have been reviewed
                review_count = 0
                for i, interval in enumerate(review_intervals):
                    if days_since_created >= interval:
                        review_count = i + 1
                    else:
                        break

                # Check if item is due for review
                if review_count < len(review_intervals):
                    next_interval = review_intervals[review_count]
                    if days_since_updated >= next_interval:
                        # Calculate priority based on content type and staleness
                        priority = 1.0

                        # Higher priority for articles and YouTube videos
                        if metadata.content_type == ContentType.ARTICLE:
                            priority += 0.5
                        elif metadata.content_type == ContentType.YOUTUBE:
                            priority += 0.3

                        # Higher priority for items with more tags (more processed)
                        priority += len(metadata.tags) * 0.1

                        # Increase priority based on how overdue the review is
                        overdue_factor = min(days_since_updated / next_interval, 3.0)
                        priority *= overdue_factor

                        recall_candidates.append(
                            {
                                "metadata": metadata,
                                "priority": priority,
                                "days_overdue": days_since_updated - next_interval,
                                "review_interval": next_interval,
                            }
                        )

            except (ValueError, AttributeError):
                continue

        # Sort by priority (highest first)
        recall_candidates.sort(key=lambda x: float(x["priority"]), reverse=True)

        # Return top items up to limit
        return [item["metadata"] for item in recall_candidates[:limit]]  # type: ignore


def create_metadata_manager(config: Dict[str, Any]) -> MetadataManager:
    """Factory function to create metadata manager."""
    return MetadataManager(config)


# Convenience functions for common operations
def create_article_metadata(
    source: str, title: str, config: Dict[str, Any]
) -> ContentMetadata:
    """Create metadata for an article."""
    manager = create_metadata_manager(config)
    return manager.create_metadata(ContentType.ARTICLE, source, title)


def create_podcast_metadata(
    source: str, title: str, config: Dict[str, Any], **kwargs
) -> ContentMetadata:
    """Create metadata for a podcast episode."""
    manager = create_metadata_manager(config)
    return manager.create_metadata(ContentType.PODCAST, source, title, **kwargs)


def create_youtube_metadata(
    source: str, title: str, config: Dict[str, Any], **kwargs
) -> ContentMetadata:
    """Create metadata for a YouTube video."""
    manager = create_metadata_manager(config)
    return manager.create_metadata(ContentType.YOUTUBE, source, title, **kwargs)
