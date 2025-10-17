#!/usr/bin/env python3
"""
Transcript Parser for Atlas
Parses raw transcript content into structured data with speaker attribution,
segments, timestamps, and topic extraction for enhanced search capabilities.
"""

import re
from typing import Dict, List, Any, Optional
from datetime import datetime


class TranscriptParser:
    """Parse transcript content into structured, searchable segments."""

    def __init__(self):
        # Common speaker patterns in transcripts
        self.speaker_patterns = [
            r"^([A-Z][a-z]+ [A-Z][a-z]+):\s*(.+)",  # "Lex Fridman: text"
            r"^([A-Z][A-Z\s]+):\s*(.+)",  # "HOST: text"
            r"^\[([^\]]+)\]:\s*(.+)",  # "[Speaker Name]: text"
            r"^(\w+):\s*(.+)",  # "Speaker: text"
            r"^\*\*([^*]+)\*\*:\s*(.+)",  # "**Speaker**: text"
        ]

        # Timestamp patterns
        self.timestamp_patterns = [
            r"\[(\d{1,2}:\d{2}:\d{2})\]",  # [1:23:45]
            r"\[(\d{1,2}:\d{2})\]",  # [12:34]
            r"(\d{1,2}:\d{2}:\d{2})",  # 1:23:45
            r"(\d+:\d{2})",  # 12:34
        ]

        # Common filler words and patterns to clean
        self.filler_patterns = [
            r"\[music\]",
            r"\[applause\]",
            r"\[laughter\]",
            r"\[inaudible\]",
            r"\[crosstalk\]",
            r"\[background noise\]",
        ]

        # Topic transition indicators
        self.topic_indicators = [
            "let me ask you about",
            "speaking of",
            "that reminds me",
            "on a different topic",
            "shifting gears",
            "moving on to",
            "i wanted to ask about",
            "what about",
            "tell me about",
        ]

    def parse_transcript(
        self, raw_text: str, metadata: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Parse raw transcript into structured data."""
        if not raw_text or not raw_text.strip():
            return {
                "speakers": [],
                "segments": [],
                "topics": [],
                "metadata": metadata or {},
                "parse_quality": "empty",
            }

        # Clean the text
        cleaned_text = self._clean_text(raw_text)

        # Extract speakers
        speakers = self._extract_speakers(cleaned_text)

        # Segment by speaker
        segments = self._segment_by_speaker(cleaned_text, speakers)

        # Extract topics
        topics = self._extract_topics(segments)

        # Classify segments
        for segment in segments:
            segment["type"] = self._classify_segment(segment, speakers)

        # Assess parse quality
        quality = self._assess_parse_quality(segments, speakers)

        return {
            "speakers": speakers,
            "segments": segments,
            "topics": topics,
            "metadata": metadata or {},
            "parse_quality": quality,
            "parsed_at": datetime.now().isoformat(),
        }

    def _clean_text(self, text: str) -> str:
        """Clean transcript text of common artifacts."""
        # Remove multiple whitespace
        text = re.sub(r"\s+", " ", text)

        # Remove filler patterns
        for pattern in self.filler_patterns:
            text = re.sub(pattern, "", text, flags=re.IGNORECASE)

        # Clean up line breaks and normalize
        text = text.replace("\r\n", "\n").replace("\r", "\n")

        return text.strip()

    def _extract_speakers(self, text: str) -> List[str]:
        """Extract unique speaker names from transcript."""
        speakers = set()

        for line in text.split("\n"):
            line = line.strip()
            if not line:
                continue

            for pattern in self.speaker_patterns:
                match = re.match(pattern, line)
                if match:
                    speaker = match.group(1).strip()
                    # Clean speaker name
                    speaker = self._clean_speaker_name(speaker)
                    if speaker:
                        speakers.add(speaker)
                    break

        # Convert to sorted list for consistency
        speaker_list = sorted(list(speakers))

        # If no speakers found, try to infer from metadata or content
        if not speaker_list:
            speaker_list = self._infer_speakers_from_content(text)

        return speaker_list

    def _clean_speaker_name(self, speaker: str) -> str:
        """Clean and normalize speaker names."""
        # Remove common prefixes/suffixes
        speaker = re.sub(
            r"^(Dr\.?|Mr\.?|Ms\.?|Mrs\.?|Prof\.?)\s*", "", speaker, flags=re.IGNORECASE
        )

        # Handle all caps
        if speaker.isupper():
            speaker = speaker.title()

        # Remove extra whitespace
        speaker = re.sub(r"\s+", " ", speaker).strip()

        # Filter out generic names
        generic_names = {
            "host",
            "guest",
            "interviewer",
            "interviewee",
            "speaker",
            "narrator",
        }
        if speaker.lower() in generic_names:
            return speaker.title()

        return speaker

    def _infer_speakers_from_content(self, text: str) -> List[str]:
        """Infer speakers when no explicit speaker patterns are found."""
        # Look for names mentioned in the content
        # This is a simple heuristic - could be enhanced
        name_pattern = r"\b([A-Z][a-z]+ [A-Z][a-z]+)\b"
        potential_names = re.findall(name_pattern, text)

        # Filter and deduplicate
        speakers = []
        seen = set()
        for name in potential_names:
            if name not in seen and len(name.split()) == 2:  # First Last format
                speakers.append(name)
                seen.add(name)
                if len(speakers) >= 3:  # Limit to reasonable number
                    break

        return speakers[:3] if speakers else ["Speaker"]

    def _segment_by_speaker(
        self, text: str, speakers: List[str]
    ) -> List[Dict[str, Any]]:
        """Split transcript into speaker segments."""
        segments = []
        current_speaker = None
        current_content = []
        segment_id = 0

        for line_num, line in enumerate(text.split("\n")):
            line = line.strip()
            if not line:
                continue

            # Check if line starts with a speaker
            speaker_found = False
            speaker_content = None

            for pattern in self.speaker_patterns:
                match = re.match(pattern, line)
                if match:
                    speaker_name = self._clean_speaker_name(match.group(1))
                    speaker_content = match.group(2).strip()

                    # Save previous segment if exists
                    if current_speaker and current_content:
                        segments.append(
                            {
                                "id": segment_id,
                                "speaker": current_speaker,
                                "content": " ".join(current_content).strip(),
                                "start_line": line_num - len(current_content),
                                "end_line": line_num - 1,
                                "timestamp": self._extract_timestamp(line),
                                "word_count": len(" ".join(current_content).split()),
                            }
                        )
                        segment_id += 1

                    # Start new segment
                    current_speaker = speaker_name
                    current_content = [speaker_content] if speaker_content else []
                    speaker_found = True
                    break

            # If no speaker pattern, add to current content
            if not speaker_found and current_speaker:
                current_content.append(line)
            elif not speaker_found and not current_speaker:
                # No speaker identified yet, treat as generic content
                if not segments:  # First segment
                    segments.append(
                        {
                            "id": segment_id,
                            "speaker": "Unknown",
                            "content": line,
                            "start_line": line_num,
                            "end_line": line_num,
                            "timestamp": self._extract_timestamp(line),
                            "word_count": len(line.split()),
                        }
                    )
                    segment_id += 1

        # Add final segment
        if current_speaker and current_content:
            segments.append(
                {
                    "id": segment_id,
                    "speaker": current_speaker,
                    "content": " ".join(current_content).strip(),
                    "start_line": len(text.split("\n")) - len(current_content),
                    "end_line": len(text.split("\n")) - 1,
                    "timestamp": None,
                    "word_count": len(" ".join(current_content).split()),
                }
            )

        return segments

    def _extract_timestamp(self, text: str) -> Optional[str]:
        """Extract timestamp from text if present."""
        for pattern in self.timestamp_patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1)
        return None

    def _extract_topics(self, segments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extract topics and themes from segments."""
        topics = []

        # Simple topic extraction based on keywords and transitions
        current_topic = None
        topic_segments = []

        for segment in segments:
            content = segment["content"].lower()

            # Check for topic transition indicators
            topic_transition = any(
                indicator in content for indicator in self.topic_indicators
            )

            # Extract key phrases (simple approach)
            keywords = self._extract_keywords(segment["content"])

            if topic_transition or (current_topic and len(topic_segments) > 5):
                # Save previous topic
                if current_topic and topic_segments:
                    topics.append(
                        {
                            "topic": current_topic,
                            "segments": topic_segments.copy(),
                            "keywords": self._consolidate_keywords(topic_segments),
                            "start_segment": topic_segments[0],
                            "end_segment": topic_segments[-1],
                        }
                    )

                # Start new topic
                current_topic = self._generate_topic_name(keywords, segment["content"])
                topic_segments = [segment["id"]]
            else:
                # Continue current topic
                if not current_topic:
                    current_topic = self._generate_topic_name(
                        keywords, segment["content"]
                    )
                topic_segments.append(segment["id"])

        # Add final topic
        if current_topic and topic_segments:
            topics.append(
                {
                    "topic": current_topic,
                    "segments": topic_segments,
                    "keywords": self._consolidate_keywords(
                        [s for s in segments if s["id"] in topic_segments]
                    ),
                    "start_segment": topic_segments[0],
                    "end_segment": topic_segments[-1],
                }
            )

        return topics

    def _extract_keywords(self, text: str) -> List[str]:
        """Extract important keywords from text segment."""
        # Simple keyword extraction - could be enhanced with NLP
        words = re.findall(r"\b[a-zA-Z]{4,}\b", text.lower())

        # Filter common words
        stopwords = {
            "that",
            "this",
            "with",
            "have",
            "will",
            "from",
            "they",
            "know",
            "been",
            "were",
            "said",
            "each",
            "which",
            "their",
            "time",
            "what",
            "about",
            "think",
            "people",
            "things",
            "really",
            "going",
            "want",
        }

        keywords = [w for w in words if w not in stopwords and len(w) > 3]

        # Return most frequent keywords
        from collections import Counter

        return [word for word, count in Counter(keywords).most_common(5)]

    def _generate_topic_name(self, keywords: List[str], content: str) -> str:
        """Generate a topic name from keywords and content."""
        if keywords:
            # Use top keywords
            return " ".join(keywords[:2]).title()
        else:
            # Extract from first few words of content
            words = content.split()[:5]
            return (
                " ".join(words).title()[:50] + "..."
                if len(" ".join(words)) > 50
                else " ".join(words).title()
            )

    def _consolidate_keywords(self, segments: List[Dict[str, Any]]) -> List[str]:
        """Consolidate keywords from multiple segments."""
        all_keywords = []
        for segment in segments:
            all_keywords.extend(self._extract_keywords(segment["content"]))

        from collections import Counter

        return [word for word, count in Counter(all_keywords).most_common(10)]

    def _classify_segment(self, segment: Dict[str, Any], speakers: List[str]) -> str:
        """Classify segment type (question, answer, discussion, etc.)."""
        content = segment["content"].lower()

        # Question indicators
        question_indicators = [
            "?",
            "what",
            "how",
            "why",
            "when",
            "where",
            "can you",
            "do you",
            "would you",
        ]
        if any(indicator in content for indicator in question_indicators):
            return "question"

        # Answer indicators (following a question)
        if len(content) > 100:  # Longer responses likely answers
            return "answer"

        # Transition indicators
        if any(indicator in content for indicator in self.topic_indicators):
            return "transition"

        # Default
        return "discussion"

    def _assess_parse_quality(
        self, segments: List[Dict[str, Any]], speakers: List[str]
    ) -> str:
        """Assess the quality of the parse."""
        if not segments:
            return "failed"

        # Calculate metrics
        avg_segment_length = (
            sum(s["word_count"] for s in segments) / len(segments) if segments else 0
        )
        speaker_count = len(speakers)
        segments_with_speakers = sum(1 for s in segments if s["speaker"] != "Unknown")
        speaker_attribution_rate = (
            segments_with_speakers / len(segments) if segments else 0
        )

        # Determine quality
        if (
            speaker_attribution_rate > 0.8
            and speaker_count > 1
            and avg_segment_length > 10
        ):
            return "excellent"
        elif speaker_attribution_rate > 0.6 and avg_segment_length > 5:
            return "good"
        elif speaker_attribution_rate > 0.3:
            return "fair"
        else:
            return "poor"


def main():
    """Test transcript parser with sample data."""
    parser = TranscriptParser()

    # Sample transcript text
    sample_text = """
    Lex Fridman: Welcome to another episode. Today I'm speaking with Elon Musk about AI and the future.

    Elon Musk: Thanks for having me, Lex. AI is both exciting and terrifying.

    Lex Fridman: What do you think is the biggest risk with artificial intelligence?

    Elon Musk: I think the biggest risk is that we create something smarter than us and then we can't control it.

    [1:23:45]

    Lex Fridman: Speaking of control, let me ask you about neural interfaces and Neuralink.

    Elon Musk: Neuralink is about creating a high-bandwidth interface between the human brain and computers.
    """

    result = parser.parse_transcript(sample_text, {"episode": "Sample Episode"})

    print("Transcript Parse Results:")
    print(f"Speakers: {result['speakers']}")
    print(f"Segments: {len(result['segments'])}")
    print(f"Topics: {len(result['topics'])}")
    print(f"Quality: {result['parse_quality']}")

    for i, segment in enumerate(result["segments"]):
        print(f"\nSegment {i+1}: {segment['speaker']}")
        print(f"Type: {segment['type']}")
        print(f"Content: {segment['content'][:100]}...")


if __name__ == "__main__":
    main()
