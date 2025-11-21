#!/usr/bin/env python3
"""
TRANSCRIPT QUALITY VALIDATOR
Rigorous validation to ensure we only store real, high-quality transcripts
Not just character count - semantic and structural validation
"""

import re
import requests
from typing import Dict, Optional, Tuple

class TranscriptQualityValidator:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })

    def validate_transcript_quality(self, content: str, url: str = "", title: str = "") -> Dict:
        """
        COMPREHENSIVE QUALITY VALIDATION
        Returns detailed quality assessment with pass/fail and reasons
        """
        if not content or len(content) < 1000:
            return {
                "is_valid": False,
                "score": 0.0,
                "reason": "Content too short (< 1000 chars)",
                "category": "insufficient_content"
            }

        # Run all validation checks
        checks = {
            "length_check": self._check_length(content),
            "transcript_indicators": self._check_transcript_indicators(content),
            "conversation_structure": self._check_conversation_structure(content),
            "navigation_pollution": self._check_navigation_pollution(content),
            "content_density": self._check_content_density(content),
            "repetition_patterns": self._check_repetition_patterns(content),
            "language_quality": self._check_language_quality(content),
            "podcast_specific": self._check_podcast_specific_patterns(content, title),
        }

        # Calculate overall score
        total_score = sum(check["score"] for check in checks.values())
        max_score = len(checks) * 1.0
        normalized_score = total_score / max_score

        # Determine if valid (must pass critical checks + good score)
        critical_checks = ["length_check", "transcript_indicators", "conversation_structure"]
        critical_passed = all(checks[check]["passed"] for check in critical_checks)

        is_valid = critical_passed and normalized_score >= 0.6

        # Determine quality category
        if normalized_score >= 0.9:
            category = "excellent"
        elif normalized_score >= 0.8:
            category = "high_quality"
        elif normalized_score >= 0.6:
            category = "acceptable"
        else:
            category = "poor_quality"

        # Generate detailed reason
        failed_checks = [name for name, check in checks.items() if not check["passed"]]
        if failed_checks:
            reason = f"Failed checks: {', '.join(failed_checks)}"
        else:
            reason = f"Quality score: {normalized_score:.2f}"

        return {
            "is_valid": is_valid,
            "score": normalized_score,
            "category": category,
            "reason": reason,
            "details": checks,
            "content_length": len(content),
            "url": url
        }

    def _check_length(self, content: str) -> Dict:
        """Check if content length suggests real transcript"""
        length = len(content)

        if length >= 50000:  # 50k+ = excellent
            return {"passed": True, "score": 1.0, "detail": f"Excellent length: {length:,} chars"}
        elif length >= 20000:  # 20k+ = good
            return {"passed": True, "score": 0.9, "detail": f"Good length: {length:,} chars"}
        elif length >= 10000:  # 10k+ = acceptable
            return {"passed": True, "score": 0.7, "detail": f"Acceptable length: {length:,} chars"}
        elif length >= 5000:   # 5k+ = minimum
            return {"passed": True, "score": 0.5, "detail": f"Minimum length: {length:,} chars"}
        else:
            return {"passed": False, "score": 0.0, "detail": f"Too short: {length:,} chars"}

    def _check_transcript_indicators(self, content: str) -> Dict:
        """Check for authentic transcript markers"""
        content_lower = content.lower()

        # Strong indicators (high weight)
        strong_indicators = [
            r"speaker\s*\d*:", r"host:", r"guest:", r"interviewer:",
            r"\[music\]", r"\[laughter\]", r"\[applause\]", r"\[sound effect\]",
            r"welcome to", r"today on", r"this is", r"i'm your host",
            r"thanks for listening", r"that's all for today"
        ]

        # Medium indicators
        medium_indicators = [
            r"uh", r"um", r"you know", r"i mean", r"like,",
            r"right\?", r"okay\?", r"so,", r"well,",
            r"transcript", r"episode", r"podcast"
        ]

        # Weak indicators
        weak_indicators = [
            r"said", r"asked", r"replied", r"continued",
            r"yeah", r"yes", r"no", r"sure", r"exactly"
        ]

        strong_count = sum(1 for pattern in strong_indicators
                          if re.search(pattern, content_lower))
        medium_count = sum(1 for pattern in medium_indicators
                          if re.search(pattern, content_lower))
        weak_count = sum(1 for pattern in weak_indicators
                        if re.search(pattern, content_lower))

        # Weighted score
        weighted_score = (strong_count * 0.5 + medium_count * 0.2 + weak_count * 0.1)
        normalized_score = min(weighted_score / 5.0, 1.0)  # Cap at 1.0

        passed = strong_count >= 2 or (strong_count >= 1 and medium_count >= 3)

        return {
            "passed": passed,
            "score": normalized_score,
            "detail": f"Strong: {strong_count}, Medium: {medium_count}, Weak: {weak_count}"
        }

    def _check_conversation_structure(self, content: str) -> Dict:
        """Check if content has conversation-like structure"""
        lines = content.split('\n')

        # Look for dialogue patterns
        dialogue_patterns = [
            r"^[A-Z][a-z\s]+:",  # "Speaker Name:"
            r"^\w+:",             # "Name:"
            r"^Speaker\s*\d*:",   # "Speaker 1:"
            r"^Host:",            # "Host:"
            r"^Guest:",           # "Guest:"
        ]

        dialogue_lines = 0
        for line in lines:
            line = line.strip()
            if any(re.match(pattern, line) for pattern in dialogue_patterns):
                dialogue_lines += 1

        # Check for back-and-forth conversation
        total_lines = len([line for line in lines if line.strip()])
        if total_lines == 0:
            return {"passed": False, "score": 0.0, "detail": "No content lines"}

        dialogue_ratio = dialogue_lines / total_lines

        # Also check for question marks (conversations have questions)
        question_count = content.count('?')
        question_density = question_count / len(content) * 1000  # per 1000 chars

        if dialogue_ratio >= 0.1 or question_density >= 2:
            score = min((dialogue_ratio * 5 + question_density * 0.2), 1.0)
            return {
                "passed": True,
                "score": score,
                "detail": f"Dialogue ratio: {dialogue_ratio:.2f}, Questions: {question_count}"
            }
        else:
            return {
                "passed": False,
                "score": dialogue_ratio * 2,
                "detail": f"Low dialogue ratio: {dialogue_ratio:.2f}"
            }

    def _check_navigation_pollution(self, content: str) -> Dict:
        """Check for website navigation/menu pollution"""
        content_lower = content.lower()

        # Common navigation/menu pollution indicators
        pollution_indicators = [
            r"home\s*\|\s*about", r"privacy policy", r"terms of service",
            r"subscribe\s*\|\s*contact", r"menu", r"navigation",
            r"footer", r"header", r"sidebar", r"breadcrumb",
            r"search this site", r"related posts", r"recent posts",
            r"categories", r"tags", r"archives", r"rss feed",
            r"click here", r"read more", r"continue reading",
            r"advertisement", r"sponsored", r"affiliate"
        ]

        pollution_count = sum(1 for pattern in pollution_indicators
                             if re.search(pattern, content_lower))

        # Calculate pollution ratio
        pollution_ratio = pollution_count / (len(content) / 1000)  # per 1000 chars

        if pollution_ratio <= 2:  # Low pollution
            return {"passed": True, "score": 1.0, "detail": f"Low pollution: {pollution_count} indicators"}
        elif pollution_ratio <= 5:  # Medium pollution
            return {"passed": True, "score": 0.7, "detail": f"Medium pollution: {pollution_count} indicators"}
        else:  # High pollution
            return {"passed": False, "score": 0.3, "detail": f"High pollution: {pollution_count} indicators"}

    def _check_content_density(self, content: str) -> Dict:
        """Check content density (words per character ratio)"""
        words = len(re.findall(r'\b\w+\b', content))
        chars = len(content)

        if chars == 0:
            return {"passed": False, "score": 0.0, "detail": "No content"}

        # Good transcripts have reasonable word density
        word_density = words / chars

        if 0.15 <= word_density <= 0.25:  # Optimal range
            return {"passed": True, "score": 1.0, "detail": f"Good density: {word_density:.3f}"}
        elif 0.1 <= word_density <= 0.3:   # Acceptable range
            return {"passed": True, "score": 0.8, "detail": f"OK density: {word_density:.3f}"}
        else:  # Too sparse or too dense
            return {"passed": False, "score": 0.4, "detail": f"Poor density: {word_density:.3f}"}

    def _check_repetition_patterns(self, content: str) -> Dict:
        """Check for excessive repetition (copy/paste errors)"""
        # Split into chunks and check for exact repeats
        chunk_size = 200
        chunks = [content[i:i+chunk_size] for i in range(0, len(content), chunk_size)]

        unique_chunks = set(chunks)
        repetition_ratio = 1 - (len(unique_chunks) / len(chunks))

        if repetition_ratio <= 0.1:  # Low repetition
            return {"passed": True, "score": 1.0, "detail": f"Low repetition: {repetition_ratio:.2f}"}
        elif repetition_ratio <= 0.3:  # Medium repetition
            return {"passed": True, "score": 0.7, "detail": f"Medium repetition: {repetition_ratio:.2f}"}
        else:  # High repetition
            return {"passed": False, "score": 0.3, "detail": f"High repetition: {repetition_ratio:.2f}"}

    def _check_language_quality(self, content: str) -> Dict:
        """Check for coherent language patterns"""
        # Check sentence structure
        sentences = re.split(r'[.!?]+', content)
        meaningful_sentences = [s for s in sentences if len(s.strip()) > 20]

        if len(meaningful_sentences) == 0:
            return {"passed": False, "score": 0.0, "detail": "No meaningful sentences"}

        # Check average sentence length
        avg_sentence_length = sum(len(s) for s in meaningful_sentences) / len(meaningful_sentences)

        # Check for common English words
        common_words = ['the', 'and', 'a', 'to', 'of', 'in', 'is', 'it', 'that', 'for']
        content_lower = content.lower()
        common_word_count = sum(1 for word in common_words if word in content_lower)

        if avg_sentence_length >= 30 and common_word_count >= 5:
            return {"passed": True, "score": 1.0, "detail": f"Good language: {avg_sentence_length:.0f} avg chars/sentence"}
        elif avg_sentence_length >= 20 and common_word_count >= 3:
            return {"passed": True, "score": 0.7, "detail": f"OK language: {avg_sentence_length:.0f} avg chars/sentence"}
        else:
            return {"passed": False, "score": 0.4, "detail": f"Poor language: {avg_sentence_length:.0f} avg chars/sentence"}

    def _check_podcast_specific_patterns(self, content: str, title: str = "") -> Dict:
        """Check for podcast-specific patterns"""
        content_lower = content.lower()
        title_lower = title.lower()

        # Podcast-specific terms
        podcast_terms = [
            r"episode", r"podcast", r"show", r"host", r"guest",
            r"interview", r"conversation", r"discussion",
            r"welcome back", r"thanks for joining", r"outro music"
        ]

        podcast_term_count = sum(1 for term in podcast_terms
                                if re.search(term, content_lower))

        # Check if title appears in content (good sign)
        title_in_content = False
        if title and len(title) > 5:
            # Check for title or parts of title in content
            title_words = re.findall(r'\b\w+\b', title_lower)
            if len(title_words) >= 2:
                title_pattern = r'\b' + r'\b.*\b'.join(title_words[:3]) + r'\b'
                title_in_content = bool(re.search(title_pattern, content_lower))

        score = min((podcast_term_count * 0.2 + (0.3 if title_in_content else 0)), 1.0)

        return {
            "passed": podcast_term_count >= 2,
            "score": score,
            "detail": f"Podcast terms: {podcast_term_count}, Title match: {title_in_content}"
        }

    def quick_validate(self, content: str, min_score: float = 0.6) -> bool:
        """Quick validation for use in discovery pipelines"""
        if not content or len(content) < 5000:
            return False

        result = self.validate_transcript_quality(content)
        return result["is_valid"] and result["score"] >= min_score

    def test_url_for_quality_transcript(self, url: str, timeout: int = 15) -> Optional[Dict]:
        """Fetch URL and validate transcript quality"""
        try:
            response = self.session.get(url, timeout=timeout)
            if response.status_code == 200:
                # Extract title from HTML if possible
                title_match = re.search(r'<title[^>]*>([^<]+)</title>', response.text, re.IGNORECASE)
                title = title_match.group(1) if title_match else ""

                validation = self.validate_transcript_quality(response.text, url, title)

                if validation["is_valid"]:
                    return {
                        "url": url,
                        "content": response.text,
                        "quality": validation,
                        "title": title
                    }
        except Exception as e:
            print(f"Error testing {url}: {e}")

        return None

