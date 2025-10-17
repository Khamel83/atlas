#!/usr/bin/env python3
"""
Transcript Search API
Enhanced search capabilities for transcript content with speaker attribution,
topic filtering, and conversation-aware results.
"""

import logging
from typing import Dict, List, Any
from flask import Flask, request, jsonify

from helpers.transcript_search_indexer import TranscriptSearchIndexer
from helpers.transcript_search_ranking import ConversationRanking


class TranscriptSearchAPI:
    """API for searching transcript content with enhanced capabilities."""

    def __init__(self, app: Flask = None):
        self.indexer = TranscriptSearchIndexer()
        self.ranker = ConversationRanking()
        self.logger = logging.getLogger(__name__)

        if app:
            self.init_app(app)

    def init_app(self, app: Flask):
        """Initialize Flask app with transcript search routes."""
        app.add_url_rule(
            "/api/transcript/search",
            "transcript_search",
            self.search_transcripts,
            methods=["GET", "POST"],
        )
        app.add_url_rule(
            "/api/transcript/speaker/<speaker_name>/topics",
            "speaker_topics",
            self.get_speaker_topics,
            methods=["GET"],
        )
        app.add_url_rule(
            "/api/transcript/segment/<int:segment_id>/related",
            "related_segments",
            self.get_related_segments,
            methods=["GET"],
        )
        app.add_url_rule(
            "/api/transcript/speakers",
            "list_speakers",
            self.list_speakers,
            methods=["GET"],
        )
        app.add_url_rule(
            "/api/transcript/topics", "list_topics", self.list_topics, methods=["GET"]
        )
        app.add_url_rule(
            "/api/transcript/stats",
            "search_stats",
            self.get_search_stats,
            methods=["GET"],
        )

    def search_transcripts(self):
        """
        Search transcript content with multiple filters.

        Parameters:
        - q: Search query text
        - speaker: Filter by speaker name
        - topic: Filter by topic
        - type: Filter by segment type (question, answer, discussion, transition)
        - limit: Maximum results (default 50)
        - format: Response format (json, detailed)
        """
        try:
            # Get parameters from query string or JSON body
            if request.method == "POST":
                data = request.get_json() or {}
            else:
                data = request.args.to_dict()

            query = data.get("q", "").strip()
            speaker = data.get("speaker", "").strip()
            topic = data.get("topic", "").strip()
            segment_type = data.get("type", "").strip()
            limit = int(data.get("limit", 50))
            format_type = data.get("format", "json")

            # Validate inputs
            if not query and not speaker and not topic:
                return (
                    jsonify(
                        {
                            "error": "At least one search parameter required (q, speaker, or topic)",
                            "status": "error",
                        }
                    ),
                    400,
                )

            if limit > 200:  # Prevent excessive queries
                limit = 200

            # Perform search
            results = self.indexer.search_transcripts(
                query=query or None,
                speaker=speaker or None,
                topic=topic or None,
                segment_type=segment_type or None,
                limit=limit,
            )

            # Apply conversation-aware ranking
            if query:
                results = self.ranker.rank_transcript_results(
                    results, self._get_query_type(query)
                )

            # Format results
            if format_type == "detailed":
                formatted_results = self._format_detailed_results(results, query)
            else:
                formatted_results = self._format_standard_results(results)

            return jsonify(
                {
                    "results": formatted_results,
                    "count": len(formatted_results),
                    "query": {
                        "text": query,
                        "speaker": speaker,
                        "topic": topic,
                        "type": segment_type,
                        "limit": limit,
                    },
                    "status": "success",
                }
            )

        except Exception as e:
            self.logger.error(f"Error in transcript search: {e}")
            return jsonify({"error": "Internal search error", "status": "error"}), 500

    def get_speaker_topics(self, speaker_name: str):
        """Get all topics discussed by a specific speaker."""
        try:
            topics = self.indexer.get_speaker_topics(speaker_name)

            return jsonify(
                {
                    "speaker": speaker_name,
                    "topics": topics,
                    "count": len(topics),
                    "status": "success",
                }
            )

        except Exception as e:
            self.logger.error(f"Error getting speaker topics for {speaker_name}: {e}")
            return (
                jsonify(
                    {"error": "Error retrieving speaker topics", "status": "error"}
                ),
                500,
            )

    def get_related_segments(self, segment_id: int):
        """Get segments related to a specific segment by topic."""
        try:
            limit = int(request.args.get("limit", 5))
            related = self.indexer.find_related_segments(segment_id, limit)

            return jsonify(
                {
                    "segment_id": segment_id,
                    "related_segments": related,
                    "count": len(related),
                    "status": "success",
                }
            )

        except Exception as e:
            self.logger.error(f"Error finding related segments for {segment_id}: {e}")
            return (
                jsonify({"error": "Error finding related segments", "status": "error"}),
                500,
            )

    def list_speakers(self):
        """List all speakers with statistics."""
        try:
            stats = self.indexer.get_search_stats()
            speakers = stats.get("top_speakers", [])

            # Add search parameter for more speakers if needed
            limit = int(request.args.get("limit", 50))

            return jsonify(
                {
                    "speakers": speakers[:limit],
                    "count": len(speakers[:limit]),
                    "total_speakers": stats.get("total_speakers", 0),
                    "status": "success",
                }
            )

        except Exception as e:
            self.logger.error(f"Error listing speakers: {e}")
            return (
                jsonify({"error": "Error retrieving speakers", "status": "error"}),
                500,
            )

    def list_topics(self):
        """List all topics with statistics."""
        try:
            stats = self.indexer.get_search_stats()
            topics = stats.get("top_topics", [])

            limit = int(request.args.get("limit", 50))

            return jsonify(
                {
                    "topics": topics[:limit],
                    "count": len(topics[:limit]),
                    "total_topics": stats.get("total_topics", 0),
                    "status": "success",
                }
            )

        except Exception as e:
            self.logger.error(f"Error listing topics: {e}")
            return jsonify({"error": "Error retrieving topics", "status": "error"}), 500

    def get_search_stats(self):
        """Get comprehensive search index statistics."""
        try:
            stats = self.indexer.get_search_stats()

            return jsonify({"stats": stats, "status": "success"})

        except Exception as e:
            self.logger.error(f"Error getting search stats: {e}")
            return (
                jsonify(
                    {"error": "Error retrieving search statistics", "status": "error"}
                ),
                500,
            )

    def _get_query_type(self, query: str) -> str:
        """Determine query type for ranking optimization."""
        query_lower = query.lower()

        # Question queries
        question_indicators = [
            "what",
            "how",
            "why",
            "when",
            "where",
            "who",
            "can",
            "do",
            "would",
            "should",
        ]
        if any(word in query_lower for word in question_indicators) or "?" in query:
            return "question"

        # Topic queries
        if any(
            word in query_lower for word in ["about", "discuss", "topic", "regarding"]
        ):
            return "topic"

        # Default
        return "general"

    def _format_standard_results(
        self, results: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Format search results in standard format."""
        formatted = []

        for result in results:
            formatted_result = {
                "id": result.get("id"),
                "content": result.get("content"),
                "speaker": result.get("speaker"),
                "segment_type": result.get("segment_type"),
                "word_count": result.get("word_count"),
                "topics": result.get("topic_tags", []),
                "content_uid": result.get("content_uid"),
                "timestamp": result.get("start_timestamp"),
            }
            formatted.append(formatted_result)

        return formatted

    def _format_detailed_results(
        self, results: List[Dict[str, Any]], query: str
    ) -> List[Dict[str, Any]]:
        """Format search results with additional context and conversation flow."""
        formatted = []

        for result in results:
            # Get conversation context
            context = self._get_conversation_context(
                result.get("id"), result.get("content_uid")
            )

            formatted_result = {
                "id": result.get("id"),
                "content": result.get("content"),
                "speaker": result.get("speaker"),
                "segment_type": result.get("segment_type"),
                "word_count": result.get("word_count"),
                "topics": result.get("topic_tags", []),
                "content_uid": result.get("content_uid"),
                "timestamp": result.get("start_timestamp"),
                "context": context,
                "relevance_score": self._calculate_relevance_score(result, query),
            }
            formatted.append(formatted_result)

        return formatted

    def _get_conversation_context(
        self, segment_id: int, content_uid: str, context_lines: int = 2
    ) -> Dict[str, Any]:
        """Get conversation context around a segment."""
        try:
            # This would get segments before and after the current one
            # For now, return a simple context structure
            return {
                "before": [],
                "after": [],
                "conversation_flow": "Available in full implementation",
            }

        except Exception as e:
            self.logger.error(f"Error getting conversation context: {e}")
            return {"before": [], "after": [], "error": "Context unavailable"}

    def _calculate_relevance_score(self, result: Dict[str, Any], query: str) -> float:
        """Calculate relevance score for search result."""
        try:
            score = 0.0
            content = (result.get("content") or "").lower()
            query_lower = query.lower()

            # Simple relevance scoring
            query_words = query_lower.split()
            for word in query_words:
                if word in content:
                    score += 1.0

            # Bonus for segment type
            if result.get("segment_type") == "answer" and any(
                q in query_lower for q in ["what", "how", "why"]
            ):
                score += 0.5

            # Bonus for word count (longer segments often more informative)
            word_count = result.get("word_count", 0)
            if word_count > 50:
                score += 0.2

            return round(score, 2)

        except Exception as e:
            self.logger.error(f"Error calculating relevance score: {e}")
            return 0.0


def create_transcript_search_app():
    """Create Flask app with transcript search API."""
    app = Flask(__name__)

    # Initialize transcript search API
    transcript_api = TranscriptSearchAPI(app)

    @app.route("/api/transcript")
    def transcript_api_info():
        """API information endpoint."""
        return jsonify(
            {
                "name": "Atlas Transcript Search API",
                "version": "1.0.0",
                "endpoints": {
                    "search": "/api/transcript/search",
                    "speaker_topics": "/api/transcript/speaker/<name>/topics",
                    "related_segments": "/api/transcript/segment/<id>/related",
                    "speakers": "/api/transcript/speakers",
                    "topics": "/api/transcript/topics",
                    "stats": "/api/transcript/stats",
                },
                "status": "active",
            }
        )

    return app


def main():
    """Run transcript search API server."""
    app = create_transcript_search_app()
    app.run(debug=True, host="0.0.0.0", port=5001)


if __name__ == "__main__":
    main()
