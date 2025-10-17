#!/usr/bin/env python3
"""
Semantic Content Quality Evaluator

Uses actual content analysis to determine quality, not just character count.
Designed to be integrated into the ingestion pipeline.
"""

import re
import nltk
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from collections import Counter
import math

# Download required NLTK data if not present
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    print("Downloading NLTK punkt tokenizer...")
    nltk.download('punkt', quiet=True)

try:
    nltk.data.find('corpora/stopwords')
except LookupError:
    print("Downloading NLTK stopwords...")
    nltk.download('stopwords', quiet=True)

from nltk.tokenize import sent_tokenize, word_tokenize
from nltk.corpus import stopwords


@dataclass
class ContentQualityResult:
    """Result of content quality analysis."""
    overall_score: float  # 0.0-1.0
    dimensions: Dict[str, float]  # Individual quality dimensions
    issues: List[str]  # Specific problems found
    recommendations: List[str]  # How to improve/reprocess
    is_reprocessable: bool  # Can this be improved by reprocessing?
    confidence: float  # How confident we are in this assessment


class SemanticContentEvaluator:
    """Evaluates content quality using semantic and structural analysis."""

    def __init__(self):
        self.stop_words = set(stopwords.words('english'))
        self.error_patterns = [
            # Web errors
            r'404.*not found',
            r'access denied',
            r'subscription required',
            r'please enable javascript',
            r'wayback machine.*javascript',
            r'this page requires',
            r'error.*occurred',

            # Content extraction failures
            r'^<[^>]+>.*<[^>]+>$',  # Mostly HTML tags
            r'<!DOCTYPE html',
            r'<html.*</html>',

            # Paywall/registration
            r'sign up.*continue',
            r'register.*full access',
            r'subscribe.*unlock',
        ]

    def evaluate_content(self,
                        content: str,
                        title: str = "",
                        url: str = "",
                        content_type: str = "",
                        expected_language: str = "english") -> ContentQualityResult:
        """
        Comprehensively evaluate content quality using multiple dimensions.
        """
        if not content or not content.strip():
            return ContentQualityResult(
                overall_score=0.0,
                dimensions={"content_exists": 0.0},
                issues=["empty_content"],
                recommendations=["Reprocess source to extract content"],
                is_reprocessable=True,
                confidence=1.0
            )

        # Analyze multiple quality dimensions
        dimensions = {}
        issues = []
        recommendations = []
        is_reprocessable = True

        # 1. Error Detection (binary - either it's an error or not)
        error_score, error_issues = self._detect_errors(content)
        dimensions["error_free"] = error_score
        issues.extend(error_issues)

        if error_score < 0.5:
            recommendations.append("Retry download with different method")
            is_reprocessable = True

        # 2. Language Quality (is this coherent text?)
        lang_score, lang_issues = self._analyze_language_quality(content)
        dimensions["language_quality"] = lang_score
        issues.extend(lang_issues)

        # 3. Content Structure (proper article/document structure)
        structure_score, structure_issues = self._analyze_structure(content, content_type)
        dimensions["structure"] = structure_score
        issues.extend(structure_issues)

        # Special case: podcast feed pages are automatically failed
        if "podcast_feed_page" in structure_issues:
            return ContentQualityResult(
                overall_score=0.1,
                dimensions={"structure": 0.1, "error_free": 0.1},
                issues=["podcast_feed_page"],
                recommendations=["Find actual transcript source", "Try alternative podcast archive"],
                is_reprocessable=True,
                confidence=0.9
            )

        # 4. Content Completeness (does it seem cut off or incomplete?)
        completeness_score, completeness_issues = self._analyze_completeness(content)
        dimensions["completeness"] = completeness_score
        issues.extend(completeness_issues)

        # 5. Topic Relevance (does content match title?)
        if title:
            relevance_score, relevance_issues = self._analyze_topic_relevance(content, title)
            dimensions["topic_relevance"] = relevance_score
            issues.extend(relevance_issues)
        else:
            dimensions["topic_relevance"] = 0.7  # Neutral if no title

        # 6. Information Density (meaningful content vs fluff)
        density_score, density_issues = self._analyze_information_density(content)
        dimensions["information_density"] = density_score
        issues.extend(density_issues)

        # Calculate overall score (weighted average)
        weights = {
            "error_free": 0.3,          # Critical - errors make content unusable
            "language_quality": 0.25,   # Very important - must be readable
            "structure": 0.15,          # Structure indicates quality
            "completeness": 0.15,       # Incomplete content is frustrating
            "topic_relevance": 0.10,    # Should match what user expects
            "information_density": 0.05 # Nice to have but not critical
        }

        overall_score = sum(dimensions[dim] * weights[dim] for dim in weights if dim in dimensions)

        # Adjust reprocessability based on error type
        if any("wayback" in issue for issue in issues):
            recommendations.append("Try alternative archive source")
        if any("paywall" in issue for issue in issues):
            recommendations.append("Try reader mode or alternative source")
            is_reprocessable = False  # Paywalls can't be easily bypassed

        # Confidence based on how clear the signals are
        confidence = min(1.0, len(issues) * 0.1 + 0.6)

        return ContentQualityResult(
            overall_score=overall_score,
            dimensions=dimensions,
            issues=list(set(issues)),  # Remove duplicates
            recommendations=list(set(recommendations)),
            is_reprocessable=is_reprocessable,
            confidence=confidence
        )

    def _detect_errors(self, content: str) -> Tuple[float, List[str]]:
        """Detect error messages and broken content."""
        issues = []
        content_lower = content.lower()

        for pattern in self.error_patterns:
            if re.search(pattern, content_lower):
                if "404" in pattern:
                    issues.append("404_error")
                elif "wayback" in pattern:
                    issues.append("wayback_error")
                elif "javascript" in pattern:
                    issues.append("javascript_required")
                elif "subscription" in pattern or "paywall" in pattern:
                    issues.append("paywall")
                else:
                    issues.append("extraction_error")

        # Check for HTML-heavy content (extraction failure)
        html_tags = len(re.findall(r'<[^>]+>', content))
        text_chars = len(re.sub(r'<[^>]*>', '', content).strip())

        if html_tags > 0 and text_chars > 0:
            html_ratio = html_tags / (text_chars + html_tags)
            if html_ratio > 0.3:  # More than 30% HTML tags
                issues.append("html_heavy")

        score = 1.0 if not issues else 0.1
        return score, issues

    def _analyze_language_quality(self, content: str) -> Tuple[float, List[str]]:
        """Analyze if content consists of coherent language."""
        issues = []

        try:
            # Basic sentence analysis
            sentences = sent_tokenize(content)
            if len(sentences) < 2:
                issues.append("insufficient_sentences")
                return 0.3, issues

            # Word analysis
            words = word_tokenize(content.lower())
            meaningful_words = [w for w in words if w.isalpha() and w not in self.stop_words]

            if len(meaningful_words) < 50:
                issues.append("insufficient_vocabulary")

            # Sentence length analysis
            sentence_lengths = [len(word_tokenize(s)) for s in sentences]
            avg_sentence_length = sum(sentence_lengths) / len(sentence_lengths)

            # Very short or very long sentences indicate problems
            if avg_sentence_length < 3:
                issues.append("sentences_too_short")
            elif avg_sentence_length > 50:
                issues.append("sentences_too_long")

            # Vocabulary diversity (simple measure)
            unique_words = set(meaningful_words)
            if len(meaningful_words) > 0:
                diversity = len(unique_words) / len(meaningful_words)
                if diversity < 0.3:  # Very repetitive
                    issues.append("low_vocabulary_diversity")

            # Overall language quality score
            base_score = 0.8
            base_score -= len(issues) * 0.15
            return max(0.1, base_score), issues

        except Exception as e:
            issues.append("language_analysis_failed")
            return 0.5, issues

    def _analyze_structure(self, content: str, content_type: str) -> Tuple[float, List[str]]:
        """Analyze content structure quality."""
        issues = []

        # Different expectations for different content types
        if content_type == "podcast":
            return self._analyze_podcast_structure(content)
        else:
            return self._analyze_article_structure(content)

    def _analyze_podcast_structure(self, content: str) -> Tuple[float, List[str]]:
        """Analyze podcast transcript structure."""
        issues = []

        # Look for transcript indicators
        transcript_indicators = [
            "transcript", "speaker", "host", "guest",
            "audio", "podcast", "episode"
        ]

        content_lower = content.lower()
        indicator_count = sum(1 for indicator in transcript_indicators if indicator in content_lower)

        # Check for feed page indicators (bad)
        feed_indicators = [
            "listen to the episode", "subscribe", "view all episodes",
            "episode →", "leave us a review"
        ]

        feed_count = sum(1 for indicator in feed_indicators if indicator in content_lower)

        if feed_count >= 2:  # More strict detection
            issues.append("podcast_feed_page")
            return 0.1, issues

        if indicator_count < 2:
            issues.append("not_transcript_format")

        # Look for speaker patterns
        speaker_patterns = re.findall(r'^[A-Z][a-z]+\s*:', content, re.MULTILINE)
        if len(speaker_patterns) < 5 and len(content) > 1000:
            issues.append("no_speaker_structure")

        base_score = 0.7
        base_score -= len(issues) * 0.2
        return max(0.1, base_score), issues

    def _analyze_article_structure(self, content: str) -> Tuple[float, List[str]]:
        """Analyze article structure quality."""
        issues = []

        # Paragraph analysis
        paragraphs = [p.strip() for p in content.split('\n\n') if p.strip()]

        if len(paragraphs) < 3:
            issues.append("insufficient_paragraphs")

        # Check for proper article elements
        has_intro = len(paragraphs) > 0 and len(paragraphs[0]) > 100
        has_body = len(paragraphs) > 2

        if not has_intro:
            issues.append("weak_introduction")
        if not has_body:
            issues.append("insufficient_body")

        base_score = 0.7
        base_score -= len(issues) * 0.15
        return max(0.1, base_score), issues

    def _analyze_completeness(self, content: str) -> Tuple[float, List[str]]:
        """Check if content appears complete."""
        issues = []

        # Look for truncation indicators
        truncation_patterns = [
            r'\.\.\.+$',
            r'continue reading',
            r'read more',
            r'this article continues',
            r'\[truncated\]',
            r'\[cut off\]'
        ]

        content_lower = content.lower()
        for pattern in truncation_patterns:
            if re.search(pattern, content_lower):
                issues.append("content_truncated")
                break

        # Check if it ends abruptly (no proper ending)
        last_sentences = content.strip()[-200:]  # Last 200 chars
        if not re.search(r'[.!?]\s*$', last_sentences):
            issues.append("abrupt_ending")

        base_score = 0.8
        base_score -= len(issues) * 0.3
        return max(0.1, base_score), issues

    def _analyze_topic_relevance(self, content: str, title: str) -> Tuple[float, List[str]]:
        """Check if content matches the expected topic from title."""
        issues = []

        try:
            # Extract key terms from title
            title_words = set(word_tokenize(title.lower()))
            title_meaningful = title_words - self.stop_words

            # Extract key terms from content
            content_words = set(word_tokenize(content.lower()))
            content_meaningful = content_words - self.stop_words

            if len(title_meaningful) > 0:
                # Calculate overlap
                overlap = len(title_meaningful & content_meaningful)
                relevance = overlap / len(title_meaningful)

                if relevance < 0.2:
                    issues.append("topic_mismatch")

                return max(0.1, relevance), issues
            else:
                return 0.7, issues  # Neutral if can't analyze title

        except Exception:
            issues.append("relevance_analysis_failed")
            return 0.5, issues

    def _analyze_information_density(self, content: str) -> Tuple[float, List[str]]:
        """Measure how much useful information vs fluff."""
        issues = []

        try:
            words = word_tokenize(content.lower())
            meaningful_words = [w for w in words if w.isalpha() and w not in self.stop_words]

            if len(words) == 0:
                return 0.0, ["no_content"]

            # Information density = meaningful words / total words
            density = len(meaningful_words) / len(words)

            if density < 0.3:
                issues.append("low_information_density")

            return density, issues

        except Exception:
            issues.append("density_analysis_failed")
            return 0.5, issues


