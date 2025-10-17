import hashlib

from .url_utils import normalize_url


def link_uid(url: str) -> str:
    """Return a stable 16-char UID for *url* using SHA-1 of the normalised URL."""
    canonical = normalize_url(url)
    return hashlib.sha1(canonical.encode("utf-8")).hexdigest()[:16]
