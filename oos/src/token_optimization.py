#!/usr/bin/env python3
"""
Token Optimization System

Implements context engineering strategies to minimize token usage:
- Offloading to filesystem
- Context reduction and pruning
- Intelligent caching
- Efficient retrieval patterns
"""

import json
import asyncio
import hashlib
import pickle
import time
from typing import Dict, List, Any, Optional, Tuple, Union
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from pathlib import Path
import logging
import re
from collections import defaultdict


@dataclass
class TokenBudget:
    """Token budget configuration"""
    total_budget: int = 4000
    reserved_for_response: int = 1000
    available_for_context: int = 3000
    safety_margin: int = 200


@dataclass
class ContextChunk:
    """A chunk of context with metadata"""
    chunk_id: str
    content: str
    content_type: str  # 'code', 'documentation', 'conversation', 'metadata'
    importance: float  # 0.0 to 1.0
    staleness: float   # 0.0 (fresh) to 1.0 (stale)
    token_count: int
    created_at: datetime
    last_accessed: datetime
    access_count: int = 0
    tags: List[str] = None


@dataclass
class OptimizationResult:
    """Result of token optimization"""
    original_tokens: int
    optimized_tokens: int
    reduction_percentage: float
    techniques_used: List[str]
    chunks_offloaded: int
    chunks_compressed: int
    cache_hits: int


class TokenEstimator:
    """Estimates token count for various content types"""

    @staticmethod
    def estimate_tokens(text: str) -> int:
        """Estimate token count for text (rough approximation)"""
        if not text:
            return 0

        # Simple estimation: ~4 characters per token on average
        # This is a rough approximation - real tokenizers vary
        char_count = len(text)
        word_count = len(text.split())

        # Use whichever gives a higher estimate for safety
        char_estimate = char_count // 4
        word_estimate = int(word_count * 1.3)  # Account for punctuation, etc.

        return max(char_estimate, word_estimate)

    @staticmethod
    def estimate_code_tokens(code: str) -> int:
        """Estimate tokens for code (typically more tokens per character)"""
        if not code:
            return 0

        # Code typically has more tokens per character due to syntax
        char_count = len(code)
        return char_count // 3  # More conservative estimate for code

    @staticmethod
    def estimate_json_tokens(data: dict) -> int:
        """Estimate tokens for JSON data"""
        json_str = json.dumps(data, separators=(',', ':'))
        return TokenEstimator.estimate_tokens(json_str)


