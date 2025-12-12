"""
Ad and Sponsor Detection/Removal for Atlas.

Detects and removes advertisement content from:
- Podcast transcripts (baked-in ad reads)
- YouTube transcripts (mid-roll ads)
- Newsletter sponsor sections
- Native/sponsored article content

Three-tier approach to minimize false positives:
1. Pattern-based: Known sponsor phrases and advertisers
2. Position-based: Ads cluster at predictable positions
3. LLM-assisted: Optional fallback for ambiguous cases

Principle: Better to leave an ad than delete real content.
"""

import re
import logging
from dataclasses import dataclass, field
from typing import List, Optional, Tuple, Dict, Any
from enum import Enum
from pathlib import Path

import yaml

logger = logging.getLogger(__name__)


class ContentType(Enum):
    """Content types with different ad patterns."""
    PODCAST = "podcast"
    YOUTUBE = "youtube"
    ARTICLE = "article"
    NEWSLETTER = "newsletter"
    UNKNOWN = "unknown"


class DetectionMethod(Enum):
    """How an ad was detected."""
    KEYWORD = "keyword"
    ADVERTISER = "advertiser"
    POSITION = "position"
    URL_PATTERN = "url_pattern"
    SECTION_HEADER = "section_header"
    LLM = "llm"


class ConfidenceTier(Enum):
    """Confidence tiers for action decisions."""
    HIGH = "high"      # >0.9: Auto-remove
    MEDIUM = "medium"  # 0.7-0.9: Review queue
    LOW = "low"        # <0.7: Skip


@dataclass
class AdDetection:
    """A detected advertisement segment."""
    start_char: int
    end_char: int
    text: str
    method: DetectionMethod
    confidence: float  # 0.0 - 1.0
    matched_pattern: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def length(self) -> int:
        return self.end_char - self.start_char

    @property
    def tier(self) -> ConfidenceTier:
        """Get confidence tier for this detection."""
        if self.confidence >= 0.9:
            return ConfidenceTier.HIGH
        elif self.confidence >= 0.7:
            return ConfidenceTier.MEDIUM
        else:
            return ConfidenceTier.LOW


@dataclass
class StrippingResult:
    """Result of ad stripping operation."""
    original_text: str
    cleaned_text: str
    detections: List[AdDetection]
    chars_removed: int
    percent_removed: float

    @property
    def ads_found(self) -> int:
        return len(self.detections)


