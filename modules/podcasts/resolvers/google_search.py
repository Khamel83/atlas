#!/usr/bin/env python3
"""
Google Search Transcript Resolver

Uses Google search to find podcast transcripts that exist on external sites,
transcript services, fan sites, and other sources we're currently missing.
"""

import logging
import requests
import time
import re
from typing import List, Dict, Any, Optional
from urllib.parse import urlparse
import random

from modules.podcasts.store import Episode

logger = logging.getLogger(__name__)


class GoogleSearchResolver:
    """Resolver that uses Google search to find external transcript sources"""

    def __init__(self, user_agent: str = "Atlas-Pod/1.0", timeout: int = 30):
        self.user_agent = user_agent
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": self.user_agent})

        # Rate limiting for Google
        self.last_search_time = 0
        self.min_delay = 2.0  # Minimum 2 seconds between searches

    def resolve(
        self, episode: Episode, podcast_config: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Search Google for external transcript sources

        Returns list of transcript sources with:
        - url: source URL
        - confidence: 0.0-1.0 confidence score
        - resolver: 'google_search'
        - metadata: search info and snippet
        """
        sources = []

        try:
            # Rate limiting
            self._rate_limit()

            # Build search queries
            search_queries = self._build_search_queries(episode, podcast_config)

            for query in search_queries[:3]:  # Limit to top 3 queries
                try:
                    results = self._google_search(query)

                    for result in results:
                        transcript_sources = self._process_search_result(
                            result, episode, query
                        )
                        sources.extend(transcript_sources)

                    # Add delay between queries
                    time.sleep(random.uniform(1.0, 3.0))

                except Exception as e:
                    logger.error(f"Error processing search query '{query}': {e}")

            logger.info(
                f"Google search found {len(sources)} potential transcript sources for: {episode.title}"
            )

        except Exception as e:
            logger.error(
                f"Error in Google search resolver for episode {episode.title}: {e}"
            )

        return sources

    def _rate_limit(self):
        """Apply rate limiting for Google searches"""
        current_time = time.time()
        time_since_last = current_time - self.last_search_time

        if time_since_last < self.min_delay:
            sleep_time = self.min_delay - time_since_last + random.uniform(0.5, 1.5)
            time.sleep(sleep_time)

        self.last_search_time = time.time()

    def _build_search_queries(
        self, episode: Episode, podcast_config: Dict[str, Any]
    ) -> List[str]:
        """Build targeted Google search queries for transcript discovery"""
        queries = []

        podcast_name = podcast_config.get("title", "").strip()
        episode_title = episode.title or ""

        # Clean up titles for search
        podcast_clean = self._clean_for_search(podcast_name)
        episode_clean = self._clean_for_search(episode_title)

        if podcast_clean and episode_clean:
            # Primary queries - most specific
            queries.extend(
                [
                    f'"{podcast_clean}" "{episode_clean}" transcript',
                    f'"{podcast_clean}" "{episode_clean}" transcription',
                    f'"{podcast_clean}" "{episode_clean}" full text',
                ]
            )

            # Secondary queries - broader
            queries.extend(
                [
                    f'"{podcast_clean}" transcript site:rev.com',
                    f'"{podcast_clean}" transcript site:otter.ai',
                    f'"{podcast_clean}" transcript site:temi.com',
                    f'"{podcast_clean}" transcript site:scribie.com',
                    f'"{podcast_clean}" "{episode_clean}" site:reddit.com',
                    f'"{podcast_clean}" "{episode_clean}" site:medium.com',
                ]
            )

            # Episode-specific patterns
            if episode.published_at:
                date_str = episode.published_at.strftime("%Y")
                queries.append(f'"{podcast_clean}" transcript {date_str}')

            # Look for fan transcripts and summaries
            queries.extend(
                [
                    f'"{podcast_clean}" fan transcript',
                    f'"{podcast_clean}" episode summary transcript',
                    f'"{podcast_clean}" notes transcript',
                ]
            )

        elif podcast_clean:
            # Fallback - podcast only
            queries.extend(
                [
                    f'"{podcast_clean}" transcript',
                    f'"{podcast_clean}" transcription service',
                    f'"{podcast_clean}" episode transcripts',
                ]
            )

        return queries[:8]  # Limit total queries

    def _clean_for_search(self, text: str) -> str:
        """Clean text for Google search"""
        if not text:
            return ""

        # Remove common podcast suffixes that add noise
        text = re.sub(
            r"\s+(podcast|show|radio|with\s+\w+)$", "", text, flags=re.IGNORECASE
        )

        # Remove special characters but keep essential ones
        text = re.sub(r"[^\w\s\-\&\.]", " ", text)

        # Collapse whitespace
        text = re.sub(r"\s+", " ", text).strip()

        return text

    def _google_search(self, query: str) -> List[Dict[str, Any]]:
        """Perform Google search and return results"""
        results = []

        try:
            # Use Google Custom Search API if available, otherwise scrape
            search_url = "https://www.google.com/search"
            params = {
                "q": query,
                "num": 10,  # Get 10 results
                "hl": "en",
                "safe": "off",
            }

            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }

            response = self.session.get(
                search_url, params=params, headers=headers, timeout=self.timeout
            )
            response.raise_for_status()

            # Parse search results
            results = self._parse_google_results(response.text, query)

        except Exception as e:
            logger.error(f"Google search failed for query '{query}': {e}")

        return results

    def _parse_google_results(self, html: str, query: str) -> List[Dict[str, Any]]:
        """Parse Google search results HTML"""
        results = []

        try:
            from bs4 import BeautifulSoup

            soup = BeautifulSoup(html, "html.parser")

            # Find search result divs
            search_results = soup.find_all("div", {"class": re.compile(r"g|tF2Cxc")})

            for result_div in search_results[:10]:
                try:
                    # Extract link
                    link_elem = result_div.find("a", href=True)
                    if not link_elem:
                        continue

                    url = link_elem.get("href")
                    if not url or not url.startswith("http"):
                        continue

                    # Extract title
                    title_elem = result_div.find("h3")
                    title = title_elem.get_text() if title_elem else ""

                    # Extract snippet
                    snippet_elem = result_div.find(
                        ["span", "div"], {"class": re.compile(r"st|s3v9rd|VwiC3b")}
                    )
                    snippet = snippet_elem.get_text() if snippet_elem else ""

                    # Filter out non-relevant results
                    if self._is_relevant_result(url, title, snippet):
                        results.append(
                            {
                                "url": url,
                                "title": title,
                                "snippet": snippet,
                                "query": query,
                            }
                        )

                except Exception as e:
                    logger.debug(f"Error parsing search result: {e}")
                    continue

        except ImportError:
            logger.error("BeautifulSoup not available for search result parsing")
        except Exception as e:
            logger.error(f"Error parsing Google results: {e}")

        return results

    def _is_relevant_result(self, url: str, title: str, snippet: str) -> bool:
        """Check if search result is relevant for transcript discovery"""

        # Skip irrelevant domains
        domain = urlparse(url).netloc.lower()
        skip_domains = [
            "google.com",
            "youtube.com",
            "spotify.com",
            "apple.com",
            "facebook.com",
            "twitter.com",
            "instagram.com",
            "itunes.apple.com",
            "podcasts.apple.com",
        ]

        if any(skip in domain for skip in skip_domains):
            return False

        # Look for transcript indicators
        text_to_check = f"{title} {snippet}".lower()

        transcript_indicators = [
            "transcript",
            "transcription",
            "transcribed",
            "full text",
            "episode notes",
            "show notes",
            "conversation",
            "interview",
            "complete text",
            "written version",
            "text version",
        ]

        has_transcript_indicator = any(
            indicator in text_to_check for indicator in transcript_indicators
        )

        # Good domains for transcripts
        good_domains = [
            "rev.com",
            "otter.ai",
            "temi.com",
            "scribie.com",
            "reddit.com",
            "medium.com",
            "substack.com",
            "transcript.com",
            "podscripts.co",
        ]

        has_good_domain = any(good in domain for good in good_domains)

        return has_transcript_indicator or has_good_domain

    def _process_search_result(
        self, result: Dict[str, Any], episode: Episode, query: str
    ) -> List[Dict[str, Any]]:
        """Process a search result to extract transcript content"""
        sources = []

        try:
            url = result["url"]
            title = result.get("title", "")
            snippet = result.get("snippet", "")

            # Calculate initial confidence based on search result quality
            confidence = self._calculate_search_confidence(result, episode, query)

            if confidence > 0.2:  # Only process promising results
                # Try to fetch and extract content
                try:
                    response = self.session.get(url, timeout=self.timeout)
                    response.raise_for_status()

                    # Extract transcript content
                    transcript_content = self._extract_transcript_content(response.text)

                    if transcript_content:
                        final_confidence = (
                            confidence
                            + self._calculate_content_confidence(
                                transcript_content, episode
                            )
                        )

                        if final_confidence > 0.4:  # Threshold for inclusion
                            sources.append(
                                {
                                    "url": url,
                                    "confidence": min(final_confidence, 1.0),
                                    "resolver": "google_search",
                                    "metadata": {
                                        "search_title": title,
                                        "search_snippet": snippet,
                                        "search_query": query,
                                        "content": transcript_content,
                                        "content_length": len(transcript_content),
                                        "episode_title": episode.title,
                                        "extraction_method": "google_search_discovery",
                                    },
                                }
                            )

                except Exception as e:
                    logger.debug(f"Could not fetch content from {url}: {e}")
                    # Still include as potential source even if can't fetch content
                    if confidence > 0.6:
                        sources.append(
                            {
                                "url": url,
                                "confidence": confidence,
                                "resolver": "google_search",
                                "metadata": {
                                    "search_title": title,
                                    "search_snippet": snippet,
                                    "search_query": query,
                                    "content": snippet,  # Use snippet as content
                                    "content_length": len(snippet),
                                    "episode_title": episode.title,
                                    "extraction_method": "search_result_only",
                                },
                            }
                        )

        except Exception as e:
            logger.error(f"Error processing search result: {e}")

        return sources

    def _extract_transcript_content(self, html: str) -> Optional[str]:
        """Extract transcript content from fetched page"""
        try:
            from bs4 import BeautifulSoup

            soup = BeautifulSoup(html, "html.parser")

            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()

            # Look for transcript-specific containers
            selectors = [
                ".transcript",
                ".transcription",
                ".episode-transcript",
                ".show-notes",
                ".episode-notes",
                ".content",
                ".post-content",
                ".entry-content",
                ".article-content",
                "main",
                "article",
                ".main-content",
            ]

            for selector in selectors:
                element = soup.select_one(selector)
                if element:
                    text = element.get_text(separator="\n", strip=True)
                    if len(text) > 500:  # Minimum length for transcript
                        return text

            # Fallback - get all text
            text = soup.get_text(separator="\n", strip=True)
            if len(text) > 1000:
                return text

        except ImportError:
            logger.error("BeautifulSoup not available for content extraction")
        except Exception as e:
            logger.error(f"Error extracting content: {e}")

        return None

    def _calculate_search_confidence(
        self, result: Dict[str, Any], episode: Episode, query: str
    ) -> float:
        """Calculate confidence based on search result quality"""
        confidence = 0.0

        title = result.get("title", "").lower()
        snippet = result.get("snippet", "").lower()
        url = result.get("url", "").lower()

        # High-value transcript sites
        domain = urlparse(result["url"]).netloc.lower()
        if any(site in domain for site in ["rev.com", "otter.ai", "temi.com"]):
            confidence += 0.4
        elif any(site in domain for site in ["reddit.com", "medium.com"]):
            confidence += 0.2

        # Title indicators
        if "transcript" in title:
            confidence += 0.3
        elif any(word in title for word in ["transcription", "full text"]):
            confidence += 0.2

        # URL indicators
        if "transcript" in url:
            confidence += 0.2

        # Episode title matching
        if episode.title:
            episode_words = set(episode.title.lower().split())
            result_text = f"{title} {snippet}"

            word_matches = len(episode_words.intersection(set(result_text.split())))
            if word_matches >= 3:
                confidence += 0.3
            elif word_matches >= 2:
                confidence += 0.2

        return confidence

    def _calculate_content_confidence(self, content: str, episode: Episode) -> float:
        """Calculate additional confidence based on extracted content"""
        if not content:
            return 0.0

        confidence = 0.0

        # Content length bonus
        if len(content) > 5000:
            confidence += 0.2
        elif len(content) > 2000:
            confidence += 0.1

        # Dialog pattern detection
        dialog_patterns = [
            r"[A-Z][a-z]+\s*:\s*",  # "Speaker: "
            r"[A-Z]+\s*:\s*",  # "HOST: "
            r">\s*[A-Z][a-z]+",  # "> Speaker"
        ]

        total_matches = 0
        for pattern in dialog_patterns:
            matches = re.findall(pattern, content)
            total_matches += len(matches)

        if total_matches > 10:
            confidence += 0.2
        elif total_matches > 5:
            confidence += 0.1

        return confidence
