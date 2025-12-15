"""
Atlas Content Verifier - Unified quality checking for all content types.

Checks:
- File size (minimum 500 bytes)
- Word count (100 for articles, 500 for transcripts)
- Paywall patterns ("subscribe to continue", etc.)
- Soft-404 patterns ("page not found", etc.)
- JavaScript-blocked patterns ("enable javascript")
- Quality score (1-10 scale)
"""

import re
import json
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional, List, Dict, Any


class QualityLevel(Enum):
    """Quality classification levels."""
    GOOD = "good"           # Verified, high quality content
    MARGINAL = "marginal"   # Borderline, may need review
    BAD = "bad"             # Failed verification, needs action


@dataclass
class VerificationResult:
    """Result of content verification."""
    file_path: str
    quality: QualityLevel
    score: int  # 1-10 scale
    checks_passed: List[str] = field(default_factory=list)
    checks_failed: List[str] = field(default_factory=list)
    issues: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    verified_at: str = field(default_factory=lambda: datetime.now().isoformat())

    @property
    def is_good(self) -> bool:
        return self.quality == QualityLevel.GOOD

    def to_dict(self) -> dict:
        return {
            'file_path': self.file_path,
            'quality': self.quality.value,
            'score': self.score,
            'checks_passed': self.checks_passed,
            'checks_failed': self.checks_failed,
            'issues': self.issues,
            'metadata': self.metadata,
            'verified_at': self.verified_at,
        }


# Detection patterns
PAYWALL_PATTERNS = [
    r"subscribe\s+to\s+(continue|read|access)",
    r"sign\s+in\s+to\s+(continue|read|access)",
    r"create\s+(a\s+)?free\s+account",
    r"this\s+(content|article)\s+is\s+(for\s+)?(subscribers|members)\s+only",
    r"to\s+read\s+the\s+full\s+(article|story)",
    r"premium\s+(content|article|subscriber)",
    r"unlock\s+this\s+(article|story|content)",
    r"become\s+a\s+(member|subscriber)",
    r"get\s+unlimited\s+access",
    r"already\s+a\s+subscriber\?\s*sign\s+in",
    r"register\s+to\s+continue\s+reading",
    r"free\s+trial",
    r"start\s+your\s+subscription",
]

SOFT_404_PATTERNS = [
    r"page\s*(not\s*found|doesn't\s*exist|could\s*not\s*be\s*found)",
    r"(404|not\s*found)\s*error",
    r"(this\s*)?(page|article|content)\s*(has\s*been\s*)?(deleted|removed|expired)",
    r"no\s*longer\s*available",
    r"content\s*unavailable",
    r"we\s*couldn't\s*find\s*(that|the)\s*page",
    r"sorry,?\s*we\s*can('|no)t\s*find",
    r"the\s*requested\s*(url|page|resource)\s*was\s*not\s*found",
    r"oops[!,]?\s*(page|that)?\s*not\s*found",
    r"this\s*link\s*(may\s*be\s*)?(broken|expired)",
]

JS_BLOCKED_PATTERNS = [
    r"(please\s+)?enable\s+javascript",
    r"javascript\s+(is\s+)?(required|must\s+be\s+enabled)",
    r"this\s+(page|site)\s+requires\s+javascript",
    r"you\s+need\s+to\s+enable\s+javascript",
    r"browser\s+doesn't\s+support\s+javascript",
    r"noscript",
]

# Transcript quality indicators
TRANSCRIPT_INDICATORS = [
    "transcript", "speaker", "host", "guest",
    "[music]", "[applause]", "[laughter]",
    "welcome to", "today we", "our guest",
    "let me", "i think", "you know",
    "episode", "podcast", "show",
]


