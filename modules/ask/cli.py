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


def cmd_quote(args):
    """Extract quotable passages on a topic."""
    from modules.ask.intelligence import QuoteExtractor

    extractor = QuoteExtractor()
    try:
        source_filter = None
        if args.source:
            source_filter = [s.strip() for s in args.source.split(",")]

        quotes = extractor.extract_quotes(
            topic=args.topic,
            limit=args.limit,
            min_length=args.min_length,
            max_length=args.max_length,
            source_filter=source_filter,
        )

        if not quotes:
            print(f"\nNo quotable passages found for: {args.topic}")
            return 1

        print(f"\n{'='*60}")
        print(f"QUOTES: {args.topic}")
        print('='*60)

        for i, quote in enumerate(quotes, 1):
            if args.markdown:
                print(f"\n{quote.as_markdown()}")
            else:
                print(f"\n{i}. {quote}")
            print(f"   [relevance: {quote.relevance_score:.3f}]")

        return 0
    finally:
        extractor.close()


def cmd_source(args):
    """Query what a specific source thinks about a topic."""
    from modules.ask.intelligence import SourceQueryEngine

    engine = SourceQueryEngine()
    try:
        if args.compare:
            # Compare multiple sources
            sources = [s.strip() for s in args.source.split(",")]
            perspectives = engine.compare_sources(sources, args.topic)

            if not perspectives:
                print(f"\nNo perspectives found for sources: {sources}")
                return 1

            print(f"\n{'='*60}")
            print(f"SOURCE COMPARISON: {args.topic}")
            print('='*60)

            for source, perspective in perspectives.items():
                print(f"\n## {source}")
                print(f"{perspective.summary}")
                if perspective.key_points:
                    print("\nKey points:")
                    for point in perspective.key_points:
                        print(f"  • {point}")
                if perspective.quotes:
                    print("\nNotable quote:")
                    print(f"  {perspective.quotes[0]}")
        else:
            # Single source perspective
            perspective = engine.what_does_x_think(args.source, args.topic)

            if not perspective:
                print(f"\nNo content found from {args.source} about {args.topic}")
                return 1

            print(f"\n{'='*60}")
            print(f"WHAT {args.source.upper()} THINKS ABOUT: {args.topic}")
            print('='*60)

            print(f"\n{perspective.summary}")

            if perspective.key_points:
                print("\nKey Points:")
                for point in perspective.key_points:
                    print(f"  • {point}")

            if perspective.quotes:
                print("\nQuotes:")
                for quote in perspective.quotes[:2]:
                    print(f"\n  {quote}")

            print(f"\n[Based on {perspective.chunk_count} chunks, avg relevance: {perspective.avg_relevance:.3f}]")

        return 0
    finally:
        engine.close()


def cmd_thread(args):
    """Manage research threads."""
    from modules.ask.intelligence import ThreadStore

    store = ThreadStore()

    if args.subcommand == "new":
        tags = [t.strip() for t in args.tags.split(",")] if args.tags else []
        thread = store.create_thread(args.title, args.description, tags)
        print(f"Created thread [{thread.id}]: {thread.title}")

    elif args.subcommand == "list":
        threads = store.list_threads(limit=args.limit)
        if not threads:
            print("No research threads found.")
            return 0

        print(f"\n{'='*60}")
        print("RESEARCH THREADS")
        print('='*60)

        for t in threads:
            tags_str = f" [{', '.join(t.tags)}]" if t.tags else ""
            print(f"\n[{t.id}] {t.title}{tags_str}")
            print(f"   {len(t.queries)} queries | Updated: {t.updated_at.strftime('%Y-%m-%d %H:%M')}")

    elif args.subcommand == "show":
        thread = store.get_thread(args.thread_id)
        if not thread:
            print(f"Thread not found: {args.thread_id}")
            return 1

        print(f"\n{'='*60}")
        print(f"THREAD: {thread.title}")
        print('='*60)

        if thread.description:
            print(f"\n{thread.description}")

        print(f"\nQueries ({len(thread.queries)}):")
        for q in thread.queries:
            print(f"\n  Q: {q.query}")
            print(f"  A: {q.answer[:200]}..." if len(q.answer) > 200 else f"  A: {q.answer}")

    elif args.subcommand == "continue":
        # Continue a thread with a new query
        thread = store.get_thread(args.thread_id)
        if not thread:
            print(f"Thread not found: {args.thread_id}")
            return 1

        # Use conversational session with thread context
        from modules.ask.intelligence import ConversationalSession

        session = ConversationalSession()
        try:
            # Preload history from thread
            for q in thread.queries[-3:]:  # Last 3 queries for context
                session.history.append({"role": "user", "content": q.query})
                session.history.append({"role": "assistant", "content": q.answer})

            answer = session.ask(args.query)

            # Save to thread
            store.add_query(args.thread_id, args.query, answer, [])

            print(f"\n{answer}")
            print(f"\n[Added to thread: {thread.title}]")
        finally:
            session.close()

    return 0


