#!/usr/bin/env python3
"""
AI Summarizer for Atlas

This module implements AI-powered content summarization capabilities for Atlas.
"""

import re
from typing import List, Dict, Any, Optional
from collections import Counter
import math

class AISummarizer:
    """AI-powered content summarizer"""

    def __init__(self):
        """Initialize the AI summarizer"""
        self.summarization_methods = {
            'extractive': self._extractive_summarization,
            'abstractive': self._abstractive_summarization,
            'keyword_based': self._keyword_based_summarization,
            'sentence_scoring': self._sentence_scoring_summarization
        }

    def summarize(self, content: str, method: str = 'extractive',
                  summary_length: int = 3, language: str = 'en') -> str:
        """
        Generate a summary of content using specified method

        Args:
            content (str): Content to summarize
            method (str): Summarization method ('extractive', 'abstractive', etc.)
            summary_length (int): Number of sentences in summary
            language (str): Content language

        Returns:
            str: Generated summary
        """
        if method in self.summarization_methods:
            return self.summarization_methods[method](
                content, summary_length, language
            )
        else:
            # Default to extractive summarization
            return self._extractive_summarization(content, summary_length, language)

    def _extractive_summarization(self, content: str, summary_length: int,
                                language: str) -> str:
        """
        Extractive summarization - selects important sentences from original text

        Args:
            content (str): Content to summarize
            summary_length (int): Number of sentences in summary
            language (str): Content language

        Returns:
            str: Extractive summary
        """
        # Split content into sentences
        sentences = self._split_into_sentences(content)

        if len(sentences) <= summary_length:
            return ' '.join(sentences)

        # Score sentences based on various factors
        sentence_scores = {}

        # Get word frequencies
        word_freq = self._get_word_frequencies(content, language)

        # Score each sentence
        for i, sentence in enumerate(sentences):
            score = self._score_sentence(sentence, word_freq, i, len(sentences))
            sentence_scores[i] = score

        # Select top sentences
        top_sentences = sorted(
            sentence_scores.items(),
            key=lambda x: x[1],
            reverse=True
        )[:summary_length]

        # Sort by original order
        top_sentences.sort(key=lambda x: x[0])

        # Build summary
        summary_sentences = [sentences[i] for i, _ in top_sentences]
        return ' '.join(summary_sentences)

    def _abstractive_summarization(self, content: str, summary_length: int,
                                 language: str) -> str:
        """
        Abstractive summarization - generates new sentences that capture key ideas

        Args:
            content (str): Content to summarize
            summary_length (int): Number of sentences in summary
            language (str): Content language

        Returns:
            str: Abstractive summary (placeholder implementation)
        """
        # In a real implementation, this would use advanced NLP models
        # For now, we'll use a simplified approach

        # Split content into sentences
        sentences = self._split_into_sentences(content)

        if len(sentences) <= summary_length:
            return ' '.join(sentences)

        # Get key phrases
        key_phrases = self._extract_key_phrases(content, language)

        # Generate summary sentences
        summary_sentences = []

        # Create summary by selecting and slightly modifying key sentences
        sentence_scores = {}
        word_freq = self._get_word_frequencies(content, language)

        for i, sentence in enumerate(sentences):
            score = self._score_sentence(sentence, word_freq, i, len(sentences))
            sentence_scores[i] = score

        # Select top sentences
        top_sentences = sorted(
            sentence_scores.items(),
            key=lambda x: x[1],
            reverse=True
        )[:summary_length * 2]  # Get more candidates

        # Sort by original order
        top_sentences.sort(key=lambda x: x[0])

        # Modify sentences to create abstraction
        for i, _ in top_sentences[:summary_length]:
            sentence = sentences[i]
            # In a real implementation, this would use paraphrasing
            # For now, we'll just truncate and add abstraction indicator
            abstracted_sentence = self._abstract_sentence(sentence, key_phrases)
            summary_sentences.append(abstracted_sentence)

        return ' '.join(summary_sentences)

    def _keyword_based_summarization(self, content: str, summary_length: int,
                                   language: str) -> str:
        """
        Keyword-based summarization - focuses on sentences with important keywords

        Args:
            content (str): Content to summarize
            summary_length (int): Number of sentences in summary
            language (str): Content language

        Returns:
            str: Keyword-based summary
        """
        # Extract keywords
        keywords = self._extract_keywords(content, language)

        # Split content into sentences
        sentences = self._split_into_sentences(content)

        if len(sentences) <= summary_length:
            return ' '.join(sentences)

        # Score sentences based on keyword presence
        sentence_scores = {}

        for i, sentence in enumerate(sentences):
            score = self._score_sentence_by_keywords(sentence, keywords)
            sentence_scores[i] = score

        # Select top sentences
        top_sentences = sorted(
            sentence_scores.items(),
            key=lambda x: x[1],
            reverse=True
        )[:summary_length]

        # Sort by original order
        top_sentences.sort(key=lambda x: x[0])

        # Build summary
        summary_sentences = [sentences[i] for i, _ in top_sentences]
        return ' '.join(summary_sentences)

    def _sentence_scoring_summarization(self, content: str, summary_length: int,
                                       language: str) -> str:
        """
        Sentence scoring summarization - combines multiple scoring techniques

        Args:
            content (str): Content to summarize
            summary_length (int): Number of sentences in summary
            language (str): Content language

        Returns:
            str: Sentence scoring summary
        """
        # Split content into sentences
        sentences = self._split_into_sentences(content)

        if len(sentences) <= summary_length:
            return ' '.join(sentences)

        # Get word frequencies and keywords
        word_freq = self._get_word_frequencies(content, language)
        keywords = self._extract_keywords(content, language)

        # Score sentences using multiple criteria
        sentence_scores = {}

        for i, sentence in enumerate(sentences):
            # Multiple scoring factors
            word_score = self._score_sentence(sentence, word_freq, i, len(sentences))
            keyword_score = self._score_sentence_by_keywords(sentence, keywords)
            position_score = self._score_sentence_by_position(i, len(sentences))
            length_score = self._score_sentence_by_length(sentence)

            # Combined score (weighted average)
            combined_score = (
                0.4 * word_score +
                0.3 * keyword_score +
                0.2 * position_score +
                0.1 * length_score
            )

            sentence_scores[i] = combined_score

        # Select top sentences
        top_sentences = sorted(
            sentence_scores.items(),
            key=lambda x: x[1],
            reverse=True
        )[:summary_length]

        # Sort by original order
        top_sentences.sort(key=lambda x: x[0])

        # Build summary
        summary_sentences = [sentences[i] for i, _ in top_sentences]
        return ' '.join(summary_sentences)

    def _split_into_sentences(self, content: str) -> List[str]:
        """
        Split content into sentences

        Args:
            content (str): Content to split

        Returns:
            List[str]: List of sentences
        """
        # Simple sentence splitting (in a real implementation, use NLTK or similar)
        sentences = re.split(r'[.!?]+', content)
        sentences = [s.strip() for s in sentences if s.strip()]
        return sentences

    def _get_word_frequencies(self, content: str, language: str) -> Dict[str, int]:
        """
        Get word frequencies in content

        Args:
            content (str): Content to analyze
            language (str): Content language

        Returns:
            Dict[str, int]: Word frequencies
        """
        # Simple word frequency calculation
        words = re.findall(r'\b\w+\b', content.lower())

        # Remove stop words based on language
        stop_words = self._get_stop_words(language)
        words = [word for word in words if word not in stop_words and len(word) > 2]

        # Count frequencies
        word_freq = Counter(words)
        return dict(word_freq)

    def _score_sentence(self, sentence: str, word_freq: Dict[str, int],
                       position: int, total_sentences: int) -> float:
        """
        Score a sentence based on word frequencies and position

        Args:
            sentence (str): Sentence to score
            word_freq (Dict[str, int]): Word frequencies
            position (int): Sentence position
            total_sentences (int): Total number of sentences

        Returns:
            float: Sentence score
        """
        # Extract words from sentence
        words = re.findall(r'\b\w+\b', sentence.lower())

        # Calculate score based on word frequencies
        score = 0
        for word in words:
            score += word_freq.get(word, 0)

        # Normalize by sentence length
        if len(words) > 0:
            score /= len(words)

        # Boost score for sentences at beginning or end
        if position == 0 or position == total_sentences - 1:
            score *= 1.2

        return score

    def _score_sentence_by_keywords(self, sentence: str, keywords: List[str]) -> float:
        """
        Score a sentence based on keyword presence

        Args:
            sentence (str): Sentence to score
            keywords (List[str]): Important keywords

        Returns:
            float: Sentence score
        """
        sentence_lower = sentence.lower()
        score = 0

        for keyword in keywords:
            if keyword.lower() in sentence_lower:
                score += 1

        return score

    def _score_sentence_by_position(self, position: int, total_sentences: int) -> float:
        """
        Score a sentence based on its position

        Args:
            position (int): Sentence position
            total_sentences (int): Total number of sentences

        Returns:
            float: Position score
        """
        # Give higher scores to sentences at beginning and end
        if position == 0 or position == total_sentences - 1:
            return 1.0
        elif position == 1 or position == total_sentences - 2:
            return 0.8
        elif position < total_sentences / 3 or position > 2 * total_sentences / 3:
            return 0.6
        else:
            return 0.4

    def _score_sentence_by_length(self, sentence: str) -> float:
        """
        Score a sentence based on its length

        Args:
            sentence (str): Sentence to score

        Returns:
            float: Length score
        """
        words = re.findall(r'\b\w+\b', sentence)

        # Prefer medium-length sentences (not too short, not too long)
        if len(words) < 5:
            return 0.5  # Too short
        elif len(words) > 30:
            return 0.5  # Too long
        else:
            # Score based on how close to ideal length (15 words)
            ideal_length = 15
            deviation = abs(len(words) - ideal_length)
            return max(0.1, 1.0 - (deviation / ideal_length) * 0.5)

    def _extract_keywords(self, content: str, language: str) -> List[str]:
        """
        Extract important keywords from content

        Args:
            content (str): Content to analyze
            language (str): Content language

        Returns:
            List[str]: Extracted keywords
        """
        # Get word frequencies
        word_freq = self._get_word_frequencies(content, language)

        # Sort by frequency and get top keywords
        sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
        keywords = [word for word, freq in sorted_words[:20]]  # Top 20 words

        return keywords

    def _extract_key_phrases(self, content: str, language: str) -> List[str]:
        """
        Extract key phrases from content

        Args:
            content (str): Content to analyze
            language (str): Content language

        Returns:
            List[str]: Extracted key phrases
        """
        # Simple key phrase extraction (in a real implementation, use more advanced NLP)
        sentences = self._split_into_sentences(content)

        # Extract noun phrases (simplified approach)
        key_phrases = []

        for sentence in sentences:
            # Look for patterns like "X of Y", "Y X", etc.
            phrases = re.findall(r'\b\w+\s+(?:of\s+)?\w+', sentence)
            key_phrases.extend(phrases)

        # Remove duplicates and limit
        key_phrases = list(set(key_phrases))[:10]
        return key_phrases

    def _abstract_sentence(self, sentence: str, key_phrases: List[str]) -> str:
        """
        Abstract a sentence by modifying it slightly

        Args:
            sentence (str): Sentence to abstract
            key_phrases (List[str]): Key phrases to preserve

        Returns:
            str: Abstracted sentence
        """
        # In a real implementation, this would use paraphrasing models
        # For now, we'll just indicate abstraction
        return f"[Abstracted] {sentence}"

    def _get_stop_words(self, language: str) -> List[str]:
        """
        Get stop words for a language

        Args:
            language (str): Language code

        Returns:
            List[str]: Stop words
        """
        # Simplified stop words for different languages
        stop_words = {
            'en': {
                'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
                'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'have',
                'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should',
                'may', 'might', 'must', 'can', 'this', 'that', 'these', 'those', 'i',
                'you', 'he', 'she', 'it', 'we', 'they', 'me', 'him', 'her', 'us', 'them'
            },
            'es': {
                'el', 'la', 'los', 'las', 'un', 'una', 'unos', 'unas', 'y', 'o', 'pero',
                'en', 'de', 'a', 'por', 'para', 'con', 'sin', 'sobre', 'bajo', 'entre',
                'desde', 'hasta', 'durante', 'antes', 'después', 'es', 'son', 'era',
                'fue', 'ser', 'estar', 'haber', 'tener', 'hacer', 'decir', 'poder',
                'querer', 'deber', 'este', 'ese', 'aquel', 'esta', 'esa', 'aquella',
                'estos', 'esos', 'aquellos', 'yo', 'tú', 'él', 'ella', 'nosotros',
                'vosotros', 'ellos', 'ellas', 'me', 'te', 'lo', 'la', 'nos', 'os', 'los', 'las'
            },
            'fr': {
                'le', 'la', 'les', 'un', 'une', 'des', 'du', 'de', 'et', 'ou', 'mais',
                'dans', 'en', 'à', 'au', 'aux', 'par', 'pour', 'avec', 'sans', 'sur',
                'sous', 'entre', 'avant', 'après', 'pendant', 'est', 'sont', 'était',
                'était', 'être', 'avoir', 'faire', 'dire', 'pouvoir', 'vouloir', 'devoir',
                'ce', 'cette', 'ces', 'je', 'tu', 'il', 'elle', 'nous', 'vous', 'ils',
                'elles', 'me', 'te', 'se', 'lui', 'leur', 'y', 'en'
            }
        }

        return list(stop_words.get(language, stop_words['en']))

    def generate_multiple_summaries(self, content: str,
                                  methods: List[str] = None) -> Dict[str, str]:
        """
        Generate multiple summaries using different methods

        Args:
            content (str): Content to summarize
            methods (List[str], optional): Methods to use (default: all)

        Returns:
            Dict[str, str]: Summaries by method
        """
        if methods is None:
            methods = list(self.summarization_methods.keys())

        summaries = {}

        for method in methods:
            try:
                summary = self.summarize(content, method=method)
                summaries[method] = summary
            except Exception as e:
                summaries[method] = f"Error generating {method} summary: {str(e)}"

        return summaries

