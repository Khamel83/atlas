"""
URL normalization for Atlas v4.

Implements URL normalization rules for deduplication as specified in PRD.
Handles canonical URL generation from various URL formats.
"""

import re
import urllib.parse
from typing import Optional
from urllib.parse import urlparse, urlunparse, parse_qs, urlencode


def normalize_url(url: str) -> str:
    """
    Normalize URL according to PRD specifications.

    URL Normalization Rules:
    1. Lowercase entire URL before hashing
    2. Remove ALL query parameters except: ?id, ?v (YouTube video IDs)
    3. Remove fragment identifiers (#...)
    4. Strip trailing slashes unless the path is root
    5. Remove duplicate slashes in path
    6. Convert percent-encoded characters to their decoded form

    Args:
        url: URL to normalize

    Returns:
        Normalized URL
    """
    if not url:
        return ""

    # Parse URL
    try:
        parsed = urlparse(url)
    except Exception:
        # If URL parsing fails, return lowercase version
        return url.lower()

    # Convert to lowercase
    scheme = parsed.scheme.lower()
    netloc = parsed.netloc.lower()

    # Normalize path
    path = normalize_path(parsed.path)

    # Handle query parameters - keep only allowed ones
    query = normalize_query_parameters(parsed.query)

    # Remove fragment
    fragment = ""

    # Reconstruct URL
    normalized_parts = (
        scheme,
        netloc,
        path,
        "",  # params
        query,
        fragment
    )

    normalized_url = urlunparse(normalized_parts)

    # Decode percent-encoded characters
    normalized_url = urllib.parse.unquote(normalized_url)

    return normalized_url


def normalize_path(path: str) -> str:
    """
    Normalize URL path by removing duplicate slashes and trailing slashes.

    Args:
        path: URL path component

    Returns:
        Normalized path
    """
    if not path or path == "/":
        return "/"

    # Remove duplicate slashes
    path = re.sub(r'/+', '/', path)

    # Remove trailing slash unless it's root
    if path != "/" and path.endswith("/"):
        path = path.rstrip("/")

    return path


def normalize_query_parameters(query: str) -> str:
    """
    Normalize query parameters by keeping only allowed ones.

    Allowed parameters: id, v (for YouTube video IDs)

    Args:
        query: Query string

    Returns:
        Normalized query string
    """
    if not query:
        return ""

    # Parse query parameters
    params = parse_qs(query, keep_blank_values=True)

    # Keep only allowed parameters
    allowed_params = {}
    for key, values in params.items():
        if key.lower() in ['id', 'v']:
            # Keep first value for each parameter
            allowed_params[key] = values[0]

    # Reconstruct query string
    if allowed_params:
        return urlencode(allowed_params, doseq=True)
    else:
        return ""


def is_youtube_url(url: str) -> bool:
    """
    Check if URL is a YouTube URL.

    Args:
        url: URL to check

    Returns:
        True if YouTube URL
    """
    youtube_domains = [
        'youtube.com',
        'youtu.be',
        'm.youtube.com',
        'www.youtube.com'
    ]

    try:
        parsed = urlparse(url.lower())
        return any(domain in parsed.netloc for domain in youtube_domains)
    except Exception:
        return False


def extract_youtube_video_id(url: str) -> Optional[str]:
    """
    Extract YouTube video ID from URL.

    Args:
        url: YouTube URL

    Returns:
        YouTube video ID or None if not found
    """
    try:
        parsed = urlparse(url.lower())
        query_params = parse_qs(parsed.query)

        # Standard YouTube URL: ?v=VIDEO_ID
        if 'v' in query_params:
            return query_params['v'][0]

        # Short URL: youtu.be/VIDEO_ID
        if 'youtu.be' in parsed.netloc:
            return parsed.path.lstrip('/')

        # Embed URL: /embed/VIDEO_ID
        if '/embed/' in parsed.path:
            return parsed.path.split('/embed/')[-1]

        return None

    except Exception:
        return None


def is_rss_feed_url(url: str) -> bool:
    """
    Check if URL appears to be an RSS feed.

    Args:
        url: URL to check

    Returns:
        True if likely RSS feed
    """
    rss_indicators = [
        '/feed',
        '/rss',
        '/rss.xml',
        '/feed.xml',
        '.rss',
        '.xml',
        'rss.xml',
        'feed.xml'
    ]

    url_lower = url.lower()
    return any(indicator in url_lower for indicator in rss_indicators)


def extract_domain(url: str) -> str:
    """
    Extract domain from URL.

    Args:
        url: URL to extract domain from

    Returns:
        Domain name or empty string
    """
    try:
        parsed = urlparse(url.lower())
        return parsed.netloc
    except Exception:
        return ""


def create_canonical_id(
    url: str,
    guid: Optional[str] = None,
    title: Optional[str] = None
) -> str:
    """
    Create canonical ID from URL/GUID/title.

    Priority: GUID → URL → Title-based ID

    Args:
        url: Content URL
        guid: Content GUID (optional)
        title: Content title (optional)

    Returns:
        Canonical ID string
    """
    if guid:
        return f"guid_{guid}"
    elif url:
        normalized = normalize_url(url)
        # Create short hash of normalized URL for ID
        import hashlib
        url_hash = hashlib.md5(normalized.encode()).hexdigest()[:8]
        return f"url_{url_hash}"
    elif title:
        # Create ID from title
        import re
        title_clean = re.sub(r'[^a-z0-9]', '-', title.lower())
        title_clean = re.sub(r'-+', '-', title_clean).strip('-')
        return f"title_{title_clean}"
    else:
        return "unknown"


def compare_urls(url1: str, url2: str) -> bool:
    """
    Compare two URLs after normalization.

    Args:
        url1: First URL
        url2: Second URL

    Returns:
        True if URLs are equivalent after normalization
    """
    return normalize_url(url1) == normalize_url(url2)


def sanitize_url_for_display(url: str, max_length: int = 100) -> str:
    """
    Sanitize URL for safe display in logs and UI.

    Args:
        url: URL to sanitize
        max_length: Maximum length for display

    Returns:
        Sanitized URL safe for display
    """
    if not url:
        return ""

    # Remove sensitive parameters
    try:
        parsed = urlparse(url)
        query_params = parse_qs(parsed.query)

        # Remove potentially sensitive parameters
        sensitive_params = [
            'api_key', 'token', 'password', 'secret', 'key',
            'auth', 'session', 'sid', 'phpsessid'
        ]

        safe_params = {}
        for key, values in query_params.items():
            if key.lower() not in sensitive_params:
                safe_params[key] = values

        # Reconstruct URL with safe parameters
        safe_query = urlencode(safe_params, doseq=True)
        safe_url = urlunparse((
            parsed.scheme,
            parsed.netloc,
            parsed.path,
            parsed.params,
            safe_query,
            ""  # Remove fragment for safety
        ))

        # Truncate if too long
        if len(safe_url) > max_length:
            safe_url = safe_url[:max_length-3] + "..."

        return safe_url

    except Exception:
        # If sanitization fails, return truncated original
        return url[:max_length-3] + "..." if len(url) > max_length else url