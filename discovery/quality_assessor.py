#!/usr/bin/env python3
"""
Quality Assessor for Atlas

This module assesses content quality using multiple metrics including
readability, depth, factual accuracy, and bias detection.
"""

import re
from typing import List, Dict, Any, Optional, Tuple
from collections import defaultdict
import math


class ContentQualityScorer:
    """Content quality assessment system"""

    def __init__(self):
        """Initialize the quality scorer"""
        # Readability scoring parameters
        self.flesch_kincaid_weights = {
            'sentence_length': 0.39,
            'syllables_per_word': 11.8,
            'base': 15.59
        }

        # Content depth indicators
        self.depth_indicators = {
            'headings': r'<h[1-6][^>]*>(.*?)</h[1-6]>',
            'lists': r'<(ul|ol)[^>]*>.*?</\1>',
            'code_blocks': r'<pre[^>]*>.*?</pre>',
            'images': r'<img[^>]*>',
            'links': r'<a[^>]*href=[^>]*>.*?</a>',
            'tables': r'<table[^>]*>.*?</table>'
        }

        # Factual accuracy keywords
        self.accuracy_indicators = [
            'according to', 'research shows', 'study found', 'data indicates',
            'survey results', 'statistical analysis', 'peer-reviewed',
            'evidence suggests', 'scientific consensus'
        ]

        # Bias detection patterns
        self.bias_patterns = {
            'political_left': [
                'progressive', 'liberal', 'conservative agenda', 'right-wing bias',
                'corporate media', 'establishment narrative'
            ],
            'political_right': [
                'liberal media', 'left-wing bias', 'socialist agenda',
                'mainstream media conspiracy', 'traditional values'
            ],
            'sensationalist': [
                'shocking', 'unbelievable', 'you won\'t believe', 'insane',
                'crazy', 'mind-blowing', 'jaw-dropping'
            ]
        }

    def assess_content_quality(self, content: str, title: str = "",
                             metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Assess overall content quality using multiple metrics

        Args:
            content (str): Content to assess
            title (str): Content title
            metadata (Dict[str, Any]): Additional metadata

        Returns:
            Dict[str, Any]: Quality assessment results
        """
        print("Assessing content quality...")

        # Calculate readability score
        readability_score = self.calculate_readability_score(content)

        # Calculate depth score
        depth_score = self.calculate_depth_score(content)

        # Calculate factual accuracy score
        accuracy_score = self.calculate_factual_accuracy_score(content)

        # Calculate bias score
        bias_scores = self.detect_bias(content)

        # Calculate completeness score
        completeness_score = self.calculate_completeness_score(content, title, metadata)

        # Calculate overall quality score
        overall_score = self._calculate_overall_quality_score(
            readability_score, depth_score, accuracy_score,
            bias_scores, completeness_score
        )

        assessment = {
            'readability_score': readability_score,
            'depth_score': depth_score,
            'accuracy_score': accuracy_score,
            'bias_scores': bias_scores,
            'completeness_score': completeness_score,
            'overall_quality_score': overall_score,
            'quality_level': self._classify_quality_level(overall_score),
            'assessment_timestamp': __import__('time').time()
        }

        return assessment

    def calculate_readability_score(self, content: str) -> float:
        """
        Calculate readability score using Flesch-Kincaid grade level

        Args:
            content (str): Content to analyze

        Returns:
            float: Readability score (0.0 to 1.0)
        """
        # Clean content for analysis
        clean_content = re.sub(r'<[^>]+>', '', content)  # Remove HTML tags
        clean_content = re.sub(r'[^\w\s]', ' ', clean_content)  # Remove punctuation
        clean_content = re.sub(r'\s+', ' ', clean_content).strip()  # Normalize whitespace

        if not clean_content:
            return 0.0

        # Count sentences
        sentences = re.split(r'[.!?]+', clean_content)
        sentences = [s.strip() for s in sentences if s.strip()]
        sentence_count = len(sentences)

        if sentence_count == 0:
            return 0.0

        # Count words
        words = clean_content.split()
        word_count = len(words)

        if word_count == 0:
            return 0.0

        # Count syllables (approximation)
        syllable_count = sum(self._count_syllables(word) for word in words)

        # Calculate Flesch-Kincaid grade level
        avg_sentence_length = word_count / sentence_count
        avg_syllables_per_word = syllable_count / word_count

        fk_grade = (
            self.flesch_kincaid_weights['sentence_length'] * avg_sentence_length +
            self.flesch_kincaid_weights['syllables_per_word'] * avg_syllables_per_word -
            self.flesch_kincaid_weights['base']
        )

        # Convert to 0-1 scale (assuming grade 0-20 scale)
        readability_score = max(0.0, min(1.0, 1.0 - (fk_grade / 20.0)))

        return readability_score

    def calculate_depth_score(self, content: str) -> float:
        """
        Calculate content depth score based on structural elements

        Args:
            content (str): Content to analyze

        Returns:
            float: Depth score (0.0 to 1.0)
        """
        depth_score = 0.0
        max_possible_score = 0.0
        actual_score = 0.0

        # Check for various structural elements
        for element_name, pattern in self.depth_indicators.items():
            matches = re.findall(pattern, content, re.DOTALL | re.IGNORECASE)
            count = len(matches)

            # Assign weights to different elements
            weights = {
                'headings': 0.2,
                'lists': 0.15,
                'code_blocks': 0.2,
                'images': 0.1,
                'links': 0.1,
                'tables': 0.25
            }

            weight = weights.get(element_name, 0.1)
            max_possible_score += weight

            # Score based on count (with diminishing returns)
            if count > 0:
                element_score = weight * min(1.0, count / 5.0)  # Cap at 5 elements
                actual_score += element_score

        if max_possible_score > 0:
            depth_score = actual_score / max_possible_score

        return min(depth_score, 1.0)

    def calculate_factual_accuracy_score(self, content: str) -> float:
        """
        Calculate factual accuracy score based on evidence indicators

        Args:
            content (str): Content to analyze

        Returns:
            float: Accuracy score (0.0 to 1.0)
        """
        content_lower = content.lower()
        indicator_count = 0

        # Count accuracy indicators
        for indicator in self.accuracy_indicators:
            indicator_count += content_lower.count(indicator)

        # Score based on indicator density (per 1000 words)
        word_count = len(content.split())
        if word_count > 0:
            indicator_density = (indicator_count / word_count) * 1000
            # Normalize to 0-1 scale (assuming max 5 indicators per 1000 words)
            accuracy_score = min(1.0, indicator_density / 5.0)
        else:
            accuracy_score = 0.0

        return accuracy_score

    def detect_bias(self, content: str) -> Dict[str, float]:
        """
        Detect potential bias in content

        Args:
            content (str): Content to analyze

        Returns:
            Dict[str, float]: Bias scores for different categories
        """
        content_lower = content.lower()
        bias_scores = {}

        # Check for different types of bias
        for bias_type, patterns in self.bias_patterns.items():
            pattern_count = 0
            for pattern in patterns:
                pattern_count += content_lower.count(pattern)

            # Score bias (higher = more biased)
            # Normalize to 0-1 scale (assuming max 3 patterns per 1000 words)
            word_count = len(content.split())
            if word_count > 0:
                bias_density = (pattern_count / word_count) * 1000
                bias_scores[bias_type] = min(1.0, bias_density / 3.0)
            else:
                bias_scores[bias_type] = 0.0

        return bias_scores

    def calculate_completeness_score(self, content: str, title: str = "",
                                   metadata: Dict[str, Any] = None) -> float:
        """
        Calculate content completeness score

        Args:
            content (str): Content to analyze
            title (str): Content title
            metadata (Dict[str, Any]): Additional metadata

        Returns:
            float: Completeness score (0.0 to 1.0)
        """
        completeness_score = 0.0
        completed_elements = 0
        total_elements = 5  # Title, content, length, structure, metadata

        # Check if title exists
        if title and title.strip():
            completed_elements += 1

        # Check if content exists
        if content and content.strip():
            completed_elements += 1

        # Check content length (at least 500 words)
        word_count = len(content.split())
        if word_count >= 500:
            completed_elements += 1

        # Check for structural elements (headings, lists, etc.)
        structural_elements = sum(
            1 for pattern in self.depth_indicators.values()
            if re.search(pattern, content, re.DOTALL | re.IGNORECASE)
        )
        if structural_elements >= 3:  # At least 3 structural elements
            completed_elements += 1

        # Check metadata completeness
        if metadata:
            required_metadata = ['author', 'date', 'source']
            metadata_elements = sum(
                1 for key in required_metadata
                if key in metadata and metadata[key]
            )
            if metadata_elements >= 2:  # At least 2 metadata elements
                completed_elements += 1
        else:
            # If no metadata, we can't check completeness
            total_elements -= 1

        if total_elements > 0:
            completeness_score = completed_elements / total_elements

        return completeness_score

    def _calculate_overall_quality_score(self, readability: float, depth: float,
                                       accuracy: float, bias_scores: Dict[str, float],
                                       completeness: float) -> float:
        """
        Calculate overall quality score from component scores

        Args:
            readability (float): Readability score
            depth (float): Depth score
            accuracy (float): Accuracy score
            bias_scores (Dict[str, float]): Bias scores
            completeness (float): Completeness score

        Returns:
            float: Overall quality score (0.0 to 1.0)
        """
        # Average bias scores
        avg_bias = sum(bias_scores.values()) / len(bias_scores) if bias_scores else 0.0

        # Calculate overall score with weights
        overall_score = (
            readability * 0.2 +      # 20% weight
            depth * 0.25 +          # 25% weight
            accuracy * 0.25 +       # 25% weight
            (1.0 - avg_bias) * 0.15 +  # 15% weight (inverted bias)
            completeness * 0.15     # 15% weight
        )

        return min(overall_score, 1.0)

    def _classify_quality_level(self, quality_score: float) -> str:
        """
        Classify quality level based on score

        Args:
            quality_score (float): Quality score

        Returns:
            str: Quality level classification
        """
        if quality_score >= 0.8:
            return 'excellent'
        elif quality_score >= 0.6:
            return 'good'
        elif quality_score >= 0.4:
            return 'fair'
        elif quality_score >= 0.2:
            return 'poor'
        else:
            return 'very_poor'

    def _count_syllables(self, word: str) -> int:
        """
        Count syllables in a word (approximation)

        Args:
            word (str): Word to count syllables for

        Returns:
            int: Syllable count
        """
        word = word.lower()
        if len(word) <= 3:
            return 1

        # Count vowel groups
        vowels = "aeiouy"
        syllable_count = 0
        prev_was_vowel = False

        for char in word:
            is_vowel = char in vowels
            if is_vowel and not prev_was_vowel:
                syllable_count += 1
            prev_was_vowel = is_vowel

        # Handle silent 'e' at the end
        if word.endswith('e') and syllable_count > 1:
            syllable_count -= 1

        return max(1, syllable_count)


def main():
    """Example usage of ContentQualityScorer"""
    # Create quality scorer
    scorer = ContentQualityScorer()

    # Sample content
    sample_content = """
    <h1>Introduction to Machine Learning</h1>

    <p>Machine learning is a subset of artificial intelligence that focuses on
    algorithms that can learn from and make predictions or decisions based on data.
    According to research published in the Journal of Machine Learning Research,
    these algorithms improve automatically through experience.</p>

    <h2>Key Concepts</h2>

    <ul>
        <li>Supervised Learning: Learning with labeled training data</li>
        <li>Unsupervised Learning: Finding patterns in unlabeled data</li>
        <li>Reinforcement Learning: Learning through interaction with an environment</li>
    </ul>

    <h2>Popular Algorithms</h2>

    <p>Some of the most widely used machine learning algorithms include:</p>

    <ol>
        <li>Linear Regression</li>
        <li>Decision Trees</li>
        <li>Random Forest</li>
        <li>Support Vector Machines</li>
        <li>Neural Networks</li>
    </ol>

    <h2>Applications</h2>

    <p>Machine learning has numerous applications across various industries:</p>

    <table>
        <tr>
            <th>Industry</th>
            <th>Application</th>
        </tr>
        <tr>
            <td>Healthcare</td>
            <td>Disease diagnosis, drug discovery</td>
        </tr>
        <tr>
            <td>Finance</td>
            <td>Fraud detection, algorithmic trading</td>
        </tr>
        <tr>
            <td>Retail</td>
            <td>Recommendation systems, inventory management</td>
        </tr>
    </table>

    <p>Statistical analysis shows that companies implementing machine learning
    solutions see an average 15% increase in operational efficiency within
    the first year of deployment.</p>
    """

    sample_title = "Introduction to Machine Learning"
    sample_metadata = {
        'author': 'Dr. Jane Smith',
        'date': '2023-06-01',
        'source': 'Tech Education Journal'
    }

    # Assess content quality
    print("Assessing content quality...")
    quality_assessment = scorer.assess_content_quality(
        sample_content, sample_title, sample_metadata
    )

    # Display results
    print(f"\nQuality Assessment Results:")
    print(f"  Readability Score: {quality_assessment['readability_score']:.2f}")
    print(f"  Depth Score: {quality_assessment['depth_score']:.2f}")
    print(f"  Accuracy Score: {quality_assessment['accuracy_score']:.2f}")
    print(f"  Completeness Score: {quality_assessment['completeness_score']:.2f}")
    print(f"  Overall Quality Score: {quality_assessment['overall_quality_score']:.2f}")
    print(f"  Quality Level: {quality_assessment['quality_level']}")

    # Display bias scores
    print(f"\nBias Scores:")
    for bias_type, score in quality_assessment['bias_scores'].items():
        print(f"  {bias_type}: {score:.2f}")

    # Test with different content
    print("\n\nTesting with poor quality content...")
    poor_content = "This is bad content. Very bad. Not good at all. Bad bad bad."
    poor_assessment = scorer.assess_content_quality(poor_content, "Bad Content")

    print(f"\nPoor Content Assessment:")
    print(f"  Overall Quality Score: {poor_assessment['overall_quality_score']:.2f}")
    print(f"  Quality Level: {poor_assessment['quality_level']}")


if __name__ == "__main__":
    main()