# Retrieval and RAG Patterns for OOS Context Engineering

*Analysis of retrieval approaches for optimal context engineering in OOS middleware*
*Created: 2025-09-14*

## Current Retrieval Implementation in OOS

### Analysis of Existing Learning System
The current `src/learning_system.py` implements several retrieval patterns:

1. **TF-IDF Vector Similarity** (Line 19-20)
   - Uses sklearn's TfidfVectorizer for command sequence modeling
   - Cosine similarity for pattern matching
   - Good for: Textual pattern matching, command similarity

2. **SQLite Pattern Storage** (Lines 110-162)
   - Structured storage for patterns, usage data, and suggestions
   - Indexed queries for performance
   - Good for: Exact matches, structured queries, temporal analysis

3. **Frequency-Based Filtering** (Lines 236-239)
   - Filters patterns by minimum frequency threshold
   - Good for: Reducing noise, focusing on proven patterns

## Retrieval Pattern Analysis

### 1. Vector-Based Retrieval vs Agentic Search

#### Vector-Based Approach (Current)
```python
# Current TF-IDF approach in learning_system.py
self.command_sequence_model = TfidfVectorizer(max_features=1000)

# Strengths:
+ Fast similarity computation
+ Good for textual pattern matching
+ Deterministic results
+ Low computational overhead

# Weaknesses:
- Limited semantic understanding
- Poor for conceptual similarity
- No reasoning about context
- Fixed feature space
```

#### Agentic Search Approach (Recommended Enhancement)
```python
class AgenticRetrieval:
    """Model-driven retrieval with reasoning"""

    async def retrieve_relevant_patterns(self, query: str, context: Dict) -> List[Pattern]:
        # Let the model reason about what's relevant
        reasoning_prompt = f"""
        Query: {query}
        Context: {context}

        What patterns would be most relevant for this task?
        Consider: semantic similarity, contextual fit, success probability
        """

        # Get model reasoning
        relevant_criteria = await self.model.reason(reasoning_prompt)

        # Apply criteria to pattern database
        return self._filter_by_criteria(relevant_criteria)
```

### 2. Hybrid Retrieval Strategy

Based on research findings, optimal approach combines multiple retrieval methods:

```python
class HybridRetrieval:
    """Multi-modal retrieval combining vector, agentic, and structured approaches"""

    def __init__(self):
        self.vector_retriever = VectorRetriever()  # For fast similarity
        self.agentic_retriever = AgenticRetriever()  # For reasoning
        self.structured_retriever = StructuredRetriever()  # For exact matches

    async def retrieve(self, query: str, context: Dict, retrieval_type: str = "auto") -> List[Pattern]:
        if retrieval_type == "auto":
            retrieval_type = await self._determine_optimal_retrieval(query, context)

        if retrieval_type == "fast":
            return await self.vector_retriever.retrieve(query, context)
        elif retrieval_type == "reasoning":
            return await self.agentic_retriever.retrieve(query, context)
        elif retrieval_type == "exact":
            return await self.structured_retriever.retrieve(query, context)
        else:  # hybrid
            return await self._hybrid_retrieve(query, context)

    async def _hybrid_retrieve(self, query: str, context: Dict) -> List[Pattern]:
        # Parallel retrieval from all sources
        vector_results = await self.vector_retriever.retrieve(query, context)
        agentic_results = await self.agentic_retriever.retrieve(query, context)
        structured_results = await self.structured_retriever.retrieve(query, context)

        # Model-driven result fusion
        return await self._fuse_results(vector_results, agentic_results, structured_results, query, context)
```

### 3. Context-Aware Retrieval Optimization

```python
class ContextAwareRetrieval:
    """Retrieval that adapts to context and performance"""

    def __init__(self):
        self.performance_tracker = {}
        self.context_patterns = {}

    async def retrieve(self, query: str, context: Dict) -> List[Pattern]:
        # Analyze context to choose optimal retrieval strategy
        context_type = self._classify_context(context)

        # Use learned patterns for this context type
        optimal_strategy = self.context_patterns.get(context_type, "hybrid")

        # Execute retrieval
        results = await self._execute_strategy(optimal_strategy, query, context)

        # Track performance for learning
        self._track_performance(results, context_type, optimal_strategy)

        return results

    def _classify_context(self, context: Dict) -> str:
        """Classify context to determine optimal retrieval approach"""
        if context.get("urgent", False):
            return "fast"
        elif context.get("complex_reasoning", False):
            return "agentic"
        elif context.get("exact_match_needed", False):
            return "structured"
        else:
            return "hybrid"
```

## When to Use Each Approach

### Vector-Based Retrieval
**Use When:**
- Fast response time required (< 100ms)
- Textual similarity is primary concern
- Large corpus with good semantic density
- Resource constraints (CPU/memory)

**Examples in OOS:**
- Command name similarity matching
- Quick parameter suggestion lookup
- Real-time autocomplete features