class ContentVerifier:
    """Unified content quality verification system."""

    def __init__(self, db_path: str = "data/quality/verification.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        """Initialize SQLite database for tracking."""
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS verifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_path TEXT UNIQUE,
                content_type TEXT,
                quality TEXT,
                score INTEGER,
                file_size INTEGER,
                word_count INTEGER,
                checks_passed TEXT,
                checks_failed TEXT,
                issues TEXT,
                verified_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_quality ON verifications(quality)
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_content_type ON verifications(content_type)
        """)
        conn.commit()
        conn.close()

    def verify_file(self, file_path: str | Path, content_type: str = "auto") -> VerificationResult:
        """
        Verify a single content file.

        Args:
            file_path: Path to the content file
            content_type: One of 'article', 'transcript', 'newsletter', 'auto'

        Returns:
            VerificationResult with quality assessment
        """
        file_path = Path(file_path)

        if not file_path.exists():
            return VerificationResult(
                file_path=str(file_path),
                quality=QualityLevel.BAD,
                score=0,
                checks_failed=["file_exists"],
                issues=["File does not exist"],
            )

        try:
            content = file_path.read_text(encoding='utf-8', errors='ignore')
        except Exception as e:
            return VerificationResult(
                file_path=str(file_path),
                quality=QualityLevel.BAD,
                score=0,
                checks_failed=["readable"],
                issues=[f"Cannot read file: {e}"],
            )

        # Auto-detect content type
        if content_type == "auto":
            content_type = self._detect_content_type(file_path, content)

        # Skip verification for notes - user-curated content
        if content_type == "note" or '/note/' in str(file_path):
            return VerificationResult(
                file_path=str(file_path),
                quality=QualityLevel.GOOD,
                score=10,
                checks_passed=["note_exempt"],
                checks_failed=[],
                issues=[],
                metadata={"content_type": "note", "verification_skipped": True},
            )

        return self._verify_content(str(file_path), content, content_type)

    def _detect_content_type(self, file_path: Path, content: str) -> str:
        """Detect content type from path and content."""
        path_str = str(file_path).lower()

        if '/podcasts/' in path_str or '/transcripts/' in path_str:
            return 'transcript'
        if '/newsletter/' in path_str:
            return 'newsletter'
        if '/article/' in path_str or '/articles/' in path_str:
            return 'article'
        if '/stratechery/' in path_str:
            # Stratechery can be either articles or podcasts
            if '/podcasts/' in path_str:
                return 'transcript'
            return 'article'

        # Content-based detection
        content_lower = content.lower()
        transcript_score = sum(1 for ind in TRANSCRIPT_INDICATORS if ind in content_lower)
        if transcript_score >= 3:
            return 'transcript'

        return 'article'

    def _verify_content(self, file_path: str, content: str, content_type: str) -> VerificationResult:
        """Run all verification checks on content."""
        checks_passed = []
        checks_failed = []
        issues = []
        score = 0

        file_size = len(content.encode('utf-8'))
        words = content.split()
        word_count = len(words)
        paragraphs = [p for p in content.split('\n\n') if p.strip()]
        paragraph_count = len(paragraphs)

        metadata = {
            'file_size': file_size,
            'word_count': word_count,
            'paragraph_count': paragraph_count,
            'content_type': content_type,
        }

        # Check 1: File size (minimum 500 bytes)
        if file_size >= 500:
            checks_passed.append("min_size")
            score += 1
        else:
            checks_failed.append("min_size")
            issues.append(f"Too small: {file_size} bytes (min 500)")

        # Check 2: Word count (type-specific)
        min_words = 500 if content_type == 'transcript' else 100
        if word_count >= min_words:
            checks_passed.append("min_words")
            score += 2
        else:
            checks_failed.append("min_words")
            issues.append(f"Too few words: {word_count} (min {min_words})")

        # Check 3: Paywall patterns (with smart false-positive prevention)
        content_lower = content.lower()
        paywall_passed = True

        # Files > 5000 words are clearly not paywalled - real paywalls show very little content
        if word_count > 5000:
            paywall_passed = True
        else:
            # Only check first/last 1000 chars where paywalls actually appear
            check_region = content_lower[:1000] + content_lower[-1000:]
            paywall_matches = []
            for pattern in PAYWALL_PATTERNS:
                if re.search(pattern, check_region):
                    paywall_matches.append(pattern)

            # Require 2+ different patterns to flag (single match is likely false positive)
            if len(paywall_matches) >= 2:
                paywall_passed = False
                metadata['paywall_patterns'] = paywall_matches[:3]

        if paywall_passed:
            checks_passed.append("no_paywall")
            score += 2
        else:
            checks_failed.append("no_paywall")
            issues.append(f"Paywall detected: {len(paywall_matches)} patterns in header/footer")

        # Check 4: Soft-404 patterns (with smart false-positive prevention)
        soft404_passed = True

        # Files > 5000 words are clearly not 404 pages
        if word_count > 5000:
            soft404_passed = True
        else:
            # Only check first/last 1000 chars where 404 messages appear
            check_region = content_lower[:1000] + content_lower[-1000:]
            soft404_matches = []
            for pattern in SOFT_404_PATTERNS:
                if re.search(pattern, check_region):
                    soft404_matches.append(pattern)

            # Require 2+ patterns OR very short content with 1 pattern
            if len(soft404_matches) >= 2 or (len(soft404_matches) >= 1 and word_count < 200):
                soft404_passed = False
                metadata['soft_404_patterns'] = soft404_matches[:3]

        if soft404_passed:
            checks_passed.append("no_soft_404")
            score += 2
        else:
            checks_failed.append("no_soft_404")
            issues.append(f"Soft-404 detected: {len(soft404_matches)} patterns")

        # Check 5: JavaScript blocked patterns (with smart false-positive prevention)
        js_passed = True

        # Files > 5000 words are clearly not JS-blocked - real blocked pages show nothing
        if word_count > 5000:
            js_passed = True
        else:
            # Only check first/last 1000 chars where JS warnings typically appear
            check_region = content_lower[:1000] + content_lower[-1000:]
            js_matches = []
            for pattern in JS_BLOCKED_PATTERNS:
                if re.search(pattern, check_region):
                    js_matches.append(pattern)

            # Require match in header/footer region for short content
            if js_matches:
                js_passed = False
                metadata['js_patterns'] = js_matches[:3]

        if js_passed:
            checks_passed.append("no_js_block")
            score += 1
        else:
            checks_failed.append("no_js_block")
            issues.append(f"JS-blocked content detected")

        # Check 6: Has actual paragraphs (with smart threshold)
        # Files with 300+ words don't need 3 paragraphs - single-block content is valid
        min_paragraphs = 3 if word_count < 300 else 1
        if paragraph_count >= min_paragraphs:
            checks_passed.append("has_paragraphs")
            score += 1
        else:
            checks_failed.append("has_paragraphs")
            issues.append(f"Too few paragraphs: {paragraph_count}")

        # Check 7: Transcript-specific - has dialogue indicators
        if content_type == 'transcript':
            transcript_score = sum(1 for ind in TRANSCRIPT_INDICATORS if ind in content_lower)
            if transcript_score >= 2:
                checks_passed.append("transcript_indicators")
                score += 1
            else:
                checks_failed.append("transcript_indicators")
                issues.append(f"Missing transcript indicators (found {transcript_score})")

        # Determine quality level
        max_score = 10
        pct = score / max_score

        if pct >= 0.7 and not checks_failed:
            quality = QualityLevel.GOOD
        elif pct >= 0.5 and 'no_paywall' in checks_passed and 'no_soft_404' in checks_passed:
            quality = QualityLevel.MARGINAL
        else:
            quality = QualityLevel.BAD

        # Critical failures override score
        if 'no_paywall' in checks_failed or 'no_soft_404' in checks_failed:
            quality = QualityLevel.BAD
        if file_size < 200:
            quality = QualityLevel.BAD

        return VerificationResult(
            file_path=file_path,
            quality=quality,
            score=score,
            checks_passed=checks_passed,
            checks_failed=checks_failed,
            issues=issues,
            metadata=metadata,
        )

    def save_result(self, result: VerificationResult, content_type: str = "unknown"):
        """Save verification result to database."""
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            INSERT OR REPLACE INTO verifications
            (file_path, content_type, quality, score, file_size, word_count,
             checks_passed, checks_failed, issues, verified_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            result.file_path,
            content_type,
            result.quality.value,
            result.score,
            result.metadata.get('file_size', 0),
            result.metadata.get('word_count', 0),
            json.dumps(result.checks_passed),
            json.dumps(result.checks_failed),
            json.dumps(result.issues),
            result.verified_at,
        ))
        conn.commit()
        conn.close()

    def get_stats(self) -> Dict[str, Any]:
        """Get verification statistics from database."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row

        stats = {
            'total': 0,
            'by_quality': {},
            'by_type': {},
            'recent_failures': [],
        }

        # Total count
        row = conn.execute("SELECT COUNT(*) as cnt FROM verifications").fetchone()
        stats['total'] = row['cnt']

        # By quality
        for row in conn.execute("""
            SELECT quality, COUNT(*) as cnt FROM verifications GROUP BY quality
        """):
            stats['by_quality'][row['quality']] = row['cnt']

        # By content type
        for row in conn.execute("""
            SELECT content_type, quality, COUNT(*) as cnt
            FROM verifications GROUP BY content_type, quality
        """):
            if row['content_type'] not in stats['by_type']:
                stats['by_type'][row['content_type']] = {}
            stats['by_type'][row['content_type']][row['quality']] = row['cnt']

        # Recent failures
        for row in conn.execute("""
            SELECT file_path, quality, score, issues, verified_at
            FROM verifications
            WHERE quality = 'bad'
            ORDER BY verified_at DESC
            LIMIT 20
        """):
            stats['recent_failures'].append({
                'file_path': row['file_path'],
                'score': row['score'],
                'issues': json.loads(row['issues']),
                'verified_at': row['verified_at'],
            })

        conn.close()
        return stats

    def verify_directory(self, directory: Path, content_type: str = "auto",
                        pattern: str = "*.md") -> List[VerificationResult]:
        """Verify all files in a directory."""
        results = []
        for file_path in directory.rglob(pattern):
            if file_path.is_file():
                result = self.verify_file(file_path, content_type)
                self.save_result(result, result.metadata.get('content_type', content_type))
                results.append(result)
        return results


# Convenience functions
def verify_file(file_path: str | Path, content_type: str = "auto") -> VerificationResult:
    """Quick verification of a single file."""
    verifier = ContentVerifier()
    return verifier.verify_file(file_path, content_type)


def verify_content(content: str, content_type: str = "article") -> VerificationResult:
    """Verify content string (for use in pipelines before saving)."""
    verifier = ContentVerifier()
    return verifier._verify_content("<memory>", content, content_type)
