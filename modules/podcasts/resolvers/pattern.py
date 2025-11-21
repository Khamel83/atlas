#!/usr/bin/env python3
"""
Pattern Resolver

Uses URL patterns and heuristics to construct likely transcript URLs
without fetching content first.
"""

import logging
import re
from typing import List, Dict, Any
from urllib.parse import urlparse
from datetime import datetime

from modules.podcasts.store import Episode

logger = logging.getLogger(__name__)


class PatternResolver:
    """Resolver that constructs transcript URLs using patterns"""

    def __init__(self):
        # Site-specific URL patterns for transcript construction
        self.site_patterns = {
            "slate.com": {
                "episode_to_transcript": [
                    # /podcasts/political-gabfest/2023/12/episode -> /transcripts/political-gabfest/2023/12/episode
                    lambda url: url.replace("/podcasts/", "/transcripts/"),
                    # Add /transcript suffix
                    lambda url: (
                        f"{url}/transcript"
                        if not url.endswith("/")
                        else f"{url}transcript"
                    ),
                ],
                "confidence_base": 0.6,
            },
            "conversationswithtyler.com": {
                "episode_to_transcript": [
                    # /episodes/name -> /episodes/name/transcript
                    lambda url: (
                        f"{url}/transcript"
                        if not url.endswith("/")
                        else f"{url}transcript"
                    ),
                    # /episodes/name -> /transcripts/name
                    lambda url: url.replace("/episodes/", "/transcripts/"),
                ],
                "confidence_base": 0.7,
            },
            "npr.org": {
                "episode_to_transcript": [
                    # Add /transcript suffix
                    lambda url: f"{url}/transcript",
                    # Add transcript parameter
                    lambda url: f"{url}?transcript=true",
                ],
                "confidence_base": 0.5,
            },
            "nytimes.com": {
                "episode_to_transcript": [
                    # NYT podcast pages sometimes have transcripts embedded
                    lambda url: url,  # Check same page for embedded transcript
                ],
                "confidence_base": 0.4,
            },
            "radiolab.org": {
                "episode_to_transcript": [
                    # /story/episode-name -> /story/episode-name/transcript
                    lambda url: f"{url}/transcript",
                    # /episodes/episode-name -> /transcripts/episode-name
                    lambda url: url.replace("/episodes/", "/transcripts/"),
                ],
                "confidence_base": 0.6,
            },
            "stratechery.com": {
                "episode_to_transcript": [
                    # Stratechery posts often contain full transcript
                    lambda url: url,  # Check same page
                ],
                "confidence_base": 0.5,
            },
        }

        # Generic patterns to try on any site
        self.generic_patterns = [
            # Add /transcript path
            lambda url: f"{url}/transcript",
            lambda url: f"{url}/transcription",
            lambda url: f"{url}/full-text",
            lambda url: f"{url}/show-notes",
            # Replace episode with transcript
            lambda url: url.replace("/episode/", "/transcript/"),
            lambda url: url.replace("/episodes/", "/transcripts/"),
            lambda url: url.replace("/show/", "/transcript/"),
            lambda url: url.replace("/shows/", "/transcripts/"),
            # Add query parameters
            lambda url: f"{url}?transcript=true",
            lambda url: f"{url}?format=transcript",
            lambda url: f"{url}?view=transcript",
            # Subdomain variations
            lambda url: url.replace("www.", "transcripts."),
            lambda url: url.replace("://www.", "://transcript."),
        ]

    def resolve(
        self, episode: Episode, podcast_config: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Generate likely transcript URLs using patterns

        Returns list of transcript sources with:
        - url: constructed transcript URL
        - confidence: 0.0-1.0 confidence score
        - resolver: 'pattern'
        - metadata: additional info
        """
        sources = []

        try:
            if not episode.url:
                return sources

            domain = urlparse(episode.url).netloc.lower()

            # Remove www. prefix for matching
            domain_key = domain.replace("www.", "")

            # Try site-specific patterns first
            if domain_key in self.site_patterns:
                pattern_config = self.site_patterns[domain_key]
                patterns = pattern_config["episode_to_transcript"]
                base_confidence = pattern_config["confidence_base"]

                for i, pattern_func in enumerate(patterns):
                    try:
                        transcript_url = pattern_func(episode.url)
                        if transcript_url and transcript_url != episode.url:
                            # Decrease confidence for later patterns
                            confidence = base_confidence - (i * 0.1)

                            sources.append(
                                {
                                    "url": transcript_url,
                                    "confidence": max(confidence, 0.2),
                                    "resolver": "pattern",
                                    "metadata": {
                                        "pattern_type": "site_specific",
                                        "domain": domain_key,
                                        "pattern_index": i,
                                        "original_url": episode.url,
                                        "episode_title": episode.title,
                                    },
                                }
                            )
                    except Exception as e:
                        logger.debug(
                            f"Error applying site pattern {i} to {episode.url}: {e}"
                        )

            # Try generic patterns
            for i, pattern_func in enumerate(self.generic_patterns):
                try:
                    transcript_url = pattern_func(episode.url)
                    if transcript_url and transcript_url != episode.url:
                        # Check if we already have this URL
                        if not any(s["url"] == transcript_url for s in sources):
                            # Lower confidence for generic patterns
                            confidence = 0.3 - (i * 0.02)

                            sources.append(
                                {
                                    "url": transcript_url,
                                    "confidence": max(confidence, 0.1),
                                    "resolver": "pattern",
                                    "metadata": {
                                        "pattern_type": "generic",
                                        "pattern_index": i,
                                        "original_url": episode.url,
                                        "episode_title": episode.title,
                                    },
                                }
                            )
                except Exception as e:
                    logger.debug(
                        f"Error applying generic pattern {i} to {episode.url}: {e}"
                    )

            # Try RSS-based patterns if we have RSS metadata
            rss_sources = self._generate_rss_based_patterns(episode, podcast_config)
            sources.extend(rss_sources)

            logger.info(
                f"Pattern resolver generated {len(sources)} potential URLs for: {episode.title}"
            )

        except Exception as e:
            logger.error(f"Error in pattern resolver for episode {episode.title}: {e}")

        return sources

    def _generate_rss_based_patterns(
        self, episode: Episode, podcast_config: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Generate transcript URLs based on RSS feed patterns"""
        sources = []

        try:
            # Get RSS URL from podcast config
            rss_url = podcast_config.get("rss_url", "")
            site_url = podcast_config.get("site_url", "")

            if not site_url:
                return sources

            # Try to construct episode URL from episode data
            if episode.guid and episode.publish_date:
                # Parse publish date for date-based URLs
                try:
                    if isinstance(episode.publish_date, str):
                        pub_date = datetime.fromisoformat(
                            episode.publish_date.replace("Z", "+00:00")
                        )
                    else:
                        pub_date = episode.publish_date

                    year = pub_date.year
                    month = pub_date.month

                    # Common podcast URL patterns
                    title_slug = self._create_slug(episode.title)

                    url_patterns = [
                        f"{site_url}/transcripts/{year}/{month:02d}/{title_slug}",
                        f"{site_url}/transcript/{year}/{title_slug}",
                        f"{site_url}/episodes/{title_slug}/transcript",
                        f"{site_url}/transcripts/{title_slug}",
                        f"{site_url}/{year}/{month:02d}/{title_slug}/transcript",
                    ]

                    for i, url in enumerate(url_patterns):
                        sources.append(
                            {
                                "url": url,
                                "confidence": 0.4 - (i * 0.05),
                                "resolver": "pattern",
                                "metadata": {
                                    "pattern_type": "rss_based",
                                    "pattern_index": i,
                                    "constructed_from": "title_and_date",
                                    "episode_title": episode.title,
                                    "publish_date": episode.publish_date,
                                },
                            }
                        )

                except Exception as e:
                    logger.debug(f"Error creating date-based patterns: {e}")

        except Exception as e:
            logger.error(f"Error generating RSS-based patterns: {e}")

        return sources

    def _create_slug(self, title: str) -> str:
        """Create URL slug from episode title"""
        if not title:
            return ""

        # Convert to lowercase and replace special chars
        slug = re.sub(r"[^\w\s-]", "", title.lower())
        slug = re.sub(r"[-\s]+", "-", slug)
        slug = slug.strip("-")

        # Limit length
        if len(slug) > 80:
            words = slug.split("-")
            slug = "-".join(words[:8])  # Take first 8 words

        return slug

    def validate_pattern_url(self, url: str) -> bool:
        """Quick validation of pattern-generated URL"""
        try:
            parsed = urlparse(url)

            # Must have scheme and netloc
            if not parsed.scheme or not parsed.netloc:
                return False

            # Avoid obviously bad patterns
            if any(
                bad in url.lower()
                for bad in ["example.com", "localhost", "test.", ".test"]
            ):
                return False

            return True

        except Exception:
            return False
