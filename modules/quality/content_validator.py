"""
Content Quality Validator - Prevent garbage content from being saved.

This module validates content quality BEFORE saving to prevent:
1. JavaScript-required pages that failed to render
2. Error/redirect pages
3. Tracking pixels and analytics URLs
4. Profile/landing pages without actual content
5. Paywalled/login-required pages
"""

import re
import logging
from typing import Tuple, Optional, List
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


# Garbage title patterns - content with these titles should be rejected
GARBAGE_TITLE_PATTERNS = [
    r"^\s*$",  # Empty or whitespace only
    r"^https?://",  # Just a URL
    r"^\[no[- ]?title\]$",
    r"^untitled$",
    r"^no title$",
    r"^page not found",
    r"^404",
    r"^403",
    r"^error",
    r"^access denied",
    r"^forbidden",
    r"^sign in",
    r"^log in",
    r"^login",
    r"^loading",
    r"^redirecting",
    r"^just a moment",
    r"^please wait",
    r"^verifying",
    r"^checking your browser",
    r"^one moment",
    r"^bloomberg link",  # Tracking links
    r"^spotify$",  # App redirect pages
]

# Garbage content patterns - reject if content matches these
GARBAGE_CONTENT_PATTERNS = [
    r"this site requires javascript",
    r"please (enable|turn on) javascript",
    r"javascript is (required|disabled|not enabled)",
    r"unblock scripts",
    r"error occurred while",
    r"retrieving sharing information",
    r"please try again later",
    r"access denied",
    r"you don't have permission",
    r"this page doesn't exist",
    r"page not found",
    r"404 not found",
    r"403 forbidden",
    r"502 bad gateway",
    r"503 service unavailable",
    r"checking your browser",
    r"please verify you are human",
    r"complete the captcha",
    r"enable cookies",
    r"your browser .* out of date",
    r"browser not supported",
    r"this content is not available",
    r"subscription required",
    r"sign in to continue",
    r"log in to view",
    r"create.* account to",
    r"members only",
    r"premium content",
    r"include playlist\s*an error occurred",  # YouTube share errors
    r"^share\s*include playlist",  # YouTube share dialog
]

# URL patterns that indicate garbage/tracking (extends robust_fetcher's list)
GARBAGE_URL_PATTERNS = [
    r"/e/o/eyJ",  # Email open tracking pixels
    r"/e/c/eyJ",  # Email click tracking
    r"eotrx\.",  # Email tracking pixels
    r"\.gif\?",  # Tracking pixels
    r"/pixel",
    r"/beacon",
    r"/track[ing]?",
    r"doubleclick\.net",
    r"googlesyndication",
    r"googleadservices",
    r"facebook\.net.*fbevents",
    r"connect\.facebook\.net",
    r"cdn\.segment\.com",
    r"segment\.io",
    r"mixpanel\.com",
    r"amplitude\.com",
    r"heap\.io",
    r"intercom\.io",
    r"hotjar\.com",
    r"fullstory\.com",
    r"sentry\.io",
    r"bugsnag\.com",
    r"loggly\.com",
    r"logz\.io",
    r"datadoghq\.com",
    r"nr-data\.net",  # New Relic
    r"mparticle\.com",
    r"branch\.io",
    r"adjust\.com",
    r"appsflyer\.com",
    r"kochava\.com",
    r"apps\.apple\.com.*open",  # App Store redirects
    r"play\.google\.com.*open",  # Play Store redirects
    r"substackcdn\.com/image/",  # Substack image CDN (not articles)
    r"/image/youtube/",  # YouTube thumbnail images
]

# Domains that are mostly garbage when saved directly
GARBAGE_DOMAINS = [
    "eotrx.substackcdn.com",  # Email tracking
    "email.mg",  # Mailgun tracking
    "links.message.bloomberg.com",  # Bloomberg redirect links
    "bloom.bg",  # Bloomberg short links (usually redirects)
    "post.spmailtechnolo.com",  # Email tracking
    "click.email",
    "t.co",  # Twitter shortlinks
    "lnkd.in",  # LinkedIn shortlinks
    "bit.ly",
    "tinyurl.com",
    "ow.ly",
    "buff.ly",
    "goo.gl",
]


