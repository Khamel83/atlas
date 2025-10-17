"""
Content validation for Atlas v4.

Implements content validation rules as specified in PRD.
Enforces minimum thresholds, required fields, and content quality standards.
"""

import re
from datetime import datetime
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass

from .content_hash import validate_content_hash
from .url_normalizer import normalize_url, is_youtube_url, extract_youtube_video_id


@dataclass
class ValidationResult:
    """Result of content validation."""
    is_valid: bool
    errors: List[str]
    warnings: List[str]
    metadata: Dict[str, Any]


class ValidationError:
    """Content validation errors."""
    pass


class ContentValidator:
    """Validates content items against Atlas standards."""

    def __init__(self):
        # Validation thresholds from PRD
        self.thresholds = {
            'newsletter': {'min_length': 300},
            'article': {'min_length': 300},
            'podcast': {'min_description_length': 100, 'min_transcript_length': 500},
            'youtube': {'min_description_length': 100, 'min_transcript_length': 500},
            'email': {'min_length': 50}
        }

        # Required fields for all content types
        self.required_fields = ['id', 'type', 'source', 'title', 'date', 'ingested_at']

    def validate_content_item(self, content_item: Dict[str, Any]) -> ValidationResult:
        """
        Validate a complete content item.

        Args:
            content_item: Content item dictionary with frontmatter and content

        Returns:
            ValidationResult with validation status and details
        """
        errors = []
        warnings = []
        metadata = {}

        # Extract content type
        content_type = content_item.get('type', '').lower()
        if not content_type:
            errors.append("Content type is required")
            return ValidationResult(False, errors, warnings, metadata)

        # Validate required fields
        self._validate_required_fields(content_item, errors)

        # Validate content hash
        self._validate_content_hash(content_item, errors)

        # Validate dates
        self._validate_dates(content_item, errors, warnings)

        # Validate URLs
        self._validate_urls(content_item, errors, warnings)

        # Validate content based on type
        if content_type == 'newsletter':
            self._validate_newsletter(content_item, errors, warnings)
        elif content_type == 'article':
            self._validate_article(content_item, errors, warnings)
        elif content_type == 'podcast':
            self._validate_podcast(content_item, errors, warnings)
        elif content_type == 'youtube':
            self._validate_youtube(content_item, errors, warnings)
        elif content_type == 'email':
            self._validate_email(content_item, errors, warnings)

        # Validate tags
        self._validate_tags(content_item, warnings)

        # Create metadata
        metadata = {
            'content_type': content_type,
            'validation_timestamp': datetime.now().isoformat(),
            'error_count': len(errors),
            'warning_count': len(warnings)
        }

        is_valid = len(errors) == 0
        return ValidationResult(is_valid, errors, warnings, metadata)

    def _validate_required_fields(self, content_item: Dict[str, Any], errors: List[str]) -> None:
        """Validate required fields are present and non-empty."""
        for field in self.required_fields:
            value = content_item.get(field)
            if value is None or (isinstance(value, str) and not value.strip()):
                errors.append(f"Required field '{field}' is missing or empty")

    def _validate_content_hash(self, content_item: Dict[str, Any], errors: List[str]) -> None:
        """Validate content hash is present and valid."""
        content_hash = content_item.get('content_hash')
        if not content_hash:
            errors.append("Content hash is required")
        elif not validate_content_hash(content_hash):
            errors.append("Content hash is not a valid SHA256 hash")

    def _validate_dates(self, content_item: Dict[str, Any], errors: List[str], warnings: List[str]) -> None:
        """Validate date fields are in ISO8601 format."""
        date_fields = ['date', 'published_at', 'ingested_at', 'updated_at']

        for field in date_fields:
            if field in content_item:
                date_value = content_item[field]
                if isinstance(date_value, str):
                    try:
                        # Try to parse as ISO8601
                        datetime.fromisoformat(date_value.replace('Z', '+00:00'))
                    except ValueError:
                        errors.append(f"Date field '{field}' is not in valid ISO8601 format: {date_value}")
                elif not isinstance(date_value, datetime):
                    warnings.append(f"Date field '{field}' should be string in ISO8601 format")

    def _validate_urls(self, content_item: Dict[str, Any], errors: List[str], warnings: List[str]) -> None:
        """Validate URL fields are properly formatted."""
        url_fields = ['url', 'audio_url', 'video_url']

        for field in url_fields:
            if field in content_item and content_item[field]:
                url = content_item[field]
                if not self._is_valid_url(url):
                    errors.append(f"URL field '{field}' is not a valid URL: {url}")

    def _is_valid_url(self, url: str) -> bool:
        """Check if URL has valid format."""
        url_pattern = re.compile(
            r'^https?://'  # http:// or https://
            r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
            r'localhost|'  # localhost...
            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
            r'(?::\d+)?'  # optional port
            r'(?:/?|[/?]\S+)$', re.IGNORECASE)
        return url_pattern.match(url) is not None

    def _validate_newsletter(self, content_item: Dict[str, Any], errors: List[str], warnings: List[str]) -> None:
        """Validate newsletter content."""
        content = content_item.get('content', '')
        min_length = self.thresholds['newsletter']['min_length']

        if len(content) < min_length:
            errors.append(f"Newsletter content too short: {len(content)} chars (minimum {min_length})")

        # Check for newsletter-specific structure
        if not content_item.get('author'):
            warnings.append("Newsletter missing author information")

    def _validate_article(self, content_item: Dict[str, Any], errors: List[str], warnings: List[str]) -> None:
        """Validate article content."""
        content = content_item.get('content', '')
        min_length = self.thresholds['article']['min_length']

        if len(content) < min_length:
            errors.append(f"Article content too short: {len(content)} chars (minimum {min_length})")

        # Check for article-specific structure
        if not content_item.get('author'):
            warnings.append("Article missing author information")

        # Check if content has proper structure (headings, paragraphs)
        if not re.search(r'^#{1,6}\s+', content, re.MULTILINE):
            warnings.append("Article appears to lack proper markdown headings")

    def _validate_podcast(self, content_item: Dict[str, Any], errors: List[str], warnings: List[str]) -> None:
        """Validate podcast content."""
        description = content_item.get('description', '')
        transcript = content_item.get('transcript', '')
        show_notes = content_item.get('show_notes', '')

        # Check description length
        min_desc_length = self.thresholds['podcast']['min_description_length']
        if len(description) < min_desc_length:
            errors.append(f"Podcast description too short: {len(description)} chars (minimum {min_desc_length})")

        # Check for audio URL
        if not content_item.get('audio_url'):
            errors.append("Podcast missing audio_url field")

        # Check for show notes or transcript
        if not show_notes and not transcript:
            warnings.append("Podcast has neither show notes nor transcript")

        # Check transcript length if available
        if transcript:
            min_transcript_length = self.thresholds['podcast']['min_transcript_length']
            if len(transcript) < min_transcript_length:
                warnings.append(f"Podcast transcript quite short: {len(transcript)} chars")

    def _validate_youtube(self, content_item: Dict[str, Any], errors: List[str], warnings: List[str]) -> None:
        """Validate YouTube content."""
        description = content_item.get('description', '')
        transcript = content_item.get('transcript', '')
        video_url = content_item.get('url', '')

        # Check description length
        min_desc_length = self.thresholds['youtube']['min_description_length']
        if len(description) < min_desc_length:
            errors.append(f"YouTube description too short: {len(description)} chars (minimum {min_desc_length})")

        # Validate YouTube URL
        if video_url:
            if not is_youtube_url(video_url):
                errors.append(f"URL does not appear to be a YouTube URL: {video_url}")
            else:
                video_id = extract_youtube_video_id(video_url)
                if not video_id:
                    errors.append(f"Could not extract YouTube video ID from URL: {video_url}")
        else:
            errors.append("YouTube content missing URL")

        # Check for transcript
        if not transcript:
            warnings.append("YouTube video missing transcript")

        # Check transcript length if available
        if transcript:
            min_transcript_length = self.thresholds['youtube']['min_transcript_length']
            if len(transcript) < min_transcript_length:
                warnings.append(f"YouTube transcript quite short: {len(transcript)} chars")

    def _validate_email(self, content_item: Dict[str, Any], errors: List[str], warnings: List[str]) -> None:
        """Validate email content."""
        content = content_item.get('content', '')
        subject = content_item.get('subject', '')
        min_length = self.thresholds['email']['min_length']

        if len(content) < min_length:
            errors.append(f"Email content too short: {len(content)} chars (minimum {min_length})")

        # Check for email-specific fields
        if not subject:
            warnings.append("Email missing subject field")

        if not content_item.get('from'):
            errors.append("Email missing sender information")

        if not content_item.get('to'):
            errors.append("Email missing recipient information")

    def _validate_tags(self, content_item: Dict[str, Any], warnings: List[str]) -> None:
        """Validate tags are properly formatted."""
        tags = content_item.get('tags', [])

        if tags and not isinstance(tags, list):
            warnings.append("Tags field should be a list")

        if isinstance(tags, list):
            for tag in tags:
                if not isinstance(tag, str):
                    warnings.append(f"Tag should be string, got {type(tag)}")
                elif len(tag) > 50:
                    warnings.append(f"Tag quite long: {tag} ({len(tag)} chars)")

    def validate_batch(self, content_items: List[Dict[str, Any]]) -> List[ValidationResult]:
        """
        Validate multiple content items.

        Args:
            content_items: List of content items to validate

        Returns:
            List of ValidationResult objects
        """
        results = []
        for item in content_items:
            result = self.validate_content_item(item)
            results.append(result)

        return results

    def get_validation_summary(self, results: List[ValidationResult]) -> Dict[str, Any]:
        """
        Get summary of validation results.

        Args:
            results: List of ValidationResult objects

        Returns:
            Summary statistics
        """
        total = len(results)
        valid = sum(1 for r in results if r.is_valid)
        invalid = total - valid

        total_errors = sum(len(r.errors) for r in results)
        total_warnings = sum(len(r.warnings) for r in results)

        error_types = {}
        for result in results:
            for error in result.errors:
                error_type = error.split(':')[0].strip()
                error_types[error_type] = error_types.get(error_type, 0) + 1

        return {
            'total_items': total,
            'valid_items': valid,
            'invalid_items': invalid,
            'success_rate': (valid / total * 100) if total > 0 else 0,
            'total_errors': total_errors,
            'total_warnings': total_warnings,
            'common_errors': error_types
        }


# Convenience function for quick validation
def validate_content(content_item: Dict[str, Any]) -> ValidationResult:
    """
    Quick validation of a single content item.

    Args:
        content_item: Content item to validate

    Returns:
        ValidationResult object
    """
    validator = ContentValidator()
    return validator.validate_content_item(content_item)


def is_content_valid(content_item: Dict[str, Any]) -> bool:
    """
    Quick check if content item is valid.

    Args:
        content_item: Content item to check

    Returns:
        True if valid, False otherwise
    """
    result = validate_content(content_item)
    return result.is_valid