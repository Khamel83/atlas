#!/usr/bin/env python3
"""
CLI for Atlas Ask - semantic search and Q&A over your content.

Usage:
    # Ask a question
    python -m modules.ask.cli ask "What are the implications of AI for jobs?"

    # Search without synthesizing an answer
    python -m modules.ask.cli search "nuclear power" --limit 5

    # Index new content
    python -m modules.ask.cli index --path data/podcasts/acquired/transcripts

    # Show stats
    python -m modules.ask.cli stats
"""

import argparse
import sys
import os
import logging
from pathlib import Path

# Add project root
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s: %(message)s"
)
logger = logging.getLogger(__name__)


def cmd_ask(args):
    """Ask a question and get an answer."""
    from modules.ask.config import get_config
    from modules.ask.retriever import HybridRetriever
    from modules.ask.synthesizer import AnswerSynthesizer

    config = get_config()
    retriever = HybridRetriever(config)
    synthesizer = AnswerSynthesizer(config)

    try:
        # Retrieve relevant context
        logger.info(f"Searching for: {args.query}")
        results = retriever.retrieve(
            args.query,
            limit=args.context_chunks,
        )

        if not results:
            print("\nNo relevant content found.")
            return 1

        # Show retrieved chunks if verbose
        if args.verbose:
            print(f"\n{'='*60}")
            print(f"RETRIEVED {len(results)} CHUNKS")
            print('='*60)
            for i, r in enumerate(results, 1):
                title = r.metadata.get("title", r.content_id)
                ranks = []
                if r.vector_rank:
                    ranks.append(f"vec:{r.vector_rank}")
                if r.keyword_rank:
                    ranks.append(f"kw:{r.keyword_rank}")
                rank_str = f" ({', '.join(ranks)})" if ranks else ""
                print(f"\n{i}. [{r.score:.4f}]{rank_str} {title}")
                preview = r.text[:200].replace('\n', ' ')
                print(f"   {preview}...")

        # Synthesize answer
        logger.info("Generating answer...")
        answer = synthesizer.synthesize(args.query, results)

        print(f"\n{'='*60}")
        print("ANSWER")
        print('='*60)
        print(f"\n{answer.answer}")
        print(f"\n[Confidence: {answer.confidence} | Sources: {len(answer.sources)} | Tokens: {answer.tokens_used}]")

        if args.verbose and answer.sources:
            print(f"\nSources: {', '.join(answer.sources[:5])}")

        return 0

    finally:
        retriever.close()


def cmd_search(args):
    """Search for relevant content without synthesizing."""
    from modules.ask.config import get_config
    from modules.ask.retriever import HybridRetriever

    config = get_config()
    retriever = HybridRetriever(config)

    try:
        logger.info(f"Searching for: {args.query}")
        results = retriever.retrieve(
            args.query,
            limit=args.limit,
            vector_only=args.vector_only,
            keyword_only=args.keyword_only,
        )

        if not results:
            print("\nNo results found.")
            return 1

        print(f"\n{'='*60}")
        print(f"SEARCH RESULTS ({len(results)} matches)")
        print('='*60)

        for i, r in enumerate(results, 1):
            title = r.metadata.get("title", r.content_id)

            # Show ranking sources
            ranks = []
            if r.vector_rank:
                ranks.append(f"vec:{r.vector_rank}")
            if r.keyword_rank:
                ranks.append(f"kw:{r.keyword_rank}")
            rank_str = f" ({', '.join(ranks)})" if ranks else ""

            print(f"\n{i}. [{r.score:.4f}]{rank_str}")
            print(f"   Title: {title}")
            print(f"   Content: {r.content_id} (chunk {r.chunk_index})")

            # Show text preview
            preview = r.text[:300].replace('\n', ' ')
            print(f"   Preview: {preview}...")

        return 0

    finally:
        retriever.close()


