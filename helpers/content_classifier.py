"""
Atlas Content Classification Engine
ML-based content categorization with confidence scoring and manual review
"""

import re
import json
import sqlite3
from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import urllib.parse


@dataclass
class ClassificationResult:
    """Result of content classification"""

    category: str
    confidence: float
    subcategory: Optional[str]
    tags: List[str]
    reasoning: str
    manual_review_required: bool


class ContentClassifier:
    """Intelligent content categorization with ML-like features"""

    def __init__(self, db_path: str = None):
        self.db_path = db_path or str(
            Path(__file__).parent.parent / "data" / "podcasts" / "atlas_podcasts.db"
        )

        # Initialize classification rules and patterns
        self.category_rules = self._init_category_rules()
        self.tag_extractors = self._init_tag_extractors()
        self.confidence_thresholds = {"high": 0.85, "medium": 0.65, "low": 0.45}

        # Initialize classification database
        self._init_classification_database()

    def _init_classification_database(self):
        """Initialize classification tracking database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Classification history table
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS classification_history (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        content_id TEXT,
                        content_type TEXT,
                        content_preview TEXT,
                        predicted_category TEXT,
                        predicted_confidence REAL,
                        predicted_tags TEXT,
                        manual_category TEXT,
                        manual_tags TEXT,
                        manual_feedback TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        reviewed_at TIMESTAMP,
                        review_status TEXT DEFAULT 'pending'
                    )
                """
                )

                # Category performance tracking
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS category_performance (
                        category TEXT PRIMARY KEY,
                        total_predictions INTEGER DEFAULT 0,
                        correct_predictions INTEGER DEFAULT 0,
                        accuracy REAL DEFAULT 0.0,
                        last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """
                )

                # Learning feedback table
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS classification_feedback (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        content_pattern TEXT,
                        correct_category TEXT,
                        feedback_type TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """
                )

                conn.commit()
        except Exception as e:
            print(f"Error initializing classification database: {e}")

    def _init_category_rules(self) -> Dict:
        """Initialize categorization rules with patterns and weights"""
        return {
            # Technology & Development
            "technology": {
                "url_patterns": [
                    (r"github\.com", 0.9),
                    (r"stackoverflow\.com", 0.85),
                    (r"dev\.to", 0.8),
                    (r"medium\.com.*tech", 0.75),
                    (r"hackernews\.com", 0.8),
                    (r"techcrunch\.com", 0.85),
                    (r"arstechnica\.com", 0.8),
                ],
                "text_patterns": [
                    (r"\b(?:python|javascript|react|vue|angular|nodejs)\b", 0.8),
                    (r"\b(?:api|database|sql|nosql|mongodb)\b", 0.7),
                    (r"\b(?:machine learning|ai|artificial intelligence)\b", 0.85),
                    (r"\b(?:docker|kubernetes|devops|ci/cd)\b", 0.8),
                    (r"\b(?:programming|coding|development|software)\b", 0.7),
                    (r"```[\s\S]*?```", 0.9),  # Code blocks
                    (r"`[^`]+`", 0.6),  # Inline code
                ],
                "subcategories": [
                    "web_development",
                    "data_science",
                    "devops",
                    "mobile_development",
                    "ai_ml",
                ],
            },
            # Business & Finance
            "business": {
                "url_patterns": [
                    (r"bloomberg\.com", 0.9),
                    (r"wsj\.com", 0.9),
                    (r"forbes\.com", 0.85),
                    (r"harvard\.edu.*business", 0.8),
                    (r"inc\.com", 0.8),
                    (r"entrepreneur\.com", 0.8),
                ],
                "text_patterns": [
                    (r"\b(?:startup|entrepreneur|funding|vc|venture capital)\b", 0.8),
                    (r"\b(?:revenue|profit|loss|expenses|budget)\b", 0.7),
                    (r"\b(?:market|stocks|investment|portfolio)\b", 0.75),
                    (r"\b(?:strategy|management|leadership|execution)\b", 0.6),
                    (r"\$[\d,]+(?:\.\d{2})?[kmb]?", 0.7),  # Money amounts
                    (r"\b(?:ipo|merger|acquisition|valuation)\b", 0.85),
                ],
                "subcategories": [
                    "startups",
                    "finance",
                    "strategy",
                    "leadership",
                    "economics",
                ],
            },
            # Science & Research
            "science": {
                "url_patterns": [
                    (r"arxiv\.org", 0.95),
                    (r"nature\.com", 0.9),
                    (r"science\.org", 0.9),
                    (r"pubmed\.ncbi\.nlm\.nih\.gov", 0.95),
                    (r"sciencedirect\.com", 0.85),
                    (r"doi\.org", 0.9),
                ],
                "text_patterns": [
                    (r"\b(?:research|study|experiment|hypothesis)\b", 0.7),
                    (r"\b(?:methodology|statistical|significance|correlation)\b", 0.8),
                    (r"\b(?:peer.?reviewed|journal|publication)\b", 0.85),
                    (r"\b(?:climate|environment|sustainability)\b", 0.75),
                    (r"\b(?:genetics|dna|protein|molecular)\b", 0.8),
                    (r"\[[0-9]+\]", 0.6),  # Citations
                    (r"\bet\s+al\.", 0.8),
                ],
                "subcategories": [
                    "medical",
                    "environmental",
                    "physics",
                    "biology",
                    "chemistry",
                ],
            },
            # News & Current Events
            "news": {
                "url_patterns": [
                    (r"nytimes\.com", 0.9),
                    (r"washingtonpost\.com", 0.9),
                    (r"reuters\.com", 0.9),
                    (r"bbc\.com/news", 0.9),
                    (r"cnn\.com", 0.85),
                    (r"npr\.org", 0.85),
                    (r"politico\.com", 0.8),
                ],
                "text_patterns": [
                    (r"\b(?:breaking|urgent|developing|update)\b", 0.8),
                    (r"\b(?:president|congress|senate|parliament)\b", 0.75),
                    (r"\b(?:election|vote|campaign|ballot)\b", 0.8),
                    (r"\b(?:war|conflict|peace|treaty)\b", 0.75),
                    (r"\b(?:crisis|emergency|disaster)\b", 0.7),
                    (r"\b\d{4}\s*election\b", 0.85),
                ],
                "subcategories": [
                    "politics",
                    "international",
                    "local",
                    "breaking",
                    "analysis",
                ],
            },
            # Education & Learning
            "education": {
                "url_patterns": [
                    (r"coursera\.org", 0.85),
                    (r"edx\.org", 0.85),
                    (r"khanacademy\.org", 0.9),
                    (r"mit\.edu", 0.8),
                    (r"stanford\.edu", 0.8),
                    (r"youtube\.com.*tutorial", 0.7),
                ],
                "text_patterns": [
                    (r"\b(?:learn|tutorial|course|lesson|education)\b", 0.7),
                    (r"\b(?:how\s+to|step\s+by\s+step|guide|instruction)\b", 0.8),
                    (r"\b(?:university|college|academic|curriculum)\b", 0.75),
                    (r"\b(?:certificate|degree|diploma|graduation)\b", 0.8),
                    (r"\b(?:student|teacher|professor|lecture)\b", 0.65),
                ],
                "subcategories": [
                    "tutorials",
                    "courses",
                    "academic",
                    "skills",
                    "certification",
                ],
            },
            # Health & Wellness
            "health": {
                "url_patterns": [
                    (r"webmd\.com", 0.85),
                    (r"mayoclinic\.org", 0.9),
                    (r"healthline\.com", 0.8),
                    (r"nih\.gov", 0.9),
                    (r"cdc\.gov", 0.9),
                ],
                "text_patterns": [
                    (r"\b(?:health|wellness|fitness|nutrition)\b", 0.7),
                    (r"\b(?:diet|exercise|workout|meditation)\b", 0.75),
                    (r"\b(?:symptoms|treatment|diagnosis|therapy)\b", 0.8),
                    (r"\b(?:mental health|anxiety|depression|stress)\b", 0.85),
                    (r"\b(?:medicine|pharmaceutical|drug|medication)\b", 0.8),
                    (r"\b(?:calories|protein|vitamins|supplements)\b", 0.7),
                ],
                "subcategories": [
                    "fitness",
                    "nutrition",
                    "mental_health",
                    "medical",
                    "wellness",
                ],
            },
            # Personal & Lifestyle
            "personal": {
                "url_patterns": [
                    (r"pinterest\.com", 0.7),
                    (r"instagram\.com", 0.6),
                    (r"lifestyle.*blog", 0.7),
                ],
                "text_patterns": [
                    (r"\b(?:personal|lifestyle|hobby|interest)\b", 0.6),
                    (r"\b(?:recipe|cooking|baking|kitchen)\b", 0.8),
                    (r"\b(?:travel|vacation|trip|destination)\b", 0.8),
                    (r"\b(?:family|relationship|friends|social)\b", 0.6),
                    (r"\b(?:home|house|apartment|decoration)\b", 0.7),
                    (r"\b(?:fashion|style|clothing|outfit)\b", 0.75),
                ],
                "subcategories": [
                    "cooking",
                    "travel",
                    "relationships",
                    "home",
                    "fashion",
                ],
            },
            # Entertainment & Media
            "entertainment": {
                "url_patterns": [
                    (r"youtube\.com/watch", 0.6),
                    (r"netflix\.com", 0.8),
                    (r"spotify\.com", 0.7),
                    (r"imdb\.com", 0.8),
                    (r"rottentomatoes\.com", 0.8),
                ],
                "text_patterns": [
                    (r"\b(?:movie|film|cinema|director|actor)\b", 0.8),
                    (r"\b(?:music|song|album|artist|band)\b", 0.8),
                    (r"\b(?:game|gaming|video game|esports)\b", 0.8),
                    (r"\b(?:tv show|series|episode|season)\b", 0.8),
                    (r"\b(?:entertainment|comedy|drama|thriller)\b", 0.7),
                    (r"\b(?:podcast|episode|host|guest)\b", 0.75),
                ],
                "subcategories": ["movies", "music", "gaming", "tv_shows", "podcasts"],
            },
        }

    def _init_tag_extractors(self) -> Dict:
        """Initialize tag extraction patterns"""
        return {
            "programming_languages": {
                "pattern": r"\b(python|javascript|java|c\+\+|rust|go|swift|kotlin|typescript|php|ruby|scala|clojure)\b",
                "confidence": 0.9,
            },
            "technologies": {
                "pattern": r"\b(react|vue|angular|django|flask|spring|rails|express|laravel|tensorflow|pytorch)\b",
                "confidence": 0.85,
            },
            "companies": {
                "pattern": r"\b(google|apple|microsoft|amazon|facebook|meta|netflix|uber|airbnb|tesla|spacex)\b",
                "confidence": 0.8,
            },
            "topics": {"pattern": r"#([a-zA-Z0-9_]+)", "confidence": 0.7},
            "academic_fields": {
                "pattern": r"\b(machine learning|artificial intelligence|data science|cybersecurity|blockchain|quantum computing)\b",
                "confidence": 0.85,
            },
            "business_terms": {
                "pattern": r"\b(startup|entrepreneur|saas|b2b|b2c|roi|kpi|mvp|agile|scrum|venture capital)\b",
                "confidence": 0.8,
            },
        }

    def classify_content(
        self, content: str, content_type: str = "text", context: Optional[Dict] = None
    ) -> ClassificationResult:
        """
        Classify content and assign category with confidence score

        Args:
            content: Content to classify (URL or text)
            content_type: Type of content (url, text, voice)
            context: Optional context (source_app, detected_type, etc.)

        Returns:
            ClassificationResult with category and confidence
        """

        # Determine if this is URL or text analysis
        is_url = content_type == "url" or self._is_url(content)

        if is_url:
            return self._classify_url(content, context)
        else:
            return self._classify_text(content, context)

    def _is_url(self, content: str) -> bool:
        """Check if content is a URL"""
        try:
            parsed = urllib.parse.urlparse(content.strip())
            return bool(parsed.scheme and parsed.netloc)
        except:
            return False

    def _classify_url(
        self, url: str, context: Optional[Dict] = None
    ) -> ClassificationResult:
        """Classify URL-based content"""

        url_lower = url.lower()
        category_scores = {}

        # Score each category based on URL patterns
        for category, rules in self.category_rules.items():
            score = 0.0
            matched_patterns = []

            for pattern, weight in rules["url_patterns"]:
                if re.search(pattern, url_lower):
                    score += weight
                    matched_patterns.append(pattern)

            if score > 0:
                category_scores[category] = {
                    "score": min(score, 1.0),  # Cap at 1.0
                    "patterns": matched_patterns,
                }

        # Apply context boost
        if context:
            category_scores = self._apply_context_boost(category_scores, context)

        # Find best category
        if category_scores:
            best_category = max(
                category_scores.keys(), key=lambda x: category_scores[x]["score"]
            )
            confidence = category_scores[best_category]["score"]

            # Determine subcategory
            subcategory = self._determine_subcategory(url, best_category)

            # Extract tags
            tags = self._extract_tags(url)

            # Determine if manual review is needed
            manual_review = confidence < self.confidence_thresholds["medium"]

            return ClassificationResult(
                category=best_category,
                confidence=confidence,
                subcategory=subcategory,
                tags=tags,
                reasoning=f"URL pattern match: {category_scores[best_category]['patterns']}",
                manual_review_required=manual_review,
            )

        # Fallback
        return self._fallback_classification(url, "No URL patterns matched")

    def _classify_text(
        self, text: str, context: Optional[Dict] = None
    ) -> ClassificationResult:
        """Classify text-based content"""

        text_lower = text.lower()
        category_scores = {}

        # Score each category based on text patterns
        for category, rules in self.category_rules.items():
            score = 0.0
            matched_patterns = []
            total_matches = 0

            for pattern, weight in rules["text_patterns"]:
                matches = len(re.findall(pattern, text_lower, re.IGNORECASE))
                if matches > 0:
                    # Weight by number of matches and text length
                    pattern_score = weight * min(
                        matches / 3, 1.0
                    )  # Diminishing returns
                    score += pattern_score
                    matched_patterns.append(f"{pattern}({matches})")
                    total_matches += matches

            if score > 0:
                # Normalize by text length to avoid bias toward longer texts
                normalized_score = min(score / max(len(text) / 1000, 1.0), 1.0)
                category_scores[category] = {
                    "score": normalized_score,
                    "patterns": matched_patterns,
                    "matches": total_matches,
                }

        # Apply context boost
        if context:
            category_scores = self._apply_context_boost(category_scores, context)

        # Find best category
        if category_scores:
            best_category = max(
                category_scores.keys(), key=lambda x: category_scores[x]["score"]
            )
            confidence = category_scores[best_category]["score"]

            # Determine subcategory
            subcategory = self._determine_subcategory(text, best_category)

            # Extract tags
            tags = self._extract_tags(text)

            # Determine if manual review is needed
            manual_review = confidence < self.confidence_thresholds["medium"]

            return ClassificationResult(
                category=best_category,
                confidence=confidence,
                subcategory=subcategory,
                tags=tags,
                reasoning=f"Text pattern analysis: {category_scores[best_category]['patterns']}",
                manual_review_required=manual_review,
            )

        # Fallback
        return self._fallback_classification(text, "No text patterns matched")

    def _apply_context_boost(self, scores: Dict, context: Dict) -> Dict:
        """Apply confidence boost based on context"""

        # Source app context
        source_app = context.get("source_app", "").lower()
        app_category_boost = {
            "safari": {"news": 0.1, "business": 0.05},
            "github": {"technology": 0.2},
            "youtube": {"entertainment": 0.1, "education": 0.1},
            "notes": {"personal": 0.1},
            "research": {"science": 0.15, "education": 0.1},
        }

        if source_app in app_category_boost:
            for category, boost in app_category_boost[source_app].items():
                if category in scores:
                    scores[category]["score"] = min(
                        scores[category]["score"] + boost, 1.0
                    )

        # Detected type context
        detected_type = context.get("detected_type", "")
        type_category_boost = {
            "academic_paper": {"science": 0.15, "education": 0.1},
            "news_article": {"news": 0.15},
            "blog_post": {"personal": 0.1, "technology": 0.05},
            "code_snippet": {"technology": 0.2},
            "youtube_video": {"entertainment": 0.1, "education": 0.1},
        }

        if detected_type in type_category_boost:
            for category, boost in type_category_boost[detected_type].items():
                if category in scores:
                    scores[category]["score"] = min(
                        scores[category]["score"] + boost, 1.0
                    )

        return scores

    def _determine_subcategory(self, content: str, category: str) -> Optional[str]:
        """Determine subcategory within the main category"""

        if category not in self.category_rules:
            return None

        subcategories = self.category_rules[category].get("subcategories", [])
        if not subcategories:
            return None

        content_lower = content.lower()

        # Define subcategory patterns
        subcategory_patterns = {
            "technology": {
                "web_development": r"\b(html|css|javascript|react|vue|angular|frontend|backend|web)\b",
                "data_science": r"\b(data|analytics|machine learning|ml|ai|python|pandas|numpy)\b",
                "devops": r"\b(docker|kubernetes|ci/cd|deployment|infrastructure|cloud)\b",
                "mobile_development": r"\b(ios|android|mobile|app|swift|kotlin|react native)\b",
                "ai_ml": r"\b(artificial intelligence|machine learning|neural|deep learning|ai|ml)\b",
            },
            "business": {
                "startups": r"\b(startup|entrepreneur|funding|seed|series a|vc)\b",
                "finance": r"\b(finance|investment|stocks|trading|market|portfolio)\b",
                "strategy": r"\b(strategy|planning|roadmap|vision|goals)\b",
                "leadership": r"\b(leadership|management|team|culture|hiring)\b",
                "economics": r"\b(economics|economy|gdp|inflation|recession|monetary)\b",
            },
            "science": {
                "medical": r"\b(medical|health|disease|treatment|clinical|patient)\b",
                "environmental": r"\b(climate|environment|sustainability|renewable|carbon)\b",
                "physics": r"\b(physics|quantum|particle|energy|matter|universe)\b",
                "biology": r"\b(biology|genetics|dna|protein|evolution|organism)\b",
                "chemistry": r"\b(chemistry|chemical|molecule|reaction|compound)\b",
            },
        }

        if category in subcategory_patterns:
            for subcat, pattern in subcategory_patterns[category].items():
                if re.search(pattern, content_lower):
                    return subcat

        return None

    def _extract_tags(self, content: str) -> List[str]:
        """Extract relevant tags from content"""

        tags = set()
        content_lower = content.lower()

        # Extract tags using defined patterns
        for tag_type, config in self.tag_extractors.items():
            pattern = config["pattern"]
            matches = re.findall(pattern, content_lower, re.IGNORECASE)
            for match in matches:
                if isinstance(match, tuple):
                    match = match[0]  # For groups in regex
                tags.add(match.lower())

        # Extract custom hashtags
        hashtags = re.findall(r"#([a-zA-Z0-9_]+)", content)
        tags.update([tag.lower() for tag in hashtags])

        # Limit tags and return sorted list
        return sorted(list(tags))[:10]  # Max 10 tags

    def _fallback_classification(
        self, content: str, reason: str
    ) -> ClassificationResult:
        """Provide fallback classification when no patterns match"""

        # Simple heuristics for fallback
        content_lower = content.lower()

        if len(content) < 50:
            category = "personal"
            confidence = 0.3
        elif any(word in content_lower for word in ["http", "www", ".com"]):
            category = "news"  # Generic web content
            confidence = 0.35
        else:
            category = "personal"  # Generic text content
            confidence = 0.25

        return ClassificationResult(
            category=category,
            confidence=confidence,
            subcategory=None,
            tags=[],
            reasoning=f"Fallback classification: {reason}",
            manual_review_required=True,
        )

    def record_classification(
        self, content_id: str, content: str, result: ClassificationResult
    ) -> None:
        """Record classification for learning and review"""

        try:
            with sqlite3.connect(self.db_path) as conn:
                # Store classification result
                conn.execute(
                    """
                    INSERT INTO classification_history
                    (content_id, content_type, content_preview, predicted_category,
                     predicted_confidence, predicted_tags, review_status)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        content_id,
                        "url" if self._is_url(content) else "text",
                        content[:500],  # Preview
                        result.category,
                        result.confidence,
                        json.dumps(result.tags),
                        (
                            "manual_review"
                            if result.manual_review_required
                            else "auto_approved"
                        ),
                    ),
                )

                # Update category performance
                conn.execute(
                    """
                    INSERT OR REPLACE INTO category_performance (category, total_predictions)
                    VALUES (?, COALESCE((SELECT total_predictions FROM category_performance WHERE category = ?), 0) + 1)
                """,
                    (result.category, result.category),
                )

                conn.commit()

        except Exception as e:
            print(f"Error recording classification: {e}")

    def get_manual_review_queue(self, limit: int = 20) -> List[Dict]:
        """Get items that need manual review"""

        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row

                results = conn.execute(
                    """
                    SELECT id, content_preview, predicted_category, predicted_confidence,
                           predicted_tags, created_at
                    FROM classification_history
                    WHERE review_status = 'manual_review'
                    ORDER BY created_at DESC
                    LIMIT ?
                """,
                    (limit,),
                ).fetchall()

                return [dict(row) for row in results]

        except Exception as e:
            print(f"Error getting manual review queue: {e}")
            return []

    def submit_manual_feedback(
        self,
        classification_id: int,
        correct_category: str,
        correct_tags: List[str],
        feedback: str = "",
    ) -> None:
        """Submit manual feedback for learning"""

        try:
            with sqlite3.connect(self.db_path) as conn:
                # Update classification record
                conn.execute(
                    """
                    UPDATE classification_history
                    SET manual_category = ?, manual_tags = ?, manual_feedback = ?,
                        reviewed_at = ?, review_status = 'reviewed'
                    WHERE id = ?
                """,
                    (
                        correct_category,
                        json.dumps(correct_tags),
                        feedback,
                        datetime.now().isoformat(),
                        classification_id,
                    ),
                )

                # Record feedback for learning
                classification = conn.execute(
                    """
                    SELECT content_preview, predicted_category FROM classification_history WHERE id = ?
                """,
                    (classification_id,),
                ).fetchone()

                if classification:
                    conn.execute(
                        """
                        INSERT INTO classification_feedback
                        (content_pattern, correct_category, feedback_type)
                        VALUES (?, ?, ?)
                    """,
                        (
                            classification[0][:100],  # Content pattern
                            correct_category,
                            "manual_correction",
                        ),
                    )

                conn.commit()

        except Exception as e:
            print(f"Error submitting manual feedback: {e}")

    def get_classification_stats(self) -> Dict:
        """Get classification performance statistics"""

        try:
            with sqlite3.connect(self.db_path) as conn:
                # Overall stats
                total_classifications = conn.execute(
                    """
                    SELECT COUNT(*) FROM classification_history
                """
                ).fetchone()[0]

                manual_reviews = conn.execute(
                    """
                    SELECT COUNT(*) FROM classification_history
                    WHERE review_status = 'manual_review'
                """
                ).fetchone()[0]

                avg_confidence = (
                    conn.execute(
                        """
                    SELECT AVG(predicted_confidence) FROM classification_history
                """
                    ).fetchone()[0]
                    or 0.0
                )

                # Category breakdown
                conn.row_factory = sqlite3.Row
                category_stats = conn.execute(
                    """
                    SELECT predicted_category, COUNT(*) as count,
                           AVG(predicted_confidence) as avg_confidence
                    FROM classification_history
                    GROUP BY predicted_category
                    ORDER BY count DESC
                """
                ).fetchall()

                return {
                    "total_classifications": total_classifications,
                    "pending_manual_reviews": manual_reviews,
                    "manual_review_rate": manual_reviews
                    / max(total_classifications, 1),
                    "average_confidence": avg_confidence,
                    "category_breakdown": [dict(row) for row in category_stats],
                }

        except Exception as e:
            print(f"Error getting classification stats: {e}")
            return {}
