#!/usr/bin/env python3
"""
Conversation-Aware Ranking for Transcript Search
Implements ranking algorithms optimized for conversational content,
Q&A patterns, and dialogue flow.
"""

import logging
from typing import List, Dict, Any


class ConversationRanking:
    """Ranking system optimized for conversational transcript content."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

        # Weight factors for different ranking signals
        self.weights = {
            "text_relevance": 1.0,
            "segment_type": 0.8,
            "speaker_importance": 0.6,
            "word_count": 0.4,
            "topic_relevance": 0.7,
            "conversation_context": 0.5,
        }

        # Segment type priorities for different query types
        self.segment_priorities = {
            "question": {
                "answer": 1.0,
                "discussion": 0.8,
                "question": 0.6,
                "transition": 0.3,
            },
            "topic": {
                "discussion": 1.0,
                "answer": 0.9,
                "transition": 0.7,
                "question": 0.5,
            },
            "general": {
                "answer": 0.9,
                "discussion": 1.0,
                "question": 0.7,
                "transition": 0.5,
            },
        }

    def rank_transcript_results(
        self, results: List[Dict[str, Any]], query_type: str = "general"
    ) -> List[Dict[str, Any]]:
        """Rank transcript search results using conversation-aware algorithms."""
        if not results:
            return results

        try:
            # Calculate ranking scores for each result
            scored_results = []
            for result in results:
                score = self._calculate_conversation_score(result, query_type)
                scored_results.append((score, result))

            # Sort by score (descending)
            scored_results.sort(key=lambda x: x[0], reverse=True)

            # Return ranked results
            ranked_results = [result for score, result in scored_results]

            self.logger.info(
                f"Ranked {len(ranked_results)} results for query type: {query_type}"
            )
            return ranked_results

        except Exception as e:
            self.logger.error(f"Error ranking results: {e}")
            return results  # Return original order on error

    def _calculate_conversation_score(
        self, result: Dict[str, Any], query_type: str
    ) -> float:
        """Calculate comprehensive conversation-aware score for a search result."""
        total_score = 0.0

        try:
            # Segment type relevance
            segment_type = result.get("segment_type", "discussion")
            type_priorities = self.segment_priorities.get(
                query_type, self.segment_priorities["general"]
            )
            type_score = type_priorities.get(segment_type, 0.5)
            total_score += type_score * self.weights["segment_type"]

            # Speaker importance (guest responses often more valuable than host questions)
            speaker_score = self._calculate_speaker_importance(
                result.get("speaker", "")
            )
            total_score += speaker_score * self.weights["speaker_importance"]

            # Word count factor (longer segments often more informative)
            word_count_score = self._calculate_word_count_score(
                result.get("word_count", 0)
            )
            total_score += word_count_score * self.weights["word_count"]

            # Topic relevance
            topic_score = self._calculate_topic_relevance(result.get("topic_tags", []))
            total_score += topic_score * self.weights["topic_relevance"]

            # Content quality indicators
            content_score = self._calculate_content_quality(result.get("content", ""))
            total_score += content_score * self.weights["text_relevance"]

            return round(total_score, 3)

        except Exception as e:
            self.logger.error(f"Error calculating conversation score: {e}")
            return 0.5  # Default middle score

    def _calculate_speaker_importance(self, speaker: str) -> float:
        """Calculate speaker importance score."""
        if not speaker:
            return 0.3

        speaker_lower = speaker.lower()

        # Host/interviewer patterns (usually less important for content)
        host_patterns = ["host", "interviewer", "lex", "joe", "tim"]
        if any(pattern in speaker_lower for pattern in host_patterns):
            return 0.4

        # Guest speakers (usually more important for content)
        return 0.8

    def _calculate_word_count_score(self, word_count: int) -> float:
        """Calculate score based on segment word count."""
        if word_count <= 0:
            return 0.1
        elif word_count < 10:
            return 0.3
        elif word_count < 30:
            return 0.6
        elif word_count < 100:
            return 1.0
        elif word_count < 300:
            return 0.9
        else:
            return 0.7  # Very long segments might be less focused

    def _calculate_topic_relevance(self, topics: List[str]) -> float:
        """Calculate topic relevance score."""
        if not topics:
            return 0.5

        # More topics might indicate more comprehensive coverage
        topic_count = len(topics)
        if topic_count == 1:
            return 0.7
        elif topic_count <= 3:
            return 1.0
        else:
            return 0.8  # Too many topics might indicate less focus

    def _calculate_content_quality(self, content: str) -> float:
        """Calculate content quality score based on various indicators."""
        if not content:
            return 0.0

        score = 0.5  # Base score
        content_lower = content.lower()

        # Question indicators
        if "?" in content:
            score += 0.1

        # Explanation indicators
        explanation_words = [
            "because",
            "therefore",
            "however",
            "actually",
            "essentially",
            "specifically",
        ]
        if any(word in content_lower for word in explanation_words):
            score += 0.2

        # Technical depth indicators
        technical_words = [
            "algorithm",
            "system",
            "process",
            "method",
            "approach",
            "technology",
        ]
        if any(word in content_lower for word in technical_words):
            score += 0.1

        # Insight indicators
        insight_words = [
            "interesting",
            "important",
            "key",
            "crucial",
            "significant",
            "realize",
        ]
        if any(word in content_lower for word in insight_words):
            score += 0.1

        # Avoid filler content
        filler_indicators = ["um", "uh", "you know", "like", "sort of"]
        filler_count = sum(content_lower.count(filler) for filler in filler_indicators)
        if filler_count > 3:
            score -= 0.2

        return max(0.0, min(1.0, score))  # Clamp between 0 and 1

    def rank_by_conversation_flow(
        self,
        results: List[Dict[str, Any]],
        context_segments: List[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Rank results considering conversation flow and context."""
        if not results:
            return results

        try:
            # Group results by content/episode
            episode_groups = {}
            for result in results:
                content_uid = result.get("content_uid", "unknown")
                if content_uid not in episode_groups:
                    episode_groups[content_uid] = []
                episode_groups[content_uid].append(result)

            # Rank within each episode group
            ranked_results = []
            for content_uid, episode_results in episode_groups.items():
                # Sort by segment order within episode
                episode_results.sort(key=lambda x: x.get("segment_id", 0))

                # Apply conversation flow scoring
                flow_scored = self._apply_conversation_flow_scoring(episode_results)
                ranked_results.extend(flow_scored)

            return ranked_results

        except Exception as e:
            self.logger.error(f"Error ranking by conversation flow: {e}")
            return results

    def _apply_conversation_flow_scoring(
        self, episode_results: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Apply conversation flow scoring within an episode."""
        if len(episode_results) <= 1:
            return episode_results

        # Look for Q&A patterns
        qa_pairs = self._identify_qa_pairs(episode_results)

        # Boost scores for Q&A pairs
        for i, result in enumerate(episode_results):
            if i in qa_pairs:
                # This segment is part of a Q&A pair
                if "conversation_flow_score" not in result:
                    result["conversation_flow_score"] = 0.0
                result["conversation_flow_score"] += 0.3

        return episode_results

    def _identify_qa_pairs(self, segments: List[Dict[str, Any]]) -> List[int]:
        """Identify question-answer pairs in conversation segments."""
        qa_indices = []

        for i in range(len(segments) - 1):
            current = segments[i]
            next_segment = segments[i + 1]

            # Look for question followed by answer
            if (
                current.get("segment_type") == "question"
                and next_segment.get("segment_type") == "answer"
            ):
                qa_indices.extend([i, i + 1])

            # Look for speaker transitions that might indicate Q&A
            current_speaker = current.get("speaker", "")
            next_speaker = next_segment.get("speaker", "")

            if current_speaker != next_speaker and (
                "?" in current.get("content", "")
                or any(
                    word in current.get("content", "").lower()
                    for word in ["what", "how", "why"]
                )
            ):
                qa_indices.extend([i, i + 1])

        return list(set(qa_indices))  # Remove duplicates

    def boost_guest_insights(
        self, results: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Boost ranking for guest insights over host questions."""
        for result in results:
            speaker = result.get("speaker", "").lower()
            content = result.get("content", "").lower()

            # Identify likely host speakers
            host_indicators = ["lex", "joe", "tim", "host", "interviewer"]
            is_likely_host = any(indicator in speaker for indicator in host_indicators)

            # Boost guest responses, especially substantive ones
            if not is_likely_host and len(content) > 50:
                if "ranking_boost" not in result:
                    result["ranking_boost"] = 0.0
                result["ranking_boost"] += 0.2

            # Reduce ranking for obvious host questions
            elif is_likely_host and "?" in content and len(content) < 30:
                if "ranking_boost" not in result:
                    result["ranking_boost"] = 0.0
                result["ranking_boost"] -= 0.1

        return results

    def calculate_relevance_score(self, segment: Dict[str, Any], query: str) -> float:
        """Calculate relevance score for a segment against a specific query."""
        try:
            content = segment.get("content", "").lower()
            query_lower = query.lower()

            # Basic text matching
            query_words = query_lower.split()
            matches = sum(1 for word in query_words if word in content)
            text_score = matches / len(query_words) if query_words else 0

            # Segment type relevance
            segment_type = segment.get("segment_type", "discussion")
            query_type = self._determine_query_type(query)
            type_priorities = self.segment_priorities.get(
                query_type, self.segment_priorities["general"]
            )
            type_score = type_priorities.get(segment_type, 0.5)

            # Combined score
            relevance = (text_score * 0.7) + (type_score * 0.3)

            return round(relevance, 3)

        except Exception as e:
            self.logger.error(f"Error calculating relevance score: {e}")
            return 0.5

    def _determine_query_type(self, query: str) -> str:
        """Determine query type for ranking optimization."""
        query_lower = query.lower()

        question_indicators = ["what", "how", "why", "when", "where", "who", "?"]
        if any(indicator in query_lower for indicator in question_indicators):
            return "question"

        topic_indicators = ["about", "discuss", "topic", "regarding", "concerning"]
        if any(indicator in query_lower for indicator in topic_indicators):
            return "topic"

        return "general"


def main():
    """Test conversation ranking system."""
    ranker = ConversationRanking()

    # Sample search results
    sample_results = [
        {
            "id": 1,
            "content": "What do you think about AI safety?",
            "speaker": "Lex Fridman",
            "segment_type": "question",
            "word_count": 8,
            "topic_tags": ["AI Safety"],
        },
        {
            "id": 2,
            "content": "AI safety is crucial because we need to ensure that artificial intelligence systems remain aligned with human values as they become more powerful.",
            "speaker": "Elon Musk",
            "segment_type": "answer",
            "word_count": 25,
            "topic_tags": ["AI Safety", "Alignment"],
        },
    ]

    # Test ranking
    ranked = ranker.rank_transcript_results(sample_results, "question")

    print("Ranking test results:")
    for i, result in enumerate(ranked):
        print(f"{i+1}. Speaker: {result['speaker']}, Type: {result['segment_type']}")
        print(f"   Content: {result['content'][:50]}...")
        print()


if __name__ == "__main__":
    main()