def cmd_index(args):
    """Index content from disk."""
    from modules.ask.config import get_config
    from modules.ask.embeddings import EmbeddingClient
    from modules.ask.chunker import ContentChunker
    from modules.ask.vector_store import VectorStore

    config = get_config()
    embedding_client = EmbeddingClient(config)
    chunker = ContentChunker(config)
    vector_store = VectorStore(config)

    path = Path(args.path)
    if not path.exists():
        print(f"Path not found: {path}")
        return 1

    # Find markdown files
    if path.is_file():
        files = [path]
    else:
        files = list(path.glob("**/*.md"))

    if not files:
        print(f"No markdown files found in {path}")
        return 1

    print(f"Found {len(files)} files to index")

    if args.dry_run:
        for f in files[:10]:
            print(f"  Would index: {f}")
        if len(files) > 10:
            print(f"  ... and {len(files) - 10} more")
        return 0

    # Process files
    total_chunks = 0
    for i, file_path in enumerate(files, 1):
        try:
            content = file_path.read_text()
            if len(content) < 100:
                logger.debug(f"Skipping short file: {file_path}")
                continue

            # Use filename as content ID
            content_id = file_path.stem

            # Check if already indexed
            existing = vector_store.get_chunks_for_content(content_id)
            if existing and not args.force:
                logger.debug(f"Already indexed: {content_id}")
                continue

            # Chunk
            chunks = chunker.chunk_text(
                content,
                content_id=content_id,
                metadata={"title": file_path.stem.replace("-", " ").title()}
            )

            if not chunks:
                continue

            # Embed
            chunk_texts = [c.text for c in chunks]
            embeddings = embedding_client.embed_chunks(chunk_texts)

            # Store
            vector_store.store_chunks(chunks, embeddings)
            total_chunks += len(chunks)

            if i % 10 == 0:
                print(f"Indexed {i}/{len(files)} files ({total_chunks} chunks)")

        except Exception as e:
            logger.error(f"Failed to index {file_path}: {e}")

    print(f"\nIndexed {total_chunks} chunks from {len(files)} files")

    # Show stats
    stats = vector_store.get_stats()
    print(f"\nVector store stats:")
    for k, v in stats.items():
        print(f"  {k}: {v}")

    vector_store.close()
    return 0


def cmd_stats(args):
    """Show vector store statistics."""
    from modules.ask.config import get_config
    from modules.ask.vector_store import VectorStore

    config = get_config()
    vector_store = VectorStore(config)

    stats = vector_store.get_stats()

    print(f"\n{'='*60}")
    print("ATLAS ASK STATISTICS")
    print('='*60)

    print(f"\nVector Store:")
    for k, v in stats.items():
        print(f"  {k}: {v}")

    print(f"\nConfiguration:")
    print(f"  Embedding model: {config.embeddings.model}")
    print(f"  LLM model: {config.llm.model}")
    print(f"  Provider: {config.provider}")
    print(f"  Chunk size: {config.chunking.max_chunk_tokens} tokens")
    print(f"  Vector weight: {config.retrieval.vector_weight}")
    print(f"  Keyword weight: {config.retrieval.keyword_weight}")

    vector_store.close()
    return 0


def main():
    parser = argparse.ArgumentParser(
        description="Atlas Ask - semantic search and Q&A",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # ask command
    ask_parser = subparsers.add_parser("ask", help="Ask a question")
    ask_parser.add_argument("query", help="Question to ask")
    ask_parser.add_argument("-v", "--verbose", action="store_true", help="Show retrieved chunks")
    ask_parser.add_argument("--context-chunks", type=int, default=5, help="Number of chunks for context")

    # search command
    search_parser = subparsers.add_parser("search", help="Search without synthesizing")
    search_parser.add_argument("query", help="Search query")
    search_parser.add_argument("--limit", type=int, default=10, help="Max results")
    search_parser.add_argument("--vector-only", action="store_true", help="Vector search only")
    search_parser.add_argument("--keyword-only", action="store_true", help="Keyword search only")

    # index command
    index_parser = subparsers.add_parser("index", help="Index content")
    index_parser.add_argument("--path", required=True, help="Path to content")
    index_parser.add_argument("--force", action="store_true", help="Re-index existing content")
    index_parser.add_argument("--dry-run", action="store_true", help="Show what would be indexed")

    # stats command
    subparsers.add_parser("stats", help="Show statistics")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    # Check for API key
    if not os.getenv("OPENROUTER_API_KEY"):
        print("OPENROUTER_API_KEY not set.")
        print("Run with: ./scripts/run_with_secrets.sh python -m modules.ask.cli ...")
        return 1

    commands = {
        "ask": cmd_ask,
        "search": cmd_search,
        "index": cmd_index,
        "stats": cmd_stats,
    }

    return commands[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
