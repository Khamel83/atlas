#!/usr/bin/env python3
"""
Production Optimizer - Phase C1
Performance optimization, caching, and database indexing for production deployment.
"""

import os
import sqlite3
import json
import time
import logging
import psutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional
import threading
from functools import lru_cache

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ProductionOptimizer:
    """Production-level performance optimizations."""

    def __init__(self, config: Dict[str, Any] = None):
        """Initialize production optimizer."""
        self.config = config or {}
        self.main_db = self.config.get('main_db', 'data/atlas.db')
        self.cache_dir = Path(self.config.get('cache_dir', 'data/cache'))
        self.cache_dir.mkdir(exist_ok=True)

        # Performance monitoring
        self.performance_stats = {
            'query_times': [],
            'cache_hits': 0,
            'cache_misses': 0,
            'memory_usage': [],
            'startup_time': time.time()
        }

        # In-memory cache
        self._memory_cache = {}
        self._cache_timestamps = {}
        self.cache_ttl = self.config.get('cache_ttl_seconds', 3600)  # 1 hour

        # Lock for thread safety
        self._cache_lock = threading.RLock()

    def optimize_database_performance(self) -> Dict[str, Any]:
        """Optimize database performance with indexes and query optimization."""
        logger.info("🚀 Optimizing database performance...")

        optimizations = {
            'indexes_created': 0,
            'queries_analyzed': 0,
            'vacuum_completed': False,
            'pragma_settings': {},
            'performance_improvement': {}
        }

        try:
            if not os.path.exists(self.main_db):
                return {'error': 'Database not found'}

            conn = sqlite3.connect(self.main_db)
            cursor = conn.cursor()

            # Analyze current performance
            before_stats = self._analyze_database_performance(cursor)

            # 1. Create performance indexes
            indexes_to_create = [
                # Content table indexes
                ("idx_content_created_at", "CREATE INDEX IF NOT EXISTS idx_content_created_at ON content (created_at DESC)"),
                ("idx_content_type", "CREATE INDEX IF NOT EXISTS idx_content_type ON content (content_type)"),
                ("idx_content_url", "CREATE INDEX IF NOT EXISTS idx_content_url ON content (url)"),
                ("idx_content_title_fts", "CREATE INDEX IF NOT EXISTS idx_content_title_fts ON content (title)"),

                # Composite indexes for common queries
                ("idx_content_type_created", "CREATE INDEX IF NOT EXISTS idx_content_type_created ON content (content_type, created_at DESC)"),
                ("idx_content_length", "CREATE INDEX IF NOT EXISTS idx_content_length ON content (LENGTH(content))"),

                # JSON metadata indexes (if supported)
                ("idx_domain", "CREATE INDEX IF NOT EXISTS idx_domain ON content (json_extract(metadata, '$.domain'))"),
                ("idx_word_count", "CREATE INDEX IF NOT EXISTS idx_word_count ON content (json_extract(metadata, '$.word_count'))"),
            ]

            for index_name, index_sql in indexes_to_create:
                try:
                    cursor.execute(index_sql)
                    optimizations['indexes_created'] += 1
                    logger.info(f"   ✅ Created index: {index_name}")
                except Exception as e:
                    logger.warning(f"   ⚠️ Failed to create {index_name}: {e}")

            # 2. Optimize SQLite settings
            pragma_settings = [
                ("journal_mode", "WAL"),  # Better concurrency
                ("synchronous", "NORMAL"),  # Faster writes
                ("cache_size", "-64000"),  # 64MB cache
                ("temp_store", "MEMORY"),  # Memory temp tables
                ("mmap_size", "268435456"),  # 256MB memory map
                ("optimize", None),  # Optimize database
            ]

            for pragma, value in pragma_settings:
                try:
                    if value:
                        cursor.execute(f"PRAGMA {pragma} = {value}")
                    else:
                        cursor.execute(f"PRAGMA {pragma}")

                    # Get current setting
                    cursor.execute(f"PRAGMA {pragma}")
                    result = cursor.fetchone()
                    optimizations['pragma_settings'][pragma] = result[0] if result else 'set'

                except Exception as e:
                    logger.warning(f"   ⚠️ Failed to set PRAGMA {pragma}: {e}")

            # 3. Update table statistics
            try:
                cursor.execute("ANALYZE")
                logger.info("   ✅ Updated table statistics")
            except Exception as e:
                logger.warning(f"   ⚠️ Failed to analyze: {e}")

            # 4. Vacuum database (compact)
            try:
                cursor.execute("VACUUM")
                optimizations['vacuum_completed'] = True
                logger.info("   ✅ Database compacted")
            except Exception as e:
                logger.warning(f"   ⚠️ Failed to vacuum: {e}")

            conn.commit()

            # Analyze performance after optimization
            after_stats = self._analyze_database_performance(cursor)

            # Calculate improvement
            if before_stats and after_stats:
                optimizations['performance_improvement'] = {
                    'query_time_improvement': f"{((before_stats.get('avg_query_time', 1) - after_stats.get('avg_query_time', 1)) / before_stats.get('avg_query_time', 1) * 100):.1f}%",
                    'database_size_before': before_stats.get('database_size', 0),
                    'database_size_after': after_stats.get('database_size', 0)
                }

            conn.close()

            logger.info(f"   ✅ Database optimization complete: {optimizations['indexes_created']} indexes created")
            return optimizations

        except Exception as e:
            logger.error(f"Database optimization failed: {e}")
            return {'error': str(e)}

    def _analyze_database_performance(self, cursor) -> Dict[str, Any]:
        """Analyze database performance metrics."""
        try:
            stats = {}

            # Database size
            cursor.execute("SELECT page_count * page_size as size FROM pragma_page_count(), pragma_page_size()")
            result = cursor.fetchone()
            if result:
                stats['database_size'] = result[0]

            # Table counts
            cursor.execute("SELECT COUNT(*) FROM content")
            stats['content_count'] = cursor.fetchone()[0]

            # Sample query performance
            start_time = time.time()
            cursor.execute("SELECT COUNT(*) FROM content WHERE created_at > datetime('now', '-30 days')")
            query_time = time.time() - start_time
            stats['avg_query_time'] = query_time

            return stats

        except Exception as e:
            logger.error(f"Performance analysis failed: {e}")
            return {}

    def implement_response_caching(self) -> Dict[str, Any]:
        """Implement response caching for expensive operations."""
        logger.info("🗄️ Implementing response caching...")

        cache_stats = {
            'cache_enabled': True,
            'cache_directory': str(self.cache_dir),
            'cache_policies': {},
            'cache_size_mb': 0
        }

        try:
            # Cache policies for different operations
            self.cache_policies = {
                'search_results': {'ttl': 300, 'max_size': 100},  # 5 minutes
                'content_analytics': {'ttl': 1800, 'max_size': 50},  # 30 minutes
                'knowledge_graph': {'ttl': 3600, 'max_size': 10},  # 1 hour
                'recommendations': {'ttl': 1800, 'max_size': 20},  # 30 minutes
                'tf_idf_vectors': {'ttl': 86400, 'max_size': 5},  # 24 hours
            }

            cache_stats['cache_policies'] = self.cache_policies

            # Clear old cache files
            self._clean_cache_directory()

            # Calculate current cache size
            cache_size = sum(f.stat().st_size for f in self.cache_dir.rglob('*') if f.is_file())
            cache_stats['cache_size_mb'] = round(cache_size / (1024 * 1024), 2)

            logger.info(f"   ✅ Cache system initialized: {cache_stats['cache_size_mb']} MB")
            return cache_stats

        except Exception as e:
            logger.error(f"Cache implementation failed: {e}")
            return {'error': str(e)}

    def _clean_cache_directory(self):
        """Clean expired cache files."""
        try:
            current_time = time.time()
            cleaned_count = 0

            for cache_file in self.cache_dir.rglob('*.json'):
                # Check file age
                file_age = current_time - cache_file.stat().st_mtime

                # Extract cache type from filename
                cache_type = cache_file.stem.split('_')[0] if '_' in cache_file.stem else 'default'
                max_age = self.cache_policies.get(cache_type, {}).get('ttl', 3600)

                if file_age > max_age:
                    cache_file.unlink()
                    cleaned_count += 1

            if cleaned_count > 0:
                logger.info(f"   🧹 Cleaned {cleaned_count} expired cache files")

        except Exception as e:
            logger.warning(f"Cache cleanup failed: {e}")

    @lru_cache(maxsize=128)
    def get_cached_response(self, cache_key: str, operation_type: str = 'default') -> Optional[Any]:
        """Get cached response with thread safety."""
        with self._cache_lock:
            try:
                # Check in-memory cache first
                if cache_key in self._memory_cache:
                    cache_time = self._cache_timestamps.get(cache_key, 0)
                    if time.time() - cache_time < self.cache_ttl:
                        self.performance_stats['cache_hits'] += 1
                        return self._memory_cache[cache_key]
                    else:
                        # Expired, remove from memory
                        del self._memory_cache[cache_key]
                        del self._cache_timestamps[cache_key]

                # Check file cache
                cache_file = self.cache_dir / f"{operation_type}_{hash(cache_key) % 10000}.json"

                if cache_file.exists():
                    file_age = time.time() - cache_file.stat().st_mtime
                    max_age = self.cache_policies.get(operation_type, {}).get('ttl', 3600)

                    if file_age < max_age:
                        with open(cache_file, 'r') as f:
                            data = json.load(f)

                        # Store in memory cache
                        self._memory_cache[cache_key] = data
                        self._cache_timestamps[cache_key] = time.time()

                        self.performance_stats['cache_hits'] += 1
                        return data
                    else:
                        # Expired file cache
                        cache_file.unlink()

                self.performance_stats['cache_misses'] += 1
                return None

            except Exception as e:
                logger.error(f"Cache retrieval failed: {e}")
                self.performance_stats['cache_misses'] += 1
                return None

    def set_cached_response(self, cache_key: str, data: Any, operation_type: str = 'default'):
        """Set cached response with thread safety."""
        with self._cache_lock:
            try:
                # Store in memory cache
                self._memory_cache[cache_key] = data
                self._cache_timestamps[cache_key] = time.time()

                # Store in file cache for persistence
                cache_file = self.cache_dir / f"{operation_type}_{hash(cache_key) % 10000}.json"

                with open(cache_file, 'w') as f:
                    json.dump(data, f, indent=2, default=str)

            except Exception as e:
                logger.error(f"Cache storage failed: {e}")

    def optimize_memory_usage(self) -> Dict[str, Any]:
        """Optimize memory usage and monitor resource consumption."""
        logger.info("🧠 Optimizing memory usage...")

        memory_stats = {
            'before': {},
            'after': {},
            'optimizations_applied': []
        }

        try:
            # Get initial memory stats
            process = psutil.Process()
            memory_stats['before'] = {
                'memory_mb': round(process.memory_info().rss / 1024 / 1024, 2),
                'memory_percent': process.memory_percent(),
                'num_threads': process.num_threads()
            }

            # 1. Clear unused imports and variables
            import gc
            gc.collect()
            memory_stats['optimizations_applied'].append('garbage_collection')

            # 2. Optimize cache sizes
            max_memory_cache_items = 100
            if len(self._memory_cache) > max_memory_cache_items:
                # Remove oldest items
                sorted_cache = sorted(
                    self._cache_timestamps.items(),
                    key=lambda x: x[1]
                )

                items_to_remove = len(self._memory_cache) - max_memory_cache_items
                for cache_key, _ in sorted_cache[:items_to_remove]:
                    del self._memory_cache[cache_key]
                    del self._cache_timestamps[cache_key]

                memory_stats['optimizations_applied'].append(f'cache_cleanup_{items_to_remove}_items')

            # 3. Clear old performance stats
            if len(self.performance_stats['query_times']) > 1000:
                self.performance_stats['query_times'] = self.performance_stats['query_times'][-500:]
                memory_stats['optimizations_applied'].append('performance_stats_cleanup')

            if len(self.performance_stats['memory_usage']) > 100:
                self.performance_stats['memory_usage'] = self.performance_stats['memory_usage'][-50:]
                memory_stats['optimizations_applied'].append('memory_stats_cleanup')

            # 4. Force another garbage collection
            gc.collect()

            # Get final memory stats
            memory_stats['after'] = {
                'memory_mb': round(process.memory_info().rss / 1024 / 1024, 2),
                'memory_percent': process.memory_percent(),
                'num_threads': process.num_threads()
            }

            # Calculate improvement
            memory_saved = memory_stats['before']['memory_mb'] - memory_stats['after']['memory_mb']
            memory_stats['memory_saved_mb'] = round(memory_saved, 2)

            # Store current memory usage for monitoring
            self.performance_stats['memory_usage'].append({
                'timestamp': time.time(),
                'memory_mb': memory_stats['after']['memory_mb'],
                'memory_percent': memory_stats['after']['memory_percent']
            })

            logger.info(f"   ✅ Memory optimized: {memory_stats['memory_saved_mb']} MB saved")
            return memory_stats

        except Exception as e:
            logger.error(f"Memory optimization failed: {e}")
            return {'error': str(e)}

    def get_performance_report(self) -> Dict[str, Any]:
        """Generate comprehensive performance report."""
        try:
            process = psutil.Process()
            uptime = time.time() - self.performance_stats['startup_time']

            report = {
                'generated_at': datetime.now().isoformat(),
                'uptime_seconds': round(uptime, 1),
                'uptime_human': f"{uptime//3600:.0f}h {(uptime%3600)//60:.0f}m",
                'system_resources': {
                    'memory_mb': round(process.memory_info().rss / 1024 / 1024, 2),
                    'memory_percent': process.memory_percent(),
                    'cpu_percent': process.cpu_percent(),
                    'num_threads': process.num_threads(),
                    'num_files': process.num_fds() if hasattr(process, 'num_fds') else 'N/A'
                },
                'cache_performance': {
                    'cache_hits': self.performance_stats['cache_hits'],
                    'cache_misses': self.performance_stats['cache_misses'],
                    'hit_rate': round(
                        (self.performance_stats['cache_hits'] /
                         max(1, self.performance_stats['cache_hits'] + self.performance_stats['cache_misses'])) * 100, 1
                    ),
                    'memory_cache_size': len(self._memory_cache),
                    'cache_directory_size_mb': self._get_cache_directory_size()
                },
                'query_performance': {
                    'total_queries': len(self.performance_stats['query_times']),
                    'average_query_time_ms': round(
                        sum(self.performance_stats['query_times']) / max(1, len(self.performance_stats['query_times'])) * 1000, 2
                    ) if self.performance_stats['query_times'] else 0,
                    'recent_queries': self.performance_stats['query_times'][-10:] if self.performance_stats['query_times'] else []
                },
                'memory_trends': self.performance_stats['memory_usage'][-20:],  # Last 20 measurements
                'optimization_status': {
                    'database_optimized': os.path.exists(self.main_db),
                    'cache_enabled': True,
                    'memory_monitoring': True
                }
            }

            return report

        except Exception as e:
            logger.error(f"Performance report generation failed: {e}")
            return {'error': str(e)}

    def _get_cache_directory_size(self) -> float:
        """Get cache directory size in MB."""
        try:
            total_size = sum(f.stat().st_size for f in self.cache_dir.rglob('*') if f.is_file())
            return round(total_size / (1024 * 1024), 2)
        except:
            return 0.0

    def run_comprehensive_optimization(self) -> Dict[str, Any]:
        """Run all production optimizations."""
        logger.info("🚀 Running comprehensive production optimization...")

        optimization_results = {
            'started_at': datetime.now().isoformat(),
            'database_optimization': {},
            'caching_setup': {},
            'memory_optimization': {},
            'performance_report': {},
            'overall_status': 'unknown'
        }

        try:
            # 1. Database optimization
            optimization_results['database_optimization'] = self.optimize_database_performance()

            # 2. Response caching
            optimization_results['caching_setup'] = self.implement_response_caching()

            # 3. Memory optimization
            optimization_results['memory_optimization'] = self.optimize_memory_usage()

            # 4. Generate performance report
            optimization_results['performance_report'] = self.get_performance_report()

            # Determine overall status
            has_errors = any('error' in result for result in optimization_results.values() if isinstance(result, dict))
            optimization_results['overall_status'] = 'success' if not has_errors else 'partial_success'

            optimization_results['completed_at'] = datetime.now().isoformat()

            logger.info(f"   ✅ Comprehensive optimization complete: {optimization_results['overall_status']}")
            return optimization_results

        except Exception as e:
            logger.error(f"Comprehensive optimization failed: {e}")
            optimization_results['overall_status'] = 'failed'
            optimization_results['error'] = str(e)
            return optimization_results

def test_production_optimization():
    """Test production optimization features."""
    logger.info("🧪 Testing Production Optimization")

    optimizer = ProductionOptimizer()

    # Run comprehensive optimization
    results = optimizer.run_comprehensive_optimization()

    logger.info("📊 Optimization Results:")
    logger.info(f"   Overall status: {results['overall_status']}")
    logger.info(f"   Database indexes: {results['database_optimization'].get('indexes_created', 0)}")
    logger.info(f"   Cache size: {results['caching_setup'].get('cache_size_mb', 0)} MB")
    logger.info(f"   Memory usage: {results['performance_report'].get('system_resources', {}).get('memory_mb', 0)} MB")

if __name__ == "__main__":
    test_production_optimization()