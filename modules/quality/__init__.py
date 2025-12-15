"""
Atlas Quality Module - Content verification and quality scoring.

This module provides:
- ContentVerifier: Unified quality checking for all content types
- verify_file(): Quick single-file verification
- verify_all(): Full system verification with reporting

Usage:
    from modules.quality import verify_file, ContentVerifier

    # Quick check
    result = verify_file("/path/to/content.md")
    print(f"Quality: {result.quality} Score: {result.score}")

    # Full verification
    verifier = ContentVerifier()
    report = verifier.verify_all()
"""

from .verifier import (
    ContentVerifier,
    VerificationResult,
    QualityLevel,
    verify_file,
    verify_content,
)

__all__ = [
    'ContentVerifier',
    'VerificationResult',
    'QualityLevel',
    'verify_file',
    'verify_content',
]