def cmd_recommend(args):
    """Get personalized content recommendations."""
    from modules.ask.intelligence import RecommendationEngine

    engine = RecommendationEngine()
    try:
        recommendations = engine.get_recommendations(limit=args.limit)

        if not recommendations:
            print("\nNo recommendations available. Try annotating some content first!")
            return 1

        print(f"\n{'='*60}")
        print("RECOMMENDED FOR YOU")
        print('='*60)

        for i, r in enumerate(recommendations, 1):
            title = r.metadata.get("title", r.content_id)
            print(f"\n{i}. {title}")
            print(f"   {r.text[:200]}...")
            print(f"   [relevance: {r.score:.3f}]")

        return 0
    finally:
        engine.close()


def cmd_contradict(args):
    """Find contradictions on a topic across sources."""
    from modules.ask.intelligence import ContradictionRadar

    radar = ContradictionRadar()
    try:
        contradictions = radar.find_contradictions(args.topic, min_sources=args.min_sources)

        if not contradictions:
            print(f"\nNo contradictions found across sources for: {args.topic}")
            print("Sources seem to agree, or there's not enough coverage.")
            return 0

        print(f"\n{'='*60}")
        print(f"CONTRADICTIONS: {args.topic}")
        print('='*60)

        for i, c in enumerate(contradictions, 1):
            print(f"\n{i}. {c.topic}")
            print(f"   {c.source_a}: {c.position_a}")
            print(f"   vs")
            print(f"   {c.source_b}: {c.position_b}")
            print(f"\n   Explanation: {c.explanation}")
            print(f"   [confidence: {c.confidence:.0%}]")

        return 0
    finally:
        radar.close()


def cmd_chat(args):
    """Interactive conversational mode."""
    from modules.ask.intelligence import ConversationalSession

    session = ConversationalSession()

    print(f"\n{'='*60}")
    print("ATLAS CHAT - Conversational Research Mode")
    print('='*60)
    print("Type your questions. Use 'quit' to exit, 'reset' to clear context.")
    print()

    try:
        while True:
            try:
                query = input("You: ").strip()
            except EOFError:
                break

            if not query:
                continue

            if query.lower() in ("quit", "exit", "q"):
                break

            if query.lower() == "reset":
                session.reset()
                print("Context cleared.\n")
                continue

            if query.lower() == "history":
                for turn in session.get_history():
                    prefix = "You" if turn.role == "user" else "Atlas"
                    print(f"{prefix}: {turn.content[:100]}...")
                print()
                continue

            answer = session.ask(query)
            print(f"\nAtlas: {answer}\n")

    except KeyboardInterrupt:
        print("\n")
    finally:
        session.close()

    return 0