class ContentValidator:
    """Validates content quality before saving."""

    def __init__(self, min_content_length: int = 200, min_title_length: int = 5):
        """
        Initialize validator.

        Args:
            min_content_length: Minimum content length in characters
            min_title_length: Minimum title length in characters
        """
        self.min_content_length = min_content_length
        self.min_title_length = min_title_length

        # Compile patterns for efficiency
        self._garbage_title_patterns = [
            re.compile(p, re.IGNORECASE) for p in GARBAGE_TITLE_PATTERNS
        ]
        self._garbage_content_patterns = [
            re.compile(p, re.IGNORECASE) for p in GARBAGE_CONTENT_PATTERNS
        ]
        self._garbage_url_patterns = [
            re.compile(p, re.IGNORECASE) for p in GARBAGE_URL_PATTERNS
        ]

    def validate_url(self, url: str) -> Tuple[bool, str]:
        """
        Check if URL is likely garbage/tracking.

        Returns:
            Tuple of (is_valid, reason_if_invalid)
        """
        if not url:
            return False, "Empty URL"

        url_lower = url.lower()

        # Check domain
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()

            for garbage_domain in GARBAGE_DOMAINS:
                if garbage_domain in domain:
                    return False, f"Garbage domain: {garbage_domain}"
        except Exception:
            pass

        # Check URL patterns
        for pattern in self._garbage_url_patterns:
            if pattern.search(url_lower):
                return False, f"Matches garbage URL pattern"

        return True, ""

    def validate_title(self, title: str, url: str = "") -> Tuple[bool, str]:
        """
        Check if title indicates garbage content.

        Returns:
            Tuple of (is_valid, reason_if_invalid)
        """
        if not title:
            return False, "Empty title"

        title_clean = title.strip().lower()

        # Check minimum length
        if len(title_clean) < self.min_title_length:
            return False, f"Title too short: {len(title_clean)} chars"

        # Check if title is just the URL
        if url and title_clean in url.lower():
            return False, "Title is just the URL"

        # Check garbage patterns
        for pattern in self._garbage_title_patterns:
            if pattern.search(title_clean):
                return False, f"Garbage title pattern"

        # Check if title ends with common garbage suffixes
        if title_clean.endswith(" | substack"):
            # This is usually a profile page, not an article
            return False, "Substack profile page"

        return True, ""

    def validate_content(self, content: str, title: str = "") -> Tuple[bool, str]:
        """
        Check if content is garbage.

        Returns:
            Tuple of (is_valid, reason_if_invalid)
        """
        if not content:
            return False, "Empty content"

        content_clean = content.strip().lower()

        # Check minimum length
        if len(content_clean) < self.min_content_length:
            return False, f"Content too short: {len(content_clean)} chars"

        # Check garbage patterns
        for pattern in self._garbage_content_patterns:
            if pattern.search(content_clean):
                return False, "Garbage content pattern"

        # Check if content is mostly the title repeated
        if title:
            title_lower = title.lower()
            if content_clean.count(title_lower) > 3:
                return False, "Content is mostly repeated title"

        # Check word count (at least 50 words for meaningful content)
        words = content_clean.split()
        if len(words) < 50:
            return False, f"Too few words: {len(words)}"

        return True, ""

    def validate_all(
        self,
        url: str,
        title: str,
        content: str
    ) -> Tuple[bool, str, List[str]]:
        """
        Run all validations.

        Logic:
        - If content is good, we keep it even if URL is a shortlink
        - If title is garbage (errors, etc), reject
        - If content is garbage (JS required, etc), reject
        - Only reject on URL alone for tracking pixels (no content)

        Returns:
            Tuple of (is_valid, primary_reason, all_issues)
        """
        issues = []

        # Validate title first - garbage titles are always bad
        title_valid, title_reason = self.validate_title(title, url)
        if not title_valid:
            # Exception: short titles are ok if content is good
            if "too short" not in title_reason.lower():
                issues.append(f"Title: {title_reason}")

        # Validate content
        content_valid, content_reason = self.validate_content(content, title)
        if not content_valid:
            issues.append(f"Content: {content_reason}")

        # URL validation - only reject for tracking pixels, not shortlinks with real content
        url_valid, url_reason = self.validate_url(url)
        if not url_valid:
            # If content looks good, keep it despite bad URL (shortlink was resolved)
            if content_valid and title_valid:
                pass  # Don't add URL issue - content is good
            else:
                # No good content, and URL is garbage = reject
                issues.append(f"URL: {url_reason}")

        is_valid = len(issues) == 0
        primary_reason = issues[0] if issues else ""

        return is_valid, primary_reason, issues


# Singleton instance
_validator: Optional[ContentValidator] = None


def get_validator() -> ContentValidator:
    """Get or create singleton validator."""
    global _validator
    if _validator is None:
        _validator = ContentValidator()
    return _validator


def is_garbage_content(
    url: str = "",
    title: str = "",
    content: str = ""
) -> Tuple[bool, str]:
    """
    Quick check if content is garbage.

    Returns:
        Tuple of (is_garbage, reason)
    """
    validator = get_validator()
    is_valid, reason, _ = validator.validate_all(url, title, content)
    return not is_valid, reason


def validate_before_save(
    url: str,
    title: str,
    content: str,
    strict: bool = True
) -> Tuple[bool, str]:
    """
    Validate content before saving.

    Args:
        url: Source URL
        title: Content title
        content: Content body
        strict: If True, reject on any issue. If False, only reject clear garbage.

    Returns:
        Tuple of (should_save, reason_if_not)
    """
    validator = get_validator()
    is_valid, reason, issues = validator.validate_all(url, title, content)

    if strict:
        return is_valid, reason

    # In non-strict mode, only reject if URL is garbage or content has garbage patterns
    if issues:
        for issue in issues:
            if "URL:" in issue or "Garbage" in issue:
                return False, issue

    return True, ""