### Agentic Search
**Use When:**
- Complex reasoning required
- Context heavily influences relevance
- Quality over speed priority
- Novel query patterns

**Examples in OOS:**
- Multi-step workflow analysis
- Complex repository pattern discovery
- Context-dependent command generation

### Structured Queries
**Use When:**
- Exact criteria matching needed
- Metadata-rich queries
- Compliance/audit requirements
- Performance optimization needed

**Examples in OOS:**
- Success rate filtering
- Time-based pattern analysis
- User-specific pattern retrieval

## Implementation Roadmap

### Phase 1: Enhance Current System (Immediate)
1. **Improve Vector Embeddings**
   ```python
   # Replace TF-IDF with modern embeddings
   from sentence_transformers import SentenceTransformer

   class ModernVectorRetrieval:
       def __init__(self):
           self.encoder = SentenceTransformer('all-MiniLM-L6-v2')
           self.pattern_embeddings = {}

       def encode_patterns(self, patterns: List[Pattern]):
           for pattern in patterns:
               text = self._pattern_to_text(pattern)
               self.pattern_embeddings[pattern.id] = self.encoder.encode(text)
   ```

2. **Add Context-Aware Filtering**
   ```python
   def filter_by_context(self, patterns: List[Pattern], context: Dict) -> List[Pattern]:
       filtered = []
       for pattern in patterns:
           if self._context_matches(pattern, context):
               pattern.relevance_score = self._calculate_relevance(pattern, context)
               filtered.append(pattern)
       return sorted(filtered, key=lambda p: p.relevance_score, reverse=True)
   ```

### Phase 2: Add Agentic Layer (Medium Term)
1. **Reasoning-Based Retrieval**
   ```python
   class AgenticRetrieval:
       async def reason_about_relevance(self, query: str, patterns: List[Pattern]) -> List[Pattern]:
           reasoning_prompt = self._build_reasoning_prompt(query, patterns)
           relevant_ids = await self.model.extract_relevant_patterns(reasoning_prompt)
           return [p for p in patterns if p.id in relevant_ids]
   ```

2. **Dynamic Query Expansion**
   ```python
   async def expand_query(self, original_query: str, context: Dict) -> List[str]:
       expansion_prompt = f"""
       Original query: {original_query}
       Context: {context}

       Generate 3-5 related queries that might find relevant patterns:
       """
       return await self.model.generate_expansions(expansion_prompt)
   ```

### Phase 3: Intelligent Fusion (Long Term)
1. **Multi-Modal Result Fusion**
2. **Adaptive Strategy Learning**
3. **Performance-Based Optimization**

## Performance Metrics

Track these metrics for retrieval optimization:

```python
@dataclass
class RetrievalMetrics:
    query_time_ms: float
    relevance_score: float  # Human or model-judged
    recall_at_k: float     # Found relevant items in top K
    precision_at_k: float  # Relevant items in top K results
    cache_hit_rate: float
    context_match_accuracy: float
```

## Integration with Context Engineering

### Memory Offloading Strategy
```python
class ContextEngineeredRetrieval:
    """Retrieval system optimized for context engineering principles"""

    def __init__(self):
        self.memory_tiers = {
            "hot": [],      # Current context (in LLM window)
            "warm": [],     # Recent patterns (fast vector lookup)
            "cold": [],     # All patterns (database query)
        }

    async def retrieve_with_memory_management(self, query: str, context: Dict, max_tokens: int = 4000) -> str:
        # Start with hot memory (already in context)
        results = self._search_hot_memory(query)
        tokens_used = self._estimate_tokens(results)

        if tokens_used < max_tokens * 0.5:
            # Add warm memory results
            warm_results = await self._search_warm_memory(query, max_tokens - tokens_used)
            results.extend(warm_results)
            tokens_used += self._estimate_tokens(warm_results)

        if tokens_used < max_tokens * 0.8:
            # Add cold memory results
            cold_results = await self._search_cold_memory(query, max_tokens - tokens_used)
            results.extend(cold_results)

        return self._format_results_for_context(results, max_tokens)
```

## Research-Based Recommendations

### From Manus AI Lessons:
1. **Design Around KV-Cache**: Keep retrieval prompts stable for cache efficiency
2. **Compress But Keep Restorable**: Summarize retrieved patterns but maintain reference to full data
3. **Use File System as Context**: Store retrieval results in files for persistence across interactions

### From Context Engineering Framework:
1. **Write Principle**: Store retrieval results outside the context window
2. **Select Principle**: Use intelligent retrieval to pull only relevant patterns
3. **Compress Principle**: Summarize retrieved patterns for token efficiency
4. **Isolate Principle**: Separate retrieval concerns from reasoning logic

## Implementation Priority

1. **High Priority**: Enhance vector embeddings, add context filtering
2. **Medium Priority**: Implement agentic reasoning layer
3. **Low Priority**: Advanced fusion and adaptive strategies

The goal is to build a retrieval system that scales with model improvements while providing immediate performance benefits for OOS middleware functionality.