def cmd_briefing(args):
    """Generate a personalized daily briefing."""
    from modules.ask.intelligence import RecommendationEngine, QuoteExtractor
    from modules.digest.summarizer import generate_digest
    from datetime import datetime

    print(f"\n{'='*60}")
    print(f"DAILY BRIEFING - {datetime.now().strftime('%A, %B %d, %Y')}")
    print('='*60)

    # Get recent digest
    try:
        digest = generate_digest(days=args.days, max_items=10)
        if digest and digest.get("clusters"):
            print("\n## What's New")
            for cluster in digest["clusters"][:3]:
                print(f"\n**{cluster.get('topic', 'Topic')}** ({cluster.get('count', 0)} items)")
                if cluster.get("summary"):
                    print(f"  {cluster['summary'][:200]}...")
    except Exception as e:
        logger.debug(f"Digest generation failed: {e}")

    # Get recommendations
    try:
        engine = RecommendationEngine()
        recommendations = engine.get_recommendations(limit=3)
        engine.close()

        if recommendations:
            print("\n## Recommended Reading")
            for r in recommendations:
                title = r.metadata.get("title", r.content_id)
                print(f"\n• **{title}**")
                print(f"  {r.text[:150]}...")
    except Exception as e:
        logger.debug(f"Recommendations failed: {e}")

    # Get a notable quote
    try:
        extractor = QuoteExtractor()
        quotes = extractor.extract_quotes("important insights", limit=1)
        extractor.close()

        if quotes:
            print("\n## Quote of the Day")
            print(f"\n{quotes[0].as_markdown()}")
    except Exception as e:
        logger.debug(f"Quote extraction failed: {e}")

    print(f"\n{'='*60}")
    return 0


def cmd_topicmap(args):
    """Generate a topic map visualization."""
    from modules.ask.topic_map import TopicMapper

    mapper = TopicMapper()
    print("Generating topic map...")

    topic_map = mapper.generate_map(
        limit=args.limit,
        min_cluster_size=args.min_cluster,
    )

    if not topic_map.clusters:
        print("\nNo topics found. Make sure content is indexed.")
        return 1

    print(f"\n{'='*60}")
    print("TOPIC MAP")
    print('='*60)

    print(f"\nTotal content: {topic_map.total_content}")
    print(f"Topic clusters: {len(topic_map.clusters)}")

    print("\nTop Topics:")
    for c in topic_map.clusters[:10]:
        sources_str = ", ".join(c.sources[:3])
        print(f"  • {c.label}: {c.content_count} items ({sources_str})")

    print("\nSource Distribution:")
    for source, count in list(topic_map.source_distribution.items())[:10]:
        print(f"  • {source}: {count}")

    if args.html:
        output_path = mapper.save_html(topic_map)
        print(f"\nHTML visualization saved to: {output_path}")
        print("Open in browser to view interactive charts.")

    return 0


def cmd_annotate(args):
    """Add an annotation to a chunk or content."""
    from modules.ask.annotations import AnnotationStore, AnnotationType, Reaction

    store = AnnotationStore()

    if args.subcommand == "note":
        ann = store.add_note(
            target_id=args.target_id,
            note=args.note,
            target_type=args.type,
        )
        print(f"Added note [{ann.id}] to {args.type} {args.target_id}")

    elif args.subcommand == "react":
        try:
            reaction = Reaction(args.reaction)
        except ValueError:
            print(f"Invalid reaction. Use: {', '.join(r.value for r in Reaction)}")
            return 1

        ann = store.add_reaction(
            target_id=args.target_id,
            reaction=reaction,
            target_type=args.type,
        )
        print(f"Added {args.reaction} reaction [{ann.id}] to {args.type} {args.target_id}")

    elif args.subcommand == "importance":
        ann = store.set_importance(
            chunk_id=args.chunk_id,
            weight=args.weight,
        )
        print(f"Set importance weight {args.weight} for chunk {args.chunk_id}")

    elif args.subcommand == "list":
        annotations = store.list_annotated(limit=args.limit)

        if not annotations:
            print("No annotations found.")
            return 0

        print(f"\n{'='*60}")
        print(f"ANNOTATIONS ({len(annotations)} found)")
        print('='*60)

        for ann in annotations:
            print(f"\n[{ann.id}] {ann.annotation_type.value} on {ann.target_type} {ann.target_id}")
            print(f"   Value: {ann.value[:100]}{'...' if len(ann.value) > 100 else ''}")
            print(f"   Created: {ann.created_at.strftime('%Y-%m-%d %H:%M')}")

    elif args.subcommand == "stats":
        stats = store.stats()
        print(f"\n{'='*60}")
        print("ANNOTATION STATISTICS")
        print('='*60)
        for k, v in stats.items():
            print(f"  {k}: {v}")

    return 0


