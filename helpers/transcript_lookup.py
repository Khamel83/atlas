#!/usr/bin/env python3
"""
Atlas Transcript Lookup System

This system implements the brilliant idea of looking up existing transcripts
from various sources before falling back to transcription. This is much more
efficient and often provides better quality transcripts.

Sources checked (in order of preference):
1. YouTube auto-generated transcripts (via youtube-transcript-api)
2. Podcast show notes with embedded transcripts
3. RSS feed descriptions with transcripts
4. Common transcript hosting services (Rev, Otter, etc.)
5. Cached transcripts from previous runs
6. Fallback to local/API transcription

Usage:
    from helpers.transcript_lookup import TranscriptLookup

    lookup = TranscriptLookup(config)
    transcript = lookup.get_transcript(url, audio_path, metadata)
"""

import json
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from youtube_transcript_api import (NoTranscriptFound, TranscriptsDisabled,
                                    YouTubeTranscriptApi)

from helpers.transcription import transcribe_audio
from helpers.transcription_openrouter import \
    transcribe_audio as transcribe_openrouter
from helpers.utils import log_error, log_info


class TranscriptSource:
    """Represents a source where transcripts might be found."""

    def __init__(self, name: str, quality_score: int, cost: str):
        self.name = name
        self.quality_score = quality_score  # 1-10, higher is better
        self.cost = cost  # "free", "api", "expensive"


