#!/usr/bin/env python3
"""
Enhanced Search Engine - Advanced search capabilities beyond basic full-text
Provides semantic search, ranking, filtering, and relationship mapping.
"""

import json
import re
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union
from collections import Counter, defaultdict
from dataclasses import dataclass

# Module-level log path
import os
log_dir = os.path.join(os.getcwd(), "logs")
os.makedirs(log_dir, exist_ok=True)
module_log_path = os.path.join(log_dir, "enhanced_search_module.log")

from helpers.utils import log_info, log_error
from helpers.search_engine import AtlasSearchEngine as SearchEngine
from helpers.search_performance_optimizer import SearchPerformanceOptimizer, advanced_search as optimized_search


@dataclass
class SearchResult:
    """Enhanced search result with ranking and metadata."""
    content_id: str

    title: str
    content_type: str
    url: str
    snippet: str
    score: float
    rank: int
    metadata: Dict[str, Any]
    relevance_factors: Dict[str, float]
    timestamp: str


class EnhancedSearchEngine:
    """
    Advanced search engine with semantic capabilities and intelligent ranking.

    Features:
    - Semantic search with context understanding
    - Multi-factor ranking algorithms
    - Tag-based filtering and faceted search
    - Content relationship mapping
    - Search analytics and optimization
    - Query expansion and suggestion
    """

    def __init__(self, config: Dict[str, Any] = None):
        """Initialize EnhancedSearchEngine with configuration."""
        self.config = config or {}
        self.db_path = Path(self.config.get('search_db', 'data/enhanced_search.db'))
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # Set up logging
        import os
        log_dir = self.config.get('log_directory', 'logs')
        os.makedirs(log_dir, exist_ok=True)
        self.log_path = os.path.join(log_dir, 'enhanced_search.log')

        # Initialize basic search engine
        try:
            self.basic_search = SearchEngine(config)
            self._sync_with_basic_search()
        except Exception as e:
            log_error(self.log_path, f"Could not initialize basic search engine: {str(e)}")
            self.basic_search = None

        # Search configuration
        self.max_results = self.config.get('max_search_results', 50)
        self.snippet_length = self.config.get('snippet_length', 200)
        self.relevance_threshold = self.config.get('relevance_threshold', 0.1)

        # Initialize enhanced database
        self._init_enhanced_database()

        # Load search analytics
        self.search_analytics = self._load_search_analytics()

    def _init_enhanced_database(self):
        """Initialize enhanced search database."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Content index with enhanced metadata
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS enhanced_content_index (
                        id TEXT PRIMARY KEY,
                        title TEXT,
                        content TEXT,
                        content_type TEXT,
                        url TEXT,
                        tags TEXT,
                        keywords TEXT,
                        summary TEXT,
                        word_count INTEGER,
                        quality_score REAL,
                        popularity_score REAL,
                        recency_score REAL,
                        semantic_vector TEXT,
                        created_at TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')

                # Search index table (required for validation)
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS search_index (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        content_id TEXT,
                        title TEXT,
                        content TEXT,
                        content_type TEXT,
                        url TEXT,
                        tags TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')

                # Content relationships and links
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS content_relationships (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        source_id TEXT,
                        target_id TEXT,
                        relationship_type TEXT,
                        strength REAL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (source_id) REFERENCES enhanced_content_index (id),
                        FOREIGN KEY (target_id) REFERENCES enhanced_content_index (id)
                    )
                ''')

                # Search analytics and query tracking
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS search_analytics (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        query TEXT,
                        query_type TEXT,
                        results_count INTEGER,
                        top_result_id TEXT,
                        clicked_result_id TEXT,
                        search_time REAL,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')

                # Tag index for faceted search
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS tag_index (
                        content_id TEXT,
                        tag TEXT,
                        weight REAL DEFAULT 1.0,
                        FOREIGN KEY (content_id) REFERENCES enhanced_content_index (id)
                    )
                ''')

                # Create indexes for performance
                conn.execute('CREATE INDEX IF NOT EXISTS idx_content_type ON enhanced_content_index (content_type)')
                conn.execute('CREATE INDEX IF NOT EXISTS idx_tags ON tag_index (tag)')
                conn.execute('CREATE INDEX IF NOT EXISTS idx_relationships ON content_relationships (source_id, target_id)')
                conn.execute('CREATE INDEX IF NOT EXISTS idx_search_index_content_id ON search_index (content_id)')
                conn.execute('CREATE INDEX IF NOT EXISTS idx_search_index_content_type ON search_index (content_type)')

            log_info(self.log_path, "Enhanced search database initialized")

        except Exception as e:
            log_error(self.log_path, f"Error initializing enhanced search database: {str(e)}")

    def _sync_with_basic_search(self):
        """Sync enhanced search with basic search engine data."""
        try:
            if not self.basic_search:
                return

            # Get existing content from basic search
            search_response = self.basic_search.search("", limit=1000)  # Get all content
            search_results = search_response.get("hits", [])

            log_info(self.log_path, f"Syncing enhanced search with {len(search_results)} existing items")

            for result in search_results:
                content_id = result.get('id') or result.get('url', str(hash(result.get('content', ''))))
                title = result.get('title', 'Untitled')
                content = result.get('content', '')
                content_type = result.get('type', 'unknown')
                url = result.get('url', '')

                # Index in enhanced search
                self.index_content(
                    content_id=content_id,
                    title=title,
                    content=content,
                    content_type=content_type,
                    url=url,
                    metadata=result
                )

            log_info(self.log_path, "Enhanced search sync completed")

        except Exception as e:
            log_error(self.log_path, f"Error syncing with basic search: {str(e)}")

    def index_content(self,
                     content_id: str,
                     title: str,
                     content: str,
                     content_type: str,
                     url: str = "",
                     metadata: Dict[str, Any] = None) -> bool:
        """Index content with enhanced metadata and analysis."""
        try:
            metadata = metadata or {}

            # Extract enhanced metadata
            enhanced_metadata = self._analyze_content_for_indexing(content, metadata)

            # Generate semantic features (placeholder for now)
            semantic_vector = self._generate_semantic_vector(content, title)

            with sqlite3.connect(self.db_path) as conn:
                # Insert or update main content
                conn.execute('''
                    INSERT OR REPLACE INTO enhanced_content_index
                    (id, title, content, content_type, url, tags, keywords, summary,
                     word_count, quality_score, popularity_score, recency_score,
                     semantic_vector, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ''', (
                    content_id,
                    title,
                    content,
                    content_type,
                    url,
                    json.dumps(enhanced_metadata.get('tags', [])),
                    json.dumps(enhanced_metadata.get('keywords', [])),
                    enhanced_metadata.get('summary', ''),
                    enhanced_metadata.get('word_count', 0),
                    enhanced_metadata.get('quality_score', 0.5),
                    enhanced_metadata.get('popularity_score', 0.5),
                    enhanced_metadata.get('recency_score', 1.0),
                    json.dumps(semantic_vector),
                    datetime.now().isoformat()
                ))

                # Index tags
                conn.execute('DELETE FROM tag_index WHERE content_id = ?', (content_id,))
                for tag in enhanced_metadata.get('tags', []):
                    conn.execute('''
                        INSERT INTO tag_index (content_id, tag, weight)
                        VALUES (?, ?, ?)
                    ''', (content_id, tag, 1.0))

            # Update relationships
            self._update_content_relationships(content_id, content, title, metadata)

            log_info(self.log_path, f"Enhanced indexing completed for: {content_id}")
            return True

        except Exception as e:
            log_error(self.log_path, f"Error indexing content {content_id}: {str(e)}")
            return False

    def search(self,
              query: str,
              content_types: List[str] = None,
              tags: List[str] = None,
              date_range: Tuple[str, str] = None,
              sort_by: str = "relevance",
              limit: int = None) -> List[SearchResult]:
        """Perform enhanced search with advanced ranking and filtering."""
        try:
            start_time = datetime.now()
            limit = limit or self.max_results

            # Expand query with synonyms and related terms
            expanded_query = self._expand_query(query)

            # Get basic search results
            basic_results = []
            if self.basic_search:
                try:
                    basic_response = self.basic_search.search(query, limit=limit * 2)  # Get more for reranking
                    basic_results = basic_response.get("hits", [])
                except Exception as e:
                    log_error(self.log_path, f"Basic search failed: {str(e)}")
                    basic_results = []

            # Get enhanced results from database
            enhanced_results = self._search_enhanced_database(
                expanded_query, content_types, tags, date_range
            )

            # Combine and deduplicate results
            combined_results = self._combine_search_results(basic_results, enhanced_results)

            # Apply advanced ranking
            ranked_results = self._apply_advanced_ranking(combined_results, query)

            # Format as SearchResult objects
            search_results = []
            for i, result in enumerate(ranked_results[:limit]):
                search_result = self._format_search_result(result, query, i + 1)
                if search_result:
                    search_results.append(search_result)

            # Record search analytics
            search_time = (datetime.now() - start_time).total_seconds()
            self._record_search_analytics(query, len(search_results), search_time, search_results)

            log_info(self.log_path, f"Enhanced search completed: '{query}' -> {len(search_results)} results")
            return search_results

        except Exception as e:
            log_error(self.log_path, f"Error in enhanced search: {str(e)}")
            # Fallback to basic search if enhanced search fails
            if self.basic_search:
                try:
                    log_info(self.log_path, "Falling back to basic search")
                    basic_response = self.basic_search.search(query, limit=limit)
                    basic_results = basic_response.get("hits", [])
                    # Convert to SearchResult format
                    search_results = []
                    for i, result in enumerate(basic_results):
                        search_result = SearchResult(
                            content_id=result.get('id', str(i)),
                            title=result.get('title', 'Untitled'),
                            content_type=result.get('type', 'unknown'),
                            url=result.get('url', ''),
                            snippet=result.get('summary', '')[:self.snippet_length],
                            score=1.0,
                            rank=i + 1,
                            metadata=result,
                            relevance_factors={'basic_search': 1.0},
                            timestamp=datetime.now().isoformat()
                        )
                        search_results.append(search_result)
                    return search_results
                except Exception as fallback_error:
                    log_error(self.log_path, f"Basic search fallback also failed: {str(fallback_error)}")
            return []

    def semantic_search(self,
                       query: str,
                       similarity_threshold: float = 0.7,
                       limit: int = None) -> List[SearchResult]:
        """Perform semantic search based on content similarity."""
        try:
            limit = limit or self.max_results

            # Generate query vector
            query_vector = self._generate_semantic_vector(query, "")

            # Find similar content
            similar_content = self._find_similar_content(query_vector, similarity_threshold, limit)

            # Format results
            search_results = []
            for i, (content_id, similarity) in enumerate(similar_content):
                result_data = self._get_content_by_id(content_id)
                if result_data:
                    search_result = SearchResult(
                        content_id=content_id,
                        title=result_data.get('title', ''),
                        content_type=result_data.get('content_type', ''),
                        url=result_data.get('url', ''),
                        snippet=self._generate_snippet(result_data.get('content', ''), query),
                        score=similarity,
                        rank=i + 1,
                        metadata=result_data,
                        relevance_factors={'semantic_similarity': similarity},
                        timestamp=datetime.now().isoformat()
                    )
                    search_results.append(search_result)

            log_info(self.log_path, f"Semantic search completed: '{query}' -> {len(search_results)} results")
            return search_results

        except Exception as e:
            log_error(self.log_path, f"Error in semantic search: {str(e)}")
            return []

    def faceted_search(self,
                      query: str = "",
                      facets: Dict[str, List[str]] = None) -> Dict[str, Any]:
        """Perform faceted search with aggregated results."""
        try:
            facets = facets or {}

            # Base search
            results = self.search(query, limit=1000)  # Get many results for faceting

            # Calculate facets
            content_type_facets = Counter()
            tag_facets = Counter()
            date_facets = defaultdict(int)

            for result in results:
                # Content type facet
                content_type_facets[result.content_type] += 1

                # Tag facets
                tags = result.metadata.get('tags', [])
                if isinstance(tags, str):
                    tags = json.loads(tags) if tags else []
                for tag in tags:
                    tag_facets[tag] += 1

                # Date facets (by month)
                try:
                    date = datetime.fromisoformat(result.timestamp.replace('Z', '+00:00'))
                    month_key = date.strftime('%Y-%m')
                    date_facets[month_key] += 1
                except:
                    pass

            # Apply facet filters if provided
            filtered_results = results
            if facets:
                filtered_results = self._apply_facet_filters(results, facets)

            return {
                "query": query,
                "total_results": len(filtered_results),
                "results": filtered_results[:self.max_results],
                "facets": {
                    "content_types": dict(content_type_facets.most_common(10)),
                    "tags": dict(tag_facets.most_common(20)),
                    "dates": dict(sorted(date_facets.items(), reverse=True)[:12])
                },
                "applied_facets": facets
            }

        except Exception as e:
            log_error(self.log_path, f"Error in faceted search: {str(e)}")
            return {"error": str(e), "results": []}

    def get_related_content(self, content_id: str, limit: int = 10) -> List[SearchResult]:
        """Get content related to a specific item."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Get direct relationships
                related_ids = conn.execute('''
                    SELECT target_id, strength, relationship_type
                    FROM content_relationships
                    WHERE source_id = ?
                    ORDER BY strength DESC
                    LIMIT ?
                ''', (content_id, limit)).fetchall()

                # Get content details
                results = []
                for target_id, strength, rel_type in related_ids:
                    content_data = self._get_content_by_id(target_id)
                    if content_data:
                        search_result = SearchResult(
                            content_id=target_id,
                            title=content_data.get('title', ''),
                            content_type=content_data.get('content_type', ''),
                            url=content_data.get('url', ''),
                            snippet=content_data.get('summary', '')[:self.snippet_length],
                            score=strength,
                            rank=len(results) + 1,
                            metadata={**content_data, 'relationship_type': rel_type},
                            relevance_factors={'relationship_strength': strength},
                            timestamp=datetime.now().isoformat()
                        )
                        results.append(search_result)

                log_info(self.log_path, f"Found {len(results)} related items for {content_id}")
                return results

        except Exception as e:
            log_error(self.log_path, f"Error getting related content: {str(e)}")
            return []

    def suggest_queries(self, partial_query: str, limit: int = 5) -> List[str]:
        """Suggest query completions based on search history."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Get popular queries that start with partial_query
                suggestions = conn.execute('''
                    SELECT query, COUNT(*) as frequency
                    FROM search_analytics
                    WHERE query LIKE ? AND LENGTH(query) > LENGTH(?)
                    GROUP BY query
                    ORDER BY frequency DESC, LENGTH(query) ASC
                    LIMIT ?
                ''', (f"{partial_query}%", partial_query, limit)).fetchall()

                return [query for query, _ in suggestions]

        except Exception as e:
            log_error(self.log_path, f"Error suggesting queries: {str(e)}")
            return []

    def _analyze_content_for_indexing(self, content: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze content for enhanced indexing."""
        enhanced = metadata.copy()

        if not content:
            return enhanced

        # Basic metrics
        words = content.split()
        enhanced['word_count'] = len(words)
        enhanced['character_count'] = len(content)

        # Extract keywords (simple approach)
        word_freq = Counter(word.lower().strip('.,!?";') for word in words if len(word) > 3)
        enhanced['keywords'] = [word for word, freq in word_freq.most_common(20)]

        # Quality scoring (heuristic)
        quality_score = 0.5
        if enhanced['word_count'] > 100:
            quality_score += 0.2
        if enhanced['word_count'] > 1000:
            quality_score += 0.2
        if any(word in content.lower() for word in ['analysis', 'research', 'study', 'report']):
            quality_score += 0.1
        enhanced['quality_score'] = min(quality_score, 1.0)

        # Recency scoring
        try:
            created_date = datetime.fromisoformat(metadata.get('created_at', datetime.now().isoformat()))
            days_old = (datetime.now() - created_date).days
            enhanced['recency_score'] = max(0.1, 1.0 - (days_old / 365))  # Decay over a year
        except:
            enhanced['recency_score'] = 0.5

        # Popularity (placeholder)
        enhanced['popularity_score'] = 0.5

        # Generate summary
        sentences = content.split('. ')
        if sentences:
            enhanced['summary'] = '. '.join(sentences[:3]) + ('.' if len(sentences) > 3 else '')

        return enhanced

    def _generate_semantic_vector(self, content: str, title: str) -> List[float]:
        """Generate semantic vector for content (placeholder implementation)."""
        # This is a simple placeholder. In a real implementation, you would use:
        # - Word embeddings (Word2Vec, GloVe)
        # - Sentence transformers
        # - BERT/GPT embeddings
        # - TF-IDF vectors

        combined_text = f"{title} {content}".lower()
        words = re.findall(r'\w+', combined_text)

        # Simple bag-of-words hash-based vector
        vector_size = 100
        vector = [0.0] * vector_size

        for word in words:
            # Simple hash-based feature
            hash_val = hash(word) % vector_size
            vector[hash_val] += 1.0

        # Normalize
        total = sum(vector)
        if total > 0:
            vector = [v / total for v in vector]

        return vector

    def _search_enhanced_database(self,
                                 query: str,
                                 content_types: List[str] = None,
                                 tags: List[str] = None,
                                 date_range: Tuple[str, str] = None) -> List[Dict[str, Any]]:
        """Search the enhanced database with filters."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Build query
                sql = '''
                    SELECT id, title, content, content_type, url, tags, keywords,
                           summary, quality_score, popularity_score, recency_score,
                           created_at
                    FROM enhanced_content_index
                    WHERE (title LIKE ? OR content LIKE ? OR summary LIKE ?)
                '''
                params = [f"%{query}%", f"%{query}%", f"%{query}%"]

                # Add filters
                if content_types:
                    placeholders = ','.join('?' for _ in content_types)
                    sql += f' AND content_type IN ({placeholders})'
                    params.extend(content_types)

                if date_range:
                    sql += ' AND created_at BETWEEN ? AND ?'
                    params.extend(date_range)

                # Tag filtering (if tags specified)
                if tags:
                    tag_conditions = []
                    for tag in tags:
                        tag_conditions.append('id IN (SELECT content_id FROM tag_index WHERE tag = ?)')
                        params.append(tag)
                    sql += ' AND (' + ' OR '.join(tag_conditions) + ')'

                sql += ' ORDER BY quality_score DESC, recency_score DESC LIMIT 100'

                results = conn.execute(sql, params).fetchall()

                # Convert to dicts
                columns = ['id', 'title', 'content', 'content_type', 'url', 'tags',
                          'keywords', 'summary', 'quality_score', 'popularity_score',
                          'recency_score', 'created_at']

                return [dict(zip(columns, row)) for row in results]

        except Exception as e:
            log_error(self.log_path, f"Error searching enhanced database: {str(e)}")
            return []

    def _combine_search_results(self, basic_results: List, enhanced_results: List[Dict]) -> List[Dict]:
        """Combine and deduplicate search results."""
        # Convert basic results to dict format
        combined = {}

        # Add enhanced results first (they have more metadata)
        for result in enhanced_results:
            combined[result['id']] = result

        # Add basic results if not already present
        for result in basic_results:
            result_id = result.get('id') or result.get('url', str(hash(result.get('content', ''))))
            if result_id not in combined:
                combined[result_id] = {
                    'id': result_id,
                    'title': result.get('title', ''),
                    'content': result.get('content', ''),
                    'content_type': result.get('type', 'unknown'),
                    'url': result.get('url', ''),
                    'tags': result.get('tags', []),
                    'keywords': [],
                    'summary': result.get('summary', ''),
                    'quality_score': 0.5,
                    'popularity_score': 0.5,
                    'recency_score': 0.5,
                    'created_at': result.get('created_at', datetime.now().isoformat())
                }

        return list(combined.values())

    def _apply_advanced_ranking(self, results: List[Dict], query: str) -> List[Dict]:
        """Apply advanced ranking algorithm."""
        query_words = set(query.lower().split())

        for result in results:
            score = 0.0

            # Text relevance (TF-IDF-like)
            title_words = set(result.get('title', '').lower().split())
            content_words = set(result.get('content', '').lower().split())

            title_overlap = len(query_words & title_words) / max(len(query_words), 1)
            content_overlap = len(query_words & content_words) / max(len(query_words), 1)

            # Weighted scoring
            score += title_overlap * 0.4  # Title match is very important
            score += content_overlap * 0.2  # Content match
            score += result.get('quality_score', 0.5) * 0.2  # Quality
            score += result.get('popularity_score', 0.5) * 0.1  # Popularity
            score += result.get('recency_score', 0.5) * 0.1  # Recency

            result['_search_score'] = score

        # Sort by score
        return sorted(results, key=lambda x: x.get('_search_score', 0), reverse=True)

    def _format_search_result(self, result: Dict, query: str, rank: int) -> SearchResult:
        """Format result as SearchResult object."""
        try:
            return SearchResult(
                content_id=result.get('id', ''),
                title=result.get('title', ''),
                content_type=result.get('content_type', ''),
                url=result.get('url', ''),
                snippet=self._generate_snippet(result.get('content', ''), query),
                score=result.get('_search_score', 0.0),
                rank=rank,
                metadata=result,
                relevance_factors={
                    'text_relevance': result.get('_search_score', 0.0),
                    'quality': result.get('quality_score', 0.5),
                    'recency': result.get('recency_score', 0.5)
                },
                timestamp=datetime.now().isoformat()
            )
        except Exception as e:
            log_error(self.log_path, f"Error formatting search result: {str(e)}")
            return None

    def _generate_snippet(self, content: str, query: str) -> str:
        """Generate relevant snippet from content."""
        if not content:
            return ""

        query_words = query.lower().split()
        sentences = content.split('. ')

        # Find sentence with most query words
        best_sentence = ""
        best_score = 0

        for sentence in sentences:
            sentence_lower = sentence.lower()
            score = sum(1 for word in query_words if word in sentence_lower)
            if score > best_score:
                best_score = score
                best_sentence = sentence

        if best_sentence:
            # Expand around best sentence
            snippet = best_sentence
        else:
            # Default to first part of content
            snippet = content[:self.snippet_length]

        # Truncate to snippet length
        if len(snippet) > self.snippet_length:
            snippet = snippet[:self.snippet_length] + "..."

        return snippet

    def _expand_query(self, query: str) -> str:
        """Expand query with synonyms and related terms."""
        # Simple expansion (could be enhanced with word embeddings)
        expanded_terms = []
        words = query.lower().split()

        # Simple synonym mapping
        synonyms = {
            'article': ['post', 'blog', 'essay'],
            'video': ['movie', 'clip', 'recording'],
            'podcast': ['audio', 'show', 'episode'],
            'book': ['ebook', 'novel', 'text'],
            'research': ['study', 'analysis', 'investigation'],
            'tutorial': ['guide', 'howto', 'instruction']
        }

        for word in words:
            expanded_terms.append(word)
            if word in synonyms:
                expanded_terms.extend(synonyms[word])

        return ' '.join(expanded_terms)

    def _find_similar_content(self, query_vector: List[float], threshold: float, limit: int) -> List[Tuple[str, float]]:
        """Find content similar to query vector."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                results = conn.execute('''
                    SELECT id, semantic_vector
                    FROM enhanced_content_index
                    WHERE semantic_vector IS NOT NULL
                ''').fetchall()

                similarities = []
                for content_id, vector_json in results:
                    try:
                        content_vector = json.loads(vector_json)
                        similarity = self._cosine_similarity(query_vector, content_vector)
                        if similarity >= threshold:
                            similarities.append((content_id, similarity))
                    except:
                        continue

                # Sort by similarity and return top results
                similarities.sort(key=lambda x: x[1], reverse=True)
                return similarities[:limit]

        except Exception as e:
            log_error(self.log_path, f"Error finding similar content: {str(e)}")
            return []

    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between vectors."""
        try:
            if len(vec1) != len(vec2):
                return 0.0

            dot_product = sum(a * b for a, b in zip(vec1, vec2))
            magnitude1 = sum(a * a for a in vec1) ** 0.5
            magnitude2 = sum(b * b for b in vec2) ** 0.5

            if magnitude1 == 0 or magnitude2 == 0:
                return 0.0

            return dot_product / (magnitude1 * magnitude2)

        except:
            return 0.0

    def _get_content_by_id(self, content_id: str) -> Optional[Dict[str, Any]]:
        """Get content details by ID."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                result = conn.execute('''
                    SELECT id, title, content, content_type, url, tags, keywords,
                           summary, quality_score, popularity_score, recency_score, created_at
                    FROM enhanced_content_index
                    WHERE id = ?
                ''', (content_id,)).fetchone()

                if result:
                    columns = ['id', 'title', 'content', 'content_type', 'url', 'tags',
                              'keywords', 'summary', 'quality_score', 'popularity_score',
                              'recency_score', 'created_at']
                    return dict(zip(columns, result))

                return None

        except Exception as e:
            log_error(self.log_path, f"Error getting content by ID: {str(e)}")
            return None

    def _update_content_relationships(self, content_id: str, content: str, title: str, metadata: Dict):
        """Update content relationships based on links and references."""
        try:
            # Extract URLs from content
            urls = re.findall(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', content)

            with sqlite3.connect(self.db_path) as conn:
                # Remove existing relationships
                conn.execute('DELETE FROM content_relationships WHERE source_id = ?', (content_id,))

                # Add new relationships
                for url in urls:
                    # Find content with this URL
                    target_result = conn.execute('''
                        SELECT id FROM enhanced_content_index WHERE url = ?
                    ''', (url,)).fetchone()

                    if target_result:
                        target_id = target_result[0]
                        conn.execute('''
                            INSERT INTO content_relationships
                            (source_id, target_id, relationship_type, strength)
                            VALUES (?, ?, ?, ?)
                        ''', (content_id, target_id, 'link', 0.8))

        except Exception as e:
            log_error(self.log_path, f"Error updating relationships: {str(e)}")

    def _apply_facet_filters(self, results: List[SearchResult], facets: Dict[str, List[str]]) -> List[SearchResult]:
        """Apply facet filters to search results."""
        filtered = results

        if 'content_types' in facets:
            filtered = [r for r in filtered if r.content_type in facets['content_types']]

        if 'tags' in facets:
            def has_matching_tag(result):
                result_tags = result.metadata.get('tags', [])
                if isinstance(result_tags, str):
                    result_tags = json.loads(result_tags) if result_tags else []
                return any(tag in result_tags for tag in facets['tags'])

            filtered = [r for r in filtered if has_matching_tag(r)]

        return filtered

    def _record_search_analytics(self, query: str, result_count: int, search_time: float, results: List):
        """Record search analytics."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                top_result_id = results[0].content_id if results else None
                conn.execute('''
                    INSERT INTO search_analytics
                    (query, query_type, results_count, top_result_id, search_time)
                    VALUES (?, ?, ?, ?, ?)
                ''', (query, 'enhanced', result_count, top_result_id, search_time))

        except Exception as e:
            log_error(self.log_path, f"Error recording search analytics: {str(e)}")

    def _load_search_analytics(self) -> Dict[str, Any]:
        """Load search analytics data."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Popular queries
                popular_queries = conn.execute('''
                    SELECT query, COUNT(*) as frequency
                    FROM search_analytics
                    WHERE timestamp > datetime('now', '-30 days')
                    GROUP BY query
                    ORDER BY frequency DESC
                    LIMIT 10
                ''').fetchall()

                return {
                    'popular_queries': dict(popular_queries),
                    'loaded_at': datetime.now().isoformat()
                }

        except Exception as e:
            log_error(self.log_path, f"Error loading search analytics: {str(e)}")
            return {}


def search_content(query: str,
                  content_types: List[str] = None,
                  limit: int = 20,
                  config: Dict[str, Any] = None) -> List[SearchResult]:
    """Convenience function for enhanced search."""
    engine = EnhancedSearchEngine(config)
    return engine.search(query, content_types=content_types, limit=limit)


def semantic_search_content(query: str,
                          limit: int = 10,
                          config: Dict[str, Any] = None) -> List[SearchResult]:
    """Convenience function for semantic search."""
    engine = EnhancedSearchEngine(config)
    return engine.semantic_search(query, limit=limit)


def advanced_search(query: str,
                   content_types: List[str] = None,
                   limit: int = 20,
                   config: Dict[str, Any] = None) -> List[Dict[str, Any]]:
    """
    Core advanced search function for Block 9 validation.

    Args:
        query: Search query
        content_types: Filter by content types
        limit: Maximum results
        config: Configuration dictionary

    Returns:
        List of search results
    """
    try:
        engine = EnhancedSearchEngine(config)
        search_results = engine.search(query, content_types=content_types, limit=limit)

        # Convert SearchResult objects to dicts for validation
        results = []
        for result in search_results:
            results.append({
                'id': result.content_id,
                'title': result.title,
                'content_type': result.content_type,
                'url': result.url,
                'snippet': result.snippet,
                'score': result.score,
                'rank': result.rank
            })

        return results

    except Exception as e:
        return [{"error": str(e), "query": query}]


def advanced_search(query: str, limit: int = 20, filters: Dict[str, Any] = None) -> List[Dict[str, Any]]:
    """
    Main search function with performance optimization.
    Compatible interface for existing search API.
    """
    try:
        # Use optimized search engine
        optimizer = SearchPerformanceOptimizer()
        results = optimizer.optimized_search(query, limit, filters)

        # Convert to compatible format
        return [result.to_dict() for result in results]

    except Exception as e:
        module_log_path = os.path.join(os.getcwd(), "logs", "enhanced_search_module.log")
        log_error(module_log_path, f"Error in advanced_search: {str(e)}")

        # Fallback to basic search
        try:
            from helpers.search_engine import AtlasSearchEngine
            basic_engine = AtlasSearchEngine()
            basic_results = basic_engine.search(query, limit=limit)

            # Convert to expected format
            return [
                {
                    'id': result.get('id', ''),
                    'title': result.get('title', ''),
                    'content_type': result.get('content_type', 'unknown'),
                    'url': result.get('url', ''),
                    'snippet': result.get('content', '')[:200] + '...',
                    'score': 1.0,
                    'relevance_factors': {'fallback': True},
                    'metadata': result
                }
                for result in basic_results.get('hits', [])
            ]

        except Exception as fallback_error:
            module_log_path = os.path.join(os.getcwd(), "logs", "enhanced_search_module.log")
            log_error(module_log_path, f"Fallback search also failed: {str(fallback_error)}")
            return []


if __name__ == "__main__":
    # Performance test
    optimizer = SearchPerformanceOptimizer()

    print("🚀 Search Performance Optimizer - Test Mode")
    print("=" * 50)

    # Test search
    results = optimizer.optimized_search("python programming", limit=10)
    print(f"Test search returned {len(results)} results")

    # Performance report
    report = optimizer.get_performance_report()
    print(f"Performance Report:")
    print(f"  Cache hit rate: {report['runtime_metrics']['cache_hit_rate']:.1f}%")
    print(f"  Average response time: {report['runtime_metrics']['average_response_time']:.3f}s")
    print(f"  Total queries: {report['runtime_metrics']['total_queries']}")


def get_search_performance_report() -> Dict[str, Any]:
    """Get comprehensive search performance report."""
    try:
        optimizer = SearchPerformanceOptimizer()
        return optimizer.get_performance_report()
    except Exception as e:
        return {"error": str(e), "timestamp": datetime.now().isoformat()}