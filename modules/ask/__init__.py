"""
Atlas Ask - Semantic search and Q&A for the Atlas knowledge base.

Components:
- embeddings: Generate embeddings via OpenRouter (openai/text-embedding-3-small)
- chunker: Split content into searchable chunks
- vector_store: SQLite-vec storage for embeddings
- retriever: Hybrid search (vector + FTS5)
- synthesizer: LLM-powered answer generation (google/gemini-2.5-flash-lite)

Usage:
    from modules.ask import ask

    answer = ask("What are the implications of AI for jobs?")
    print(answer.answer)
"""

from .config import get_config
from .embeddings import EmbeddingClient, embed_text, embed_texts
from .chunker import ContentChunker, Chunk, chunk_content
from .vector_store import VectorStore, SearchResult
from .retriever import HybridRetriever, RetrievalResult, retrieve
from .synthesizer import AnswerSynthesizer, SynthesizedAnswer, ask
from .indexer import ContentIndexer, index_single

__all__ = [
    # Config
    "get_config",
    # Embeddings
    "EmbeddingClient",
    "embed_text",
    "embed_texts",
    # Chunking
    "ContentChunker",
    "Chunk",
    "chunk_content",
    # Vector store
    "VectorStore",
    "SearchResult",
    # Retriever
    "HybridRetriever",
    "RetrievalResult",
    "retrieve",
    # Synthesizer
    "AnswerSynthesizer",
    "SynthesizedAnswer",
    "ask",
    # Indexer
    "ContentIndexer",
    "index_single",
]
