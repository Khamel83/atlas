#!/usr/bin/env python3
"""
Smart Transcript Discovery System

Learns from successful transcript sources and applies patterns to find more
transcripts from the same providers. Much more efficient than random searching.
"""

import logging
import requests
import time
import re
from typing import List, Dict, Any, Optional
from urllib.parse import urlparse
import json
from pathlib import Path
from dataclasses import dataclass
from datetime import datetime

from modules.podcasts.store import Episode

logger = logging.getLogger(__name__)


@dataclass
class TranscriptPattern:
    """Pattern for finding transcripts from a known source"""

    domain: str
    url_pattern: str  # Template with {episode_id}, {title}, etc.
    confidence: float
    success_count: int
    last_success: datetime
    selector: Optional[str] = None  # CSS selector for content


class SmartDiscoveryResolver:
    """Resolver that learns patterns from successful transcript sources"""

    def __init__(
        self, data_dir: str = "data/podcasts", user_agent: str = "Atlas-Pod/1.0"
    ):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)

        self.patterns_file = self.data_dir / "transcript_patterns.json"
        self.user_agent = user_agent
        self.timeout = 30

        # Load existing patterns
        self.patterns: Dict[str, List[TranscriptPattern]] = self._load_patterns()

        # Session for requests
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": self.user_agent})

    def resolve(
        self, episode: Episode, podcast_config: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Find transcripts using learned patterns and smart discovery
        """
        sources = []
        podcast_title = podcast_config.get("title", "")

        try:
            # 1. Apply known patterns for this podcast
            pattern_sources = self._apply_known_patterns(episode, podcast_config)
            sources.extend(pattern_sources)

            # 2. If no patterns exist, do smart discovery
            if not self._has_patterns_for_podcast(podcast_title):
                discovery_sources = self._smart_discovery(episode, podcast_config)
                sources.extend(discovery_sources)

                # Learn from any successful discoveries
                for source in discovery_sources:
                    if source.get("confidence", 0) > 0.7:
                        self._learn_pattern(source, episode, podcast_config)

            # 3. Try variations of successful patterns
            variation_sources = self._try_pattern_variations(episode, podcast_config)
            sources.extend(variation_sources)

            logger.info(
                f"Smart discovery found {len(sources)} transcript sources for: {episode.title}"
            )

        except Exception as e:
            logger.error(f"Error in smart discovery for episode {episode.title}: {e}")

        return sources

    def _load_patterns(self) -> Dict[str, List[TranscriptPattern]]:
        """Load learned patterns from disk"""
        patterns = {}

        if self.patterns_file.exists():
            try:
                with open(self.patterns_file, "r") as f:
                    data = json.load(f)

                for podcast_title, pattern_list in data.items():
                    patterns[podcast_title] = []
                    for p in pattern_list:
                        pattern = TranscriptPattern(
                            domain=p["domain"],
                            url_pattern=p["url_pattern"],
                            confidence=p["confidence"],
                            success_count=p["success_count"],
                            last_success=datetime.fromisoformat(p["last_success"]),
                            selector=p.get("selector"),
                        )
                        patterns[podcast_title].append(pattern)

            except Exception as e:
                logger.error(f"Error loading patterns: {e}")

        return patterns

    def _save_patterns(self):
        """Save learned patterns to disk"""
        try:
            data = {}
            for podcast_title, pattern_list in self.patterns.items():
                data[podcast_title] = []
                for pattern in pattern_list:
                    data[podcast_title].append(
                        {
                            "domain": pattern.domain,
                            "url_pattern": pattern.url_pattern,
                            "confidence": pattern.confidence,
                            "success_count": pattern.success_count,
                            "last_success": pattern.last_success.isoformat(),
                            "selector": pattern.selector,
                        }
                    )

            with open(self.patterns_file, "w") as f:
                json.dump(data, f, indent=2)

        except Exception as e:
            logger.error(f"Error saving patterns: {e}")

    def _has_patterns_for_podcast(self, podcast_title: str) -> bool:
        """Check if we have learned patterns for this podcast"""
        return podcast_title in self.patterns and len(self.patterns[podcast_title]) > 0

    def _apply_known_patterns(
        self, episode: Episode, podcast_config: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Apply known successful patterns for this podcast"""
        sources = []
        podcast_title = podcast_config.get("title", "")

        if podcast_title not in self.patterns:
            return sources

        for pattern in self.patterns[podcast_title]:
            try:
                # Generate URLs using the pattern
                candidate_urls = self._generate_urls_from_pattern(
                    pattern, episode, podcast_config
                )

                for url in candidate_urls:
                    try:
                        # Test the URL
                        response = self.session.get(url, timeout=self.timeout)
                        if response.status_code == 200:

                            # Extract content
                            content = self._extract_content(
                                response.text, pattern.selector
                            )

                            if content and len(content) > 500:
                                # Success! Update pattern stats
                                pattern.success_count += 1
                                pattern.last_success = datetime.now()
                                pattern.confidence = min(pattern.confidence + 0.1, 1.0)

                                sources.append(
                                    {
                                        "url": url,
                                        "confidence": pattern.confidence,
                                        "resolver": "smart_discovery",
                                        "metadata": {
                                            "content": content,
                                            "content_length": len(content),
                                            "episode_title": episode.title,
                                            "extraction_method": "learned_pattern",
                                            "pattern_domain": pattern.domain,
                                            "selector_used": pattern.selector,
                                        },
                                    }
                                )

                                # Save updated patterns
                                self._save_patterns()
                                break  # Found transcript for this pattern

                    except Exception as e:
                        logger.debug(f"Pattern URL failed {url}: {e}")
                        continue

            except Exception as e:
                logger.error(f"Error applying pattern {pattern.domain}: {e}")

        return sources

    def _generate_urls_from_pattern(
        self,
        pattern: TranscriptPattern,
        episode: Episode,
        podcast_config: Dict[str, Any],
    ) -> List[str]:
        """Generate candidate URLs from a learned pattern"""
        urls = []

        try:
            # Extract episode identifiers
            episode_data = {
                "title": episode.title or "",
                "title_slug": self._slugify(episode.title or ""),
                "podcast_title": podcast_config.get("title", ""),
                "podcast_slug": self._slugify(podcast_config.get("title", "")),
                "episode_id": getattr(episode, "episode_id", ""),
                "guid": getattr(episode, "guid", ""),
                "published_year": (
                    episode.published_at.year if episode.published_at else ""
                ),
                "published_month": (
                    episode.published_at.month if episode.published_at else ""
                ),
                "published_day": (
                    episode.published_at.day if episode.published_at else ""
                ),
            }

            # Try to format the pattern with available data
            try:
                url = pattern.url_pattern.format(**episode_data)
                urls.append(url)
            except KeyError as e:
                # Missing required field, try variations
                logger.debug(f"Missing field {e} for pattern {pattern.url_pattern}")

                # Try with partial data
                safe_data = {k: v for k, v in episode_data.items() if v}
                try:
                    url = pattern.url_pattern.format(**safe_data)
                    urls.append(url)
                except (KeyError, ValueError, IndexError):
                    pass  # Pattern doesn't match available data

        except Exception as e:
            logger.error(f"Error generating URLs from pattern: {e}")

        return urls

    def _slugify(self, text: str) -> str:
        """Convert text to URL-friendly slug"""
        if not text:
            return ""

        # Convert to lowercase and replace spaces/special chars with hyphens
        slug = re.sub(r"[^\w\s-]", "", text).strip().lower()
        slug = re.sub(r"[-\s]+", "-", slug)

        return slug

    def _smart_discovery(
        self, episode: Episode, podcast_config: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Smart discovery of new transcript sources"""
        sources = []

        podcast_title = podcast_config.get("title", "")
        episode_title = episode.title or ""

        # Common transcript service patterns to try
        discovery_patterns = [
            # Rev.com patterns
            "https://www.rev.com/transcript/{podcast_slug}-{episode_slug}",
            "https://www.rev.com/transcript/{podcast_slug}/{episode_slug}",
            # Otter.ai patterns
            "https://otter.ai/u/{podcast_slug}/{episode_slug}",
            # Podcast website patterns
            "https://{podcast_slug}.com/transcript/{episode_slug}",
            "https://{podcast_slug}.com/episodes/{episode_slug}/transcript",
            "https://{podcast_slug}.com/{episode_slug}-transcript",
            # Common blog patterns
            "https://medium.com/@{podcast_slug}/{episode_slug}-transcript",
            "https://{podcast_slug}.substack.com/p/{episode_slug}-transcript",
            # Fan transcript sites
            "https://podscripts.co/{podcast_slug}/{episode_slug}",
            "https://transcripts.{podcast_slug}.com/{episode_slug}",
        ]

        episode_data = {
            "podcast_slug": self._slugify(podcast_title),
            "episode_slug": self._slugify(episode_title),
            "title_slug": self._slugify(episode_title),
        }

        for pattern in discovery_patterns[:10]:  # Limit attempts
            try:
                url = pattern.format(**episode_data)

                # Test the URL
                response = self.session.get(url, timeout=self.timeout)
                if response.status_code == 200:

                    content = self._extract_content(response.text)

                    if content and len(content) > 500:
                        confidence = self._calculate_discovery_confidence(
                            url, content, episode
                        )

                        if confidence > 0.5:
                            sources.append(
                                {
                                    "url": url,
                                    "confidence": confidence,
                                    "resolver": "smart_discovery",
                                    "metadata": {
                                        "content": content,
                                        "content_length": len(content),
                                        "episode_title": episode.title,
                                        "extraction_method": "smart_discovery",
                                        "discovery_pattern": pattern,
                                    },
                                }
                            )

            except Exception as e:
                logger.debug(f"Discovery pattern failed {pattern}: {e}")
                continue

            # Rate limiting
            time.sleep(0.5)

        return sources

    def _try_pattern_variations(
        self, episode: Episode, podcast_config: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Try variations of successful patterns from other similar podcasts"""
        sources = []

        # Get patterns from other podcasts that might work
        all_patterns = []
        for podcast, patterns in self.patterns.items():
            if podcast != podcast_config.get("title", ""):
                all_patterns.extend(patterns)

        # Sort by success rate
        all_patterns.sort(key=lambda p: p.success_count, reverse=True)

        # Try top patterns
        for pattern in all_patterns[:5]:
            try:
                urls = self._generate_urls_from_pattern(
                    pattern, episode, podcast_config
                )

                for url in urls[:2]:  # Limit attempts per pattern
                    try:
                        response = self.session.get(url, timeout=self.timeout)
                        if response.status_code == 200:

                            content = self._extract_content(
                                response.text, pattern.selector
                            )

                            if content and len(content) > 500:
                                confidence = (
                                    self._calculate_discovery_confidence(
                                        url, content, episode
                                    )
                                    * 0.8
                                )  # Lower confidence for cross-podcast patterns

                                if confidence > 0.4:
                                    sources.append(
                                        {
                                            "url": url,
                                            "confidence": confidence,
                                            "resolver": "smart_discovery",
                                            "metadata": {
                                                "content": content,
                                                "content_length": len(content),
                                                "episode_title": episode.title,
                                                "extraction_method": "pattern_variation",
                                                "source_pattern_domain": pattern.domain,
                                            },
                                        }
                                    )
                                    break

                    except Exception as e:
                        logger.debug(f"Pattern variation failed {url}: {e}")
                        continue

            except Exception as e:
                logger.error(f"Error trying pattern variation: {e}")

        return sources

    def _extract_content(
        self, html: str, selector: Optional[str] = None
    ) -> Optional[str]:
        """Extract transcript content from HTML"""
        try:
            from bs4 import BeautifulSoup

            soup = BeautifulSoup(html, "html.parser")

            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()

            if selector:
                # Use specific selector
                element = soup.select_one(selector)
                if element:
                    return element.get_text(separator="\n", strip=True)

            # Generic extraction
            selectors = [
                ".transcript",
                ".transcription",
                ".episode-transcript",
                ".post-content",
                ".entry-content",
                ".content",
                "main",
                "article",
                "[data-transcript]",
            ]

            for sel in selectors:
                element = soup.select_one(sel)
                if element:
                    text = element.get_text(separator="\n", strip=True)
                    if len(text) > 500:
                        return text

            # Fallback
            text = soup.get_text(separator="\n", strip=True)
            if len(text) > 1000 and self._looks_like_transcript(text):
                return text

        except ImportError:
            logger.error("BeautifulSoup not available")
        except Exception as e:
            logger.error(f"Error extracting content: {e}")

        return None

    def _looks_like_transcript(self, text: str) -> bool:
        """Check if text looks like a transcript"""
        if len(text) < 500:
            return False

        # Look for dialog patterns
        dialog_patterns = [
            r"[A-Z][a-z]+\s*:\s*",  # "Speaker: "
            r"[A-Z]+\s*:\s*",  # "HOST: "
        ]

        dialog_matches = 0
        for pattern in dialog_patterns:
            matches = re.findall(pattern, text)
            dialog_matches += len(matches)

        return dialog_matches >= 5

    def _calculate_discovery_confidence(
        self, url: str, content: str, episode: Episode
    ) -> float:
        """Calculate confidence for discovered content"""
        confidence = 0.0

        # Content length
        if len(content) > 5000:
            confidence += 0.4
        elif len(content) > 2000:
            confidence += 0.3
        elif len(content) > 500:
            confidence += 0.2

        # Dialog patterns
        if self._looks_like_transcript(content):
            confidence += 0.3

        # URL quality
        url_lower = url.lower()
        if "transcript" in url_lower:
            confidence += 0.2
        elif any(word in url_lower for word in ["rev.com", "otter.ai"]):
            confidence += 0.3

        # Episode title matching
        if episode.title:
            title_words = set(episode.title.lower().split())
            content_words = set(content.lower().split())

            overlap = len(title_words.intersection(content_words))
            if overlap >= 3:
                confidence += 0.2

        return min(confidence, 1.0)

    def _learn_pattern(
        self, source: Dict[str, Any], episode: Episode, podcast_config: Dict[str, Any]
    ):
        """Learn a new pattern from a successful source"""
        try:
            url = source["url"]
            domain = urlparse(url).netloc
            podcast_title = podcast_config.get("title", "")

            # Try to generalize the URL into a pattern
            pattern_url = self._generalize_url(url, episode, podcast_config)

            if pattern_url:
                # Create new pattern
                pattern = TranscriptPattern(
                    domain=domain,
                    url_pattern=pattern_url,
                    confidence=source.get("confidence", 0.7),
                    success_count=1,
                    last_success=datetime.now(),
                    selector=source.get("metadata", {}).get("selector_used"),
                )

                # Add to patterns
                if podcast_title not in self.patterns:
                    self.patterns[podcast_title] = []

                self.patterns[podcast_title].append(pattern)
                self._save_patterns()

                logger.info(f"Learned new pattern for {podcast_title}: {pattern_url}")

        except Exception as e:
            logger.error(f"Error learning pattern: {e}")

    def _generalize_url(
        self, url: str, episode: Episode, podcast_config: Dict[str, Any]
    ) -> Optional[str]:
        """Convert a successful URL into a reusable pattern"""
        try:
            # Replace episode-specific parts with placeholders
            generalized = url

            if episode.title:
                title_slug = self._slugify(episode.title)
                if title_slug in url:
                    generalized = generalized.replace(title_slug, "{episode_slug}")

            podcast_title = podcast_config.get("title", "")
            if podcast_title:
                podcast_slug = self._slugify(podcast_title)
                if podcast_slug in url:
                    generalized = generalized.replace(podcast_slug, "{podcast_slug}")

            # Only return if we actually generalized something
            if generalized != url and "{" in generalized:
                return generalized

        except Exception as e:
            logger.error(f"Error generalizing URL: {e}")

        return None
