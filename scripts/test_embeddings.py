#!/usr/bin/env python3
"""
Test embedding functionality with a handful of documents.

This script:
1. Loads a few podcast transcripts from disk
2. Chunks them
3. Generates embeddings via OpenRouter
4. Stores in vector database
5. Tests semantic search

Run: ./venv/bin/python scripts/test_embeddings.py
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import os
import logging

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def main():
    # Check for API key
    if not os.getenv("OPENROUTER_API_KEY"):
        logger.error("OPENROUTER_API_KEY not set. Run with secrets or set manually.")
        logger.info("Try: ./scripts/run_with_secrets.sh python scripts/test_embeddings.py")
        return 1

    from modules.ask.config import get_config
    from modules.ask.embeddings import EmbeddingClient
    from modules.ask.chunker import ContentChunker
    from modules.ask.vector_store import VectorStore

    config = get_config()
    logger.info(f"Config loaded:")
    logger.info(f"  Embedding model: {config.embeddings.model}")
    logger.info(f"  LLM model: {config.llm.model}")
    logger.info(f"  Provider: {config.provider}")

    # Initialize components
    embedding_client = EmbeddingClient(config)
    chunker = ContentChunker(config)

    # Use a test database path
    test_db = Path("data/indexes/test_vectors.db")
    vector_store = VectorStore(config, db_path=test_db)

    # Find a few podcast transcripts to test with
    transcript_dir = Path("data/podcasts")
    test_transcripts = []

    if transcript_dir.exists():
        for podcast_dir in transcript_dir.iterdir():
            if podcast_dir.is_dir():
                transcripts_subdir = podcast_dir / "transcripts"
                if transcripts_subdir.exists():
                    for md_file in transcripts_subdir.glob("*.md"):
                        test_transcripts.append(md_file)
                        if len(test_transcripts) >= 3:
                            break
            if len(test_transcripts) >= 3:
                break

    if not test_transcripts:
        logger.warning("No transcripts found, using sample text")
        test_transcripts = None

    # Test with sample content
    sample_texts = [
        {
            "id": "test_1",
            "title": "AI and the Future of Work",
            "content": """The discussion around AI and employment continues to evolve.
            Many experts believe that AI will augment human capabilities rather than replace jobs entirely.
            The key is to focus on skills that complement AI systems, such as creativity, emotional intelligence,
            and complex problem-solving. Companies are increasingly looking for workers who can collaborate
            effectively with AI tools. This shift requires new approaches to education and training."""
        },
        {
            "id": "test_2",
            "title": "Nuclear Power Renaissance",
            "content": """There's growing interest in nuclear power as a clean energy source.
            New reactor designs promise improved safety and efficiency. Small modular reactors (SMRs)
            are particularly exciting because they can be built more quickly and at lower cost.
            Countries are reconsidering their nuclear policies in light of climate goals.
            The challenge remains public perception and regulatory frameworks."""
        },
        {
            "id": "test_3",
            "title": "Podcast Transcript: Tech Trends",
            "content": """Today we're discussing the latest developments in artificial intelligence.
            The pace of progress has been remarkable. Large language models have become increasingly capable,
            and we're seeing applications across every industry. From healthcare to finance to education,
            AI is transforming how we work. But we also need to think carefully about the implications.
            What does it mean when machines can write, reason, and create? These are the questions
            we'll explore in this episode."""
        }
    ]

    # If we found real transcripts, use those instead
    if test_transcripts:
        sample_texts = []
        for transcript_path in test_transcripts[:3]:
            content = transcript_path.read_text()
            # Truncate for testing (first 2000 chars)
            sample_texts.append({
                "id": transcript_path.stem,
                "title": transcript_path.stem.replace("-", " ").title(),
                "content": content[:2000]
            })
        logger.info(f"Using {len(sample_texts)} real transcripts for testing")

    # Process each sample
    all_chunks = []
    for sample in sample_texts:
        logger.info(f"\nProcessing: {sample['title']}")

        # Chunk the content
        chunks = chunker.chunk_text(
            sample["content"],
            content_id=sample["id"],
            metadata={"title": sample["title"]}
        )
        logger.info(f"  Created {len(chunks)} chunks")

        for chunk in chunks:
            logger.info(f"    Chunk {chunk.chunk_index}: {chunk.token_count} tokens")

        all_chunks.extend(chunks)

    # Generate embeddings
    logger.info(f"\nGenerating embeddings for {len(all_chunks)} chunks...")
    chunk_texts = [c.text for c in all_chunks]

    try:
        embeddings = embedding_client.embed_chunks(chunk_texts)
        logger.info(f"  Generated {len(embeddings)} embeddings")
        logger.info(f"  Embedding dimensions: {len(embeddings[0])}")
    except Exception as e:
        logger.error(f"Embedding failed: {e}")
        return 1

    # Store in vector database
    logger.info("\nStoring in vector database...")
    chunk_ids = vector_store.store_chunks(all_chunks, embeddings)
    logger.info(f"  Stored {len(chunk_ids)} chunks")

    # Test semantic search
    logger.info("\n" + "="*60)
    logger.info("TESTING SEMANTIC SEARCH")
    logger.info("="*60)

    test_queries = [
        "What are the implications of AI for jobs?",
        "Tell me about nuclear energy and climate",
        "How are language models being used?",
    ]

    for query in test_queries:
        logger.info(f"\nQuery: '{query}'")

        # Embed the query
        query_embedding = embedding_client.embed(query)

        # Search
        results = vector_store.search(query_embedding, limit=3)

        for i, result in enumerate(results):
            logger.info(f"  {i+1}. [score={result.score:.3f}] {result.content_id}")
            # Show first 100 chars of text
            preview = result.text[:100].replace("\n", " ")
            logger.info(f"      {preview}...")

    # Show stats
    stats = vector_store.get_stats()
    logger.info("\n" + "="*60)
    logger.info("VECTOR STORE STATS")
    logger.info("="*60)
    for key, value in stats.items():
        logger.info(f"  {key}: {value}")

    vector_store.close()
    logger.info("\nTest completed successfully!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
