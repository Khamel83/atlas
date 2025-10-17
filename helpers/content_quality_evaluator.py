#!/usr/bin/env python3
"""
Content Quality Evaluator

Assesses content quality and identifies stubs, failed downloads, and low-quality content.
"""

import re
import sqlite3
from dataclasses import dataclass
from typing import List, Tuple, Dict, Any
from datetime import datetime


@dataclass
class QualityAssessment:
    """Content quality assessment result."""
    score: float  # 0.0 = garbage, 1.0 = excellent
    issues: List[str]  # List of quality issues found
    classification: str  # stub, failed, low_quality, good, excellent
    confidence: float  # How confident we are in this assessment


class ContentQualityEvaluator:
    """Evaluates content quality and identifies problematic content."""

    def __init__(self):
        self.db_path = "atlas.db"

    def evaluate_content(self, content: str, title: str = "", content_type: str = "", url: str = "") -> QualityAssessment:
        """Evaluate a single piece of content for quality."""
        issues = []
        score = 1.0  # Start optimistic

        # Basic content checks
        if not content or not content.strip():
            return QualityAssessment(0.0, ["empty_content"], "failed", 1.0)

        content_length = len(content.strip())

        # Length-based quality assessment
        if content_length < 100:
            issues.append("very_short")
            score -= 0.8
        elif content_length < 500:
            issues.append("short_content")
            score -= 0.4
        elif content_length < 1000:
            issues.append("minimal_content")
            score -= 0.2

        # Error pattern detection
        error_patterns = [
            (r"wayback machine.*javascript", "wayback_error", 0.9),
            (r"404.*not found", "404_error", 0.8),
            (r"access denied", "access_denied", 0.8),
            (r"please enable javascript", "javascript_required", 0.8),
            (r"subscription required", "paywall", 0.6),
            (r"sign up.*continue reading", "registration_wall", 0.6),
            (r"this page requires", "access_restriction", 0.7),
            (r"error.*occurred", "generic_error", 0.5),
        ]

        content_lower = content.lower()
        for pattern, issue_name, penalty in error_patterns:
            if re.search(pattern, content_lower):
                issues.append(issue_name)
                score -= penalty

        # Podcast-specific checks
        if content_type == "podcast":
            podcast_issues = self._evaluate_podcast_content(content)
            issues.extend(podcast_issues)
            if podcast_issues:
                score -= 0.6  # Fake transcripts are major issues

        # Article-specific checks
        elif content_type != "podcast":
            article_issues = self._evaluate_article_content(content)
            issues.extend(article_issues)
            if article_issues:
                score -= 0.3

        # Content structure quality
        structure_score = self._evaluate_content_structure(content)
        score *= structure_score

        # Determine classification
        score = max(0.0, min(1.0, score))  # Clamp to 0-1

        if score < 0.2:
            classification = "failed"
        elif score < 0.4:
            classification = "stub"
        elif score < 0.6:
            classification = "low_quality"
        elif score < 0.8:
            classification = "good"
        else:
            classification = "excellent"

        confidence = min(1.0, len(issues) * 0.2 + 0.6)  # More issues = more confident

        return QualityAssessment(score, issues, classification, confidence)

    def _evaluate_podcast_content(self, content: str) -> List[str]:
        """Check for fake podcast transcripts."""
        issues = []
        content_lower = content.lower()

        # Signs this is a podcast feed page, not transcript
        feed_indicators = [
            "listen to the episode",
            "subscribe",
            "leave us a review",
            "view all episodes",
            "episode →",
            "sign up to get updates",
            "by signing up, you agree",
            "aug. ", "july ", "june ",  # Date listings
        ]

        indicator_count = sum(1 for indicator in feed_indicators if indicator in content_lower)
        if indicator_count >= 3:
            issues.append("fake_transcript")

        # Very short "transcripts" are suspicious
        if len(content) < 2000:
            issues.append("short_transcript")

        return issues

    def _evaluate_article_content(self, content: str) -> List[str]:
        """Check article content quality."""
        issues = []

        # Look for signs of incomplete articles
        incomplete_indicators = [
            "continue reading",
            "read more",
            "...",
            "subscribe to continue",
            "this article is",
        ]

        content_lower = content.lower()
        for indicator in incomplete_indicators:
            if indicator in content_lower:
                issues.append("incomplete_article")
                break

        return issues

    def _evaluate_content_structure(self, content: str) -> float:
        """Evaluate content structure quality (0.0-1.0)."""
        score = 1.0

        # Check for reasonable paragraph structure
        paragraphs = [p.strip() for p in content.split('\n\n') if p.strip()]
        if len(paragraphs) < 2:
            score -= 0.2

        # Check for reasonable sentence structure
        sentences = re.split(r'[.!?]+', content)
        avg_sentence_length = sum(len(s.split()) for s in sentences) / len(sentences) if sentences else 0

        if avg_sentence_length < 5:  # Very short sentences
            score -= 0.1
        elif avg_sentence_length > 50:  # Very long sentences
            score -= 0.1

        return max(0.0, score)

    def evaluate_database_content(self, batch_size: int = 100) -> Dict[str, int]:
        """Evaluate all content in the database and update quality scores."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Get all content
        cursor.execute("SELECT id, title, content, content_type, url FROM content WHERE content IS NOT NULL")

        stats = {"total": 0, "failed": 0, "stub": 0, "low_quality": 0, "good": 0, "excellent": 0}

        batch = cursor.fetchmany(batch_size)
        while batch:
            updates = []

            for row in batch:
                content_id, title, content, content_type, url = row

                assessment = self.evaluate_content(
                    content or "",
                    title or "",
                    content_type or "",
                    url or ""
                )

                updates.append((
                    assessment.score,
                    ",".join(assessment.issues),
                    content_id
                ))

                stats["total"] += 1
                stats[assessment.classification] += 1

            # Bulk update quality scores
            cursor.executemany(
                "UPDATE content SET quality_score = ?, quality_issues = ? WHERE id = ?",
                updates
            )
            conn.commit()

            print(f"Processed {stats['total']} items...")
            batch = cursor.fetchmany(batch_size)

        conn.close()
        return stats

    def get_quality_summary(self) -> Dict[str, Any]:
        """Get summary of content quality in database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Overall stats
        cursor.execute("SELECT COUNT(*), AVG(quality_score) FROM content WHERE content IS NOT NULL")
        total_items, avg_score = cursor.fetchone()

        # Quality distribution
        cursor.execute("""
            SELECT
                CASE
                    WHEN quality_score < 0.2 THEN 'failed'
                    WHEN quality_score < 0.4 THEN 'stub'
                    WHEN quality_score < 0.6 THEN 'low_quality'
                    WHEN quality_score < 0.8 THEN 'good'
                    ELSE 'excellent'
                END as quality_class,
                COUNT(*) as count
            FROM content
            WHERE content IS NOT NULL AND quality_score IS NOT NULL
            GROUP BY quality_class
        """)

        quality_distribution = dict(cursor.fetchall())

        # Common issues
        cursor.execute("""
            SELECT quality_issues, COUNT(*) as count
            FROM content
            WHERE quality_issues IS NOT NULL AND quality_issues != ''
            GROUP BY quality_issues
            ORDER BY count DESC
            LIMIT 10
        """)

        common_issues = cursor.fetchall()

        conn.close()

        return {
            "total_items": total_items,
            "average_score": avg_score or 0,
            "quality_distribution": quality_distribution,
            "common_issues": common_issues,
            "summary": f"{total_items} items, avg score {avg_score:.2f}" if avg_score else "No quality data"
        }


if __name__ == "__main__":
    print("🔍 Atlas Content Quality Evaluator")
    print("=" * 50)

    evaluator = ContentQualityEvaluator()

    # Run evaluation
    print("Evaluating all content in database...")
    stats = evaluator.evaluate_database_content()

    print("\n📊 Quality Assessment Results:")
    for category, count in stats.items():
        if category != "total":
            percentage = (count / stats["total"]) * 100 if stats["total"] > 0 else 0
            print(f"   {category.title()}: {count:,} ({percentage:.1f}%)")

    # Show summary
    print("\n📈 Quality Summary:")
    summary = evaluator.get_quality_summary()
    print(f"   {summary['summary']}")

    print("\n🔍 Top Issues:")
    for issue, count in summary['common_issues'][:5]:
        print(f"   {issue}: {count}")

    print(f"\n✅ Quality evaluation complete!")