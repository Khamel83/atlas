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
        - "Guest Name is/says/talks/speaks..."
        - "Guest Name: Topic"
        """
        # Verb words that indicate the name has ended (case-insensitive patterns)
        verb_words = r"(?:[Ii]s|[Ss]ays|[Tt]alks|[Ss]peaks|[Rr]eturns|[Jj]oins|[Ee]xplains|[Rr]eveals|[Dd]iscusses|[Ss]hares|[Oo]n)"

        # Name pattern that handles: Adam McKay, Ben Thompson, Michael O'Brien
        # Uses negative lookahead to stop before verb words
        # First name: capital + lowercase
        # Last name(s): capital + mix (for Mc/Mac/O' names), not followed by verb
        name_pattern = rf"[A-Z][a-z]+(?:\s+(?:Mc|Mac|O')?[A-Z][a-zA-Z']+(?!\s+{verb_words}\b))+"

        # Simpler 2-word name for verb patterns (avoids greedy capture)
        simple_name = r"[A-Z][a-z]+\s+(?:Mc|Mac|O')?[A-Z][a-zA-Z']+"

        patterns = [
            # "with Guest Name" - most common
            rf"\bwith\s+({name_pattern})",
            # "Guest Name is/says/talks/speaks/returns/joins..." at start (use simple 2-word name)
            rf"^({simple_name})\s+{verb_words}\b",
            # "Guest Name: Topic" at start
            rf"^({name_pattern}):\s+",
            # ": Guest Name on" or ": Guest Name -"
            rf":\s*({name_pattern})\s+(?:on|-)(?:\s|$)",
            # "| Guest Name" at end
            rf"\|\s*({name_pattern})\s*$",
            # "Interview with/Interview: Guest Name"
            rf"[Ii]nterview(?:\s+with|:)\s*({name_pattern})",
            # "(with Guest Name)"
            rf"\(with\s+({name_pattern})\)",
            # "Guest Name on Topic" at start (use simple name)
            rf"^({simple_name})\s+[Oo]n\s+",
            # "Featuring Guest Name"
            rf"[Ff]eaturing\s+({name_pattern})",
        ]

        false_positives = {
            'the', 'and', 'part', 'episode', 'season', 'how', 'why', 'what',
            'when', 'where', 'this', 'that', 'inside', 'behind', 'beyond'
        }

        for pattern in patterns:
            match = re.search(pattern, title)
            if match:
                guest = match.group(1).strip()
                # Filter out common false positives
                if guest.lower() not in false_positives:
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

    def extract_speakers_from_segments(self, segments: List[Dict]) -> Dict[str, str]:
        """
        Extract speaker self-identifications from WhisperX segments.

        Scans segments for patterns like "I'm Michael Lewis" and maps
        the SPEAKER_XX label to the identified name.

        Args:
            segments: WhisperX segments with 'speaker' and 'text' keys

        Returns:
            Dict mapping speaker labels to identified names, e.g.:
            {"SPEAKER_14": "Michael Lewis", "SPEAKER_07": "Lydia Jean Cott"}
        """
        speaker_identities = {}

        patterns = [
            # "I'm Name" or "I am Name"
            r"I(?:'m| am)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z']+)*)",
            # "This is Name"
            r"[Tt]his is\s+([A-Z][a-z]+(?:\s+[A-Z][a-z']+)*)",
            # "My name is Name"
            r"[Mm]y name is\s+([A-Z][a-z]+(?:\s+[A-Z][a-z']+)*)",
        ]

        false_positives = {
            'so', 'here', 'back', 'joined', 'glad', 'happy', 'excited',
            'going', 'sorry', 'sure', 'ready', 'done', 'not', 'just',
            'really', 'very', 'still', 'also', 'already', 'finally'
        }

        # Ad-related context words that indicate a self-ID is from an ad, not actual speaker
        ad_context_words = {
            'audiobook', 'subscribe', 'download', 'promo',
            'sponsor', 'brought to you', 'advertisement', 'listeners',
            'tune in', 'check out', 'app today', 'free app',
            'available on', 'apple podcasts', 'spotify', 'wherever you get',
            'iheart', 'iheartradio', 'audible', 'book club', 'earsay',
            'number one podcast', 'follow us', 'rate and review'
        }

        # First, identify which speakers appear primarily in ad contexts
        ad_speakers = set()
        speaker_ad_ratio = {}

        for seg in segments:
            speaker = seg.get("speaker")
            text = seg.get("text", "").lower()
            if not speaker:
                continue

            if speaker not in speaker_ad_ratio:
                speaker_ad_ratio[speaker] = {"ad": 0, "total": 0}

            speaker_ad_ratio[speaker]["total"] += 1
            if any(word in text for word in ad_context_words):
                speaker_ad_ratio[speaker]["ad"] += 1

        # Mark speakers with >30% ad content as ad speakers
        for speaker, counts in speaker_ad_ratio.items():
            if counts["total"] > 0:
                ratio = counts["ad"] / counts["total"]
                if ratio > 0.3:
                    ad_speakers.add(speaker)

        # Only check first portion of episode (where intros happen)
        # Usually first 50-100 segments after ads
        segments_to_check = segments[:150]

        for segment in segments_to_check:
            speaker = segment.get("speaker")
            text = segment.get("text", "")

            if not speaker or not text:
                continue

            # Skip if we already identified this speaker
            if speaker in speaker_identities:
                continue

            # Skip if this speaker appears primarily in ads
            if speaker in ad_speakers:
                continue

            # Skip if this segment looks like an ad context
            text_lower = text.lower()
            is_ad_context = any(word in text_lower for word in ad_context_words)
            if is_ad_context:
                continue

            for pattern in patterns:
                match = re.search(pattern, text)
                if match:
                    name = match.group(1).strip()
                    # Filter false positives
                    if name.lower() not in false_positives and len(name) > 2:
                        speaker_identities[speaker] = name
                        logger.info(f"Self-identification found: {speaker} = '{name}' in: \"{text[:60]}...\"")
                        break

        return speaker_identities

    def map_speakers(
        self,
        podcast_slug: str,
        episode_title: str,
        episode_description: str,
        num_speakers: int,
        transcript_text: str = "",
        segments: List[Dict] = None
    ) -> List[SpeakerMapping]:
        """
        Map speaker labels to actual names.

        Strategy (in priority order):
        1. Self-identification from segments ("I'm Michael Lewis")
        2. Known hosts from config matched to remaining labels
        3. Guest extraction from title/description
        4. Generic "Speaker N" for unmapped speakers

        Args:
            podcast_slug: Podcast identifier
            episode_title: Episode title
            episode_description: Episode description/show notes
            num_speakers: Number of speakers detected by diarization
            transcript_text: Optional transcript text (legacy, prefer segments)
            segments: Optional WhisperX segments with 'speaker' and 'text' keys

        Returns:
            List of SpeakerMapping objects
        """
        mappings = []
        mapped_labels = set()  # Track which SPEAKER_XX labels are already mapped
        used_names = set()  # Track which names have been assigned

        hosts = self.get_hosts(podcast_slug)
        format_type = self.get_format(podcast_slug)

        # Try to extract guest from metadata
        guest = (
            self.extract_guest_from_title(episode_title) or
            self.extract_guest_from_description(episode_description)
        )

        # === STEP 1: Self-identification from segments (HIGHEST PRIORITY) ===
        # This is the most reliable - "I'm Michael Lewis" tells us exactly who SPEAKER_14 is
        if segments:
            self_ids = self.extract_speakers_from_segments(segments)
            for label, name in self_ids.items():
                # Check if this name matches a known host
                confidence = 0.95
                source = "self-identification"
                for host in hosts:
                    if host.lower() in name.lower() or name.lower() in host.lower():
                        name = host  # Use canonical host name
                        source = "self-identification+config"
                        break

                mappings.append(SpeakerMapping(
                    label=label,
                    name=name,
                    confidence=confidence,
                    source=source
                ))
                mapped_labels.add(label)
                used_names.add(name.lower())
                logger.info(f"Mapped {label} -> {name} (self-ID)")

        # === STEP 2: Get all unique speaker labels from segments ===
        all_labels = set()
        if segments:
            for seg in segments:
                if seg.get("speaker"):
                    all_labels.add(seg["speaker"])
        else:
            # Fallback: assume SPEAKER_00 through SPEAKER_XX
            all_labels = {f"SPEAKER_{i:02d}" for i in range(num_speakers)}

        # === STEP 3: Map remaining hosts from config ===
        # For unmapped labels, try to assign known hosts
        remaining_labels = sorted(all_labels - mapped_labels)
        unmapped_hosts = [h for h in hosts if h.lower() not in used_names]

        # For remaining hosts, assign to remaining labels by speaking frequency
        # (assuming earlier/more-frequent speakers are likely hosts)
        if segments and unmapped_hosts:
            # Count segments per remaining speaker
            label_counts = {}
            for seg in segments:
                speaker = seg.get("speaker")
                if speaker in remaining_labels:
                    label_counts[speaker] = label_counts.get(speaker, 0) + 1

            # Sort remaining labels by frequency (most talkative first)
            sorted_remaining = sorted(
                remaining_labels,
                key=lambda x: label_counts.get(x, 0),
                reverse=True
            )

            for host in unmapped_hosts:
                if sorted_remaining:
                    label = sorted_remaining.pop(0)
                    mappings.append(SpeakerMapping(
                        label=label,
                        name=host,
                        confidence=0.65,
                        source="config+frequency"
                    ))
                    mapped_labels.add(label)
                    used_names.add(host.lower())
                    remaining_labels.remove(label)
                    logger.info(f"Mapped {label} -> {host} (config+frequency)")

        # === STEP 4: Map guest if extracted from metadata ===
        if guest and guest.lower() not in used_names and remaining_labels:
            # Assign guest to highest-frequency remaining speaker
            if segments:
                label_counts = {}
                for seg in segments:
                    speaker = seg.get("speaker")
                    if speaker in remaining_labels:
                        label_counts[speaker] = label_counts.get(speaker, 0) + 1

                if label_counts:
                    best_label = max(label_counts.keys(), key=lambda x: label_counts[x])
                    mappings.append(SpeakerMapping(
                        label=best_label,
                        name=guest,
                        confidence=0.6,
                        source="metadata+frequency"
                    ))
                    mapped_labels.add(best_label)
                    remaining_labels.remove(best_label)
                    logger.info(f"Mapped {best_label} -> {guest} (guest from metadata)")

        # === STEP 5: Fill remaining speakers with generic labels ===
        # Sort remaining labels numerically for consistent ordering
        remaining_sorted = sorted(remaining_labels, key=lambda x: int(x.split('_')[1]) if '_' in x else 0)
        speaker_num = 1
        for label in remaining_sorted:
            # Skip labels with very few segments (likely ads/bumpers)
            if segments:
                seg_count = sum(1 for seg in segments if seg.get("speaker") == label)
                if seg_count < 3:
                    continue  # Skip speakers with fewer than 3 segments (likely ads)

            # Find next available speaker number
            while f"Speaker {speaker_num}" in [m.name for m in mappings]:
                speaker_num += 1

            mappings.append(SpeakerMapping(
                label=label,
                name=f"Speaker {speaker_num}",
                confidence=0.2,
                source="unknown"
            ))
            speaker_num += 1

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
