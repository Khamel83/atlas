#!/usr/bin/env python3
"""
Speaker mapping system for podcast transcripts.

Maps WhisperX speaker labels (SPEAKER_00, SPEAKER_01, etc.) to actual names
using:
1. Known hosts from config/podcast_hosts.json
2. Guest extraction from episode titles and descriptions
3. Context-based heuristics
"""

import re
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class SpeakerMapping:
    """A mapping from speaker label to actual name"""
    label: str          # SPEAKER_00, SPEAKER_01, etc.
    name: str           # "Michael Lewis", "Guest", etc.
    confidence: float   # 0.0 - 1.0
    source: str         # 'config', 'metadata', 'transcript', 'unknown'


class SpeakerMapper:
    """Maps speaker labels to actual names for podcast transcripts."""

    def __init__(self, hosts_config_path: str = "config/podcast_hosts.json"):
        self.hosts_config = self._load_hosts_config(hosts_config_path)

    def _load_hosts_config(self, path: str) -> Dict:
        """Load hosts configuration from JSON file."""
        config_path = Path(path)
        if not config_path.exists():
            logger.warning(f"Hosts config not found at {path}")
            return {}

        try:
            with open(config_path) as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading hosts config: {e}")
            return {}

    def get_hosts(self, podcast_slug: str) -> List[str]:
        """Get known hosts for a podcast."""
        config = self.hosts_config.get(podcast_slug, {})
        return config.get("hosts", [])

    def get_format(self, podcast_slug: str) -> str:
        """Get podcast format (solo, co-hosted, interview, panel, etc.)."""
        config = self.hosts_config.get(podcast_slug, {})
        return config.get("format", "unknown")

    def extract_guest_from_title(self, title: str) -> Optional[str]:
        """
        Extract guest name from episode title.

        Common patterns:
        - "Episode Title with Guest Name"
        - "Episode Title: Guest Name on Topic"
        - "Episode Title | Guest Name"
        - "Interview: Guest Name"
        """
        patterns = [
            # "with Guest Name" - most common
            r"\bwith\s+([A-Z][a-z]+(?:\s+[A-Z][a-z']+)+)",
            # ": Guest Name on" or ": Guest Name -"
            r":\s*([A-Z][a-z]+(?:\s+[A-Z][a-z']+)+)\s+(?:on|-)(?:\s|$)",
            # "| Guest Name" at end
            r"\|\s*([A-Z][a-z]+(?:\s+[A-Z][a-z']+)+)\s*$",
            # "Interview with/Interview: Guest Name"
            r"[Ii]nterview(?:\s+with|:)\s*([A-Z][a-z]+(?:\s+[A-Z][a-z']+)+)",
            # "(with Guest Name)"
            r"\(with\s+([A-Z][a-z]+(?:\s+[A-Z][a-z']+)+)\)",
            # "Guest Name on Topic" at start
            r"^([A-Z][a-z]+(?:\s+[A-Z][a-z']+)+)\s+on\s+",
            # "Featuring Guest Name"
            r"[Ff]eaturing\s+([A-Z][a-z]+(?:\s+[A-Z][a-z']+)+)",
        ]

        for pattern in patterns:
            match = re.search(pattern, title)
            if match:
                guest = match.group(1).strip()
                # Filter out common false positives
                if guest.lower() not in ['the', 'and', 'part', 'episode', 'season']:
                    return guest

        return None

    def extract_guest_from_description(self, description: str) -> Optional[str]:
        """
        Extract guest name from episode description/show notes.

        Look for patterns like:
        - "Today's guest is Guest Name"
        - "In this episode, Host talks with Guest Name"
        - "Guest: Guest Name"
        """
        if not description:
            return None

        # Take first 1000 chars to avoid noise from full descriptions
        desc = description[:1000]

        patterns = [
            # "Today's guest is/Today we talk to"
            r"[Tt]oday(?:'s guest is|,? we (?:talk|speak) (?:to|with))\s+([A-Z][a-z]+(?:\s+[A-Z][a-z']+)+)",
            # "Guest: Name" or "Featuring: Name"
            r"(?:[Gg]uest|[Ff]eaturing):\s*([A-Z][a-z]+(?:\s+[A-Z][a-z']+)+)",
            # "Host interviews/talks to/with Guest Name"
            r"(?:interviews?|talks? (?:to|with))\s+([A-Z][a-z]+(?:\s+[A-Z][a-z']+)+)",
            # "This week: Guest Name"
            r"[Tt]his (?:week|episode):\s*([A-Z][a-z]+(?:\s+[A-Z][a-z']+)+)",
            # "Join us as we speak with Guest Name"
            r"(?:join|tune in).*?(?:speak|talk) with\s+([A-Z][a-z]+(?:\s+[A-Z][a-z']+)+)",
        ]

        for pattern in patterns:
            match = re.search(pattern, desc)
            if match:
                guest = match.group(1).strip()
                if guest.lower() not in ['the', 'and', 'part', 'episode']:
                    return guest

        return None

    def extract_speakers_from_transcript(self, transcript_text: str) -> Dict[str, str]:
        """
        Extract speaker self-identifications from transcript text.

        Look for patterns like:
        - "I'm Michael Lewis"
        - "This is Ben Thompson"
        - "My name is Guest Name"
        """
        speakers = {}

        # Take first 2000 chars where intros usually happen
        intro_text = transcript_text[:2000]

        patterns = [
            # "I'm Name" or "I am Name"
            r"I(?:'m| am)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z']+)*)",
            # "This is Name"
            r"[Tt]his is\s+([A-Z][a-z]+(?:\s+[A-Z][a-z']+)*)",
            # "My name is Name"
            r"[Mm]y name is\s+([A-Z][a-z]+(?:\s+[A-Z][a-z']+)*)",
            # "Welcome to X, I'm Name"
            r"[Ww]elcome to.*?I(?:'m| am)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z']+)*)",
        ]

        for pattern in patterns:
            matches = re.findall(pattern, intro_text)
            for name in matches:
                name = name.strip()
                # Filter common false positives
                if name.lower() not in ['so', 'here', 'back', 'joined', 'glad', 'happy', 'excited']:
                    # We don't know which SPEAKER_XX this is yet
                    # Just return found names for later matching
                    speakers[name] = name

        return speakers

    def map_speakers(
        self,
        podcast_slug: str,
        episode_title: str,
        episode_description: str,
        num_speakers: int,
        transcript_text: str = ""
    ) -> List[SpeakerMapping]:
        """
        Map speaker labels to actual names.

        Strategy:
        1. Get known hosts from config
        2. Extract guest from title/description
        3. Assign based on podcast format and speaker count

        Args:
            podcast_slug: Podcast identifier
            episode_title: Episode title
            episode_description: Episode description/show notes
            num_speakers: Number of speakers detected by diarization
            transcript_text: Optional transcript text for self-ID extraction

        Returns:
            List of SpeakerMapping objects
        """
        mappings = []
        hosts = self.get_hosts(podcast_slug)
        format_type = self.get_format(podcast_slug)

        # Try to extract guest from metadata
        guest = (
            self.extract_guest_from_title(episode_title) or
            self.extract_guest_from_description(episode_description)
        )

        # Try to extract self-identifications from transcript
        transcript_speakers = {}
        if transcript_text:
            transcript_speakers = self.extract_speakers_from_transcript(transcript_text)

        # === MAPPING LOGIC ===

        # Solo show (e.g., Asianometry, Stratechery articles)
        if num_speakers == 1:
            if hosts:
                mappings.append(SpeakerMapping(
                    label="SPEAKER_00",
                    name=hosts[0],
                    confidence=0.95,
                    source="config"
                ))
            else:
                mappings.append(SpeakerMapping(
                    label="SPEAKER_00",
                    name="Host",
                    confidence=0.3,
                    source="unknown"
                ))
            return mappings

        # Two speakers - most common case
        if num_speakers == 2:
            # Interview format: 1 host + 1 guest
            if len(hosts) == 1:
                mappings.append(SpeakerMapping(
                    label="SPEAKER_00",
                    name=hosts[0],
                    confidence=0.85,
                    source="config"
                ))
                mappings.append(SpeakerMapping(
                    label="SPEAKER_01",
                    name=guest or "Guest",
                    confidence=0.7 if guest else 0.3,
                    source="metadata" if guest else "unknown"
                ))
                return mappings

            # Co-hosted show: 2 hosts
            if len(hosts) >= 2:
                mappings.append(SpeakerMapping(
                    label="SPEAKER_00",
                    name=hosts[0],
                    confidence=0.75,
                    source="config"
                ))
                mappings.append(SpeakerMapping(
                    label="SPEAKER_01",
                    name=hosts[1],
                    confidence=0.75,
                    source="config"
                ))
                return mappings

            # Unknown hosts
            mappings.append(SpeakerMapping(
                label="SPEAKER_00",
                name="Speaker 1",
                confidence=0.2,
                source="unknown"
            ))
            mappings.append(SpeakerMapping(
                label="SPEAKER_01",
                name=guest or "Speaker 2",
                confidence=0.5 if guest else 0.2,
                source="metadata" if guest else "unknown"
            ))
            return mappings

        # Three+ speakers - panel or co-hosts + guest
        if num_speakers >= 3:
            # Assign known hosts first
            for i, host in enumerate(hosts):
                if i < num_speakers:
                    mappings.append(SpeakerMapping(
                        label=f"SPEAKER_{i:02d}",
                        name=host,
                        confidence=0.6,
                        source="config"
                    ))

            # Assign guest if we have one and space
            host_count = len(hosts)
            if guest and host_count < num_speakers:
                mappings.append(SpeakerMapping(
                    label=f"SPEAKER_{host_count:02d}",
                    name=guest,
                    confidence=0.6,
                    source="metadata"
                ))
                host_count += 1

            # Fill remaining speakers
            for i in range(host_count, num_speakers):
                mappings.append(SpeakerMapping(
                    label=f"SPEAKER_{i:02d}",
                    name=f"Speaker {i + 1}",
                    confidence=0.2,
                    source="unknown"
                ))

            return mappings

        # Fallback
        return mappings

    def format_transcript_with_speakers(
        self,
        segments: List[Dict],
        speaker_mappings: List[SpeakerMapping]
    ) -> str:
        """
        Format diarized segments into markdown with speaker names.

        Args:
            segments: WhisperX segments with 'speaker' and 'text' keys
            speaker_mappings: List of SpeakerMapping objects

        Returns:
            Formatted markdown string
        """
        # Build speaker name lookup
        speaker_names = {m.label: m.name for m in speaker_mappings}

        lines = []
        current_speaker = None
        current_text = []

        for segment in segments:
            speaker = segment.get("speaker", "UNKNOWN")
            text = segment.get("text", "").strip()

            if not text:
                continue

            speaker_name = speaker_names.get(speaker, speaker)

            # New speaker - flush current text and start new paragraph
            if speaker != current_speaker:
                if current_speaker is not None and current_text:
                    prev_name = speaker_names.get(current_speaker, current_speaker)
                    lines.append(f"**{prev_name}:** {' '.join(current_text)}")
                    lines.append("")  # Blank line between speakers

                current_speaker = speaker
                current_text = [text]
            else:
                # Same speaker - accumulate text
                current_text.append(text)

        # Flush final speaker's text
        if current_speaker is not None and current_text:
            speaker_name = speaker_names.get(current_speaker, current_speaker)
            lines.append(f"**{speaker_name}:** {' '.join(current_text)}")

        return "\n".join(lines)


# Convenience functions for direct use
_mapper = None

def get_mapper() -> SpeakerMapper:
    """Get singleton SpeakerMapper instance."""
    global _mapper
    if _mapper is None:
        _mapper = SpeakerMapper()
    return _mapper

def map_speakers(
    podcast_slug: str,
    episode_title: str,
    episode_description: str,
    num_speakers: int,
    transcript_text: str = ""
) -> List[SpeakerMapping]:
    """Convenience function to map speakers."""
    return get_mapper().map_speakers(
        podcast_slug, episode_title, episode_description,
        num_speakers, transcript_text
    )

def format_transcript(
    segments: List[Dict],
    speaker_mappings: List[SpeakerMapping]
) -> str:
    """Convenience function to format transcript."""
    return get_mapper().format_transcript_with_speakers(segments, speaker_mappings)
