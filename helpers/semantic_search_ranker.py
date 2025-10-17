#!/usr/bin/env python3
"""
Semantic Search & Ranking - Phase B3
Production-quality search with intelligent relevance scoring.
"""

import os
import sqlite3
import logging
import json
import math
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple, Set
from collections import defaultdict, Counter
import numpy as np

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SemanticSearchRanker:
    """Advanced search ranking with TF-IDF and semantic features."""

    def __init__(self, config: Dict[str, Any] = None):
        """Initialize semantic search ranker."""
        self.config = config or {}
        self.main_db = self.config.get('main_db', 'data/atlas.db')
        self.search_db = self.config.get('search_db', 'data/enhanced_search.db')

        # TF-IDF parameters
        self.min_word_length = 3
        self.max_df = 0.8  # Ignore words that appear in >80% of documents
        self.min_df = 2    # Ignore words that appear in <2 documents

        # Ranking weights
        self.ranking_weights = {
            'tf_idf': 0.4,
            'recency': 0.2,
            'quality': 0.15,
            'content_length': 0.1,
            'title_match': 0.1,
            'domain_authority': 0.05
        }

        # Cache for performance
        self._document_cache = {}
        self._tf_idf_cache = {}

    def _get_connection(self, db_path: str) -> sqlite3.Connection:
        """Get database connection."""
        if not os.path.exists(db_path):
            raise FileNotFoundError(f"Database not found: {db_path}")
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def build_tf_idf_index(self, rebuild: bool = False) -> Dict[str, Any]:
        """Build TF-IDF index for semantic search."""
        logger.info("🔍 Building TF-IDF search index...")

        # Check if we should rebuild
        index_file = Path('data/tf_idf_index.json')
        if not rebuild and index_file.exists():
            try:
                with open(index_file, 'r') as f:
                    cached_index = json.load(f)
                    if (datetime.now() - datetime.fromisoformat(cached_index.get('created_at', '2000-01-01'))).days < 1:
                        logger.info("   Using cached TF-IDF index (< 1 day old)")
                        self._tf_idf_cache = cached_index
                        return cached_index.get('stats', {})
            except Exception:
                logger.info("   Cache invalid, rebuilding...")

        # Get all documents
        documents = self._get_all_documents()
        if not documents:
            return {'error': 'No documents found'}

        logger.info(f"   Processing {len(documents)} documents...")

        # Build vocabulary and document frequency
        vocabulary = set()
        document_frequencies = defaultdict(int)

        # Process documents to build vocabulary
        for doc in documents:
            words = self._extract_words(doc.get('content', '') + ' ' + doc.get('title', ''))
            doc_words = set(words)

            for word in doc_words:
                if len(word) >= self.min_word_length:
                    vocabulary.add(word)
                    document_frequencies[word] += 1

        # Filter vocabulary by document frequency
        total_docs = len(documents)
        filtered_vocabulary = {
            word for word in vocabulary
            if self.min_df <= document_frequencies[word] <= (self.max_df * total_docs)
        }

        logger.info(f"   Vocabulary: {len(filtered_vocabulary)} terms (from {len(vocabulary)} total)")

        # Calculate TF-IDF for each document
        tf_idf_vectors = {}
        word_to_index = {word: i for i, word in enumerate(sorted(filtered_vocabulary))}

        for doc in documents:
            doc_id = str(doc['id'])
            text = doc.get('content', '') + ' ' + doc.get('title', '')
            words = self._extract_words(text)

            # Calculate term frequencies
            word_counts = Counter(words)
            total_words = len(words)

            # Calculate TF-IDF vector
            tf_idf_vector = {}

            for word in filtered_vocabulary:
                if word in word_counts:
                    # Term frequency (normalized)
                    tf = word_counts[word] / total_words

                    # Inverse document frequency
                    idf = math.log(total_docs / document_frequencies[word])

                    # TF-IDF score
                    tf_idf = tf * idf

                    if tf_idf > 0.001:  # Only store significant scores
                        tf_idf_vector[word] = tf_idf

            tf_idf_vectors[doc_id] = tf_idf_vector

        # Build content relationships
        content_relationships = self._build_content_relationships(documents, tf_idf_vectors)

        # Cache the index
        index_data = {
            'created_at': datetime.now().isoformat(),
            'vocabulary': list(filtered_vocabulary),
            'word_to_index': word_to_index,
            'tf_idf_vectors': tf_idf_vectors,
            'document_frequencies': dict(document_frequencies),
            'content_relationships': content_relationships,
            'stats': {
                'total_documents': len(documents),
                'vocabulary_size': len(filtered_vocabulary),
                'relationships_found': len(content_relationships),
                'average_vector_size': np.mean([len(vec) for vec in tf_idf_vectors.values()])
            }
        }

        # Save cache
        index_file.parent.mkdir(exist_ok=True)
        with open(index_file, 'w') as f:
            json.dump(index_data, f, indent=2)

        self._tf_idf_cache = index_data
        logger.info(f"   ✅ TF-IDF index built: {len(filtered_vocabulary)} terms, {len(content_relationships)} relationships")

        return index_data['stats']

    def _get_all_documents(self) -> List[Dict[str, Any]]:
        """Get all documents for indexing."""
        try:
            conn = self._get_connection(self.main_db)
            cursor = conn.cursor()

            cursor.execute("""
                SELECT id, title, content, content_type, url, created_at, metadata
                FROM content
                WHERE content IS NOT NULL
                  AND LENGTH(content) > 100
                ORDER BY created_at DESC
            """)

            documents = []
            for row in cursor.fetchall():
                doc = dict(row)
                # Parse metadata if it's a string
                if isinstance(doc.get('metadata'), str):
                    try:
                        doc['metadata'] = json.loads(doc['metadata'])
                    except:
                        doc['metadata'] = {}
                documents.append(doc)

            conn.close()
            return documents

        except Exception as e:
            logger.error(f"Error getting documents: {e}")
            return []

    def _extract_words(self, text: str) -> List[str]:
        """Extract and clean words from text."""
        if not text:
            return []

        # Convert to lowercase and extract words
        words = re.findall(r'\b[a-zA-Z]+\b', text.lower())

        # Filter stop words and short words
        stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with',
            'by', 'from', 'up', 'about', 'into', 'through', 'during', 'before', 'after',
            'above', 'below', 'over', 'under', 'again', 'further', 'then', 'once', 'here',
            'there', 'when', 'where', 'why', 'how', 'all', 'any', 'both', 'each', 'few',
            'more', 'most', 'other', 'some', 'such', 'no', 'nor', 'not', 'only', 'own',
            'same', 'so', 'than', 'too', 'very', 'can', 'will', 'just', 'should', 'now',
            'get', 'make', 'go', 'know', 'take', 'see', 'come', 'think', 'say', 'give',
            'use', 'find', 'tell', 'ask', 'work', 'seem', 'feel', 'try', 'leave', 'call'
        }

        filtered_words = [word for word in words
                         if len(word) >= self.min_word_length and word not in stop_words]

        return filtered_words

    def _build_content_relationships(self, documents: List[Dict[str, Any]],
                                   tf_idf_vectors: Dict[str, Dict[str, float]]) -> Dict[str, List[Dict[str, Any]]]:
        """Build content relationships based on TF-IDF similarity."""
        logger.info("   Building content relationships...")

        relationships = {}
        doc_ids = list(tf_idf_vectors.keys())

        # Calculate similarity between documents (sample for performance)
        sample_size = min(500, len(doc_ids))  # Limit for performance
        sampled_docs = doc_ids[:sample_size]

        for i, doc_id_1 in enumerate(sampled_docs):
            if i % 50 == 0:
                logger.info(f"     Processing relationships for document {i+1}/{len(sampled_docs)}")

            similarities = []
            vec_1 = tf_idf_vectors[doc_id_1]

            for doc_id_2 in sampled_docs[i+1:]:
                vec_2 = tf_idf_vectors[doc_id_2]

                # Calculate cosine similarity
                similarity = self._cosine_similarity(vec_1, vec_2)

                if similarity > 0.1:  # Only store significant similarities
                    similarities.append({
                        'related_doc_id': doc_id_2,
                        'similarity': round(similarity, 3)
                    })

            # Keep top 5 most similar documents
            similarities.sort(key=lambda x: x['similarity'], reverse=True)
            relationships[doc_id_1] = similarities[:5]

        return relationships

    def _cosine_similarity(self, vec_1: Dict[str, float], vec_2: Dict[str, float]) -> float:
        """Calculate cosine similarity between two TF-IDF vectors."""
        if not vec_1 or not vec_2:
            return 0.0

        # Find common words
        common_words = set(vec_1.keys()) & set(vec_2.keys())
        if not common_words:
            return 0.0

        # Calculate dot product
        dot_product = sum(vec_1[word] * vec_2[word] for word in common_words)

        # Calculate magnitudes
        magnitude_1 = math.sqrt(sum(score ** 2 for score in vec_1.values()))
        magnitude_2 = math.sqrt(sum(score ** 2 for score in vec_2.values()))

        if magnitude_1 == 0 or magnitude_2 == 0:
            return 0.0

        return dot_product / (magnitude_1 * magnitude_2)

    def search_with_ranking(self, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Perform semantic search with intelligent ranking."""
        if not query or not query.strip():
            return []

        logger.info(f"🔍 Semantic search: '{query}'")

        # Ensure we have TF-IDF index
        if not self._tf_idf_cache:
            self.build_tf_idf_index()

        if not self._tf_idf_cache:
            logger.error("Failed to build TF-IDF index")
            return []

        # Get initial search results using full-text search
        initial_results = self._get_initial_search_results(query)
        if not initial_results:
            return []

        # Rank results using multiple factors
        ranked_results = []
        query_words = self._extract_words(query)
        query_vector = self._create_query_vector(query_words)

        for result in initial_results:
            doc_id = str(result['id'])

            # Calculate ranking score
            ranking_score = self._calculate_ranking_score(
                result, query_vector, query_words, doc_id
            )

            result['ranking_score'] = ranking_score
            result['ranking_factors'] = ranking_score.copy()  # For debugging
            ranked_results.append(result)

        # Sort by total ranking score
        ranked_results.sort(key=lambda x: x['ranking_score']['total'], reverse=True)

        # Add related content suggestions
        final_results = []
        for result in ranked_results[:limit]:
            # Add related content if available
            doc_id = str(result['id'])
            if doc_id in self._tf_idf_cache.get('content_relationships', {}):
                result['related_content'] = self._tf_idf_cache['content_relationships'][doc_id][:3]

            final_results.append(result)

        logger.info(f"   Found {len(final_results)} ranked results")
        return final_results

    def _get_initial_search_results(self, query: str) -> List[Dict[str, Any]]:
        """Get initial search results using full-text search."""
        try:
            conn = self._get_connection(self.main_db)
            cursor = conn.cursor()

            # Use SQLite FTS if available, otherwise basic LIKE search
            search_query = f"%{query}%"

            cursor.execute("""
                SELECT id, title, content, content_type, url, created_at, metadata
                FROM content
                WHERE (title LIKE ? OR content LIKE ?)
                  AND LENGTH(content) > 100
                ORDER BY
                    CASE WHEN title LIKE ? THEN 1 ELSE 2 END,
                    created_at DESC
                LIMIT 200
            """, (search_query, search_query, search_query))

            results = []
            for row in cursor.fetchall():
                result = dict(row)
                # Parse metadata if it's a string
                if isinstance(result.get('metadata'), str):
                    try:
                        result['metadata'] = json.loads(result['metadata'])
                    except:
                        result['metadata'] = {}
                results.append(result)

            conn.close()
            return results

        except Exception as e:
            logger.error(f"Error getting initial search results: {e}")
            return []

    def _create_query_vector(self, query_words: List[str]) -> Dict[str, float]:
        """Create TF-IDF vector for query."""
        if not query_words:
            return {}

        word_counts = Counter(query_words)
        total_words = len(query_words)
        vocabulary = set(self._tf_idf_cache.get('vocabulary', []))
        document_frequencies = self._tf_idf_cache.get('document_frequencies', {})
        total_docs = self._tf_idf_cache.get('stats', {}).get('total_documents', 1)

        query_vector = {}

        for word in vocabulary:
            if word in word_counts:
                # Term frequency
                tf = word_counts[word] / total_words

                # Inverse document frequency
                df = document_frequencies.get(word, 1)
                idf = math.log(total_docs / df)

                query_vector[word] = tf * idf

        return query_vector

    def _calculate_ranking_score(self, result: Dict[str, Any], query_vector: Dict[str, float],
                                query_words: List[str], doc_id: str) -> Dict[str, float]:
        """Calculate comprehensive ranking score."""
        scores = {}

        # 1. TF-IDF similarity score
        doc_vector = self._tf_idf_cache.get('tf_idf_vectors', {}).get(doc_id, {})
        tf_idf_score = self._cosine_similarity(query_vector, doc_vector)
        scores['tf_idf'] = tf_idf_score * self.ranking_weights['tf_idf']

        # 2. Recency score
        try:
            created_at = datetime.fromisoformat(result['created_at'].replace('Z', '+00:00'))
            days_old = (datetime.now() - created_at.replace(tzinfo=None)).days
            recency_score = max(0, 1 - (days_old / 365))  # Decay over 1 year
        except:
            recency_score = 0.5  # Default for parsing errors
        scores['recency'] = recency_score * self.ranking_weights['recency']

        # 3. Quality score (based on content length, metadata)
        content_length = len(result.get('content', ''))
        length_score = min(1.0, content_length / 5000)  # Normalize to 5000 chars

        # Boost for certain content types
        content_type_boost = 1.0
        if result.get('content_type') in ['article', 'blog_post']:
            content_type_boost = 1.2
        elif result.get('content_type') in ['academic', 'research']:
            content_type_boost = 1.3

        quality_score = length_score * content_type_boost
        scores['quality'] = min(1.0, quality_score) * self.ranking_weights['quality']

        # 4. Content length score (separate from quality)
        length_score = min(1.0, math.log(content_length + 1) / 10)
        scores['content_length'] = length_score * self.ranking_weights['content_length']

        # 5. Title match score
        title = result.get('title', '').lower()
        title_words = self._extract_words(title)
        query_words_set = set(query_words)
        title_words_set = set(title_words)

        if title_words_set and query_words_set:
            title_match = len(query_words_set & title_words_set) / len(query_words_set)
        else:
            title_match = 0
        scores['title_match'] = title_match * self.ranking_weights['title_match']

        # 6. Domain authority (simple heuristic)
        url = result.get('url', '')
        domain_score = 0.5  # Default

        # High authority domains
        high_authority = ['arxiv.org', 'nature.com', 'science.org', 'mit.edu', 'stanford.edu',
                         'nytimes.com', 'economist.com', 'stratechery.com']
        medium_authority = ['medium.com', 'substack.com', 'github.com']

        for domain in high_authority:
            if domain in url:
                domain_score = 1.0
                break
        else:
            for domain in medium_authority:
                if domain in url:
                    domain_score = 0.7
                    break

        scores['domain_authority'] = domain_score * self.ranking_weights['domain_authority']

        # Calculate total score
        scores['total'] = sum(scores.values())

        return scores

    def add_search_autocomplete(self) -> Dict[str, Any]:
        """Build search autocomplete suggestions."""
        logger.info("🔍 Building search autocomplete...")

        try:
            # Get most common words from vocabulary
            if not self._tf_idf_cache:
                self.build_tf_idf_index()

            vocabulary = self._tf_idf_cache.get('vocabulary', [])
            document_frequencies = self._tf_idf_cache.get('document_frequencies', {})

            # Create autocomplete suggestions
            suggestions = []

            # Most common single words
            common_words = sorted(
                [(word, freq) for word, freq in document_frequencies.items()
                 if word in vocabulary and len(word) > 4],
                key=lambda x: x[1], reverse=True
            )[:100]

            suggestions.extend([word for word, freq in common_words])

            # Add common phrases from titles
            conn = self._get_connection(self.main_db)
            cursor = conn.cursor()

            cursor.execute("""
                SELECT title
                FROM content
                WHERE title IS NOT NULL AND LENGTH(title) > 10
                ORDER BY created_at DESC
                LIMIT 1000
            """)

            titles = [row[0] for row in cursor.fetchall()]
            conn.close()

            # Extract common phrases
            phrase_counts = Counter()
            for title in titles:
                words = self._extract_words(title)
                # Get 2-3 word phrases
                for i in range(len(words) - 1):
                    if len(words[i]) > 3 and len(words[i+1]) > 3:
                        phrase = f"{words[i]} {words[i+1]}"
                        phrase_counts[phrase] += 1

                        if i < len(words) - 2 and len(words[i+2]) > 3:
                            phrase3 = f"{words[i]} {words[i+1]} {words[i+2]}"
                            phrase_counts[phrase3] += 1

            # Add top phrases
            top_phrases = [phrase for phrase, count in phrase_counts.most_common(50) if count >= 3]
            suggestions.extend(top_phrases)

            # Save autocomplete data
            autocomplete_data = {
                'created_at': datetime.now().isoformat(),
                'suggestions': suggestions,
                'stats': {
                    'total_suggestions': len(suggestions),
                    'single_words': len(common_words),
                    'phrases': len(top_phrases)
                }
            }

            autocomplete_file = Path('data/autocomplete_suggestions.json')
            with open(autocomplete_file, 'w') as f:
                json.dump(autocomplete_data, f, indent=2)

            logger.info(f"   ✅ Built autocomplete: {len(suggestions)} suggestions")
            return autocomplete_data['stats']

        except Exception as e:
            logger.error(f"Error building autocomplete: {e}")
            return {'error': str(e)}

    def get_search_performance_stats(self) -> Dict[str, Any]:
        """Get search performance statistics."""
        stats = {
            'index_status': 'ready' if self._tf_idf_cache else 'not_built',
            'last_updated': self._tf_idf_cache.get('created_at', 'never'),
            'ranking_weights': self.ranking_weights
        }

        if self._tf_idf_cache:
            stats.update(self._tf_idf_cache.get('stats', {}))

        return stats

def test_semantic_search():
    """Test semantic search functionality."""
    logger.info("🧪 Testing Semantic Search & Ranking")

    ranker = SemanticSearchRanker()

    # Build TF-IDF index
    index_stats = ranker.build_tf_idf_index()
    logger.info(f"   Index built: {index_stats}")

    # Test searches
    test_queries = [
        'artificial intelligence',
        'technology trends',
        'machine learning'
    ]

    for query in test_queries:
        results = ranker.search_with_ranking(query, limit=5)
        logger.info(f"   '{query}': {len(results)} results")

        if results:
            top_result = results[0]
            logger.info(f"     Top result: {top_result.get('title', 'No title')[:50]}...")
            logger.info(f"     Score: {top_result.get('ranking_score', {}).get('total', 0):.3f}")

    # Build autocomplete
    autocomplete_stats = ranker.add_search_autocomplete()
    logger.info(f"   Autocomplete built: {autocomplete_stats}")

if __name__ == "__main__":
    test_semantic_search()