class ContextCompressor:
    """Compresses context while preserving essential information"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    async def compress_text(self, text: str, target_ratio: float = 0.7) -> str:
        """Compress text to target ratio of original length"""

        if not text or target_ratio >= 1.0:
            return text

        # Strategy 1: Remove redundant whitespace
        compressed = re.sub(r'\s+', ' ', text.strip())

        # Strategy 2: Remove common filler words in comments/docs
        if len(compressed) > len(text) * target_ratio:
            filler_words = ['basically', 'essentially', 'obviously', 'clearly',
                          'actually', 'really', 'quite', 'rather', 'very']
            for word in filler_words:
                compressed = re.sub(rf'\b{word}\b\s*', '', compressed, flags=re.IGNORECASE)

        # Strategy 3: Compress repetitive patterns
        if len(compressed) > len(text) * target_ratio:
            compressed = self._compress_repetitive_patterns(compressed)

        # Strategy 4: Truncate if still too long (preserve beginning and end)
        if len(compressed) > len(text) * target_ratio:
            target_length = int(len(text) * target_ratio)
            if target_length > 100:
                # Keep first 60% and last 40%
                first_part = compressed[:int(target_length * 0.6)]
                last_part = compressed[-int(target_length * 0.4):]
                compressed = first_part + " [...] " + last_part
            else:
                compressed = compressed[:target_length]

        return compressed

    def _compress_repetitive_patterns(self, text: str) -> str:
        """Compress repetitive patterns in text"""

        # Remove duplicate lines
        lines = text.split('\n')
        seen_lines = set()
        unique_lines = []

        for line in lines:
            stripped = line.strip()
            if stripped and stripped not in seen_lines:
                seen_lines.add(stripped)
                unique_lines.append(line)
            elif not stripped:  # Keep empty lines
                unique_lines.append(line)

        return '\n'.join(unique_lines)

    async def compress_code(self, code: str, target_ratio: float = 0.8) -> str:
        """Compress code while preserving functionality"""

        if not code or target_ratio >= 1.0:
            return code

        lines = code.split('\n')
        compressed_lines = []

        for line in lines:
            # Remove excessive comments but keep function docs
            if line.strip().startswith('#') and not line.strip().startswith('# TODO'):
                # Keep important comments
                if any(keyword in line.lower() for keyword in ['important', 'note', 'warning', 'todo']):
                    compressed_lines.append(line)
                elif len(compressed_lines) == 0 or not compressed_lines[-1].strip().startswith('#'):
                    # Keep first comment in a block
                    compressed_lines.append(line)
            else:
                compressed_lines.append(line)

        compressed = '\n'.join(compressed_lines)

        # Remove extra blank lines
        compressed = re.sub(r'\n\s*\n\s*\n', '\n\n', compressed)

        return compressed

    async def compress_json(self, data: dict, target_ratio: float = 0.7) -> dict:
        """Compress JSON data"""

        if target_ratio >= 1.0:
            return data

        compressed = {}

        for key, value in data.items():
            if isinstance(value, str) and len(value) > 100:
                # Compress long strings
                compressed[key] = await self.compress_text(value, target_ratio)
            elif isinstance(value, list) and len(value) > 10:
                # Truncate long lists, keeping first and last items
                target_length = max(3, int(len(value) * target_ratio))
                if target_length < len(value):
                    compressed[key] = value[:target_length//2] + ["..."] + value[-target_length//2:]
                else:
                    compressed[key] = value
            elif isinstance(value, dict):
                # Recursively compress nested objects
                compressed[key] = await self.compress_json(value, target_ratio)
            else:
                compressed[key] = value

        return compressed


class ContextCache:
    """Intelligent caching system for context chunks"""

    def __init__(self, cache_dir: Optional[str] = None):
        self.cache_dir = Path(cache_dir or Path.home() / ".oos" / "context_cache")
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        self.memory_cache = {}  # In-memory cache for hot data
        self.access_log = defaultdict(list)  # Track access patterns
        self.cache_stats = {"hits": 0, "misses": 0, "evictions": 0}

        self.logger = logging.getLogger(__name__)

    def _generate_cache_key(self, content: str, context_type: str = "") -> str:
        """Generate cache key for content"""
        content_hash = hashlib.sha256(f"{content}{context_type}".encode()).hexdigest()
        return f"{context_type}_{content_hash[:16]}"

    async def get(self, cache_key: str) -> Optional[ContextChunk]:
        """Get cached context chunk"""

        # Check memory cache first
        if cache_key in self.memory_cache:
            chunk = self.memory_cache[cache_key]
            chunk.access_count += 1
            chunk.last_accessed = datetime.now()
            self.cache_stats["hits"] += 1
            return chunk

        # Check disk cache
        cache_file = self.cache_dir / f"{cache_key}.pkl"
        if cache_file.exists():
            try:
                with open(cache_file, 'rb') as f:
                    chunk = pickle.load(f)

                chunk.access_count += 1
                chunk.last_accessed = datetime.now()

                # Promote to memory cache
                self.memory_cache[cache_key] = chunk
                self.cache_stats["hits"] += 1

                return chunk

            except Exception as e:
                self.logger.error(f"Failed to load cache file {cache_file}: {e}")

        self.cache_stats["misses"] += 1
        return None

    async def put(self, chunk: ContextChunk) -> str:
        """Cache a context chunk"""

        cache_key = self._generate_cache_key(chunk.content, chunk.content_type)

        # Store in memory cache
        self.memory_cache[cache_key] = chunk

        # Store on disk for persistence
        cache_file = self.cache_dir / f"{cache_key}.pkl"
        try:
            with open(cache_file, 'wb') as f:
                pickle.dump(chunk, f)
        except Exception as e:
            self.logger.error(f"Failed to save cache file {cache_file}: {e}")

        # Manage cache size
        await self._evict_if_needed()

        return cache_key

    async def _evict_if_needed(self):
        """Evict least recently used items if cache is too large"""

        max_memory_items = 100
        max_disk_items = 1000

        # Evict from memory cache
        if len(self.memory_cache) > max_memory_items:
            # Sort by last accessed time and access count
            items = list(self.memory_cache.items())
            items.sort(key=lambda x: (x[1].last_accessed, x[1].access_count))

            # Remove least recently used
            items_to_remove = items[:len(items) - max_memory_items]
            for cache_key, _ in items_to_remove:
                del self.memory_cache[cache_key]
                self.cache_stats["evictions"] += 1

        # Evict from disk cache
        cache_files = list(self.cache_dir.glob("*.pkl"))
        if len(cache_files) > max_disk_items:
            # Sort by modification time
            cache_files.sort(key=lambda f: f.stat().st_mtime)

            # Remove oldest files
            files_to_remove = cache_files[:len(cache_files) - max_disk_items]
            for file_path in files_to_remove:
                try:
                    file_path.unlink()
                except Exception as e:
                    self.logger.error(f"Failed to remove cache file {file_path}: {e}")

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        total_requests = self.cache_stats["hits"] + self.cache_stats["misses"]
        hit_rate = self.cache_stats["hits"] / total_requests if total_requests > 0 else 0

        return {
            "memory_cache_size": len(self.memory_cache),
            "disk_cache_size": len(list(self.cache_dir.glob("*.pkl"))),
            "cache_hits": self.cache_stats["hits"],
            "cache_misses": self.cache_stats["misses"],
            "cache_evictions": self.cache_stats["evictions"],
            "hit_rate": hit_rate
        }


class FilesystemOffloader:
    """Offloads context to filesystem for retrieval"""

    def __init__(self, storage_dir: Optional[str] = None):
        self.storage_dir = Path(storage_dir or Path.home() / ".oos" / "context_offload")
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.index_file = self.storage_dir / "index.json"
        self.index = self._load_index()
        self.logger = logging.getLogger(__name__)

    def _load_index(self) -> Dict[str, Any]:
        """Load offload index from disk"""
        if self.index_file.exists():
            try:
                return json.loads(self.index_file.read_text())
            except Exception as e:
                self.logger.error(f"Failed to load index: {e}")

        return {"chunks": {}, "metadata": {"created": datetime.now().isoformat()}}

    def _save_index(self):
        """Save offload index to disk"""
        try:
            self.index["metadata"]["updated"] = datetime.now().isoformat()
            self.index_file.write_text(json.dumps(self.index, indent=2))
        except Exception as e:
            self.logger.error(f"Failed to save index: {e}")

    async def offload_chunk(self, chunk: ContextChunk) -> str:
        """Offload context chunk to filesystem"""

        # Generate unique filename
        chunk_hash = hashlib.sha256(chunk.content.encode()).hexdigest()[:16]
        filename = f"{chunk.content_type}_{chunk_hash}.txt"
        file_path = self.storage_dir / filename

        # Save content to file
        file_path.write_text(chunk.content)

        # Update index
        self.index["chunks"][chunk.chunk_id] = {
            "filename": filename,
            "content_type": chunk.content_type,
            "importance": chunk.importance,
            "staleness": chunk.staleness,
            "token_count": chunk.token_count,
            "created_at": chunk.created_at.isoformat(),
            "last_accessed": chunk.last_accessed.isoformat(),
            "access_count": chunk.access_count,
            "tags": chunk.tags or []
        }

        self._save_index()
        return filename

    async def retrieve_chunk(self, chunk_id: str) -> Optional[ContextChunk]:
        """Retrieve offloaded context chunk"""

        if chunk_id not in self.index["chunks"]:
            return None

        chunk_info = self.index["chunks"][chunk_id]
        file_path = self.storage_dir / chunk_info["filename"]

        if not file_path.exists():
            # Remove from index if file is missing
            del self.index["chunks"][chunk_id]
            self._save_index()
            return None

        try:
            content = file_path.read_text()

            chunk = ContextChunk(
                chunk_id=chunk_id,
                content=content,
                content_type=chunk_info["content_type"],
                importance=chunk_info["importance"],
                staleness=chunk_info["staleness"],
                token_count=chunk_info["token_count"],
                created_at=datetime.fromisoformat(chunk_info["created_at"]),
                last_accessed=datetime.fromisoformat(chunk_info["last_accessed"]),
                access_count=chunk_info["access_count"],
                tags=chunk_info["tags"]
            )

            # Update access info
            chunk.last_accessed = datetime.now()
            chunk.access_count += 1

            # Update index
            self.index["chunks"][chunk_id]["last_accessed"] = chunk.last_accessed.isoformat()
            self.index["chunks"][chunk_id]["access_count"] = chunk.access_count
            self._save_index()

            return chunk

        except Exception as e:
            self.logger.error(f"Failed to retrieve chunk {chunk_id}: {e}")
            return None

    async def search_chunks(self, query: str, limit: int = 10) -> List[ContextChunk]:
        """Search offloaded chunks by content or tags"""

        matching_chunks = []
        query_lower = query.lower()

        for chunk_id, chunk_info in self.index["chunks"].items():
            # Search in tags
            if any(query_lower in tag.lower() for tag in chunk_info["tags"]):
                chunk = await self.retrieve_chunk(chunk_id)
                if chunk:
                    matching_chunks.append(chunk)

            # Search in content (load file to search)
            elif len(matching_chunks) < limit:
                file_path = self.storage_dir / chunk_info["filename"]
                if file_path.exists():
                    try:
                        content = file_path.read_text()
                        if query_lower in content.lower():
                            chunk = await self.retrieve_chunk(chunk_id)
                            if chunk:
                                matching_chunks.append(chunk)
                    except Exception:
                        continue

        # Sort by importance and recency
        matching_chunks.sort(
            key=lambda c: (c.importance, c.last_accessed),
            reverse=True
        )

        return matching_chunks[:limit]

    def get_offload_stats(self) -> Dict[str, Any]:
        """Get offload statistics"""
        return {
            "total_chunks": len(self.index["chunks"]),
            "storage_size_mb": sum(
                (self.storage_dir / info["filename"]).stat().st_size
                for info in self.index["chunks"].values()
                if (self.storage_dir / info["filename"]).exists()
            ) / (1024 * 1024),
            "content_types": defaultdict(int, {
                info["content_type"]: 1
                for info in self.index["chunks"].values()
            })
        }


class TokenOptimizer:
    """Main token optimization orchestrator"""

    def __init__(self):
        self.token_estimator = TokenEstimator()
        self.compressor = ContextCompressor()
        self.cache = ContextCache()
        self.offloader = FilesystemOffloader()
        self.logger = logging.getLogger(__name__)

    async def optimize_context(self, context: Dict[str, Any], budget: TokenBudget) -> Tuple[Dict[str, Any], OptimizationResult]:
        """Optimize context to fit within token budget"""

        original_tokens = self._calculate_total_tokens(context)

        if original_tokens <= budget.available_for_context:
            # No optimization needed
            return context, OptimizationResult(
                original_tokens=original_tokens,
                optimized_tokens=original_tokens,
                reduction_percentage=0.0,
                techniques_used=[],
                chunks_offloaded=0,
                chunks_compressed=0,
                cache_hits=0
            )

        # Start optimization
        optimized_context = context.copy()
        techniques_used = []
        chunks_offloaded = 0
        chunks_compressed = 0
        cache_hits = 0

        # Phase 1: Check cache for similar context
        cache_key = self.cache._generate_cache_key(str(context))
        cached_chunk = await self.cache.get(cache_key)

        if cached_chunk and cached_chunk.token_count <= budget.available_for_context:
            # Use cached optimized version
            try:
                optimized_context = json.loads(cached_chunk.content)
                cache_hits = 1
                techniques_used.append("cache_hit")
            except Exception:
                pass  # Fall through to normal optimization

        if cache_hits == 0:
            # Phase 2: Identify chunks for optimization
            chunks = self._identify_chunks(optimized_context)

            # Sort chunks by importance (least important first for offloading)
            chunks.sort(key=lambda c: (c.importance, -c.staleness))

            # Phase 3: Offload least important chunks
            current_tokens = original_tokens
            for chunk in chunks:
                if current_tokens <= budget.available_for_context:
                    break

                if chunk.importance < 0.5:  # Low importance threshold
                    # Offload to filesystem
                    await self.offloader.offload_chunk(chunk)

                    # Replace with reference
                    optimized_context = self._replace_chunk_with_reference(
                        optimized_context, chunk
                    )

                    current_tokens -= chunk.token_count
                    chunks_offloaded += 1
                    techniques_used.append("filesystem_offload")

            # Phase 4: Compress remaining chunks if still over budget
            current_tokens = self._calculate_total_tokens(optimized_context)

            if current_tokens > budget.available_for_context:
                compression_ratio = budget.available_for_context / current_tokens

                for key, value in list(optimized_context.items()):
                    if isinstance(value, str) and len(value) > 100:
                        compressed = await self.compressor.compress_text(value, compression_ratio)
                        if len(compressed) < len(value):
                            optimized_context[key] = compressed
                            chunks_compressed += 1

                    elif isinstance(value, dict):
                        compressed = await self.compressor.compress_json(value, compression_ratio)
                        if self.token_estimator.estimate_json_tokens(compressed) < \
                           self.token_estimator.estimate_json_tokens(value):
                            optimized_context[key] = compressed
                            chunks_compressed += 1

                techniques_used.append("compression")

            # Phase 5: Final truncation if still over budget
            final_tokens = self._calculate_total_tokens(optimized_context)

            if final_tokens > budget.available_for_context:
                # Aggressive truncation - keep most important parts
                optimized_context = await self._truncate_to_budget(
                    optimized_context, budget.available_for_context
                )
                techniques_used.append("truncation")

            # Cache the optimized result
            optimized_chunk = ContextChunk(
                chunk_id=cache_key,
                content=json.dumps(optimized_context),
                content_type="optimized_context",
                importance=1.0,
                staleness=0.0,
                token_count=self._calculate_total_tokens(optimized_context),
                created_at=datetime.now(),
                last_accessed=datetime.now()
            )
            await self.cache.put(optimized_chunk)

        # Calculate final stats
        final_tokens = self._calculate_total_tokens(optimized_context)
        reduction_percentage = (original_tokens - final_tokens) / original_tokens * 100

        result = OptimizationResult(
            original_tokens=original_tokens,
            optimized_tokens=final_tokens,
            reduction_percentage=reduction_percentage,
            techniques_used=techniques_used,
            chunks_offloaded=chunks_offloaded,
            chunks_compressed=chunks_compressed,
            cache_hits=cache_hits
        )

        return optimized_context, result

    def _calculate_total_tokens(self, context: Dict[str, Any]) -> int:
        """Calculate total token count for context"""
        total = 0

        for key, value in context.items():
            if isinstance(value, str):
                total += self.token_estimator.estimate_tokens(value)
            elif isinstance(value, dict):
                total += self.token_estimator.estimate_json_tokens(value)
            elif isinstance(value, list):
                total += self.token_estimator.estimate_json_tokens({"items": value})
            else:
                total += self.token_estimator.estimate_tokens(str(value))

        return total

    def _identify_chunks(self, context: Dict[str, Any]) -> List[ContextChunk]:
        """Identify chunks within context for optimization"""
        chunks = []

        for key, value in context.items():
            if isinstance(value, str) and len(value) > 100:
                # Create chunk for large strings
                chunk = ContextChunk(
                    chunk_id=f"chunk_{key}",
                    content=value,
                    content_type=self._determine_content_type(value),
                    importance=self._calculate_importance(key, value),
                    staleness=self._calculate_staleness(value),
                    token_count=self.token_estimator.estimate_tokens(value),
                    created_at=datetime.now(),
                    last_accessed=datetime.now(),
                    tags=[key]
                )
                chunks.append(chunk)

            elif isinstance(value, (dict, list)) and len(str(value)) > 200:
                # Create chunk for large objects
                content = json.dumps(value, indent=2)
                chunk = ContextChunk(
                    chunk_id=f"chunk_{key}",
                    content=content,
                    content_type="structured_data",
                    importance=self._calculate_importance(key, value),
                    staleness=0.0,  # Structured data is typically fresh
                    token_count=self.token_estimator.estimate_json_tokens(value),
                    created_at=datetime.now(),
                    last_accessed=datetime.now(),
                    tags=[key]
                )
                chunks.append(chunk)

        return chunks

    def _determine_content_type(self, content: str) -> str:
        """Determine the type of content"""
        content_lower = content.lower()

        if 'def ' in content or 'class ' in content or 'import ' in content:
            return 'code'
        elif content.startswith('#') or 'documentation' in content_lower:
            return 'documentation'
        elif '"timestamp"' in content or '"created_at"' in content:
            return 'metadata'
        else:
            return 'text'

    def _calculate_importance(self, key: str, value: Any) -> float:
        """Calculate importance score for content"""

        # Key-based importance
        important_keys = ['error', 'result', 'output', 'response', 'current', 'active']
        less_important_keys = ['history', 'log', 'debug', 'metadata', 'cache']

        key_lower = key.lower()

        if any(important in key_lower for important in important_keys):
            base_importance = 0.8
        elif any(less_important in key_lower for less_important in less_important_keys):
            base_importance = 0.3
        else:
            base_importance = 0.5

        # Content-based adjustments
        if isinstance(value, str):
            if 'error' in value.lower() or 'warning' in value.lower():
                base_importance += 0.2
            elif len(value) < 50:  # Short content is often important
                base_importance += 0.1

        return min(1.0, base_importance)

    def _calculate_staleness(self, content: str) -> float:
        """Calculate staleness score based on content"""

        # Look for timestamps or indicators of age
        now = datetime.now()

        # Check for ISO timestamps
        timestamp_patterns = [
            r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}',
            r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}'
        ]

        for pattern in timestamp_patterns:
            matches = re.findall(pattern, content)
            if matches:
                try:
                    # Parse the most recent timestamp
                    latest_timestamp = max(datetime.fromisoformat(ts.replace('T', ' ')) for ts in matches)
                    age_hours = (now - latest_timestamp).total_seconds() / 3600

                    # Staleness increases with age
                    if age_hours < 1:
                        return 0.0
                    elif age_hours < 24:
                        return 0.2
                    elif age_hours < 168:  # 1 week
                        return 0.5
                    else:
                        return 0.8

                except Exception:
                    continue

        # Default staleness based on content type
        if 'debug' in content.lower() or 'log' in content.lower():
            return 0.6

        return 0.3

    def _replace_chunk_with_reference(self, context: Dict[str, Any], chunk: ContextChunk) -> Dict[str, Any]:
        """Replace chunk content with filesystem reference"""

        # Find and replace the chunk content
        for key, value in context.items():
            if chunk.chunk_id == f"chunk_{key}":
                context[key] = f"[OFFLOADED: {chunk.chunk_id} - {chunk.content_type} - {chunk.token_count} tokens]"
                break

        return context

    async def _truncate_to_budget(self, context: Dict[str, Any], budget: int) -> Dict[str, Any]:
        """Aggressively truncate context to fit budget"""

        # Calculate importance-weighted truncation
        items = []
        for key, value in context.items():
            importance = self._calculate_importance(key, value)
            token_count = self.token_estimator.estimate_tokens(str(value))
            items.append((key, value, importance, token_count))

        # Sort by importance (highest first)
        items.sort(key=lambda x: x[2], reverse=True)

        # Keep items until budget is reached
        truncated_context = {}
        used_tokens = 0

        for key, value, importance, token_count in items:
            if used_tokens + token_count <= budget:
                truncated_context[key] = value
                used_tokens += token_count
            else:
                # Try to fit a truncated version
                remaining_budget = budget - used_tokens
                if remaining_budget > 50:  # Minimum useful size
                    if isinstance(value, str):
                        truncated_value = value[:remaining_budget * 4]  # Rough chars per token
                        truncated_context[key] = truncated_value + "..."
                        break

        return truncated_context

    async def retrieve_offloaded_context(self, reference: str) -> Optional[str]:
        """Retrieve offloaded context by reference"""

        # Parse reference format: [OFFLOADED: chunk_id - content_type - token_count tokens]
        if not reference.startswith("[OFFLOADED:"):
            return None

        try:
            parts = reference[11:-1].split(" - ")  # Remove "[OFFLOADED:" and "]"
            chunk_id = parts[0].strip()

            chunk = await self.offloader.retrieve_chunk(chunk_id)
            return chunk.content if chunk else None

        except Exception as e:
            self.logger.error(f"Failed to parse offloaded reference: {e}")
            return None

    def get_optimization_stats(self) -> Dict[str, Any]:
        """Get optimization statistics"""
        cache_stats = self.cache.get_stats()
        offload_stats = self.offloader.get_offload_stats()

        return {
            "cache": cache_stats,
            "offload": offload_stats,
            "total_storage_mb": cache_stats.get("disk_cache_size", 0) + offload_stats.get("storage_size_mb", 0)
        }


# Global instance
_token_optimizer = None


def get_token_optimizer() -> TokenOptimizer:
    """Get or create global token optimizer"""
    global _token_optimizer
    if _token_optimizer is None:
        _token_optimizer = TokenOptimizer()
    return _token_optimizer


# Convenience functions
async def optimize_for_budget(context: Dict[str, Any], budget: int = 4000) -> Tuple[Dict[str, Any], OptimizationResult]:
    """Optimize context for token budget"""
    optimizer = get_token_optimizer()
    token_budget = TokenBudget(
        total_budget=budget,
        available_for_context=int(budget * 0.75)  # Reserve 25% for response
    )
    return await optimizer.optimize_context(context, token_budget)


async def estimate_context_tokens(context: Dict[str, Any]) -> int:
    """Estimate token count for context"""
    optimizer = get_token_optimizer()
    return optimizer._calculate_total_tokens(context)


async def compress_text_content(text: str, target_ratio: float = 0.7) -> str:
    """Compress text content"""
    compressor = ContextCompressor()
    return await compressor.compress_text(text, target_ratio)


# CLI interface
async def main():
    """Main CLI entry point"""
    import argparse

    parser = argparse.ArgumentParser(description="OOS Token Optimization System")
    parser.add_argument("--stats", action="store_true", help="Show optimization statistics")
    parser.add_argument("--clear-cache", action="store_true", help="Clear optimization cache")
    parser.add_argument("--test", action="store_true", help="Run optimization test")

    args = parser.parse_args()

    optimizer = get_token_optimizer()

    if args.stats:
        stats = optimizer.get_optimization_stats()
        print("Token Optimization Statistics:")
        print(json.dumps(stats, indent=2))

    elif args.clear_cache:
        # Clear caches
        import shutil
        cache_dir = Path.home() / ".oos" / "context_cache"
        offload_dir = Path.home() / ".oos" / "context_offload"

        if cache_dir.exists():
            shutil.rmtree(cache_dir)
            print("Cache cleared")

        if offload_dir.exists():
            shutil.rmtree(offload_dir)
            print("Offload storage cleared")

    elif args.test:
        # Run test optimization
        test_context = {
            "large_code": "def " + "x" * 1000,
            "documentation": "This is documentation. " * 100,
            "important_result": "Critical result",
            "debug_log": "Debug information. " * 50,
            "metadata": {"created": "2025-09-14", "items": list(range(100))}
        }

        print("Original context tokens:", await estimate_context_tokens(test_context))

        optimized, result = await optimize_for_budget(test_context, 1000)

        print("Optimization result:")
        print(f"  Original tokens: {result.original_tokens}")
        print(f"  Optimized tokens: {result.optimized_tokens}")
        print(f"  Reduction: {result.reduction_percentage:.1f}%")
        print(f"  Techniques: {', '.join(result.techniques_used)}")

    else:
        print("No action specified. Use --help for options.")


if __name__ == "__main__":
    asyncio.run(main())