class TranscriptLookup:
    """Main transcript lookup system."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger(__name__)

        # Define transcript sources in order of preference
        self.sources = [
            TranscriptSource("youtube_official", 9, "free"),
            TranscriptSource("podcast_shownotes", 8, "free"),
            TranscriptSource("rss_description", 7, "free"),
            TranscriptSource("rev_transcript", 9, "free"),
            TranscriptSource("otter_transcript", 8, "free"),
            TranscriptSource("cached_transcript", 6, "free"),
            TranscriptSource("openrouter_api", 7, "api"),
            TranscriptSource("local_whisper", 6, "expensive"),
        ]

        # Common transcript indicators in text
        self.transcript_indicators = [
            "transcript:",
            "full transcript",
            "episode transcript",
            "show transcript",
            "complete transcript",
            "[music]",
            "[applause]",
            "speaker 1:",
            "speaker 2:",
            "host:",
            "guest:",
            "interviewer:",
            "interviewee:",
        ]

        # Transcript hosting services
        self.transcript_services = [
            "rev.com",
            "otter.ai",
            "trint.com",
            "sonix.ai",
            "temi.com",
            "speechmatics.com",
        ]

    def get_transcript(
        self,
        url: str,
        audio_path: Optional[str] = None,
        metadata: Optional[Dict] = None,
    ) -> Optional[str]:
        """
        Get transcript using the best available source.

        Args:
            url: Original content URL
            audio_path: Path to audio file (for fallback transcription)
            metadata: Content metadata (may contain transcript hints)

        Returns:
            Transcript text or None if not found
        """
        log_path = self.config.get("log_path", "transcript_lookup.log")

        log_info(log_path, f"Starting transcript lookup for: {url}")

        # Try each source in order of preference
        for source in self.sources:
            try:
                transcript = self._try_source(
                    source, url, audio_path, metadata, log_path
                )
                if transcript and self._is_valid_transcript(transcript):
                    log_info(
                        log_path,
                        f"Found transcript via {source.name} (quality: {source.quality_score})",
                    )
                    return transcript
            except Exception as e:
                log_error(log_path, f"Error with {source.name}: {e}")
                continue

        log_error(log_path, f"No transcript found for {url}")
        return None

    def _try_source(
        self,
        source: TranscriptSource,
        url: str,
        audio_path: Optional[str],
        metadata: Optional[Dict],
        log_path: str,
    ) -> Optional[str]:
        """Try to get transcript from a specific source."""

        if source.name == "youtube_official":
            return self._get_youtube_transcript(url, log_path)

        elif source.name == "podcast_shownotes":
            return self._get_podcast_shownotes_transcript(url, metadata, log_path)

        elif source.name == "rss_description":
            return self._get_rss_transcript(url, metadata, log_path)

        elif source.name == "rev_transcript":
            return self._get_rev_transcript(url, log_path)

        elif source.name == "otter_transcript":
            return self._get_otter_transcript(url, log_path)

        elif source.name == "cached_transcript":
            return self._get_cached_transcript(url, log_path)

        elif source.name == "openrouter_api":
            if audio_path and self.config.get("OPENROUTER_API_KEY"):
                return self._get_openrouter_transcript(audio_path, log_path)

        elif source.name == "local_whisper":
            if audio_path:
                return self._get_local_transcript(audio_path, log_path)

        return None

    def _get_youtube_transcript(self, url: str, log_path: str) -> Optional[str]:
        """Get transcript from YouTube's official API."""
        try:
            # Extract video ID
            video_id = self._extract_youtube_id(url)
            if not video_id:
                return None

            log_info(log_path, f"Fetching YouTube transcript for video: {video_id}")

            # Try to get transcript
            transcript = YouTubeTranscriptApi.get_transcript(video_id)
            transcript_text = "\n".join([entry["text"] for entry in transcript])

            if transcript_text:
                log_info(
                    log_path, f"Found YouTube transcript ({len(transcript_text)} chars)"
                )
                return transcript_text

        except (TranscriptsDisabled, NoTranscriptFound):
            log_info(log_path, "No YouTube transcript available")
        except Exception as e:
            log_error(log_path, f"YouTube transcript error: {e}")

        return None

    def _get_podcast_shownotes_transcript(
        self, url: str, metadata: Optional[Dict], log_path: str
    ) -> Optional[str]:
        """Look for transcripts in podcast show notes."""
        try:
            # Check if we have show notes URL in metadata
            show_notes_url = None
            if metadata:
                show_notes_url = metadata.get("show_notes_url") or metadata.get("link")

            if not show_notes_url:
                # Try to construct show notes URL from podcast URL
                show_notes_url = self._guess_show_notes_url(url)

            if not show_notes_url:
                return None

            log_info(log_path, f"Checking show notes for transcript: {show_notes_url}")

            # Fetch show notes page
            response = requests.get(show_notes_url, timeout=10)
            if response.status_code != 200:
                return None

            soup = BeautifulSoup(response.content, "html.parser")

            # Look for transcript sections
            transcript_text = self._extract_transcript_from_html(soup)

            if transcript_text:
                log_info(
                    log_path,
                    f"Found transcript in show notes ({len(transcript_text)} chars)",
                )
                return transcript_text

        except Exception as e:
            log_error(log_path, f"Show notes transcript error: {e}")

        return None

    def _get_rss_transcript(
        self, url: str, metadata: Optional[Dict], log_path: str
    ) -> Optional[str]:
        """Look for transcripts in RSS feed descriptions."""
        try:
            if not metadata or not metadata.get("rss_description"):
                return None

            description = metadata["rss_description"]

            # Check if description contains transcript indicators
            if not any(
                indicator in description.lower()
                for indicator in self.transcript_indicators
            ):
                return None

            log_info(log_path, "Checking RSS description for transcript")

            # Extract transcript from description
            transcript = self._extract_transcript_from_text(description)

            if transcript:
                log_info(
                    log_path,
                    f"Found transcript in RSS description ({len(transcript)} chars)",
                )
                return transcript

        except Exception as e:
            log_error(log_path, f"RSS transcript error: {e}")

        return None

    def _get_rev_transcript(self, url: str, log_path: str) -> Optional[str]:
        """Look for Rev.com transcript links."""
        try:
            # Check if URL contains Rev.com links
            if "rev.com" not in url:
                return None

            log_info(log_path, f"Checking Rev.com transcript: {url}")

            response = requests.get(url, timeout=10)
            if response.status_code != 200:
                return None

            soup = BeautifulSoup(response.content, "html.parser")

            # Look for transcript content (Rev.com specific selectors)
            transcript_div = soup.find("div", class_="transcript-content")
            if transcript_div:
                transcript = transcript_div.get_text(strip=True)
                log_info(
                    log_path, f"Found Rev.com transcript ({len(transcript)} chars)"
                )
                return transcript

        except Exception as e:
            log_error(log_path, f"Rev.com transcript error: {e}")

        return None

    def _get_otter_transcript(self, url: str, log_path: str) -> Optional[str]:
        """Look for Otter.ai transcript links."""
        try:
            # Check if URL contains Otter.ai links
            if "otter.ai" not in url:
                return None

            log_info(log_path, f"Checking Otter.ai transcript: {url}")

            response = requests.get(url, timeout=10)
            if response.status_code != 200:
                return None

            soup = BeautifulSoup(response.content, "html.parser")

            # Look for transcript content (Otter.ai specific selectors)
            transcript_content = soup.find("div", {"data-testid": "transcript-content"})
            if transcript_content:
                transcript = transcript_content.get_text(strip=True)
                log_info(
                    log_path, f"Found Otter.ai transcript ({len(transcript)} chars)"
                )
                return transcript

        except Exception as e:
            log_error(log_path, f"Otter.ai transcript error: {e}")

        return None

    def _get_cached_transcript(self, url: str, log_path: str) -> Optional[str]:
        """Check for cached transcripts from previous runs."""
        try:
            # Create cache key from URL
            cache_key = self._create_cache_key(url)
            cache_dir = (
                Path(self.config.get("data_directory", "output")) / "transcript_cache"
            )
            cache_file = cache_dir / f"{cache_key}.txt"

            if cache_file.exists():
                log_info(log_path, f"Found cached transcript: {cache_file}")
                with open(cache_file, "r", encoding="utf-8") as f:
                    transcript = f.read()
                return transcript

        except Exception as e:
            log_error(log_path, f"Cached transcript error: {e}")

        return None

    def _get_openrouter_transcript(
        self, audio_path: str, log_path: str
    ) -> Optional[str]:
        """Get transcript using OpenRouter API."""
        try:
            log_info(log_path, f"Transcribing via OpenRouter API: {audio_path}")
            transcript = transcribe_openrouter(audio_path)

            if transcript and "failed" not in transcript.lower():
                log_info(
                    log_path,
                    f"OpenRouter transcription successful ({len(transcript)} chars)",
                )
                return transcript

        except Exception as e:
            log_error(log_path, f"OpenRouter transcription error: {e}")

        return None

    def _get_local_transcript(self, audio_path: str, log_path: str) -> Optional[str]:
        """Get transcript using local Whisper."""
        try:
            log_info(log_path, f"Transcribing locally: {audio_path}")
            transcript = transcribe_audio(audio_path, log_path)

            if transcript:
                log_info(
                    log_path,
                    f"Local transcription successful ({len(transcript)} chars)",
                )
                return transcript

        except Exception as e:
            log_error(log_path, f"Local transcription error: {e}")

        return None

    def _is_valid_transcript(self, transcript: str) -> bool:
        """Check if transcript appears to be valid."""
        if not transcript or len(transcript) < 50:
            return False

        # Check for common error messages
        error_phrases = [
            "transcription failed",
            "error occurred",
            "not available",
            "missing api key",
            "timeout",
            "access denied",
        ]

        transcript_lower = transcript.lower()
        if any(phrase in transcript_lower for phrase in error_phrases):
            return False

        # Check for reasonable word count
        word_count = len(transcript.split())
        if word_count < 10:
            return False

        return True

    def _extract_youtube_id(self, url: str) -> Optional[str]:
        """Extract YouTube video ID from URL."""
        patterns = [
            r"(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/)([a-zA-Z0-9_-]{11})",
            r"youtube\.com/v/([a-zA-Z0-9_-]{11})",
            r"^([a-zA-Z0-9_-]{11})$",  # Direct video ID
        ]

        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)

        return None

    def _guess_show_notes_url(self, audio_url: str) -> Optional[str]:
        """Try to guess show notes URL from audio URL."""
        # Common patterns for show notes URLs
        parsed = urlparse(audio_url)
        base_url = f"{parsed.scheme}://{parsed.netloc}"

        # Try common show notes patterns
        possible_paths = [
            parsed.path.replace(".mp3", "").replace(".m4a", ""),
            parsed.path.replace("/audio/", "/"),
            parsed.path.replace("/episodes/", "/"),
            parsed.path.replace("/download/", "/"),
        ]

        for path in possible_paths:
            if path != parsed.path:
                show_notes_url = urljoin(base_url, path)
                try:
                    response = requests.head(show_notes_url, timeout=5)
                    if response.status_code == 200:
                        return show_notes_url
                except Exception:
                    continue

        return None

    def _extract_transcript_from_html(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract transcript from HTML content."""
        # Look for common transcript containers
        transcript_selectors = [
            'div[class*="transcript"]',
            'div[id*="transcript"]',
            'section[class*="transcript"]',
            'article[class*="transcript"]',
            ".transcript-content",
            ".episode-transcript",
            ".show-transcript",
            ".full-transcript",
        ]

        for selector in transcript_selectors:
            elements = soup.select(selector)
            for element in elements:
                text = element.get_text(strip=True)
                if self._looks_like_transcript(text):
                    return text

        # Look for transcript in main content
        main_content = (
            soup.find("main")
            or soup.find("article")
            or soup.find("div", class_="content")
        )
        if main_content:
            text = main_content.get_text()
            if self._looks_like_transcript(text):
                return text

        return None

    def _extract_transcript_from_text(self, text: str) -> Optional[str]:
        """Extract transcript from plain text."""
        # Look for transcript sections in text
        transcript_start_patterns = [
            r"transcript:?\s*\n",
            r"full transcript:?\s*\n",
            r"episode transcript:?\s*\n",
            r"show transcript:?\s*\n",
        ]

        for pattern in transcript_start_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                transcript = text[match.end() :]
                if self._looks_like_transcript(transcript):
                    return transcript

        return None

    def _looks_like_transcript(self, text: str) -> bool:
        """Check if text looks like a transcript."""
        if not text or len(text) < 100:
            return False

        # Check for transcript indicators
        indicators_found = sum(
            1 for indicator in self.transcript_indicators if indicator in text.lower()
        )

        # Check for speaker patterns
        speaker_patterns = [
            r"\b(speaker|host|guest|interviewer|interviewee)\s*\d*\s*:",
            r"\b[A-Z][a-z]+\s*:",  # Name followed by colon
            r"\[[^\]]+\]",  # Stage directions like [music], [applause]
        ]

        speaker_matches = sum(
            1 for pattern in speaker_patterns if re.search(pattern, text)
        )

        # Must have either transcript indicators or speaker patterns
        return indicators_found > 0 or speaker_matches > 2

    def _create_cache_key(self, url: str) -> str:
        """Create cache key from URL."""
        import hashlib

        return hashlib.md5(url.encode()).hexdigest()

    def cache_transcript(self, url: str, transcript: str) -> None:
        """Cache transcript for future use."""
        try:
            cache_key = self._create_cache_key(url)
            cache_dir = (
                Path(self.config.get("data_directory", "output")) / "transcript_cache"
            )
            cache_dir.mkdir(parents=True, exist_ok=True)

            cache_file = cache_dir / f"{cache_key}.txt"
            with open(cache_file, "w", encoding="utf-8") as f:
                f.write(transcript)

            # Also save metadata
            metadata_file = cache_dir / f"{cache_key}.json"
            metadata = {
                "url": url,
                "cached_at": datetime.now().isoformat(),
                "length": len(transcript),
                "word_count": len(transcript.split()),
            }

            with open(metadata_file, "w") as f:
                json.dump(metadata, f, indent=2)

        except Exception as e:
            self.logger.error(f"Failed to cache transcript: {e}")


# Convenience function for backward compatibility
def get_transcript_with_lookup(
    url: str, audio_path: Optional[str] = None, config: Optional[Dict] = None
) -> Optional[str]:
    """
    Convenience function to get transcript with lookup.

    Args:
        url: Content URL
        audio_path: Path to audio file (optional)
        config: Configuration dictionary (optional)

    Returns:
        Transcript text or None
    """
    if not config:
        from helpers.config import load_config

        config = load_config()

    lookup = TranscriptLookup(config)
    return lookup.get_transcript(url, audio_path)