# Integration function for existing content
def evaluate_content_batch(batch_size: int = 50) -> None:
    """Evaluate content quality for all items in database."""
    import sqlite3

    evaluator = SemanticContentEvaluator()
    conn = sqlite3.connect('atlas.db')
    cursor = conn.cursor()

    print("🔍 Running semantic content quality evaluation...")

    # Get all content
    cursor.execute("SELECT id, title, content, url, content_type FROM content WHERE content IS NOT NULL LIMIT ?", (batch_size,))
    items = cursor.fetchall()

    updates = []
    for item_id, title, content, url, content_type in items:
        result = evaluator.evaluate_content(
            content=content or "",
            title=title or "",
            url=url or "",
            content_type=content_type or ""
        )

        updates.append((
            result.overall_score,
            ",".join(result.issues),
            item_id
        ))

    # Update database
    cursor.executemany(
        "UPDATE content SET quality_score = ?, quality_issues = ? WHERE id = ?",
        updates
    )

    conn.commit()
    conn.close()

    print(f"✅ Updated quality scores for {len(updates)} items")


if __name__ == "__main__":
    # Test with a sample
    evaluator = SemanticContentEvaluator()

    # Test error content
    error_content = "The Wayback Machine requires your browser to support JavaScript, please email info@archive.org if you have any questions."
    result = evaluator.evaluate_content(error_content, "Sample Article", "http://example.com")

    print("🧪 Sample Error Content Analysis:")
    print(f"Score: {result.overall_score:.2f}")
    print(f"Issues: {result.issues}")
    print(f"Reprocessable: {result.is_reprocessable}")
    print(f"Recommendations: {result.recommendations}")

    print(f"\n📊 Dimensions:")
    for dim, score in result.dimensions.items():
        print(f"  {dim}: {score:.2f}")