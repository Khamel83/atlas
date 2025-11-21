#!/usr/bin/env python3
"""
Transcript Quality Judge and Evaluation Module
Ensures found transcripts are actual high-quality podcast transcripts
"""

import re
import json
from typing import Dict, List, Tuple, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class TranscriptJudge:
    """
    Comprehensive transcript quality evaluation system
    Judges whether found content is actually a valid podcast transcript
    """

    def __init__(self):
        # Quality thresholds
        self.min_length = 5000  # Minimum viable transcript length
        self.ideal_length = 20000  # Ideal transcript length
        self.max_length = 500000  # Maximum reasonable length

        # Transcript quality indicators
        self.transcript_indicators = [
            # Speaker indicators
            r'\b(speaker\s*\d*|host|guest|interviewer|moderator):\b',
            r'\b(presenter|narrator|announcer):\b',

            # Podcast-specific patterns
            r'\b(welcome\s+to|this\s+is|today\s+we|in\s+this\s+episode)\b',
            r'\b(thanks\s+for|joining\s+us|we\'re\s+talking\s+about)\b',

            # Conversation patterns
            r'\[laughter\]|\[applause\]|\[music\]',
            r'\b(really|actually|basically|literally|exactly)\b',
            r'\b(sort\s+of|kind\s+of|you\s+know|i\s+mean)\b',

            # Technical podcast terms
            r'\b(episode|show|podcast|segment|break)\b',
            r'\b(listeners|audience|subscribers|viewers)\b',
        ]

        # Negative indicators (non-transcript content)
        self.negative_indicators = [
            # Article/website patterns
            r'<\!doctype\s+html>|<html|<body|<div',
            r'\b(click\s+here|read\s+more|subscribe\s+now)\b',
            r'\b(privacy\s+policy|terms\s+of\s+service|cookie\s+policy)\b',

            # Non-content patterns
            r'\b(copyright|all\s+rights\s+reserved|\d{4})\b',
            r'\b(loading|please\s+wait|page\s+not\s+found)\b',

            # Transcript service markers (often incomplete)
            r'\b(transcript\s+powered\s+by|generated\s+by)\b',
            r'\b(preview|summary|excerpt|sample)\s+transcript\b',
        ]

        # Podcast conversation patterns
        self.conversation_patterns = [
            r'\b(yeah|yes|no|right|exactly|sure|absolutely)\b',
            r'\b(i\s+think|we\s+think|you\s+think|they\s+think)\b',
            r'\b(let\'s|we\'re|you\'re|they\'re|i\'m)\b',
            r'\b(going\s+to|want\s+to|need\s+to|have\s+to)\b',
            r'\b(what|when|where|why|how|who|which)\b',
        ]

        # Structure indicators
        self.structure_indicators = [
            # Time stamps
            r'\d{1,2}:\d{2}(?::\d{2})?',  # HH:MM or HH:MM:SS

            # Episode markers
            r'\b(episode\s+\d+|part\s+\d+|segment\s+\d+)\b',
            r'\b(introduction|main\s+topic|conclusion|outro)\b',

            # Question patterns
            r'\?\s*$',  # Lines ending with questions
            r'\b(so|well|but|and|or)\s*$',
        ]

    def evaluate_transcript(self, content: str, podcast_name: str, episode_title: str) -> Dict:
        """
        Comprehensive transcript quality evaluation

        Returns:
            Dict with quality scores and detailed analysis
        """
        if not content or len(content.strip()) < self.min_length:
            return {
                'is_valid_transcript': False,
                'quality_score': 0.0,
                'reason': 'Content too short or empty',
                'details': {}
            }

        # Normalize content
        content_clean = self._clean_content(content)
        content_lower = content_clean.lower()

        # Calculate quality scores
        scores = {
            'length_score': self._score_length(content_clean),
            'structure_score': self._score_structure(content_clean),
            'conversation_score': self._score_conversation(content_clean),
            'accuracy_score': self._score_accuracy(content_clean, podcast_name, episode_title),
            'negative_score': self._score_negative_indicators(content_clean)
        }

        # Calculate overall quality score
        overall_score = self._calculate_overall_score(scores)

        # Determine validity
        is_valid = overall_score >= 0.6 and scores['accuracy_score'] >= 0.3

        # Detailed analysis
        analysis = {
            'length': len(content_clean),
            'word_count': len(content_clean.split()),
            'sentence_count': len(re.findall(r'[.!?]+', content_clean)),
            'speaker_indicators_found': self._count_pattern_matches(content_clean, self.transcript_indicators[:3]),
            'conversation_markers': self._count_pattern_matches(content_clean, self.conversation_patterns[:3]),
            'structure_markers': self._count_pattern_matches(content_clean, self.structure_indicators),
            'negative_indicators': self._count_pattern_matches(content_clean, self.negative_indicators),
        }

        # Generate assessment
        assessment = self._generate_assessment(scores, analysis)

        return {
            'is_valid_transcript': is_valid,
            'quality_score': overall_score,
            'confidence': self._calculate_confidence(scores),
            'assessment': assessment,
            'scores': scores,
            'analysis': analysis,
            'recommendations': self._generate_recommendations(scores, analysis)
        }

    def _clean_content(self, content: str) -> str:
        """Clean and normalize content for analysis"""
        # Remove excessive whitespace
        content = re.sub(r'\s+', ' ', content)

        # Remove HTML tags if present
        content = re.sub(r'<[^>]+>', '', content)

        # Remove common non-transcript elements
        content = re.sub(r'\b\s*(https?://|www\.)\S+\b', '', content)  # URLs
        content = re.sub(r'\b[\w\.-]+@[\w\.-]+\.\w+\b', '', content)  # Email addresses

        # Remove excessive punctuation
        content = re.sub(r'[.]{2,}', '.', content)
        content = re.sub(r'[!]{2,}', '!', content)
        content = re.sub(r'[?]{2,}', '?', content)

        return content.strip()

    def _score_length(self, content: str) -> float:
        """Score based on content length"""
        length = len(content)

        if length < self.min_length:
            return 0.0
        elif length < 10000:
            return 0.3
        elif length < self.ideal_length:
            return 0.7
        elif length < 100000:
            return 1.0
        elif length < self.max_length:
            return 0.8
        else:
            return 0.5  # Too long, might be multiple episodes

    def _score_structure(self, content: str) -> float:
        """Score based on transcript structure indicators"""
        structure_count = self._count_pattern_matches(content, self.structure_indicators)

        # More structure indicators = higher score
        if structure_count >= 10:
            return 1.0
        elif structure_count >= 5:
            return 0.8
        elif structure_count >= 2:
            return 0.5
        elif structure_count >= 1:
            return 0.3
        else:
            return 0.1

    def _score_conversation(self, content: str) -> float:
        """Score based on conversational patterns"""
        conversation_count = self._count_pattern_matches(content, self.conversation_patterns)
        word_count = len(content.split())

        if word_count == 0:
            return 0.0

        # Ratio of conversation markers to total words
        ratio = conversation_count / word_count

        if ratio >= 0.05:  # 5% or more conversation markers
            return 1.0
        elif ratio >= 0.03:
            return 0.8
        elif ratio >= 0.01:
            return 0.5
        else:
            return 0.2

    def _score_accuracy(self, content: str, podcast_name: str, episode_title: str) -> float:
        """Score based on how well content matches the specific podcast/episode"""
        content_lower = content.lower()
        podcast_lower = podcast_name.lower()
        episode_lower = episode_title.lower()

        score = 0.0

        # Podcast name matching (highest weight)
        podcast_variations = [
            podcast_lower,
            podcast_lower.replace(' podcast', ''),
            podcast_lower.replace(' the ', ' '),
            podcast_lower.replace(' with ', ' '),
        ]

        podcast_found = any(variation in content_lower for variation in podcast_variations)
        if podcast_found:
            score += 0.4

        # Episode title terms
        episode_terms = re.findall(r'\b\w{4,}\b', episode_lower)
        if episode_terms:
            terms_found = sum(1 for term in episode_terms if term in content_lower)
            term_coverage = terms_found / len(episode_terms)
            score += term_coverage * 0.4
        else:
            # If no meaningful terms, reward length
            if len(content) > 15000:
                score += 0.2

        # Content indicators (lowest weight)
        transcript_indicators_count = self._count_pattern_matches(content, self.transcript_indicators[:5])
        if transcript_indicators_count >= 5:
            score += 0.2
        elif transcript_indicators_count >= 2:
            score += 0.1

        return min(score, 1.0)

    def _score_negative_indicators(self, content: str) -> float:
        """Score negative indicators (lower is better)"""
        negative_count = self._count_pattern_matches(content, self.negative_indicators)

        # More negative indicators = lower score
        if negative_count >= 5:
            return 0.0
        elif negative_count >= 3:
            return 0.2
        elif negative_count >= 1:
            return 0.5
        else:
            return 1.0

    def _count_pattern_matches(self, content: str, patterns: List[str]) -> int:
        """Count matches of regex patterns in content"""
        total_matches = 0
        for pattern in patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            total_matches += len(matches)
        return total_matches

    def _calculate_overall_score(self, scores: Dict[str, float]) -> float:
        """Calculate overall quality score with weighted components"""
        weights = {
            'accuracy_score': 0.4,      # Most important - must be our transcript
            'length_score': 0.25,       # Must be substantial length
            'conversation_score': 0.2,   # Should sound like conversation
            'structure_score': 0.1,      # Should have some structure
            'negative_score': 0.05      # Should avoid negative patterns
        }

        weighted_score = sum(scores[key] * weights[key] for key in weights)
        return round(weighted_score, 3)

    def _calculate_confidence(self, scores: Dict[str, float]) -> str:
        """Calculate confidence level in the assessment"""
        overall = self._calculate_overall_score(scores)
        accuracy = scores['accuracy_score']

        if overall >= 0.8 and accuracy >= 0.6:
            return "HIGH"
        elif overall >= 0.6 and accuracy >= 0.4:
            return "MEDIUM"
        elif overall >= 0.4 and accuracy >= 0.3:
            return "LOW"
        else:
            return "VERY_LOW"

    def _generate_assessment(self, scores: Dict[str, float], analysis: Dict) -> str:
        """Generate human-readable assessment"""
        overall = self._calculate_overall_score(scores)

        if overall >= 0.8:
            return "HIGH-QUALITY TRANSCRIPT: Well-structured, accurate podcast transcript with good conversational flow"
        elif overall >= 0.6:
            return "GOOD TRANSCRIPT: Solid podcast transcript with minor quality issues"
        elif overall >= 0.4:
            return "FAIR TRANSCRIPT: Acceptable transcript but may have accuracy or structure issues"
        elif overall >= 0.3:
            return "POOR TRANSCRIPT: Low-quality transcript, may be incomplete or inaccurate"
        else:
            return "INVALID: Not a valid podcast transcript"

    def _generate_recommendations(self, scores: Dict[str, float], analysis: Dict) -> List[str]:
        """Generate improvement recommendations"""
        recommendations = []

        if scores['accuracy_score'] < 0.3:
            recommendations.append("Content doesn't match well with target podcast/episode")

        if scores['length_score'] < 0.5:
            if analysis['length'] < 5000:
                recommendations.append("Transcript too short - likely incomplete")
            else:
                recommendations.append("Unusual length - may contain extra content")

        if scores['conversation_score'] < 0.3:
            recommendations.append("Low conversational markers - may not be natural speech")

        if scores['structure_score'] < 0.3:
            recommendations.append("Lacks transcript structure indicators")

        if scores['negative_score'] < 0.5:
            recommendations.append("Contains non-transcript elements (website content, ads, etc.)")

        if analysis['negative_indicators'] > 3:
            recommendations.append("Multiple negative indicators found")

        return recommendations if recommendations else ["Good quality transcript"]

    def judge_multiple_transcripts(self, transcripts: List[Dict]) -> Dict:
        """
        Judge multiple transcripts and return the best one

        Args:
            transcripts: List of {'content': str, 'source': str, 'url': str}

        Returns:
            Best transcript with evaluation details
        """
        if not transcripts:
            return None

        evaluated = []
        for transcript in transcripts:
            evaluation = self.evaluate_transcript(
                transcript['content'],
                transcript.get('podcast_name', ''),
                transcript.get('episode_title', '')
            )

            evaluated.append({
                'transcript': transcript,
                'evaluation': evaluation
            })

        # Sort by quality score, then by accuracy score
        evaluated.sort(key=lambda x: (
            x['evaluation']['quality_score'],
            x['evaluation']['scores']['accuracy_score']
        ), reverse=True)

        return evaluated[0] if evaluated else None

    def generate_quality_report(self, evaluation: Dict) -> str:
        """Generate a detailed quality report"""
        if not evaluation:
            return "No evaluation data available"

        lines = []
        lines.append(f"📊 TRANSCRIPT QUALITY REPORT")
        lines.append(f"═" * 50)
        lines.append(f"Overall Quality: {evaluation['quality_score']:.1%}")
        lines.append(f"Assessment: {evaluation['assessment']}")
        lines.append(f"Confidence: {evaluation['confidence']}")
        lines.append(f"Valid Transcript: {'✅ YES' if evaluation['is_valid_transcript'] else '❌ NO'}")

        lines.append(f"\n📈 COMPONENT SCORES:")
        for component, score in evaluation['scores'].items():
            lines.append(f"  {component.replace('_', ' ').title()}: {score:.1%}")

        lines.append(f"\n📋 ANALYSIS:")
        for key, value in evaluation['analysis'].items():
            lines.append(f"  {key.replace('_', ' ').title()}: {value}")

        if evaluation['recommendations']:
            lines.append(f"\n💡 RECOMMENDATIONS:")
            for rec in evaluation['recommendations']:
                lines.append(f"  • {rec}")

        return "\n".join(lines)

# Test function
def test_transcript_judge():
    """Test the transcript judge with sample content"""
    judge = TranscriptJudge()

    # Test with high-quality transcript
    good_transcript = """
    Host: Welcome to the Tech Podcast, I'm your host Sarah.
    Guest: Thanks for having me, Sarah. It's great to be here.
    Host: Today we're talking about artificial intelligence and its impact on society.
    Guest: That's a really important topic. I think AI is changing everything.
    Host: Absolutely. Let's start with your background in AI research...
    [laughter]
    Guest: Well, I've been working in machine learning for about 15 years now.
    Host: That's impressive! Can you tell our listeners about your work?
    """

    result = judge.evaluate_transcript(good_transcript, "Tech Podcast", "AI Impact")
    print("Good Transcript Test:")
    print(judge.generate_quality_report(result))

    # Test with poor content
    bad_content = "Click here to subscribe to our newsletter! Privacy Policy | Terms of Service"
    bad_result = judge.evaluate_transcript(bad_content, "Tech Podcast", "AI Impact")
    print("\nBad Content Test:")
    print(judge.generate_quality_report(bad_result))

if __name__ == "__main__":
    test_transcript_judge()