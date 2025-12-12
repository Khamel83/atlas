"""
Approval Engine - Rule-based approval workflow for extracted links.

Reads rules from config/link_approval_rules.yml and applies them to pending links.
"""

import sqlite3
import logging
import yaml
from pathlib import Path
from typing import List, Dict, Tuple, Optional

from modules.links.models import (
    Link, LinkStatus, ApprovalResult, ApprovalRules
)

logger = logging.getLogger(__name__)

DEFAULT_CONFIG_PATH = Path('config/link_approval_rules.yml')
DEFAULT_DB_PATH = Path('data/enrich/link_queue.db')


class ApprovalEngine:
    """Apply approval rules to pending links."""

    def __init__(
        self,
        config_path: Path = DEFAULT_CONFIG_PATH,
        db_path: Path = DEFAULT_DB_PATH
    ):
        self.config_path = config_path
        self.db_path = db_path
        self.rules = self._load_rules()

    def _load_rules(self) -> ApprovalRules:
        """Load approval rules from YAML config."""
        if not self.config_path.exists():
            logger.warning(f"Config not found: {self.config_path}, using defaults")
            return ApprovalRules()

        with open(self.config_path) as f:
            data = yaml.safe_load(f)

        return ApprovalRules.from_dict(data)

    def reload_rules(self):
        """Reload rules from config file."""
        self.rules = self._load_rules()

    def evaluate_link(self, link: Dict) -> Tuple[LinkStatus, str, str]:
        """
        Evaluate a single link against approval rules.

        Returns: (new_status, rule_applied, reason)
        """
        url = link['url']
        domain = link['domain']
        score = link.get('score', 0.0)

        # Check blocked domains first (highest priority)
        if domain in self.rules.blocked_domains:
            return LinkStatus.REJECTED, 'blocked_domain', f'Domain {domain} is blocked'

        # Check trusted domains (auto-approve regardless of score)
        if domain in self.rules.trusted_domains:
            return LinkStatus.APPROVED, 'trusted_domain', f'Domain {domain} is trusted'

        # Check score thresholds
        if score >= self.rules.score_threshold:
            return LinkStatus.APPROVED, 'score_threshold', f'Score {score:.2f} >= {self.rules.score_threshold}'

        if score < self.rules.reject_threshold:
            return LinkStatus.REJECTED, 'low_score', f'Score {score:.2f} < {self.rules.reject_threshold}'

        # Middle ground - stays pending for now (no review queue initially)
        return LinkStatus.PENDING, 'no_match', f'Score {score:.2f} between thresholds'

    def get_pending_links(self, limit: int = 1000) -> List[Dict]:
        """Get pending links from database."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.execute("""
            SELECT id, url, domain, score, category, source_type
            FROM extracted_links
            WHERE status = 'pending'
            ORDER BY score DESC
            LIMIT ?
        """, (limit,))
        results = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return results

    def apply_approval(
        self,
        link_id: int,
        new_status: LinkStatus,
        rule: str
    ):
        """Update link status in database."""
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            UPDATE extracted_links
            SET status = ?, approval_rule = ?, reviewed_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (new_status.value, rule, link_id))
        conn.commit()
        conn.close()

    def run(self, dry_run: bool = False, limit: int = 10000) -> Dict:
        """
        Run approval workflow on all pending links.

        Args:
            dry_run: If True, don't update database
            limit: Maximum links to process

        Returns:
            Statistics dictionary
        """
        stats = {
            'processed': 0,
            'approved': 0,
            'rejected': 0,
            'unchanged': 0,
            'by_rule': {},
        }

        pending = self.get_pending_links(limit)
        logger.info(f"Processing {len(pending)} pending links")

        for link in pending:
            new_status, rule, reason = self.evaluate_link(link)
            stats['processed'] += 1

            if new_status == LinkStatus.APPROVED:
                stats['approved'] += 1
            elif new_status == LinkStatus.REJECTED:
                stats['rejected'] += 1
            else:
                stats['unchanged'] += 1

            # Track by rule
            stats['by_rule'][rule] = stats['by_rule'].get(rule, 0) + 1

            if not dry_run and new_status != LinkStatus.PENDING:
                self.apply_approval(link['id'], new_status, rule)

        return stats

    def get_stats(self) -> Dict:
        """Get current approval statistics."""
        conn = sqlite3.connect(self.db_path)

        stats = {}

        # By status
        cursor = conn.execute("""
            SELECT status, COUNT(*) FROM extracted_links GROUP BY status
        """)
        stats['by_status'] = dict(cursor.fetchall())

        # By approval rule
        cursor = conn.execute("""
            SELECT approval_rule, COUNT(*) FROM extracted_links
            WHERE approval_rule IS NOT NULL
            GROUP BY approval_rule
        """)
        stats['by_rule'] = dict(cursor.fetchall())

        # Approved by domain (top 20)
        cursor = conn.execute("""
            SELECT domain, COUNT(*) as cnt FROM extracted_links
            WHERE status = 'approved'
            GROUP BY domain ORDER BY cnt DESC LIMIT 20
        """)
        stats['approved_domains'] = dict(cursor.fetchall())

        conn.close()
        return stats


def approve_links(dry_run: bool = False, limit: int = 10000) -> Tuple[int, int]:
    """
    Convenience function to run approval workflow.

    Returns: (approved_count, rejected_count)
    """
    engine = ApprovalEngine()
    stats = engine.run(dry_run=dry_run, limit=limit)
    return stats['approved'], stats['rejected']
