"""
Atlas Content Type Detection and Routing System
Smart detection of content types with confidence scoring
"""

import re
import urllib.parse
from typing import Dict, Optional
from dataclasses import dataclass


@dataclass
class ContentTypeResult:
    """Result of content type detection"""

    content_type: str
    confidence: float
    processor: str
    metadata: Dict
    reasoning: str


class SmartContentDetector:
    """Intelligent content type detection with confidence scoring"""

    def __init__(self):
        self.url_patterns = self._init_url_patterns()
        self.text_patterns = self._init_text_patterns()

    def _init_url_patterns(self) -> Dict:
        """Initialize URL pattern matchers for different content types"""
        return {
            "youtube_video": {
                "patterns": [
                    r"(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/)([a-zA-Z0-9_-]{11})",
                    r"youtube\.com\/live\/([a-zA-Z0-9_-]+)",
                    r"youtube\.com\/shorts\/([a-zA-Z0-9_-]+)",
                ],
                "confidence": 0.95,
                "processor": "youtube_ingestor",
                "metadata": {"platform": "youtube", "media_type": "video"},
            },
            "youtube_channel": {
                "patterns": [
                    r"youtube\.com\/channel\/([a-zA-Z0-9_-]+)",
                    r"youtube\.com\/c\/([a-zA-Z0-9_-]+)",
                    r"youtube\.com\/@([a-zA-Z0-9_-]+)",
                    r"youtube\.com\/user\/([a-zA-Z0-9_-]+)",
                ],
                "confidence": 0.90,
                "processor": "youtube_channel_ingestor",
                "metadata": {"platform": "youtube", "media_type": "channel"},
            },
            "podcast_episode": {
                "patterns": [
                    r"spotify\.com\/episode\/([a-zA-Z0-9]+)",
                    r"podcasts\.apple\.com\/.*\/podcast\/.*/id\d+\?i=\d+",
                    r"overcast\.fm\/\+[a-zA-Z0-9]+",
                    r"pocketcasts\.com\/episode\/([a-zA-Z0-9-]+)",
                    r"\.mp3$",
                    r"\.m4a$",
                    r"\.wav$",
                ],
                "confidence": 0.85,
                "processor": "podcast_transcript_ingestor",
                "metadata": {"media_type": "audio", "content_type": "podcast"},
            },
            "news_article": {
                "patterns": [
                    r"nytimes\.com\/\d{4}\/\d{2}\/\d{2}",
                    r"wsj\.com\/articles",
                    r"reuters\.com\/.*\/article",
                    r"bbc\.com\/news",
                    r"cnn\.com\/\d{4}\/\d{2}\/\d{2}",
                    r"washingtonpost\.com\/.*\/\d{4}\/\d{2}\/\d{2}",
                ],
                "confidence": 0.90,
                "processor": "enhanced_article_ingestor",
                "metadata": {"content_type": "news", "domain_type": "news_site"},
            },
            "academic_paper": {
                "patterns": [
                    r"arxiv\.org\/abs\/\d+\.\d+",
                    r"doi\.org\/10\.\d+",
                    r"pubmed\.ncbi\.nlm\.nih\.gov",
                    r"scholar\.google\.com",
                    r"researchgate\.net",
                    r"\.pdf$",
                ],
                "confidence": 0.85,
                "processor": "academic_paper_ingestor",
                "metadata": {"content_type": "academic", "format": "paper"},
            },
            "blog_post": {
                "patterns": [
                    r"medium\.com\/@",
                    r"substack\.com\/p\/",
                    r"wordpress\.com",
                    r"blogspot\.com",
                    r"ghost\.io",
                ],
                "confidence": 0.75,
                "processor": "blog_ingestor",
                "metadata": {"content_type": "blog", "platform": "blog"},
            },
            "social_media": {
                "patterns": [
                    r"twitter\.com\/.*\/status\/\d+",
                    r"x\.com\/.*\/status\/\d+",
                    r"linkedin\.com\/posts",
                    r"reddit\.com\/r\/.*\/comments",
                    r"facebook\.com\/.*\/posts",
                ],
                "confidence": 0.70,
                "processor": "social_media_ingestor",
                "metadata": {"content_type": "social", "platform": "social_media"},
            },
            "github_repo": {
                "patterns": [
                    r"github\.com\/[^\/]+\/[^\/]+(?:\/tree|\/blob|$)",
                    r"gitlab\.com\/[^\/]+\/[^\/]+",
                    r"bitbucket\.org\/[^\/]+\/[^\/]+",
                ],
                "confidence": 0.85,
                "processor": "code_repository_ingestor",
                "metadata": {"content_type": "code", "platform": "repository"},
            },
            "documentation": {
                "patterns": [
                    r"docs\.[^\/]+\.com",
                    r"[^\/]+\.readthedocs\.io",
                    r"developer\.[^\/]+\.com",
                    r"api\.[^\/]+\.com",
                    r"help\.[^\/]+\.com",
                ],
                "confidence": 0.80,
                "processor": "documentation_ingestor",
                "metadata": {"content_type": "documentation", "format": "docs"},
            },
        }

    def _init_text_patterns(self) -> Dict:
        """Initialize text content pattern matchers"""
        return {
            "code_snippet": {
                "patterns": [
                    r"```[\s\S]*?```",  # Code blocks
                    r"`[^`]+`",  # Inline code
                    r"def\s+\w+\s*\(",  # Python functions
                    r"function\s+\w+\s*\(",  # JavaScript functions
                    r"class\s+\w+\s*[:{]",  # Class definitions
                    r"import\s+[\w,\s]+\s+from",  # Import statements
                ],
                "confidence": 0.80,
                "processor": "code_snippet_processor",
                "metadata": {"content_type": "code", "format": "snippet"},
            },
            "academic_note": {
                "patterns": [
                    r"\b(?:doi|DOI):\s*10\.\d+",
                    r"\b(?:abstract|introduction|methodology|conclusion|references)\b",
                    r"\[[0-9]+\]",  # Citations
                    r"\bet\s+al\.",  # Academic citations
                    r"\b(?:p\s*=\s*0\.\d+|p\s*<\s*0\.\d+)",  # Statistical significance
                ],
                "confidence": 0.75,
                "processor": "academic_text_processor",
                "metadata": {"content_type": "academic", "format": "note"},
            },
            "meeting_notes": {
                "patterns": [
                    r"\b(?:action\s+items?|next\s+steps|follow\s+up)\b",
                    r"\b(?:attendees?|participants?)\b",
                    r"\b(?:agenda|meeting\s+notes?|minutes)\b",
                    r"\b\d{1,2}:\d{2}\s*(?:AM|PM|am|pm)\b",  # Time stamps
                    r"@\w+",  # @ mentions
                ],
                "confidence": 0.70,
                "processor": "meeting_notes_processor",
                "metadata": {"content_type": "meeting", "format": "notes"},
            },
            "recipe": {
                "patterns": [
                    r"\b(?:ingredients?|instructions?|directions?)\b",
                    r"\b\d+\s*(?:cups?|tbsp|tsp|lbs?|oz|grams?|ml)\b",
                    r"\b(?:preheat|bake|cook|simmer|boil|fry)\b",
                    r"\b\d+\s*(?:minutes?|mins?|hours?|hrs?)\b",
                    r"\b(?:servings?|prep\s+time|cook\s+time)\b",
                ],
                "confidence": 0.85,
                "processor": "recipe_processor",
                "metadata": {"content_type": "recipe", "format": "cooking"},
            },
            "journal_entry": {
                "patterns": [
                    r"\b(?:today|yesterday|tomorrow)\b",
                    r"\b(?:feeling|felt|feel)\b",
                    r"\b(?:grateful|thankful|blessed)\b",
                    r"\b(?:learned|realized|discovered)\b",
                    r"\bI\s+(?:am|was|will|have|had)\b",
                ],
                "confidence": 0.60,
                "processor": "journal_processor",
                "metadata": {"content_type": "journal", "format": "personal"},
            },
        }

    def detect_content_type(
        self, content: str, context: Optional[Dict] = None
    ) -> ContentTypeResult:
        """
        Detect content type with confidence scoring

        Args:
            content: The content to analyze (URL or text)
            context: Optional context (source_app, capture_context, etc.)

        Returns:
            ContentTypeResult with type, confidence, and routing info
        """

        # Determine if this is a URL or text content
        if self._is_url(content):
            return self._detect_url_type(content, context)
        else:
            return self._detect_text_type(content, context)

    def _is_url(self, content: str) -> bool:
        """Check if content is a URL"""
        try:
            parsed = urllib.parse.urlparse(content.strip())
            return bool(parsed.scheme and parsed.netloc)
        except:
            return False

    def _detect_url_type(
        self, url: str, context: Optional[Dict] = None
    ) -> ContentTypeResult:
        """Detect URL content type"""

        url_lower = url.lower()
        best_match = None
        best_confidence = 0.0

        # Check each URL pattern category
        for content_type, config in self.url_patterns.items():
            confidence = 0.0

            # Check if any pattern matches
            for pattern in config["patterns"]:
                if re.search(pattern, url_lower):
                    confidence = config["confidence"]

                    # Boost confidence based on context
                    if context:
                        confidence = self._apply_context_boost(
                            confidence, content_type, context
                        )

                    if confidence > best_confidence:
                        best_confidence = confidence
                        best_match = {
                            "content_type": content_type,
                            "confidence": confidence,
                            "processor": config["processor"],
                            "metadata": config["metadata"].copy(),
                            "reasoning": f"URL pattern match for {content_type}",
                        }
                    break

        # Fallback to generic URL processor
        if not best_match:
            return ContentTypeResult(
                content_type="generic_url",
                confidence=0.50,
                processor="article_ingestor",
                metadata={"content_type": "unknown", "format": "url"},
                reasoning="No specific URL pattern matched, using generic processor",
            )

        return ContentTypeResult(**best_match)

    def _detect_text_type(
        self, text: str, context: Optional[Dict] = None
    ) -> ContentTypeResult:
        """Detect text content type"""

        text_lower = text.lower()
        scores = {}

        # Score each text pattern category
        for content_type, config in self.text_patterns.items():
            score = 0
            matches = 0

            for pattern in config["patterns"]:
                pattern_matches = len(re.findall(pattern, text_lower, re.IGNORECASE))
                if pattern_matches > 0:
                    matches += 1
                    score += pattern_matches

            if matches > 0:
                # Calculate confidence based on matches and text length
                base_confidence = config["confidence"]
                match_ratio = matches / len(config["patterns"])
                length_factor = min(
                    len(text) / 1000, 1.0
                )  # Longer text = higher confidence

                final_confidence = (
                    base_confidence * match_ratio * (0.5 + 0.5 * length_factor)
                )

                # Apply context boost
                if context:
                    final_confidence = self._apply_context_boost(
                        final_confidence, content_type, context
                    )

                scores[content_type] = {
                    "confidence": final_confidence,
                    "processor": config["processor"],
                    "metadata": config["metadata"].copy(),
                    "reasoning": f"Text pattern analysis: {matches}/{len(config['patterns'])} patterns matched",
                }

        # Return best match or fallback
        if scores:
            best_type = max(scores.keys(), key=lambda x: scores[x]["confidence"])
            return ContentTypeResult(content_type=best_type, **scores[best_type])
        else:
            return ContentTypeResult(
                content_type="generic_text",
                confidence=0.30,
                processor="text_processor",
                metadata={"content_type": "unknown", "format": "text"},
                reasoning="No specific text patterns matched, using generic processor",
            )

    def _apply_context_boost(
        self, base_confidence: float, content_type: str, context: Dict
    ) -> float:
        """Apply confidence boost based on context clues"""

        boost = 0.0

        # Source app context boosts
        source_app = context.get("source_app", "").lower()
        if source_app:
            app_boosts = {
                "safari": {"news_article": 0.1, "blog_post": 0.1, "documentation": 0.1},
                "youtube": {"youtube_video": 0.15, "youtube_channel": 0.15},
                "spotify": {"podcast_episode": 0.15},
                "notes": {"journal_entry": 0.1, "meeting_notes": 0.1},
                "github": {"github_repo": 0.15, "code_snippet": 0.1},
                "xcode": {"code_snippet": 0.15, "documentation": 0.1},
            }

            if source_app in app_boosts and content_type in app_boosts[source_app]:
                boost += app_boosts[source_app][content_type]

        # Capture context boosts
        capture_context = context.get("capture_context", "").lower()
        if capture_context:
            context_boosts = {
                "share_extension": 0.05,  # Deliberate sharing usually means higher confidence
                "siri": 0.02,  # Voice capture might be less precise
                "manual": 0.08,  # Manual capture shows intent
                "automation": 0.03,  # Automated capture is less certain
            }

            if capture_context in context_boosts:
                boost += context_boosts[capture_context]

        # Cap the boost and ensure we don't exceed 1.0
        boost = min(boost, 0.20)
        return min(base_confidence + boost, 1.0)

    def get_processing_recommendations(
        self, detection_result: ContentTypeResult
    ) -> Dict:
        """Get processing recommendations based on detection result"""

        recommendations = {
            "processor": detection_result.processor,
            "priority": self._calculate_priority(detection_result),
            "preprocessing": [],
            "postprocessing": [],
            "metadata_extraction": [],
        }

        # Add specific recommendations based on content type
        if detection_result.content_type in ["youtube_video", "podcast_episode"]:
            recommendations["preprocessing"].append("extract_audio_metadata")
            recommendations["preprocessing"].append("check_transcript_availability")
            recommendations["postprocessing"].append("generate_summary")
            recommendations["metadata_extraction"].extend(
                ["duration", "creator", "publish_date"]
            )

        elif detection_result.content_type in ["news_article", "blog_post"]:
            recommendations["preprocessing"].append("check_paywall")
            recommendations["preprocessing"].append("extract_clean_text")
            recommendations["postprocessing"].append("sentiment_analysis")
            recommendations["metadata_extraction"].extend(
                ["author", "publish_date", "tags"]
            )

        elif detection_result.content_type == "academic_paper":
            recommendations["preprocessing"].append("extract_pdf_text")
            recommendations["preprocessing"].append("identify_sections")
            recommendations["postprocessing"].append("extract_citations")
            recommendations["metadata_extraction"].extend(
                ["doi", "authors", "journal", "abstract"]
            )

        elif detection_result.content_type == "code_snippet":
            recommendations["preprocessing"].append("syntax_highlighting")
            recommendations["preprocessing"].append("language_detection")
            recommendations["postprocessing"].append("code_analysis")
            recommendations["metadata_extraction"].extend(
                ["language", "complexity", "imports"]
            )

        return recommendations

    def _calculate_priority(self, detection_result: ContentTypeResult) -> str:
        """Calculate processing priority based on confidence and content type"""

        # High priority types
        high_priority_types = ["news_article", "academic_paper", "meeting_notes"]

        # Medium priority types
        medium_priority_types = [
            "youtube_video",
            "podcast_episode",
            "blog_post",
            "documentation",
        ]

        # Calculate priority
        if detection_result.confidence >= 0.8:
            if detection_result.content_type in high_priority_types:
                return "high"
            elif detection_result.content_type in medium_priority_types:
                return "medium"
            else:
                return "medium"
        elif detection_result.confidence >= 0.6:
            return "medium"
        else:
            return "low"