class AdStripper:
    """
    Detect and remove advertisements from content.

    Usage:
        stripper = AdStripper()
        result = stripper.strip(text, content_type=ContentType.PODCAST)
        print(f"Removed {result.ads_found} ads ({result.percent_removed:.1f}%)")
        clean_text = result.cleaned_text
    """

    # Default known sponsor keywords (high confidence)
    DEFAULT_SPONSOR_KEYWORDS = [
        # Direct sponsorship phrases
        r"brought to you by",
        r"sponsored by",
        r"this episode is sponsored",
        r"this podcast is sponsored",
        r"today'?s sponsor",
        r"our sponsor",
        r"a]word from our sponsor",

        # Call to action phrases
        r"use (?:code|promo|coupon)",
        r"promo code",
        r"discount code",
        r"get \d+% off",
        r"sign up (?:now )?at",
        r"go to [a-z]+\.com/",
        r"visit [a-z]+\.com/",
        r"head (?:on )?over to",
        r"check (?:them )?out at",

        # Affiliate/tracking patterns
        r"use (?:my |our )?link",
        r"link in (?:the )?description",
        r"link (?:is )?below",
        r"special offer",
        r"exclusive offer",
        r"limited time offer",
        r"free trial",
        r"first month free",

        # Newsletter-specific
        r"this (?:issue|edition|newsletter) is (?:brought|presented|sponsored)",
        r"thanks to .{3,50} for sponsoring",
    ]

    # Common advertisers (case-insensitive matching)
    DEFAULT_KNOWN_ADVERTISERS = [
        # Tech/Software
        "squarespace", "wix", "shopify", "hubspot", "notion",
        "monday.com", "asana", "slack", "zoom", "dropbox",
        "nordvpn", "expressvpn", "surfshark", "privatevpn",

        # Health/Wellness
        "betterhelp", "talkspace", "calm", "headspace",
        "athletic greens", "ag1", "four sigmatic", "magic spoon",
        "huel", "athletic brewing", "liquid iv", "mudwtr",

        # Finance
        "mint mobile", "rocket money", "nerdwallet", "credit karma",
        "robinhood", "public.com", "wealthfront", "betterment",

        # Consumer goods
        "hellofresh", "blue apron", "factor meals", "daily harvest",
        "bombas", "allbirds", "away luggage", "casper", "helix sleep",
        "purple mattress", "brooklinen", "parachute home",
        "manscaped", "harry's", "dollar shave club", "quip",
        "warby parker", "raycon", "rayban",

        # Services
        "audible", "kindle unlimited", "masterclass", "skillshare",
        "brilliant", "coursera", "linkedin learning",
        "stamps.com", "shipstation", "indeed", "ziprecruiter",
        "grammarly", "lastpass", "1password", "dashlane",

        # Other common podcast advertisers
        "simplisafe", "ring", "aura", "lifelock",
        "state farm", "geico", "progressive",
        "draftkings", "fanduel", "betmgm",
    ]

    # URL patterns that indicate ads
    DEFAULT_URL_PATTERNS = [
        r"bit\.ly/",
        r"tinyurl\.com/",
        r"amzn\.to/",
        r"/aff/",
        r"/affiliate/",
        r"/partner/",
        r"/promo/",
        r"\?ref=",
        r"\?utm_",
        r"/go/[a-z]+",  # Common redirect pattern
    ]

    # Section headers that indicate sponsor blocks (newsletters)
    DEFAULT_SECTION_HEADERS = [
        r"^#+\s*(?:sponsor|advertisement|promoted|partner)",
        r"^\*{2,}sponsor",
        r"^---+\s*(?:ad|sponsor)",
        r"^\[(?:ad|sponsor|promoted)\]",
        r"^(?:today'?s|this week'?s|our) sponsor",
    ]

    # Negative patterns - things that LOOK like ads but aren't
    # When these match, reduce confidence significantly
    # Updated based on analysis of 7,175 removals from enrich.db
    DEFAULT_NEGATIVE_PATTERNS = [
        # Historical/contextual references
        r"Radio Advertising Bureau",
        r"Advertising Age",
        r"advertising campaign",
        r"advertising industry",
        r"history of advertising",
        r"advertising executive",
        r"advertising agency",
        r"Mad Men",  # TV show about advertising

        # Academic/journalistic discussion
        r"study (?:of|on|about) advertising",
        r"research (?:on|into) advertising",
        r"advertising practices",
        r"advertising revenue",
        r"advertising market",
        r"advertising dollars",
        r"advertising budget",

        # Government/regulatory
        r"Federal Trade Commission",
        r"FTC",
        r"advertising standards",
        r"truth in advertising",
        r"advertising regulations",

        # Sponsored in non-ad context
        r"sponsored research",
        r"sponsored study",
        r"government.sponsored",
        r"state.sponsored",
        r"sponsored legislation",
        r"sponsored bill",

        # Company discussion (not ads)
        r"(?:acquired|bought|purchased) (?:by )?\w+(?:space|help|vpn)",
        r"stock (?:price|value|dropped|rose)",
        r"earnings report",
        r"quarterly results",

        # ===== LEARNED FROM DATA ANALYSIS (Dec 2024) =====
        # Brand names used as common words (137 false positives identified)

        # "Slack" as noun/verb (61 FPs)
        r"slack\s+community",           # Slack community discussions
        r"member.only\s+Slack",         # Member Slack groups
        r"our\s+Slack",                 # "our Slack channel"
        r"in\s+the\s+earliest\s+days\s+of\s+Slack",  # Historical Slack discussion
        r"co-?founder.*Slack",          # Slack co-founder mentions
        r"Slack\s+(?:channel|workspace|group|team)",  # Slack product discussions

        # "Notion" as concept (37 FPs)
        r"notion\s+of\b",               # "notion of productivity"
        r"a\s+(?:vague\s+)?notion",     # "a vague notion"
        r"some\s+notion",               # "some notion of"
        r"this\s+notion",               # "this notion that"
        r"the\s+notion\s+that",         # "the notion that X"
        r"have\s+(?:a\s+)?notion",      # "have a notion"
        r"rejects?\s+(?:a\s+)?notion",  # "rejects a notion"

        # "Indeed" as adverb (40 FPs)
        r"\bindeed[,.]?\s*$",           # "Indeed." at end of sentence
        r"indeed[,]?\s+(?:I|we|it|the|this|that|there|an?|some)\b",  # "Indeed, I think..."
        r"is\s+indeed\b",               # "this is indeed"
        r"was\s+indeed\b",              # "it was indeed"
        r"have\s+indeed\b",             # "I have indeed heard"
        r"indeed\s+(?:true|correct|right|possible|likely)",  # "indeed true"

        # Self-promotion links (not paid ads) - 17 FPs
        r"check\s+out\s+my\s+book",     # Author self-promo
        r"my\s+newsletter",             # Newsletter self-promo
        r"my\s+substack",               # Substack self-promo
        r"for\s+more\s+of\s+my\s+work", # Author bio
        r"available\s+(?:on|at)\s+Amazon",  # Book availability (not ad)

        # Company lists (not ads) - portfolio/competitor mentions
        r"(?:Uber|Airbnb|Stripe|Snap|Discord|Asana|Notion|Slack).{0,30}(?:Uber|Airbnb|Stripe|Snap|Discord|Asana|Notion|Slack)",
        r"portfolio\s+compan",          # "portfolio companies"
        r"invested\s+in",               # "invested in Slack"
        r"backed\s+by",                 # "backed by Benchmark"

        # ===== URL PATTERN FALSE POSITIVES (112 found in analysis) =====
        # Editorial/citation links with tracking params are NOT ads

        # News/research citations
        r"(?:survey|study|report|research|published|according to).*\?utm_",
        r"\?utm_.*(?:survey|study|report|article)",

        # Website navigation/footer links
        r"(?:About|Press|Copyright|Contact|Privacy|Terms).*\?utm_",
        r"youtube\.com/(?:about|press|creators|developers)",

        # Editorial links in articles
        r"(?:published|posted|wrote|reported).*\?(?:utm_|ref=)",
        r"iopscience\.iop\.org",        # Scientific journals
        r"arxiv\.org",
        r"doi\.org",
        r"\.gov/",                      # Government sites

        # Substack/newsletter internal links
        r"substack\.com.*\?utm_source=substack",
        r"please\s+check\s+out.*(?:survey|this)",
    ]

    def __init__(
        self,
        config_path: Optional[Path] = None,
        sponsor_keywords: Optional[List[str]] = None,
        known_advertisers: Optional[List[str]] = None,
        url_patterns: Optional[List[str]] = None,
        section_headers: Optional[List[str]] = None,
        negative_patterns: Optional[List[str]] = None,
        min_confidence: float = 0.6,
        min_segment_chars: int = 50,
        max_segment_chars: int = 3000,
        auto_remove_threshold: float = 0.9,
        review_threshold: float = 0.7,
    ):
        """
        Initialize the ad stripper.

        Args:
            config_path: Path to YAML config file (optional)
            sponsor_keywords: Regex patterns for sponsor phrases
            known_advertisers: List of known advertiser names
            url_patterns: URL patterns indicating affiliate/ad links
            section_headers: Patterns for sponsor section headers
            negative_patterns: Patterns that indicate NOT an ad (reduce confidence)
            min_confidence: Minimum confidence to include in results (0.0-1.0)
            min_segment_chars: Ignore detections smaller than this
            max_segment_chars: Maximum ad segment size (sanity check)
            auto_remove_threshold: Confidence >= this is auto-removed (HIGH tier)
            review_threshold: Confidence >= this goes to review queue (MEDIUM tier)
        """
        self.min_confidence = min_confidence
        self.min_segment_chars = min_segment_chars
        self.max_segment_chars = max_segment_chars
        self.auto_remove_threshold = auto_remove_threshold
        self.review_threshold = review_threshold

        # Load config if provided
        config = {}
        if config_path and config_path.exists():
            with open(config_path) as f:
                config = yaml.safe_load(f).get("ad_stripping", {})

        # Set patterns (config > args > defaults)
        self.sponsor_keywords = self._compile_patterns(
            config.get("sponsor_keywords") or sponsor_keywords or self.DEFAULT_SPONSOR_KEYWORDS
        )
        self.known_advertisers = (
            config.get("known_advertisers") or known_advertisers or self.DEFAULT_KNOWN_ADVERTISERS
        )
        self.url_patterns = self._compile_patterns(
            config.get("url_patterns") or url_patterns or self.DEFAULT_URL_PATTERNS
        )
        self.section_headers = self._compile_patterns(
            config.get("section_headers") or section_headers or self.DEFAULT_SECTION_HEADERS
        )
        self.negative_patterns = self._compile_patterns(
            config.get("negative_patterns") or negative_patterns or self.DEFAULT_NEGATIVE_PATTERNS
        )

        # Build advertiser regex (word boundaries, case insensitive)
        advertiser_pattern = r"\b(" + "|".join(re.escape(a) for a in self.known_advertisers) + r")\b"
        self.advertiser_regex = re.compile(advertiser_pattern, re.IGNORECASE)

        logger.debug(
            f"AdStripper initialized: {len(self.sponsor_keywords)} keywords, "
            f"{len(self.known_advertisers)} advertisers, "
            f"{len(self.negative_patterns)} negative patterns"
        )

    def _compile_patterns(self, patterns: List[str]) -> List[re.Pattern]:
        """Compile regex patterns, logging any errors."""
        compiled = []
        for p in patterns:
            try:
                compiled.append(re.compile(p, re.IGNORECASE | re.MULTILINE))
            except re.error as e:
                logger.warning(f"Invalid regex pattern '{p}': {e}")
        return compiled

    def detect(
        self,
        text: str,
        content_type: ContentType = ContentType.UNKNOWN,
    ) -> List[AdDetection]:
        """
        Detect advertisement segments in text.

        Args:
            text: The content to analyze
            content_type: Type of content (affects detection strategy)

        Returns:
            List of detected ad segments
        """
        detections = []

        # Tier 1: Keyword detection
        detections.extend(self._detect_by_keywords(text))

        # Tier 1b: Known advertiser mentions
        detections.extend(self._detect_by_advertisers(text))

        # Tier 1c: URL patterns
        detections.extend(self._detect_by_urls(text))

        # Tier 2: Section headers (primarily newsletters)
        if content_type in (ContentType.NEWSLETTER, ContentType.ARTICLE, ContentType.UNKNOWN):
            detections.extend(self._detect_by_sections(text))

        # Tier 2b: Position-based (podcasts/youtube)
        if content_type in (ContentType.PODCAST, ContentType.YOUTUBE):
            detections = self._adjust_by_position(detections, text)

        # Merge overlapping detections
        detections = self._merge_detections(detections)

        # Boost compound detections (multiple signals = higher confidence)
        detections = self._boost_compound_detections(detections)

        # Apply negative patterns to reduce false positive confidence
        detections = self._apply_negative_patterns(detections)

        # Filter by confidence and size
        detections = [
            d for d in detections
            if d.confidence >= self.min_confidence
            and d.length >= self.min_segment_chars
            and d.length <= self.max_segment_chars
        ]

        return detections

    def _apply_negative_patterns(
        self,
        detections: List[AdDetection],
    ) -> List[AdDetection]:
        """
        Check detections against negative patterns and reduce confidence.

        Negative patterns indicate the text is NOT an ad (e.g., historical
        reference, journalistic discussion).
        """
        for detection in detections:
            for pattern in self.negative_patterns:
                if pattern.search(detection.text):
                    # Significant confidence reduction for negative match
                    old_confidence = detection.confidence
                    detection.confidence *= 0.4  # 60% reduction
                    detection.metadata["negative_match"] = pattern.pattern
                    logger.debug(
                        f"Negative pattern '{pattern.pattern}' reduced confidence "
                        f"from {old_confidence:.2f} to {detection.confidence:.2f}"
                    )
                    break  # One negative match is enough

        return detections

    def _boost_compound_detections(
        self,
        detections: List[AdDetection],
    ) -> List[AdDetection]:
        """
        Boost confidence when multiple signals are present.

        If a detection contains both a sponsor keyword AND a known advertiser,
        it's almost certainly a real ad.
        """
        for detection in detections:
            text_lower = detection.text.lower()

            # Check for known advertiser in the detection text
            has_advertiser = bool(self.advertiser_regex.search(detection.text))

            # Check for sponsor keywords
            has_sponsor_keyword = any(p.search(detection.text) for p in self.sponsor_keywords)

            # Check for URL with tracking params
            has_tracking_url = any(p.search(detection.text) for p in self.url_patterns)

            # Count positive signals
            signals = sum([has_advertiser, has_sponsor_keyword, has_tracking_url])

            if signals >= 2:
                old_confidence = detection.confidence
                # Boost confidence significantly for compound detections
                detection.confidence = min(0.98, detection.confidence * 1.25)
                detection.metadata["compound_signals"] = signals
                logger.debug(
                    f"Compound detection ({signals} signals) boosted confidence "
                    f"from {old_confidence:.2f} to {detection.confidence:.2f}"
                )

        return detections

    def _detect_by_keywords(self, text: str) -> List[AdDetection]:
        """Detect ads by sponsor keyword patterns."""
        detections = []

        for pattern in self.sponsor_keywords:
            for match in pattern.finditer(text):
                # Expand to sentence/paragraph boundaries
                start, end = self._expand_to_segment(text, match.start(), match.end())

                detections.append(AdDetection(
                    start_char=start,
                    end_char=end,
                    text=text[start:end],
                    method=DetectionMethod.KEYWORD,
                    confidence=0.85,
                    matched_pattern=pattern.pattern,
                ))

        return detections

    def _detect_by_advertisers(self, text: str) -> List[AdDetection]:
        """Detect ads by known advertiser mentions."""
        detections = []

        for match in self.advertiser_regex.finditer(text):
            # Look for surrounding ad context
            context_start = max(0, match.start() - 200)
            context_end = min(len(text), match.end() + 200)
            context = text[context_start:context_end].lower()

            # Only flag if advertiser appears with ad-like context
            ad_context_patterns = [
                r"sponsor", r"brought to you", r"partner", r"promo",
                r"discount", r"% off", r"free trial", r"sign up",
            ]

            has_ad_context = any(re.search(p, context) for p in ad_context_patterns)

            if has_ad_context:
                start, end = self._expand_to_segment(text, match.start(), match.end())
                detections.append(AdDetection(
                    start_char=start,
                    end_char=end,
                    text=text[start:end],
                    method=DetectionMethod.ADVERTISER,
                    confidence=0.80,
                    matched_pattern=match.group(1),
                ))

        return detections

    def _detect_by_urls(self, text: str) -> List[AdDetection]:
        """Detect ads by affiliate/tracking URL patterns."""
        detections = []

        for pattern in self.url_patterns:
            for match in pattern.finditer(text):
                start, end = self._expand_to_segment(text, match.start(), match.end())

                detections.append(AdDetection(
                    start_char=start,
                    end_char=end,
                    text=text[start:end],
                    method=DetectionMethod.URL_PATTERN,
                    confidence=0.70,
                    matched_pattern=pattern.pattern,
                ))

        return detections

    def _detect_by_sections(self, text: str) -> List[AdDetection]:
        """Detect sponsor sections by headers (newsletters/articles)."""
        detections = []

        for pattern in self.section_headers:
            for match in pattern.finditer(text):
                # Find the end of this section (next header or significant break)
                section_start = match.start()
                section_end = self._find_section_end(text, match.end())

                if section_end - section_start >= self.min_segment_chars:
                    detections.append(AdDetection(
                        start_char=section_start,
                        end_char=section_end,
                        text=text[section_start:section_end],
                        method=DetectionMethod.SECTION_HEADER,
                        confidence=0.90,
                        matched_pattern=pattern.pattern,
                    ))

        return detections

    def _expand_to_segment(
        self,
        text: str,
        match_start: int,
        match_end: int,
        max_expand: int = 500,
    ) -> Tuple[int, int]:
        """
        Expand a match to natural segment boundaries.

        Tries to capture the full ad read, not just the trigger phrase.
        """
        # Find paragraph boundaries
        para_start = text.rfind("\n\n", max(0, match_start - max_expand), match_start)
        para_start = para_start + 2 if para_start != -1 else max(0, match_start - max_expand)

        para_end = text.find("\n\n", match_end, min(len(text), match_end + max_expand))
        para_end = para_end if para_end != -1 else min(len(text), match_end + max_expand)

        # For shorter segments, use sentence boundaries instead
        if para_end - para_start > 1000:
            # Find sentence boundaries
            sent_start = max(
                text.rfind(". ", para_start, match_start),
                text.rfind("! ", para_start, match_start),
                text.rfind("? ", para_start, match_start),
            )
            sent_start = sent_start + 2 if sent_start > para_start else para_start

            sent_end = min(
                text.find(". ", match_end, para_end) if text.find(". ", match_end, para_end) != -1 else para_end,
                text.find("! ", match_end, para_end) if text.find("! ", match_end, para_end) != -1 else para_end,
                text.find("? ", match_end, para_end) if text.find("? ", match_end, para_end) != -1 else para_end,
            )
            sent_end = sent_end + 1 if sent_end < para_end else para_end

            return sent_start, sent_end

        return para_start, para_end

    def _find_section_end(self, text: str, start: int) -> int:
        """Find the end of a section (next header or major break)."""
        # Look for next markdown header
        next_header = re.search(r"\n#+\s", text[start:])
        if next_header:
            return start + next_header.start()

        # Look for horizontal rule
        next_hr = re.search(r"\n---+\n", text[start:])
        if next_hr:
            return start + next_hr.start()

        # Look for double newline after substantial content
        next_break = text.find("\n\n", start + 100)
        if next_break != -1:
            return next_break

        # Default: next 500 chars or end
        return min(len(text), start + 500)

    def _adjust_by_position(
        self,
        detections: List[AdDetection],
        text: str,
    ) -> List[AdDetection]:
        """
        Adjust confidence based on position in content.

        Podcast/YouTube ads typically appear at:
        - Start (0-10% of content)
        - Middle (~40-60% of content)
        - End (last 10% of content)
        """
        text_len = len(text)
        if text_len == 0:
            return detections

        for detection in detections:
            position = detection.start_char / text_len

            # Boost confidence for typical ad positions
            if position < 0.10:  # Start
                detection.confidence = min(1.0, detection.confidence * 1.15)
                detection.metadata["position"] = "start"
            elif 0.40 <= position <= 0.60:  # Mid-roll
                detection.confidence = min(1.0, detection.confidence * 1.10)
                detection.metadata["position"] = "middle"
            elif position > 0.90:  # End
                detection.confidence = min(1.0, detection.confidence * 1.10)
                detection.metadata["position"] = "end"

        return detections

    def _merge_detections(self, detections: List[AdDetection]) -> List[AdDetection]:
        """Merge overlapping or adjacent detections."""
        if not detections:
            return []

        # Sort by start position
        detections.sort(key=lambda d: d.start_char)

        merged = [detections[0]]
        for current in detections[1:]:
            last = merged[-1]

            # Check for overlap or adjacency (within 50 chars)
            if current.start_char <= last.end_char + 50:
                # Merge: extend the end and take higher confidence
                merged[-1] = AdDetection(
                    start_char=last.start_char,
                    end_char=max(last.end_char, current.end_char),
                    text=last.text[:100] + "..." if len(last.text) > 100 else last.text,
                    method=last.method if last.confidence >= current.confidence else current.method,
                    confidence=max(last.confidence, current.confidence),
                    matched_pattern=last.matched_pattern,
                    metadata={**last.metadata, **current.metadata},
                )
            else:
                merged.append(current)

        return merged

    def get_by_tier(
        self,
        detections: List[AdDetection],
    ) -> Dict[ConfidenceTier, List[AdDetection]]:
        """
        Group detections by confidence tier.

        Returns:
            Dict with HIGH, MEDIUM, LOW keys mapping to detection lists
        """
        result = {
            ConfidenceTier.HIGH: [],
            ConfidenceTier.MEDIUM: [],
            ConfidenceTier.LOW: [],
        }
        for d in detections:
            result[d.tier].append(d)
        return result

    def get_auto_remove(self, detections: List[AdDetection]) -> List[AdDetection]:
        """Get detections that should be auto-removed (HIGH tier)."""
        return [d for d in detections if d.confidence >= self.auto_remove_threshold]

    def get_review_queue(self, detections: List[AdDetection]) -> List[AdDetection]:
        """Get detections that need human review (MEDIUM tier)."""
        return [
            d for d in detections
            if self.review_threshold <= d.confidence < self.auto_remove_threshold
        ]

    def strip(
        self,
        text: str,
        content_type: ContentType = ContentType.UNKNOWN,
    ) -> StrippingResult:
        """
        Detect and remove advertisements from text.

        Args:
            text: The content to clean
            content_type: Type of content

        Returns:
            StrippingResult with cleaned text and detection details
        """
        detections = self.detect(text, content_type)

        if not detections:
            return StrippingResult(
                original_text=text,
                cleaned_text=text,
                detections=[],
                chars_removed=0,
                percent_removed=0.0,
            )

        # Remove detected segments (in reverse order to preserve indices)
        cleaned = text
        detections_sorted = sorted(detections, key=lambda d: d.start_char, reverse=True)

        for detection in detections_sorted:
            # Replace ad segment with a marker (optional) or just remove
            cleaned = cleaned[:detection.start_char] + cleaned[detection.end_char:]

        # Clean up extra whitespace
        cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
        cleaned = cleaned.strip()

        chars_removed = len(text) - len(cleaned)
        percent_removed = (chars_removed / len(text) * 100) if text else 0

        logger.info(
            f"Stripped {len(detections)} ads, removed {chars_removed} chars "
            f"({percent_removed:.1f}%)"
        )

        return StrippingResult(
            original_text=text,
            cleaned_text=cleaned,
            detections=detections,
            chars_removed=chars_removed,
            percent_removed=percent_removed,
        )