def main():
    """Example usage of AISummarizer"""
    # Create summarizer
    summarizer = AISummarizer()

    # Sample content
    content = """
    Python is a high-level programming language with dynamic semantics. It is used for web development,
    data science, and automation. Python has a simple syntax similar to English, making it easy to learn.
    The language supports multiple programming paradigms, including procedural, object-oriented, and functional programming.
    Python has a large standard library and a vibrant community that contributes to thousands of third-party modules and packages.
    Popular frameworks like Django and Flask make web development with Python straightforward.
    For data science, libraries like NumPy, Pandas, and Matplotlib provide powerful tools for analysis and visualization.
    Machine learning practitioners use Python with libraries like TensorFlow, PyTorch, and Scikit-learn.
    Python is also popular for automation tasks, scripting, and rapid prototyping.
    The language continues to evolve with regular updates and improvements to performance and features.
    """

    # Generate different types of summaries
    print("Generating AI-powered content summaries...")

    # Extractive summary
    extractive_summary = summarizer.summarize(content, method='extractive', summary_length=2)
    print(f"\nExtractive Summary:\n{extractive_summary}")

    # Abstractive summary
    abstractive_summary = summarizer.summarize(content, method='abstractive', summary_length=2)
    print(f"\nAbstractive Summary:\n{abstractive_summary}")

    # Keyword-based summary
    keyword_summary = summarizer.summarize(content, method='keyword_based', summary_length=2)
    print(f"\nKeyword-based Summary:\n{keyword_summary}")

    # Sentence scoring summary
    sentence_summary = summarizer.summarize(content, method='sentence_scoring', summary_length=2)
    print(f"\nSentence Scoring Summary:\n{sentence_summary}")

    # Generate all summaries
    all_summaries = summarizer.generate_multiple_summaries(content)
    print(f"\nGenerated {len(all_summaries)} summaries using different methods")

    for method, summary in all_summaries.items():
        print(f"\n{method.title()} Summary:")
        print(summary)

if __name__ == "__main__":
    main()