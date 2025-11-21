#!/usr/bin/env python3
"""
PODEMOS Ad Detection System
Detect advertisement segments in podcast transcripts for removal.
"""

import re
import json
from typing import List, Dict, Tuple, Optional
import logging
from pathlib import Path
from datetime import datetime
import sqlite3

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class PodmosAdDetector:
    """Advertisement detection system for podcast transcripts."""

    def __init__(self, patterns_file: str = None):
        """Initialize ad detector with pattern database."""
        self.patterns = self._load_ad_patterns(patterns_file)
        self.sponsor_keywords = self._load_sponsor_keywords()

    def _load_ad_patterns(self, patterns_file: str = None) -> List[Dict]:
        """Load advertisement detection patterns."""
        # Built-in patterns for common ad structures
        default_patterns = [
            {
                'name': 'sponsor_intro',
                'pattern': r'(?i)(but first|before we|let me tell you about|this episode is sponsored by|today\'s sponsor|speaking of.*let me tell you about)',
                'type': 'sponsor_intro',
                'confidence': 0.8,
                'context_words': 50
            },
            {
                'name': 'promo_code',
                'pattern': r'(?i)(use code|promo code|discount code|enter code|code\s+\w{3,10}|visit.*slash|dot com slash)',
                'type': 'promo_code',
                'confidence': 0.9,
                'context_words': 30
            },
            {
                'name': 'sponsor_url',
                'pattern': r'(?i)(visit\s+\w+\.com|go to\s+\w+\.com|\w+\.com\s*slash|\w+ dot com)',
                'type': 'sponsor_url',
                'confidence': 0.85,
                'context_words': 25
            },
            {
                'name': 'ad_transition',
                'pattern': r'(?i)(now back to|back to our|returning to|continuing with|where were we)',
                'type': 'ad_end',
                'confidence': 0.7,
                'context_words': 20
            },
            {
                'name': 'patreon_support',
                'pattern': r'(?i)(patreon|support us|made possible by|listeners like you|become a patron)',
                'type': 'support_request',
                'confidence': 0.75,
                'context_words': 40
            },
            {
                'name': 'percentage_discount',
                'pattern': r'(?i)(\d{1,2}\s*%\s*off|\d{1,2}\s*percent\s*off|save\s*\d{1,2}\s*%)',
                'type': 'discount_offer',
                'confidence': 0.8,
                'context_words': 25
            },
            {
                'name': 'free_trial',
                'pattern': r'(?i)(free trial|try.*free|free for|days free|months free|no cost)',
                'type': 'free_offer',
                'confidence': 0.7,
                'context_words': 30
            },
            {
                'name': 'host_read_ad',
                'pattern': r'(?i)(i personally use|i\'ve been using|i really love|i recommend|works great for me)',
                'type': 'host_endorsement',
                'confidence': 0.6,
                'context_words': 40
            }
        ]

        # Load custom patterns from file if provided
        if patterns_file and Path(patterns_file).exists():
            try:
                with open(patterns_file, 'r') as f:
                    custom_patterns = json.load(f)
                default_patterns.extend(custom_patterns)
                logger.info(f"Loaded {len(custom_patterns)} custom ad patterns")
            except Exception as e:
                logger.warning(f"Failed to load custom patterns: {e}")

        return default_patterns

    def _load_sponsor_keywords(self) -> List[str]:
        """Load common sponsor keywords and brand names."""
        return [
            # VPN Services
            'nordvpn', 'expressvpn', 'surfshark', 'cyberghost', 'private internet access',

            # Software/Services
            'grammarly', 'skillshare', 'masterclass', 'audible', 'spotify',
            'squarespace', 'wix', 'hostgator', 'bluehost',

            # Finance/Investment
            'betterment', 'robinhood', 'acorns', 'mint', 'personal capital',
            'credit karma', 'lending club',

            # Food/Meal Delivery
            'hellofresh', 'blue apron', 'meal kit', 'delivery service',

            # Health/Wellness
            'calm app', 'headspace', 'meditation app', 'sleep app',
            'daily vitamins', 'supplement',

            # Media/Entertainment
            'podcast app', 'streaming service', 'audiobook',

            # General Business
            'startup', 'small business', 'enterprise solution',

            # Common sponsor phrases
            'leading provider', 'trusted by millions', 'number one', 'award winning'
        ]

    def detect_ads(self, transcript_text: str, segments: List[Dict] = None) -> List[Dict]:
        """
        Detect advertisement segments in transcript.

        Args:
            transcript_text: Full transcript text
            segments: Optional list of timestamped segments from Whisper

        Returns:
            List of detected ad segments with timestamps and confidence scores
        """
        try:
            logger.info("Starting advertisement detection")

            # Split transcript into sentences for analysis
            sentences = self._split_into_sentences(transcript_text)

            # Detect ad patterns
            ad_matches = []

            for pattern_info in self.patterns:
                matches = self._find_pattern_matches(
                    sentences,
                    pattern_info['pattern'],
                    pattern_info
                )
                ad_matches.extend(matches)

            # Detect sponsor keywords
            sponsor_matches = self._detect_sponsor_mentions(sentences)
            ad_matches.extend(sponsor_matches)

            # Group adjacent matches into segments
            ad_segments = self._group_matches_into_segments(ad_matches, sentences)

            # If we have Whisper segments, map to timestamps
            if segments:
                ad_segments = self._map_to_timestamps(ad_segments, sentences, segments)

            # Calculate confidence scores
            ad_segments = self._calculate_confidence_scores(ad_segments)

            # Filter low-confidence detections
            filtered_segments = [seg for seg in ad_segments if seg['confidence'] >= 0.5]

            logger.info(f"Detected {len(filtered_segments)} advertisement segments")
            return filtered_segments

        except Exception as e:
            logger.error(f"Ad detection failed: {e}")
            return []

    def _split_into_sentences(self, text: str) -> List[str]:
        """Split text into sentences for analysis."""
        # Simple sentence splitting (could be improved with NLTK)
        sentences = re.split(r'[.!?]+\s+', text)
        return [s.strip() for s in sentences if s.strip()]

    def _find_pattern_matches(self, sentences: List[str], pattern: str, pattern_info: Dict) -> List[Dict]:
        """Find pattern matches in sentences."""
        matches = []

        for i, sentence in enumerate(sentences):
            if re.search(pattern, sentence):
                # Get context around the match
                start_idx = max(0, i - 2)
                end_idx = min(len(sentences), i + 3)
                context = ' '.join(sentences[start_idx:end_idx])

                matches.append({
                    'sentence_index': i,
                    'type': pattern_info['type'],
                    'pattern_name': pattern_info['name'],
                    'confidence': pattern_info['confidence'],
                    'matched_text': sentence,
                    'context': context,
                    'start_sentence': start_idx,
                    'end_sentence': end_idx
                })

        return matches

    def _detect_sponsor_mentions(self, sentences: List[str]) -> List[Dict]:
        """Detect mentions of known sponsors and brands."""
        matches = []

        for i, sentence in enumerate(sentences):
            sentence_lower = sentence.lower()

            for keyword in self.sponsor_keywords:
                if keyword in sentence_lower:
                    matches.append({
                        'sentence_index': i,
                        'type': 'sponsor_mention',
                        'pattern_name': 'sponsor_keyword',
                        'confidence': 0.7,
                        'matched_text': sentence,
                        'sponsor_keyword': keyword,
                        'context': sentence,
                        'start_sentence': i,
                        'end_sentence': i
                    })
                    break  # Only match one keyword per sentence

        return matches

    def _group_matches_into_segments(self, matches: List[Dict], sentences: List[str]) -> List[Dict]:
        """Group adjacent matches into advertisement segments."""
        if not matches:
            return []

        # Sort matches by sentence index
        matches.sort(key=lambda x: x['sentence_index'])

        segments = []
        current_segment = None

        for match in matches:
            if current_segment is None:
                # Start new segment
                current_segment = {
                    'start_sentence': match['start_sentence'],
                    'end_sentence': match['end_sentence'],
                    'matches': [match],
                    'types': [match['type']]
                }
            elif match['sentence_index'] <= current_segment['end_sentence'] + 3:
                # Extend current segment (within 3 sentences)
                current_segment['end_sentence'] = max(current_segment['end_sentence'], match['end_sentence'])
                current_segment['matches'].append(match)
                if match['type'] not in current_segment['types']:
                    current_segment['types'].append(match['type'])
            else:
                # Finish current segment and start new one
                segments.append(current_segment)
                current_segment = {
                    'start_sentence': match['start_sentence'],
                    'end_sentence': match['end_sentence'],
                    'matches': [match],
                    'types': [match['type']]
                }

        # Add final segment
        if current_segment:
            segments.append(current_segment)

        # Add segment text
        for segment in segments:
            segment_text = ' '.join(sentences[segment['start_sentence']:segment['end_sentence']+1])
            segment['text'] = segment_text
            segment['sentence_count'] = segment['end_sentence'] - segment['start_sentence'] + 1

        return segments

    def _map_to_timestamps(self, segments: List[Dict], sentences: List[str], whisper_segments: List[Dict]) -> List[Dict]:
        """Map sentence-based segments to timestamps using Whisper segments."""
        try:
            # Create mapping from text to timestamps
            full_text = ' '.join(sentences)

            for segment in segments:
                segment_text = segment['text']

                # Find approximate position in full text
                start_pos = full_text.find(segment_text)
                if start_pos == -1:
                    # Fallback: use first few words
                    first_words = ' '.join(segment_text.split()[:5])
                    start_pos = full_text.find(first_words)

                if start_pos >= 0:
                    # Find corresponding Whisper segment
                    chars_processed = 0

                    for w_seg in whisper_segments:
                        seg_text = w_seg.get('text', '')
                        seg_start = chars_processed
                        seg_end = chars_processed + len(seg_text)

                        if seg_start <= start_pos <= seg_end:
                            segment['start_time'] = w_seg.get('start', 0)
                            # Estimate end time
                            segment['end_time'] = segment['start_time'] + len(segment_text) * 0.05  # ~20 chars/second speech
                            break

                        chars_processed = seg_end

                # If no timestamp found, use sentence-based estimation
                if 'start_time' not in segment:
                    # Rough estimate: 3 seconds per sentence
                    segment['start_time'] = segment['start_sentence'] * 3
                    segment['end_time'] = segment['end_sentence'] * 3

            return segments

        except Exception as e:
            logger.warning(f"Failed to map timestamps: {e}")
            # Fallback to sentence-based timing
            for segment in segments:
                segment['start_time'] = segment['start_sentence'] * 3
                segment['end_time'] = segment['end_sentence'] * 3
            return segments

    def _calculate_confidence_scores(self, segments: List[Dict]) -> List[Dict]:
        """Calculate overall confidence scores for segments."""
        for segment in segments:
            # Base confidence from pattern matches
            pattern_confidences = [match['confidence'] for match in segment['matches']]
            base_confidence = sum(pattern_confidences) / len(pattern_confidences)

            # Boost confidence based on multiple indicators
            type_count = len(segment['types'])
            match_count = len(segment['matches'])

            # More types and matches = higher confidence
            type_boost = min(type_count * 0.1, 0.3)
            match_boost = min(match_count * 0.05, 0.2)

            # Penalty for very short segments
            length_penalty = 0.1 if segment['sentence_count'] < 2 else 0

            final_confidence = min(base_confidence + type_boost + match_boost - length_penalty, 1.0)
            segment['confidence'] = round(final_confidence, 2)

        return segments

    def save_detection_results(self, results: List[Dict], output_file: str) -> str:
        """Save ad detection results to JSON file."""
        try:
            detection_data = {
                'detected_at': datetime.now().isoformat(),
                'total_segments': len(results),
                'segments': results
            }

            with open(output_file, 'w') as f:
                json.dump(detection_data, f, indent=2)

            logger.info(f"Ad detection results saved to: {output_file}")
            return output_file

        except Exception as e:
            logger.error(f"Failed to save detection results: {e}")
            return None

    def export_for_audio_cutting(self, segments: List[Dict], output_file: str = None) -> str:
        """Export ad segments in format suitable for audio cutting."""
        try:
            if not output_file:
                output_file = f"ad_cuts_{int(datetime.now().timestamp())}.json"

            # Convert to simple timestamp ranges
            cut_segments = []
            for segment in segments:
                if segment.get('start_time') is not None and segment.get('end_time') is not None:
                    cut_segments.append({
                        'start_time': segment['start_time'],
                        'end_time': segment['end_time'],
                        'confidence': segment['confidence'],
                        'type': '+'.join(segment['types']),
                        'description': f"Ad segment: {segment['text'][:100]}..."
                    })

            cut_data = {
                'cut_segments': cut_segments,
                'total_duration_to_cut': sum(s['end_time'] - s['start_time'] for s in cut_segments),
                'created_at': datetime.now().isoformat()
            }

            with open(output_file, 'w') as f:
                json.dump(cut_data, f, indent=2)

            logger.info(f"Audio cutting data exported to: {output_file}")
            return output_file

        except Exception as e:
            logger.error(f"Failed to export cutting data: {e}")
            return None

