"""
Data models for the link pipeline.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any


class LinkSource(Enum):
    """Source type for extracted links."""
    TRANSCRIPT = 'transcript'
    SHOWNOTES = 'shownotes'
    ARTICLE = 'article'
    NEWSLETTER = 'newsletter'
    MANUAL = 'manual'
    UNKNOWN = 'unknown'


class LinkStatus(Enum):
    """Status of a link in the pipeline."""
    PENDING = 'pending'       # Newly extracted, awaiting approval
    APPROVED = 'approved'     # Passed approval rules
    REJECTED = 'rejected'     # Failed approval rules
    INGESTED = 'ingested'     # Written to url_queue.txt
    FETCHED = 'fetched'       # Content successfully retrieved
    FAILED = 'failed'         # Fetch failed


class LinkCategory(Enum):
    """Category of link content."""
    ARTICLE = 'article'
    RESEARCH = 'research'
    AD = 'ad'
    NAVIGATION = 'navigation'
    SOCIAL = 'social'
    UNKNOWN = 'unknown'


@dataclass
class Link:
    """A link extracted from content."""
    url: str
    domain: str
    score: float
    category: LinkCategory
    source_content_id: str
    source_path: str
    source_type: LinkSource
    anchor_text: str = ''
    surrounding_context: str = ''
    status: LinkStatus = LinkStatus.PENDING
    approval_rule: Optional[str] = None
    extracted_at: Optional[datetime] = None
    id: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for database storage."""
        return {
            'url': self.url,
            'domain': self.domain,
            'score': self.score,
            'category': self.category.value,
            'source_content_id': self.source_content_id,
            'source_path': self.source_path,
            'source_type': self.source_type.value,
            'anchor_text': self.anchor_text,
            'surrounding_context': self.surrounding_context,
            'status': self.status.value,
            'approval_rule': self.approval_rule,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Link':
        """Create from dictionary (database row)."""
        return cls(
            id=data.get('id'),
            url=data['url'],
            domain=data['domain'],
            score=data.get('score', 0.5),
            category=LinkCategory(data.get('category', 'unknown')),
            source_content_id=data.get('source_content_id', ''),
            source_path=data.get('source_path', ''),
            source_type=LinkSource(data.get('source_type', 'unknown')),
            anchor_text=data.get('anchor_text', ''),
            surrounding_context=data.get('surrounding_context', ''),
            status=LinkStatus(data.get('status', 'pending')),
            approval_rule=data.get('approval_rule'),
            extracted_at=data.get('extracted_at'),
        )


@dataclass
class ApprovalResult:
    """Result of running approval on a link."""
    link_id: int
    url: str
    old_status: LinkStatus
    new_status: LinkStatus
    rule_applied: str
    reason: str

    @property
    def changed(self) -> bool:
        return self.old_status != self.new_status


@dataclass
class ApprovalRules:
    """Configuration for link approval."""
    trusted_domains: set = field(default_factory=set)
    blocked_domains: set = field(default_factory=set)
    score_threshold: float = 0.85
    reject_threshold: float = 0.40
    drip_urls_per_run: int = 50
    drip_delay_seconds: int = 10

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ApprovalRules':
        """Create from YAML config dictionary."""
        return cls(
            trusted_domains=set(data.get('trusted_domains', [])),
            blocked_domains=set(data.get('blocked_domains', [])),
            score_threshold=data.get('score_threshold', 0.85),
            reject_threshold=data.get('reject_threshold', 0.40),
            drip_urls_per_run=data.get('drip', {}).get('urls_per_run', 50),
            drip_delay_seconds=data.get('drip', {}).get('delay_seconds', 10),
        )


@dataclass
class PipelineStats:
    """Statistics for the link pipeline."""
    total_links: int = 0
    pending: int = 0
    approved: int = 0
    rejected: int = 0
    ingested: int = 0
    fetched: int = 0
    failed: int = 0
    by_source: Dict[str, int] = field(default_factory=dict)
    by_domain: Dict[str, int] = field(default_factory=dict)
