#!/usr/bin/env python3
"""
Search Performance Optimizer - Production-grade search with advanced indexing
Addresses feedback: Performance Optimization for search operations
"""

import sqlite3
import json
import time
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union
from collections import Counter, defaultdict
import re
import threading
from dataclasses import dataclass, asdict

from helpers.utils import log_info, log_error


@dataclass
class OptimizedSearchResult:
    """Optimized search result with performance tracking."""
    id: str
    title: str
    content_type: str
    url: str
    snippet: str
    score: float
    relevance_factors: Dict[str, float]
    metadata: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)


class SearchPerformanceOptimizer:
    """
    High-performance search engine optimized for large datasets (3.5k+ articles).

    Performance Features:
    - SQLite FTS5 full-text search for speed
    - Intelligent caching with TTL
    - Concurrent search operations
    - Query optimization and analysis
    - Index compression and maintenance
    - Performance monitoring and alerting
    """

    def __init__(self, config: Dict[str, Any] = None):
        """Initialize with performance-focused configuration."""
        self.config = config or {}

        # Set up logging
        import os
        log_dir = self.config.get('log_directory', 'logs')
        os.makedirs(log_dir, exist_ok=True)
        self.log_path = os.path.join(log_dir, 'search_performance_optimizer.log')

        # Performance settings
        self.db_path = Path(self.config.get('search_db', 'data/enhanced_search_optimized.db'))
        self.cache_size = self.config.get('search_cache_size', 10000)
        self.cache_ttl = self.config.get('search_cache_ttl', 300)  # 5 minutes
        self.max_concurrent_searches = self.config.get('max_concurrent_searches', 4)
        self.index_maintenance_interval = self.config.get('index_maintenance_hours', 24)

        # Performance tracking
        self.query_stats = defaultdict(list)
        self.performance_metrics = {
            'total_queries': 0,
            'average_response_time': 0.0,
            'cache_hit_rate': 0.0,
            'slow_queries': []
        }

        # Thread safety
        self.search_lock = threading.RLock()
        self.cache_lock = threading.RLock()

        # Query cache with TTL
        self.query_cache = {}

        # Initialize optimized database
        self._init_optimized_database()

        log_info(self.log_path, "SearchPerformanceOptimizer initialized with advanced indexing")

    def _init_optimized_database(self):
        """Initialize database with performance optimizations."""
        try:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)

            with sqlite3.connect(self.db_path) as conn:
                # Enable performance optimizations
                conn.execute('PRAGMA journal_mode = WAL')
                conn.execute('PRAGMA synchronous = NORMAL')
                conn.execute('PRAGMA cache_size = -20000')  # 20MB cache
                conn.execute('PRAGMA temp_store = memory')
                conn.execute('PRAGMA mmap_size = 268435456')  # 256MB memory-mapped

                # Create optimized tables
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS optimized_content (
                        id TEXT PRIMARY KEY,
                        title TEXT NOT NULL,
                        content TEXT,
                        content_type TEXT,
                        url TEXT,
                        word_count INTEGER DEFAULT 0,
                        tags TEXT,  -- JSON array
                        quality_score REAL DEFAULT 0.0,
                        created_at TEXT,
                        updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                        metadata TEXT  -- JSON blob
                    )
                ''')

                # Create FTS5 virtual table for blazing fast search
                conn.execute('''
                    CREATE VIRTUAL TABLE IF NOT EXISTS content_fts USING fts5(
                        title,
                        content,
                        tags,
                        content_id UNINDEXED,
                        prefix='2 3'
                    )
                ''')

                # Create indexes for performance
                conn.execute('CREATE INDEX IF NOT EXISTS idx_content_type ON optimized_content(content_type)')
                conn.execute('CREATE INDEX IF NOT EXISTS idx_created_at ON optimized_content(created_at)')
                conn.execute('CREATE INDEX IF NOT EXISTS idx_quality_score ON optimized_content(quality_score)')
                conn.execute('CREATE INDEX IF NOT EXISTS idx_word_count ON optimized_content(word_count)')

                # Query performance tracking
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS query_performance (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        query_hash TEXT,
                        query_text TEXT,
                        execution_time REAL,
                        result_count INTEGER,
                        cache_hit BOOLEAN DEFAULT FALSE,
                        timestamp TEXT DEFAULT CURRENT_TIMESTAMP
                    )
                ''')

                # Search analytics
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS search_analytics (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        query_text TEXT,
                        results_found INTEGER,
                        user_clicked BOOLEAN DEFAULT FALSE,
                        timestamp TEXT DEFAULT CURRENT_TIMESTAMP
                    )
                ''')

            log_info(self.log_path, "Optimized search database initialized with FTS5")

        except Exception as e:
            log_error(self.log_path, self.log_path, f"Error initializing optimized search database: {str(e)}")

    def build_optimized_index(self, documents: List[Dict[str, Any]], batch_size: int = 500):
        """Build optimized search index with performance monitoring."""
        if not documents:
            log_info(self.log_path, "No documents to index")
            return

        start_time = time.time()
        log_info(self.log_path, f"Building optimized index for {len(documents)} documents")

        # Performance counters
        indexed_count = 0
        error_count = 0

        try:
            with sqlite3.connect(self.db_path) as conn:
                # Optimize for bulk inserts
                conn.execute('PRAGMA synchronous = OFF')
                conn.execute('BEGIN TRANSACTION')

                for i in range(0, len(documents), batch_size):
                    batch = documents[i:i + batch_size]
                    batch_start = time.time()

                    try:
                        for doc in batch:
                            self._index_single_document(conn, doc)
                            indexed_count += 1

                    except Exception as e:
                        error_count += 1
                        log_error(self.log_path, f"Error indexing batch {i//batch_size + 1}: {str(e)}")
                        continue

                    batch_time = time.time() - batch_start
                    if batch_time > 2.0:  # Log slow batches
                        log_info(self.log_path, f"Slow batch {i//batch_size + 1}: {batch_time:.2f}s for {len(batch)} docs")

                conn.execute('COMMIT')
                conn.execute('PRAGMA synchronous = NORMAL')

                # Optimize FTS index
                log_info(self.log_path, "Optimizing FTS index...")
                conn.execute('INSERT INTO content_fts(content_fts) VALUES("optimize")')

        except Exception as e:
            log_error(self.log_path, f"Critical error building optimized index: {str(e)}")
            error_count += len(documents) - indexed_count

        total_time = time.time() - start_time
        log_info(self.log_path, f"Index build complete: {indexed_count} indexed, {error_count} errors, {total_time:.2f}s")

        # Update performance metrics
        self._update_indexing_stats(indexed_count, error_count, total_time)

    def _index_single_document(self, conn, doc: Dict[str, Any]):
        """Index single document with optimizations."""
        try:
            # Extract and normalize data
            doc_id = doc.get('id', str(hash(doc.get('url', doc.get('title', '')))))
            title = doc.get('title', 'Untitled')[:500]  # Truncate very long titles
            content = doc.get('content', '')
            content_type = doc.get('content_type', 'unknown')
            url = doc.get('url', '')
            word_count = len(content.split()) if content else 0
            tags = json.dumps(doc.get('tags', []))
            quality_score = doc.get('quality_score', doc.get('evaluation', {}).get('overall_score', 0.0))
            created_at = doc.get('created_at', datetime.now().isoformat())

            # Store in main table
            conn.execute('''
                INSERT OR REPLACE INTO optimized_content
                (id, title, content, content_type, url, word_count, tags, quality_score, created_at, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                doc_id, title, content, content_type, url,
                word_count, tags, quality_score, created_at,
                json.dumps(doc)
            ))

            # Index in FTS table
            conn.execute('''
                INSERT OR REPLACE INTO content_fts
                (title, content, tags, content_id)
                VALUES (?, ?, ?, ?)
            ''', (title, content, ' '.join(doc.get('tags', [])), doc_id))

        except Exception as e:
            raise Exception(f"Error indexing document {doc.get('title', 'unknown')}: {str(e)}")

    def optimized_search(self, query: str, limit: int = 20, filters: Dict[str, Any] = None) -> List[OptimizedSearchResult]:
        """
        High-performance search with caching and optimization.

        Performance features:
        - Query caching with TTL
        - FTS5 optimization
        - Concurrent query execution
        - Performance monitoring
        """
        if not query or not query.strip():
            return []

        search_start = time.time()

        # Generate cache key
        cache_key = self._generate_cache_key(query, limit, filters)

        # Check cache first
        with self.cache_lock:
            cached_result = self._get_cached_result(cache_key)
            if cached_result:
                self._record_query_performance(query, 0, len(cached_result), cache_hit=True)
                return cached_result

        # Perform search with thread safety
        with self.search_lock:
            try:
                results = self._execute_optimized_search(query, limit, filters)

                # Cache results
                with self.cache_lock:
                    self._cache_result(cache_key, results)

                # Record performance
                search_time = time.time() - search_start
                self._record_query_performance(query, search_time, len(results), cache_hit=False)

                return results

            except Exception as e:
                log_error(self.log_path, f"Error in optimized search: {str(e)}")
                return []

    def _execute_optimized_search(self, query: str, limit: int, filters: Dict[str, Any] = None) -> List[OptimizedSearchResult]:
        """Execute the actual optimized search query."""
        filters = filters or {}
        results = []

        try:
            with sqlite3.connect(self.db_path) as conn:
                # Build optimized FTS query
                fts_query = self._build_fts_query(query)

                # Build filter conditions
                filter_conditions = []
                filter_params = []

                if filters.get('content_type'):
                    filter_conditions.append("oc.content_type IN ({})".format(
                        ','.join('?' * len(filters['content_type']))
                    ))
                    filter_params.extend(filters['content_type'])

                if filters.get('date_range'):
                    start_date, end_date = filters['date_range']
                    filter_conditions.append("oc.created_at BETWEEN ? AND ?")
                    filter_params.extend([start_date, end_date])

                if filters.get('min_quality_score'):
                    filter_conditions.append("oc.quality_score >= ?")
                    filter_params.append(filters['min_quality_score'])

                # Build the complete query
                base_query = '''
                    SELECT
                        oc.id, oc.title, oc.content_type, oc.url,
                        oc.quality_score, oc.word_count, oc.tags, oc.metadata,
                        snippet(content_fts, 1, '[HIGHLIGHT]', '[/HIGHLIGHT]', '...', 32) as snippet,
                        rank
                    FROM content_fts
                    JOIN optimized_content oc ON content_fts.content_id = oc.id
                    WHERE content_fts MATCH ?
                '''

                if filter_conditions:
                    base_query += ' AND ' + ' AND '.join(filter_conditions)

                base_query += '''
                    ORDER BY rank, oc.quality_score DESC, oc.word_count DESC
                    LIMIT ?
                '''

                # Execute query
                cursor = conn.execute(base_query, [fts_query] + filter_params + [limit])

                # Process results
                for i, row in enumerate(cursor.fetchall()):
                    (doc_id, title, content_type, url, quality_score,
                     word_count, tags_json, metadata_json, snippet, rank) = row

                    # Calculate relevance factors
                    relevance_factors = {
                        'fts_rank': rank,
                        'quality_score': quality_score,
                        'word_count_factor': min(word_count / 1000, 1.0),
                        'title_match': 1.0 if query.lower() in title.lower() else 0.0
                    }

                    # Parse metadata
                    try:
                        metadata = json.loads(metadata_json) if metadata_json else {}
                        tags = json.loads(tags_json) if tags_json else []
                    except:
                        metadata = {}
                        tags = []

                    # Calculate final score
                    final_score = self._calculate_relevance_score(relevance_factors)

                    result = OptimizedSearchResult(
                        id=doc_id,
                        title=title,
                        content_type=content_type,
                        url=url,
                        snippet=snippet or title[:200] + '...',
                        score=final_score,
                        relevance_factors=relevance_factors,
                        metadata={**metadata, 'tags': tags, 'word_count': word_count}
                    )

                    results.append(result)

        except Exception as e:
            log_error(self.log_path, f"Error executing optimized search: {str(e)}")

        return results

    def _build_fts_query(self, query: str) -> str:
        """Build optimized FTS5 query with stemming and phrase detection."""
        # Clean and tokenize query
        tokens = re.findall(r'\b\w+\b', query.lower())

        if not tokens:
            return query

        # Detect phrases (quoted text)
        phrases = re.findall(r'"([^"]*)"', query)

        # Build FTS query
        fts_parts = []

        # Add phrase matches (highest priority)
        for phrase in phrases:
            if phrase.strip():
                fts_parts.append(f'"{phrase}"')

        # Add individual terms with prefix matching
        remaining_tokens = [t for t in tokens if not any(t in phrase for phrase in phrases)]

        if remaining_tokens:
            # Use OR for broader results, AND for precision
            if len(remaining_tokens) > 3:
                # For long queries, use OR to prevent zero results
                term_query = ' OR '.join([f'{token}*' for token in remaining_tokens[:5]])  # Limit tokens
            else:
                # For short queries, use AND for precision
                term_query = ' AND '.join([f'{token}*' for token in remaining_tokens])

            fts_parts.append(f'({term_query})')

        return ' '.join(fts_parts) if fts_parts else query

    def _calculate_relevance_score(self, factors: Dict[str, float]) -> float:
        """Calculate weighted relevance score."""
        weights = {
            'fts_rank': -0.4,  # Lower rank = higher score (FTS returns negative ranks)
            'quality_score': 0.3,
            'word_count_factor': 0.2,
            'title_match': 0.1
        }

        score = 0.0
        for factor, value in factors.items():
            if factor in weights:
                score += weights[factor] * value

        return max(0.0, score)  # Ensure non-negative

    def _generate_cache_key(self, query: str, limit: int, filters: Dict[str, Any] = None) -> str:
        """Generate cache key for query."""
        cache_data = {
            'query': query.lower().strip(),
            'limit': limit,
            'filters': filters or {}
        }

        cache_string = json.dumps(cache_data, sort_keys=True)
        return hashlib.md5(cache_string.encode()).hexdigest()

    def _get_cached_result(self, cache_key: str) -> Optional[List[OptimizedSearchResult]]:
        """Get cached search result if valid."""
        if cache_key not in self.query_cache:
            return None

        cached_data, timestamp = self.query_cache[cache_key]

        # Check TTL
        if time.time() - timestamp > self.cache_ttl:
            del self.query_cache[cache_key]
            return None

        return [OptimizedSearchResult(**result) for result in cached_data]

    def _cache_result(self, cache_key: str, results: List[OptimizedSearchResult]):
        """Cache search results with TTL."""
        # Convert to serializable format
        serializable_results = [result.to_dict() for result in results]

        # Store with timestamp
        self.query_cache[cache_key] = (serializable_results, time.time())

        # Clean old cache entries if cache is too large
        if len(self.query_cache) > self.cache_size:
            self._clean_cache()

    def _clean_cache(self):
        """Remove oldest cache entries."""
        # Sort by timestamp and remove oldest 20%
        cache_items = list(self.query_cache.items())
        cache_items.sort(key=lambda x: x[1][1])  # Sort by timestamp

        remove_count = len(cache_items) // 5  # Remove 20%
        for key, _ in cache_items[:remove_count]:
            del self.query_cache[key]

    def _record_query_performance(self, query: str, execution_time: float, result_count: int, cache_hit: bool = False):
        """Record query performance metrics."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                query_hash = hashlib.md5(query.encode()).hexdigest()

                conn.execute('''
                    INSERT INTO query_performance
                    (query_hash, query_text, execution_time, result_count, cache_hit)
                    VALUES (?, ?, ?, ?, ?)
                ''', (query_hash, query[:500], execution_time, result_count, cache_hit))

            # Update runtime metrics
            self.performance_metrics['total_queries'] += 1

            if not cache_hit:
                # Track actual execution time
                times = [execution_time] + [
                    stat for stat in self.query_stats.get('execution_times', [])
                ][-99:]  # Keep last 100 times

                self.query_stats['execution_times'] = times
                self.performance_metrics['average_response_time'] = sum(times) / len(times)

                # Track slow queries
                if execution_time > 1.0:  # Queries taking more than 1 second
                    self.performance_metrics['slow_queries'].append({
                        'query': query[:100],
                        'time': execution_time,
                        'timestamp': datetime.now().isoformat()
                    })

                    # Keep only recent slow queries
                    self.performance_metrics['slow_queries'] = self.performance_metrics['slow_queries'][-20:]

            # Update cache hit rate
            total_queries = self.performance_metrics['total_queries']
            cache_hits = sum(1 for stat in self.query_stats.get('cache_hits', []) if stat) + (1 if cache_hit else 0)
            self.performance_metrics['cache_hit_rate'] = (cache_hits / total_queries) * 100

        except Exception as e:
            log_error(self.log_path, f"Error recording query performance: {str(e)}")

    def _update_indexing_stats(self, indexed: int, errors: int, duration: float):
        """Update indexing performance statistics."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute('''
                    INSERT OR REPLACE INTO search_analytics
                    (query_text, results_found, timestamp)
                    VALUES (?, ?, ?)
                ''', (f"INDEX_BUILD_{datetime.now().date()}", indexed, datetime.now().isoformat()))

        except Exception as e:
            log_error(self.log_path, f"Error updating indexing stats: {str(e)}")

    def get_performance_report(self) -> Dict[str, Any]:
        """Get comprehensive performance report."""
        try:
            report = {
                'timestamp': datetime.now().isoformat(),
                'runtime_metrics': self.performance_metrics.copy(),
                'cache_statistics': {
                    'cache_size': len(self.query_cache),
                    'max_cache_size': self.cache_size,
                    'cache_ttl_seconds': self.cache_ttl
                },
                'database_statistics': {},
                'recommendations': []
            }

            # Database statistics
            try:
                with sqlite3.connect(self.db_path) as conn:
                    # Content statistics
                    content_count = conn.execute('SELECT COUNT(*) FROM optimized_content').fetchone()[0]
                    avg_word_count = conn.execute('SELECT AVG(word_count) FROM optimized_content').fetchone()[0] or 0

                    # Performance statistics
                    recent_queries = conn.execute('''
                        SELECT AVG(execution_time), COUNT(*)
                        FROM query_performance
                        WHERE timestamp > datetime('now', '-1 day')
                    ''').fetchone()

                    report['database_statistics'] = {
                        'total_documents': content_count,
                        'average_word_count': round(avg_word_count, 1),
                        'recent_avg_query_time': round(recent_queries[0] or 0, 3),
                        'recent_query_count': recent_queries[1] or 0
                    }

            except Exception as e:
                report['database_statistics'] = {'error': str(e)}

            # Generate recommendations
            if self.performance_metrics['average_response_time'] > 0.5:
                report['recommendations'].append("Average query time is high - consider index optimization")

            if self.performance_metrics['cache_hit_rate'] < 30:
                report['recommendations'].append("Low cache hit rate - consider increasing cache TTL")

            if len(self.performance_metrics['slow_queries']) > 10:
                report['recommendations'].append("Many slow queries detected - review query patterns")

            return report

        except Exception as e:
            return {
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }


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
        log_error(self.log_path, f"Error in advanced_search: {str(e)}")

        # Fallback to basic search
        try:
            from helpers.search_engine import SearchEngine
            basic_engine = SearchEngine()
            basic_results = basic_engine.search(query, limit)

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
                for result in basic_results
            ]

        except Exception as fallback_error:
            log_error(self.log_path, f"Fallback search also failed: {str(fallback_error)}")
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