# Test function
def test_validator():
    """Test the validator with sample content"""
    validator = TranscriptQualityValidator()

    # Test with good transcript content
    good_content = """
    Host: Welcome to our podcast today. I'm your host, and we have a great show lined up.

    Guest: Thanks for having me on the show.

    Host: So tell us about your new book. What inspired you to write it?

    Guest: Well, it started when I was working at Google and I noticed that people were struggling with data analysis. I thought, you know, there has to be a better way.

    Host: That's fascinating. Can you give us an example of what you mean?

    Guest: Sure. Let's say you're trying to understand customer behavior. Traditional methods would have you looking at spreadsheets for hours, but with the approach I describe in the book, you can identify patterns in minutes.

    [Music plays]

    Host: We'll be right back after this short break.

    [Advertisement]

    Host: Welcome back. We're here with our guest talking about data analysis. Before the break, you were telling us about pattern recognition.

    Guest: Right, and I think the key insight is that most people are asking the wrong questions. Instead of asking "what happened?" we should be asking "what's likely to happen next?"

    Host: That's a great point. How do you actually implement this in practice?

    Guest: The first step is to gather clean data. Garbage in, garbage out, as they say. Then you need to choose the right visualization tools...

    Host: This has been really enlightening. Where can people find your book?

    Guest: It's available on Amazon and in most bookstores. The title is "Data Analysis for Everyone."

    Host: Thanks so much for joining us today.

    Guest: Thanks for having me.

    Host: That's all for today's episode. Don't forget to subscribe and leave us a review. Until next time!
    """

    # Test with poor content (navigation/menu)
    bad_content = """
    Home | About | Contact | Privacy Policy

    Menu
    - Episodes
    - Subscribe
    - RSS Feed
    - Social Media

    Related Posts:
    - Episode 1
    - Episode 2
    - Episode 3

    Categories:
    - Technology
    - Business
    - Science

    Recent Posts
    Tags: podcast, technology, business

    Footer
    Copyright 2024. All rights reserved.
    Subscribe to our newsletter.
    Follow us on Twitter.
    """

    print("Testing good content:")
    good_result = validator.validate_transcript_quality(good_content, title="Data Analysis Podcast")
    print(f"Valid: {good_result['is_valid']}, Score: {good_result['score']:.2f}, Category: {good_result['category']}")
    print(f"Reason: {good_result['reason']}\n")

    print("Testing bad content:")
    bad_result = validator.validate_transcript_quality(bad_content)
    print(f"Valid: {bad_result['is_valid']}, Score: {bad_result['score']:.2f}, Category: {bad_result['category']}")
    print(f"Reason: {bad_result['reason']}")

if __name__ == "__main__":
    test_validator()