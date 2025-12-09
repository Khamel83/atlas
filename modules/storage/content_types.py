"""
Content Types for Atlas File-Based Storage

Defines the data structures for all content types handled by Atlas.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any
import json
import hashlib


class ContentType(str, Enum):
    """Types of content Atlas can store."""
    ARTICLE = "article"
    PODCAST = "podcast"
    YOUTUBE = "youtube"
    NEWSLETTER = "newsletter"
    EMAIL = "email"
    DOCUMENT = "document"  # PDFs, DOCX, etc.
    NOTE = "note"  # TrojanHorse notes
    UNKNOWN = "unknown"


class SourceType(str, Enum):
    """How content was ingested."""
    EMAIL_INGEST = "email"
    API_SUBMIT = "api"
    RSS_DISCOVERY = "rss"
    YOUTUBE_HISTORY = "youtube_history"
    YOUTUBE_SUBMIT = "youtube_submit"
    NEWSLETTER = "newsletter"
    TROJANHORSE = "trojanhorse"
    MANUAL = "manual"
    MIGRATION = "migration"


class ProcessingStatus(str, Enum):
    """Processing status of content."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    DUPLICATE = "duplicate"


@dataclass
class ContentItem:
    """
    Represents a single piece of content in Atlas.

    This is the core data structure that gets serialized to metadata.json files.
    """

    # Required fields
    content_id: str  # Unique identifier (usually a hash)
    content_type: ContentType
    source_type: SourceType
    title: str

    # Source information
    source_url: Optional[str] = None
    source_email: Optional[str] = None

    # Content
    content_path: Optional[str] = None  # Path to content.md relative to content dir
    raw_path: Optional[str] = None  # Path to raw file if applicable

    # Metadata
    author: Optional[str] = None
    description: Optional[str] = None
    tags: List[str] = field(default_factory=list)

    # For podcasts
    podcast_name: Optional[str] = None
    episode_number: Optional[int] = None
    audio_url: Optional[str] = None
    transcript_source: Optional[str] = None  # online, macwhisper, whisper

    # For YouTube
    channel_name: Optional[str] = None
    video_id: Optional[str] = None
    duration_seconds: Optional[int] = None

    # Timestamps
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    published_at: Optional[datetime] = None
    ingested_at: datetime = field(default_factory=datetime.utcnow)

    # Processing
    status: ProcessingStatus = ProcessingStatus.PENDING
    error_message: Optional[str] = None
    processing_attempts: int = 0

    # Relationships
    parent_id: Optional[str] = None  # e.g., email that contained this URL
    child_ids: List[str] = field(default_factory=list)  # e.g., links extracted from content

    # Extra data
    extra: Dict[str, Any] = field(default_factory=dict)

    @staticmethod
    def generate_id(source_url: Optional[str] = None,
                    title: Optional[str] = None,
                    content: Optional[str] = None) -> str:
        """Generate a unique content ID from available data."""
        # Prefer URL-based ID for deduplication
        if source_url:
            return hashlib.sha256(source_url.encode()).hexdigest()[:16]

        # Fall back to title + content hash
        data = f"{title or ''}{content or ''}{datetime.utcnow().isoformat()}"
        return hashlib.sha256(data.encode()).hexdigest()[:16]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        def serialize(obj):
            if isinstance(obj, datetime):
                return obj.isoformat()
            elif isinstance(obj, Enum):
                return obj.value
            return obj

        result = {}
        for key, value in self.__dict__.items():
            if isinstance(value, list):
                result[key] = [serialize(v) for v in value]
            elif isinstance(value, dict):
                result[key] = {k: serialize(v) for k, v in value.items()}
            else:
                result[key] = serialize(value)
        return result

    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), indent=2, ensure_ascii=False)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ContentItem":
        """Create ContentItem from dictionary."""
        # Convert string enums back
        if "content_type" in data and isinstance(data["content_type"], str):
            data["content_type"] = ContentType(data["content_type"])
        if "source_type" in data and isinstance(data["source_type"], str):
            data["source_type"] = SourceType(data["source_type"])
        if "status" in data and isinstance(data["status"], str):
            data["status"] = ProcessingStatus(data["status"])

        # Convert datetime strings
        for field_name in ["created_at", "updated_at", "published_at", "ingested_at"]:
            if field_name in data and isinstance(data[field_name], str):
                try:
                    data[field_name] = datetime.fromisoformat(data[field_name])
                except (ValueError, TypeError):
                    data[field_name] = None

        # Handle missing fields gracefully
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})

    @classmethod
    def from_json(cls, json_str: str) -> "ContentItem":
        """Create ContentItem from JSON string."""
        return cls.from_dict(json.loads(json_str))

    def is_duplicate_of(self, other: "ContentItem") -> bool:
        """Check if this item is a duplicate of another."""
        # Same URL is definitely duplicate
        if self.source_url and other.source_url:
            return self.source_url == other.source_url

        # Same content_id
        if self.content_id == other.content_id:
            return True

        return False

    def get_storage_path(self, base_dir: str = "data/content") -> str:
        """
        Get the storage directory path for this content item.

        Structure: {base_dir}/{content_type}/{date}/{content_id}/
        """
        date_str = self.created_at.strftime("%Y/%m/%d")
        return f"{base_dir}/{self.content_type.value}/{date_str}/{self.content_id}"