def detect_ads(transcript_file: str) -> List[Dict]:
    """
    Convenience function for detecting ads from transcript file.
    This matches the required API from the acceptance criteria.
    """
    try:
        with open(transcript_file, 'r', encoding='utf-8') as f:
            transcript_text = f.read()

        detector = PodmosAdDetector()
        ads = detector.detect_ads(transcript_text)

        return ads

    except Exception as e:
        logger.error(f"Failed to detect ads from {transcript_file}: {e}")
        return []

def main():
    """Example usage and testing."""
    import argparse

    parser = argparse.ArgumentParser(description="PODEMOS Ad Detection System")
    parser.add_argument('--transcript', help='Transcript file to analyze')
    parser.add_argument('--test', action='store_true', help='Run with test transcript')
    parser.add_argument('--output', help='Output file for results')
    args = parser.parse_args()

    if args.test:
        # Create test transcript if it doesn't exist
        from podemos_transcription import create_test_transcript
        create_test_transcript()
        args.transcript = 'test_transcript.txt'

    if args.transcript:
        detector = PodmosAdDetector()

        # Read transcript
        with open(args.transcript, 'r', encoding='utf-8') as f:
            transcript_text = f.read()

        # Detect ads
        ad_segments = detector.detect_ads(transcript_text)

        print(f"Found {len(ad_segments)} ad segments:")
        for i, segment in enumerate(ad_segments):
            print(f"\nSegment {i+1}:")
            print(f"  Time: {segment.get('start_time', 0):.1f}s - {segment.get('end_time', 0):.1f}s")
            print(f"  Confidence: {segment['confidence']}")
            print(f"  Types: {', '.join(segment['types'])}")
            print(f"  Text: {segment['text'][:100]}...")

        # Save results if output file specified
        if args.output:
            detector.save_detection_results(ad_segments, args.output)
            detector.export_for_audio_cutting(ad_segments, args.output.replace('.json', '_cuts.json'))

    else:
        print("Usage: python podemos_ad_detection.py --transcript <file> [--output <file>]")
        print("       python podemos_ad_detection.py --test")

if __name__ == "__main__":
    main()