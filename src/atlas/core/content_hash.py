"""
Content hashing for Atlas v4.

Implements canonical content hash generation for deduplication.
Based on PRD specification: SHA256 of lowercase(title) + first 500 chars of body without whitespace.
"""

import hashlib
import re
from typing import Optional


def normalize_content_for_hash(content: str) -> str:
    """
    Normalize content for hashing by removing whitespace and converting to lowercase.

    Args:
        content: Raw content string

    Returns:
        Normalized content string
    """
    # Remove all whitespace characters (spaces, tabs, newlines, etc.)
    content_no_whitespace = re.sub(r'\s+', '', content)

    # Convert to lowercase
    normalized = content_no_whitespace.lower()

    return normalized


def generate_content_hash(title: str, content: str) -> str:
    """
    Generate canonical content hash for deduplication.

    Hash algorithm: SHA256 of lowercase(title) + first 500 characters of body after removing all whitespace

    Args:
        title: Content title
        content: Content body

    Returns:
        SHA256 hash as hex string
    """
    # Normalize title
    normalized_title = title.lower().strip()

    # Get first 500 characters of content and normalize
    content_preview = content[:500] if len(content) > 500 else content
    normalized_content = normalize_content_for_hash(content_preview)

    # Combine title and normalized content
    hash_input = f"{normalized_title}{normalized_content}"

    # Generate SHA256 hash
    hash_object = hashlib.sha256(hash_input.encode('utf-8'))
    hash_hex = hash_object.hexdigest()

    return hash_hex


def generate_url_hash(url: str) -> str:
    """
    Generate hash for URL-based deduplication.

    Args:
        url: URL to hash

    Returns:
        SHA256 hash as hex string
    """
    hash_object = hashlib.sha256(url.encode('utf-8'))
    return hash_object.hexdigest()


def generate_guid_hash(guid: str) -> str:
    """
    Generate hash for GUID-based deduplication.

    Args:
        guid: GUID to hash

    Returns:
        SHA256 hash as hex string
    """
    hash_object = hashlib.sha256(guid.encode('utf-8'))
    return hash_object.hexdigest()


def compare_content_hashes(hash1: str, hash2: str) -> bool:
    """
    Compare two content hashes for equality.

    Args:
        hash1: First hash
        hash2: Second hash

    Returns:
        True if hashes are equal
    """
    return hash1.lower() == hash2.lower()


def validate_content_hash(content_hash: str) -> bool:
    """
    Validate that a content hash is a valid SHA256 hash.

    Args:
        content_hash: Hash string to validate

    Returns:
        True if valid SHA256 hash
    """
    # SHA256 hashes should be 64 hexadecimal characters
    if len(content_hash) != 64:
        return False

    # Check if all characters are hexadecimal
    try:
        int(content_hash, 16)
        return True
    except ValueError:
        return False


def create_content_identifier(
    title: str,
    content: str,
    url: Optional[str] = None,
    guid: Optional[str] = None
) -> dict:
    """
    Create a comprehensive content identifier for deduplication.

    Priority order per PRD: GUID → Canonical URL → Content Hash

    Args:
        title: Content title
        content: Content body
        url: Content URL (optional)
        guid: Content GUID (optional)

    Returns:
        Dictionary with all possible identifiers
    """
    identifiers = {
        'content_hash': generate_content_hash(title, content),
    }

    if guid:
        identifiers['guid'] = guid
        identifiers['guid_hash'] = generate_guid_hash(guid)

    if url:
        identifiers['url'] = url
        identifiers['url_hash'] = generate_url_hash(url)

    return identifiers


# Utility function for testing and debugging
def debug_content_hash(title: str, content: str) -> dict:
    """
    Debug content hash generation by showing intermediate steps.

    Args:
        title: Content title
        content: Content body

    Returns:
        Dictionary with debugging information
    """
    normalized_title = title.lower().strip()
    content_preview = content[:500] if len(content) > 500 else content
    normalized_content = normalize_content_for_hash(content_preview)
    hash_input = f"{normalized_title}{normalized_content}"

    return {
        'original_title': title,
        'normalized_title': normalized_title,
        'original_content_preview': content_preview,
        'normalized_content': normalized_content,
        'hash_input': hash_input,
        'hash_input_length': len(hash_input),
        'final_hash': generate_content_hash(title, content)
    }