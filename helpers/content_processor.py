#!/usr/bin/env python3
"""
Enhanced Content Processor - Advanced content processing and analysis
Provides comprehensive content processing capabilities beyond basic ingestion.
"""

import json
import os
import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from pathlib import Path

from helpers.utils import log_info, log_error


class ContentProcessor:
    """
    Enhanced content processor for advanced analysis and processing.

    Provides capabilities beyond basic ingestion including:
    - Content enhancement and enrichment
    - Advanced text processing and analysis
    - Content optimization and formatting
    - Metadata extraction and augmentation
    """

    def __init__(self, config: Dict[str, Any] = None):
        """Initialize ContentProcessor with configuration."""
        self.config = config or {}

    def process_content(self,
                       content: str,
                       metadata: Dict[str, Any] = None,
                       options: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Process content with advanced analysis and enhancement.

        Args:
            content: Raw content text
            metadata: Content metadata
            options: Processing options

        Returns:
            Dict containing processed content and analysis
        """
        try:
            metadata = metadata or {}
            options = options or {}

            result = {
                "original_content": content,
                "processed_content": content,
                "metadata": metadata,
                "processing_info": {
                    "timestamp": datetime.now().isoformat(),
                    "processor": "ContentProcessor",
                    "version": "1.0"
                }
            }

            # Basic content processing
            processed_content = self._clean_content(content)
            result["processed_content"] = processed_content

            # Extract and enhance metadata
            enhanced_metadata = self._extract_metadata(processed_content, metadata)
            result["enhanced_metadata"] = enhanced_metadata

            # Content analysis
            analysis = self._analyze_content(processed_content)
            result["analysis"] = analysis

            # Content statistics
            stats = self._calculate_statistics(processed_content)
            result["statistics"] = stats

            log_info(f"Content processed successfully: {len(content)} -> {len(processed_content)} characters")
            return result

        except Exception as e:
            log_error(f"Error processing content: {str(e)}")
            return {
                "error": str(e),
                "original_content": content,
                "metadata": metadata or {}
            }

    def _clean_content(self, content: str) -> str:
        """Clean and normalize content text."""
        if not content:
            return ""

        # Basic cleaning
        cleaned = content.strip()

        # Remove excessive whitespace
        cleaned = re.sub(r'\n\s*\n\s*\n', '\n\n', cleaned)
        cleaned = re.sub(r' +', ' ', cleaned)

        # Remove common artifacts
        cleaned = re.sub(r'\[.*?\]', '', cleaned)  # Remove references
        cleaned = re.sub(r'^\s*[-*•]\s*', '', cleaned, flags=re.MULTILINE)  # Remove bullet points

        return cleaned.strip()

    def _extract_metadata(self, content: str, existing_metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Extract and enhance metadata from content."""
        metadata = existing_metadata.copy()

        if not content:
            return metadata

        # Extract basic metrics
        metadata["word_count"] = len(content.split())
        metadata["character_count"] = len(content)
        metadata["paragraph_count"] = len([p for p in content.split('\n\n') if p.strip()])

        # Extract patterns
        emails = re.findall(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', content)
        urls = re.findall(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', content)

        if emails:
            metadata["extracted_emails"] = emails
        if urls:
            metadata["extracted_urls"] = urls

        # Simple topic extraction (basic keywords)
        words = re.findall(r'\b[a-zA-Z]{4,}\b', content.lower())
        word_freq = {}
        for word in words:
            word_freq[word] = word_freq.get(word, 0) + 1

        # Get top keywords
        top_keywords = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)[:10]
        metadata["top_keywords"] = [word for word, freq in top_keywords]

        return metadata

    def _analyze_content(self, content: str) -> Dict[str, Any]:
        """Perform content analysis."""
        if not content:
            return {}

        analysis = {}

        # Readability analysis
        sentences = content.split('.')
        words = content.split()

        if sentences:
            avg_sentence_length = len(words) / len(sentences)
            analysis["average_sentence_length"] = avg_sentence_length
            analysis["readability_score"] = self._calculate_readability(avg_sentence_length)

        # Content type detection
        analysis["content_type"] = self._detect_content_type(content)

        # Language detection (basic)
        analysis["language"] = "en"  # Default, could be enhanced with language detection

        # Structure analysis
        analysis["has_headings"] = bool(re.search(r'^#+\s', content, re.MULTILINE))
        analysis["has_lists"] = bool(re.search(r'^\s*[-*]\s', content, re.MULTILINE))
        analysis["has_code"] = bool(re.search(r'```|`[^`]+`', content))

        return analysis

    def _calculate_statistics(self, content: str) -> Dict[str, Any]:
        """Calculate content statistics."""
        if not content:
            return {}

        stats = {}

        # Basic counts
        stats["characters"] = len(content)
        stats["characters_no_spaces"] = len(content.replace(' ', ''))
        stats["words"] = len(content.split())
        stats["sentences"] = len([s for s in content.split('.') if s.strip()])
        stats["paragraphs"] = len([p for p in content.split('\n\n') if p.strip()])
        stats["lines"] = len(content.split('\n'))

        # Reading time estimation (average 200 words per minute)
        if stats["words"] > 0:
            stats["estimated_reading_time_minutes"] = round(stats["words"] / 200, 1)

        return stats

    def _calculate_readability(self, avg_sentence_length: float) -> str:
        """Calculate basic readability score."""
        if avg_sentence_length < 10:
            return "easy"
        elif avg_sentence_length < 20:
            return "moderate"
        else:
            return "difficult"

    def _detect_content_type(self, content: str) -> str:
        """Detect content type based on patterns."""
        content_lower = content.lower()

        if re.search(r'```|def |class |import |function|variable', content):
            return "technical/code"
        elif re.search(r'recipe|ingredients|cook|bake|recipe', content_lower):
            return "recipe"
        elif re.search(r'news|breaking|report|update|announcement', content_lower):
            return "news"
        elif re.search(r'tutorial|how to|step by step|guide', content_lower):
            return "tutorial"
        elif re.search(r'opinion|i think|in my view|perspective', content_lower):
            return "opinion"
        else:
            return "general"

    def enhance_content(self, content: str, enhancement_type: str = "standard") -> str:
        """Enhance content with additional processing."""
        if not content:
            return content

        if enhancement_type == "markdown":
            return self._enhance_for_markdown(content)
        elif enhancement_type == "summary":
            return self._create_brief_summary(content)
        else:
            return self._standard_enhancement(content)

    def _enhance_for_markdown(self, content: str) -> str:
        """Enhance content for markdown format."""
        # Basic markdown enhancements
        enhanced = content

        # Convert simple headings
        enhanced = re.sub(r'^([A-Z][^.\n]{5,50})\n', r'## \1\n', enhanced, flags=re.MULTILINE)

        # Add emphasis to quoted text
        enhanced = re.sub(r'"([^"]{10,100})"', r'*"\1"*', enhanced)

        return enhanced

    def _create_brief_summary(self, content: str) -> str:
        """Create a brief summary of content."""
        if len(content) < 200:
            return content

        # Simple extractive summary - first and last sentences of each paragraph
        paragraphs = [p.strip() for p in content.split('\n\n') if p.strip()]

        summary_parts = []
        for para in paragraphs[:3]:  # First 3 paragraphs
            sentences = [s.strip() for s in para.split('.') if s.strip()]
            if sentences:
                summary_parts.append(sentences[0] + '.')

        return ' '.join(summary_parts)

    def _standard_enhancement(self, content: str) -> str:
        """Apply standard content enhancements."""
        enhanced = content

        # Fix common formatting issues
        enhanced = re.sub(r'\s+', ' ', enhanced)  # Multiple spaces
        enhanced = re.sub(r'\n\s*\n\s*\n+', '\n\n', enhanced)  # Multiple newlines

        # Ensure proper paragraph spacing
        enhanced = re.sub(r'\.([A-Z])', r'. \1', enhanced)

        return enhanced.strip()