def cmd_synthesize(args):
    """Synthesize insights from multiple sources."""
    from modules.ask.synthesis import MultiSourceSynthesizer

    synth = MultiSourceSynthesizer()

    try:
        logger.info(f"Synthesizing: {args.query} (mode: {args.mode})")

        # Parse source filter if provided
        source_filter = None
        if args.sources:
            source_filter = [s.strip() for s in args.sources.split(",")]

        result = synth.synthesize(
            query=args.query,
            mode=args.mode,
            min_sources=args.min_sources,
            max_chunks_per_source=args.chunks_per_source,
            source_filter=source_filter,
        )

        print(f"\n{'='*60}")
        print(f"SYNTHESIS ({result.mode.upper()}) - {len(result.sources)} sources")
        print('='*60)

        # Handle output format
        if args.output:
            from modules.ask.output_formats import (
                format_as_briefing,
                format_as_email,
                format_as_markdown,
                save_output,
            )

            if args.output == "briefing":
                output = format_as_briefing(result, audience=args.audience)
            elif args.output == "email":
                output = format_as_email(result, recipient_context=args.recipient or "")
            else:
                output = format_as_markdown(result)

            print(f"\n{output.content}")

            if args.save:
                filepath = save_output(output)
                print(f"\nSaved to: {filepath}")

            print(f"\n[Format: {args.output} | Tokens: {output.tokens_used}]")
        else:
            print(f"\n{result.synthesis}")

            print(f"\n{'='*60}")
            print(f"[Confidence: {result.confidence} | Sources: {len(result.sources)} | Tokens: {result.tokens_used}]")

            if args.verbose:
                print(f"\nSources used:")
                for i, cluster in enumerate(result.clusters, 1):
                    print(f"  {i}. {cluster.source_name} ({len(cluster.chunks)} chunks, avg: {cluster.avg_score:.4f})")

        return 0

    finally:
        synth.close()


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

    # quote command
    quote_parser = subparsers.add_parser("quote", help="Extract quotable passages")
    quote_parser.add_argument("topic", help="Topic to find quotes about")
    quote_parser.add_argument("--limit", "-l", type=int, default=5, help="Max quotes")
    quote_parser.add_argument("--source", "-s", help="Filter by source (comma-separated)")
    quote_parser.add_argument("--min-length", type=int, default=50, help="Min quote length")
    quote_parser.add_argument("--max-length", type=int, default=300, help="Max quote length")
    quote_parser.add_argument("--markdown", "-m", action="store_true", help="Output as markdown")

    # source command
    source_parser = subparsers.add_parser("source", help="Query what a source thinks about a topic")
    source_parser.add_argument("source", help="Source name (e.g., 'Ben Thompson')")
    source_parser.add_argument("topic", help="Topic to query")
    source_parser.add_argument("--compare", "-c", action="store_true",
                              help="Compare multiple sources (comma-separated in source arg)")

    # thread command
    thread_parser = subparsers.add_parser("thread", help="Manage research threads")
    thread_subparsers = thread_parser.add_subparsers(dest="subcommand")

    thread_new = thread_subparsers.add_parser("new", help="Create a new thread")
    thread_new.add_argument("title", help="Thread title")
    thread_new.add_argument("--description", "-d", help="Thread description")
    thread_new.add_argument("--tags", "-t", help="Comma-separated tags")

    thread_list = thread_subparsers.add_parser("list", help="List threads")
    thread_list.add_argument("--limit", "-l", type=int, default=20)

    thread_show = thread_subparsers.add_parser("show", help="Show a thread")
    thread_show.add_argument("thread_id", help="Thread ID")

    thread_continue = thread_subparsers.add_parser("continue", help="Continue a thread")
    thread_continue.add_argument("thread_id", help="Thread ID")
    thread_continue.add_argument("query", help="New query")

    # recommend command
    recommend_parser = subparsers.add_parser("recommend", help="Get personalized recommendations")
    recommend_parser.add_argument("--limit", "-l", type=int, default=5)

    # contradict command
    contradict_parser = subparsers.add_parser("contradict", help="Find contradictions on a topic")
    contradict_parser.add_argument("topic", help="Topic to check for contradictions")
    contradict_parser.add_argument("--min-sources", type=int, default=2)

    # chat command
    subparsers.add_parser("chat", help="Interactive conversational mode")

    # briefing command
    briefing_parser = subparsers.add_parser("briefing", help="Generate daily briefing")
    briefing_parser.add_argument("--days", "-d", type=int, default=7, help="Days to include")

    # topicmap command
    topicmap_parser = subparsers.add_parser("topicmap", help="Generate topic map visualization")
    topicmap_parser.add_argument("--limit", "-l", type=int, default=1000, help="Max content to analyze")
    topicmap_parser.add_argument("--min-cluster", type=int, default=5, help="Min items per cluster")
    topicmap_parser.add_argument("--html", action="store_true", help="Generate interactive HTML")

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

    # synthesize command
    synth_parser = subparsers.add_parser("synthesize", help="Multi-source synthesis")
    synth_parser.add_argument("query", help="Research question")
    synth_parser.add_argument(
        "--mode", "-m",
        choices=["compare", "timeline", "summarize", "contradict"],
        default="summarize",
        help="Synthesis mode (default: summarize)"
    )
    synth_parser.add_argument(
        "--min-sources", type=int, default=3,
        help="Minimum different sources to include (default: 3)"
    )
    synth_parser.add_argument(
        "--chunks-per-source", type=int, default=3,
        help="Max chunks per source (default: 3)"
    )
    synth_parser.add_argument(
        "--sources", type=str, default=None,
        help="Comma-separated source IDs to limit to"
    )
    synth_parser.add_argument("-v", "--verbose", action="store_true", help="Show source details")
    synth_parser.add_argument(
        "--output", "-o",
        choices=["briefing", "email", "markdown"],
        help="Output format (default: raw synthesis)"
    )
    synth_parser.add_argument(
        "--audience",
        choices=["general", "technical", "executive"],
        default="general",
        help="Audience for briefing format"
    )
    synth_parser.add_argument(
        "--recipient",
        help="Recipient context for email format"
    )
    synth_parser.add_argument(
        "--save", "-s",
        action="store_true",
        help="Save output to file"
    )

    # annotate command with subcommands
    ann_parser = subparsers.add_parser("annotate", help="Add annotations to chunks")
    ann_subparsers = ann_parser.add_subparsers(dest="subcommand", help="Annotation type")

    # annotate note
    note_parser = ann_subparsers.add_parser("note", help="Add a text note")
    note_parser.add_argument("target_id", help="Chunk or content ID")
    note_parser.add_argument("note", help="Note text")
    note_parser.add_argument("--type", "-t", default="chunk", choices=["chunk", "content"])

    # annotate react
    react_parser = ann_subparsers.add_parser("react", help="Add a reaction")
    react_parser.add_argument("target_id", help="Chunk or content ID")
    react_parser.add_argument("reaction", choices=["agree", "disagree", "interesting", "important", "question"])
    react_parser.add_argument("--type", "-t", default="chunk", choices=["chunk", "content"])

    # annotate importance
    imp_parser = ann_subparsers.add_parser("importance", help="Set importance weight")
    imp_parser.add_argument("chunk_id", help="Chunk ID")
    imp_parser.add_argument("weight", type=float, help="Weight (1.0 = normal, 2.0 = double)")

    # annotate list
    list_parser = ann_subparsers.add_parser("list", help="List annotations")
    list_parser.add_argument("--limit", "-l", type=int, default=20)

    # annotate stats
    ann_subparsers.add_parser("stats", help="Show annotation statistics")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    # Commands that don't need API key
    no_api_key_commands = {"annotate", "stats", "topicmap", "thread"}

    # Check for API key (not needed for some commands)
    if args.command not in no_api_key_commands and not os.getenv("OPENROUTER_API_KEY"):
        print("OPENROUTER_API_KEY not set.")
        print("Run with: ./scripts/run_with_secrets.sh python -m modules.ask.cli ...")
        return 1

    commands = {
        "ask": cmd_ask,
        "search": cmd_search,
        "index": cmd_index,
        "stats": cmd_stats,
        "synthesize": cmd_synthesize,
        "annotate": cmd_annotate,
        "quote": cmd_quote,
        "source": cmd_source,
        "thread": cmd_thread,
        "recommend": cmd_recommend,
        "contradict": cmd_contradict,
        "chat": cmd_chat,
        "briefing": cmd_briefing,
        "topicmap": cmd_topicmap,
    }

    return commands[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