def strip_ads(
    text: str,
    content_type: str = "unknown",
    min_confidence: float = 0.6,
) -> str:
    """
    Convenience function to strip ads from text.

    Args:
        text: Content to clean
        content_type: One of: podcast, youtube, article, newsletter, unknown
        min_confidence: Minimum confidence threshold (0.0-1.0)

    Returns:
        Cleaned text with ads removed
    """
    stripper = AdStripper(min_confidence=min_confidence)
    content_type_enum = ContentType(content_type.lower())
    result = stripper.strip(text, content_type_enum)
    return result.cleaned_text


# CLI for testing
if __name__ == "__main__":
    import argparse
    import sys

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    parser = argparse.ArgumentParser(description="Strip ads from content")
    parser.add_argument("file", nargs="?", help="File to process (or stdin)")
    parser.add_argument("--type", "-t", default="unknown",
                        choices=["podcast", "youtube", "article", "newsletter", "unknown"],
                        help="Content type")
    parser.add_argument("--confidence", "-c", type=float, default=0.6,
                        help="Minimum confidence (0.0-1.0)")
    parser.add_argument("--detect-only", "-d", action="store_true",
                        help="Only detect, don't strip")
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="Show detection details")
    args = parser.parse_args()

    # Read input
    if args.file:
        text = Path(args.file).read_text()
    else:
        text = sys.stdin.read()

    stripper = AdStripper(min_confidence=args.confidence)
    content_type = ContentType(args.type)

    if args.detect_only:
        detections = stripper.detect(text, content_type)
        print(f"Found {len(detections)} ad segments:\n")
        for i, d in enumerate(detections, 1):
            print(f"{i}. [{d.method.value}] confidence={d.confidence:.2f}")
            print(f"   Pattern: {d.matched_pattern}")
            print(f"   Text: {d.text[:100]}...")
            print()
    else:
        result = stripper.strip(text, content_type)

        if args.verbose:
            print(f"# Ad Stripping Results", file=sys.stderr)
            print(f"- Ads found: {result.ads_found}", file=sys.stderr)
            print(f"- Chars removed: {result.chars_removed}", file=sys.stderr)
            print(f"- Percent removed: {result.percent_removed:.1f}%", file=sys.stderr)
            print(f"---", file=sys.stderr)

        print(result.cleaned_text)
