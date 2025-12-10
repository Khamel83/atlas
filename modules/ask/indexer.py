"""
Content indexer for Atlas Ask.

Indexes content from the Atlas storage into the vector store.
Can be run as a one-shot batch job or hooked into the ingest pipeline.

Usage:
    # Index all unindexed content
    python -m modules.ask.indexer --all

    # Index specific content type
    python -m modules.ask.indexer --type podcasts
    python -m modules.ask.indexer --type articles

    # Dry run
    python -m modules.ask.indexer --all --dry-run
"""

import logging
import sqlite3
from pathlib import Path
from typing import List, Optional, Set, Iterator, Tuple
from dataclasses import dataclass
from datetime import datetime
import json

from .config import get_config, AskConfig
from .embeddings import EmbeddingClient
from .chunker import ContentChunker
from .vector_store import VectorStore

logger = logging.getLogger(__name__)


@dataclass
class ContentItem:
    """A piece of content to index."""
    content_id: str
    content_type: str  # "podcast", "article", "newsletter", etc.
    title: str
    text: str
    source_path: Path
    metadata: dict


class ContentIndexer:
    """
    Indexes Atlas content into the vector store.

    Discovers content from:
    - data/podcasts/{slug}/transcripts/*.md
    - data/content/article/{date}/{id}/content.md
    - data/content/newsletter/{date}/{id}/content.md
    - data/stratechery/{articles,podcasts}/*.md
    """

    def __init__(self, config: Optional[AskConfig] = None):
        self.config = config or get_config()
        self.embedding_client = EmbeddingClient(self.config)
        self.chunker = ContentChunker(self.config)
        self.vector_store = VectorStore(self.config)

        # Base paths
        self.data_dir = Path("data")
        self.podcasts_dir = self.data_dir / "podcasts"
        self.content_dir = self.data_dir / "content"
        self.stratechery_dir = self.data_dir / "stratechery"

    def get_indexed_content_ids(self) -> Set[str]:
        """Get set of already-indexed content IDs."""
        conn = self.vector_store._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT content_id FROM chunks")
        return {row[0] for row in cursor.fetchall()}

    def discover_podcasts(self) -> Iterator[ContentItem]:
        """Discover podcast transcripts."""
        if not self.podcasts_dir.exists():
            return

        for slug_dir in self.podcasts_dir.iterdir():
            if not slug_dir.is_dir():
                continue

            transcripts_dir = slug_dir / "transcripts"
            if not transcripts_dir.exists():
                continue

            for md_file in transcripts_dir.glob("*.md"):
                content_id = f"podcast:{slug_dir.name}:{md_file.stem}"

                try:
                    text = md_file.read_text()
                    if len(text) < 100:
                        continue

                    # Extract title from first line or filename
                    lines = text.strip().split('\n')
                    title = lines[0].lstrip('#').strip() if lines else md_file.stem

                    yield ContentItem(
                        content_id=content_id,
                        content_type="podcast",
                        title=title,
                        text=text,
                        source_path=md_file,
                        metadata={
                            "slug": slug_dir.name,
                            "filename": md_file.name,
                            "title": title,
                        }
                    )
                except Exception as e:
                    logger.warning(f"Failed to read {md_file}: {e}")

    def discover_articles(self) -> Iterator[ContentItem]:
        """Discover article content."""
        articles_dir = self.content_dir / "article"
        if not articles_dir.exists():
            return

        for date_dir in articles_dir.iterdir():
            if not date_dir.is_dir():
                continue

            for content_dir in date_dir.iterdir():
                if not content_dir.is_dir():
                    continue

                content_file = content_dir / "content.md"
                if not content_file.exists():
                    continue

                content_id = f"article:{date_dir.name}:{content_dir.name}"

                try:
                    text = content_file.read_text()
                    if len(text) < 100:
                        continue

                    # Try to get title from metadata.json
                    metadata_file = content_dir / "metadata.json"
                    metadata = {}
                    title = content_dir.name

                    if metadata_file.exists():
                        try:
                            metadata = json.loads(metadata_file.read_text())
                            title = metadata.get("title", title)
                        except (json.JSONDecodeError, IOError) as e:
                            logger.debug(f"Error reading metadata {metadata_file}: {e}")

                    yield ContentItem(
                        content_id=content_id,
                        content_type="article",
                        title=title,
                        text=text,
                        source_path=content_file,
                        metadata={
                            "date": date_dir.name,
                            "title": title,
                            **metadata,
                        }
                    )
                except Exception as e:
                    logger.warning(f"Failed to read {content_file}: {e}")

    def discover_newsletters(self) -> Iterator[ContentItem]:
        """Discover newsletter content."""
        newsletters_dir = self.content_dir / "newsletter"
        if not newsletters_dir.exists():
            return

        for date_dir in newsletters_dir.iterdir():
            if not date_dir.is_dir():
                continue

            for content_dir in date_dir.iterdir():
                if not content_dir.is_dir():
                    continue

                content_file = content_dir / "content.md"
                if not content_file.exists():
                    continue

                content_id = f"newsletter:{date_dir.name}:{content_dir.name}"

                try:
                    text = content_file.read_text()
                    if len(text) < 100:
                        continue

                    metadata_file = content_dir / "metadata.json"
                    metadata = {}
                    title = content_dir.name

                    if metadata_file.exists():
                        try:
                            metadata = json.loads(metadata_file.read_text())
                            title = metadata.get("title", title)
                        except (json.JSONDecodeError, IOError) as e:
                            logger.debug(f"Error reading metadata {metadata_file}: {e}")

                    yield ContentItem(
                        content_id=content_id,
                        content_type="newsletter",
                        title=title,
                        text=text,
                        source_path=content_file,
                        metadata={
                            "date": date_dir.name,
                            "title": title,
                            **metadata,
                        }
                    )
                except Exception as e:
                    logger.warning(f"Failed to read {content_file}: {e}")

    def discover_stratechery(self) -> Iterator[ContentItem]:
        """Discover Stratechery archive content."""
        if not self.stratechery_dir.exists():
            return

        for subdir in ["articles", "podcasts"]:
            content_dir = self.stratechery_dir / subdir
            if not content_dir.exists():
                continue

            content_type = "stratechery-article" if subdir == "articles" else "stratechery-podcast"

            for md_file in content_dir.glob("*.md"):
                content_id = f"stratechery:{subdir}:{md_file.stem}"

                try:
                    text = md_file.read_text()
                    if len(text) < 100:
                        continue

                    lines = text.strip().split('\n')
                    title = lines[0].lstrip('#').strip() if lines else md_file.stem

                    yield ContentItem(
                        content_id=content_id,
                        content_type=content_type,
                        title=title,
                        text=text,
                        source_path=md_file,
                        metadata={
                            "type": subdir,
                            "filename": md_file.name,
                            "title": title,
                        }
                    )
                except Exception as e:
                    logger.warning(f"Failed to read {md_file}: {e}")

    def discover_all(self, content_types: Optional[List[str]] = None) -> Iterator[ContentItem]:
        """Discover all content, optionally filtered by type."""
        types = content_types or ["podcasts", "articles", "newsletters", "stratechery"]

        if "podcasts" in types:
            yield from self.discover_podcasts()
        if "articles" in types:
            yield from self.discover_articles()
        if "newsletters" in types:
            yield from self.discover_newsletters()
        if "stratechery" in types:
            yield from self.discover_stratechery()

    def index_content(
        self,
        item: ContentItem,
        force: bool = False,
    ) -> int:
        """
        Index a single content item.

        Returns number of chunks indexed.
        """
        # Check if already indexed
        if not force:
            existing = self.vector_store.get_chunks_for_content(item.content_id)
            if existing:
                logger.debug(f"Already indexed: {item.content_id}")
                return 0

        # Chunk the content
        chunks = self.chunker.chunk_text(
            item.text,
            content_id=item.content_id,
            metadata={
                "title": item.title,
                "type": item.content_type,
                **item.metadata,
            }
        )

        if not chunks:
            logger.debug(f"No chunks generated for: {item.content_id}")
            return 0

        # Generate embeddings
        chunk_texts = [c.text for c in chunks]
        embeddings = self.embedding_client.embed_chunks(chunk_texts)

        # Store
        self.vector_store.store_chunks(chunks, embeddings)

        logger.debug(f"Indexed {len(chunks)} chunks for: {item.content_id}")
        return len(chunks)

    def index_all(
        self,
        content_types: Optional[List[str]] = None,
        force: bool = False,
        dry_run: bool = False,
        batch_size: int = 50,
    ) -> Tuple[int, int]:
        """
        Index all unindexed content.

        Returns (items_indexed, chunks_indexed).
        """
        indexed_ids = set() if force else self.get_indexed_content_ids()

        items_indexed = 0
        chunks_indexed = 0
        batch = []

        for item in self.discover_all(content_types):
            if item.content_id in indexed_ids:
                continue

            if dry_run:
                logger.info(f"Would index: {item.content_id} ({item.title[:50]}...)")
                items_indexed += 1
                continue

            batch.append(item)

            if len(batch) >= batch_size:
                for batch_item in batch:
                    try:
                        chunks = self.index_content(batch_item, force=force)
                        if chunks > 0:
                            items_indexed += 1
                            chunks_indexed += chunks
                    except Exception as e:
                        logger.error(f"Failed to index {batch_item.content_id}: {e}")

                logger.info(f"Progress: {items_indexed} items, {chunks_indexed} chunks")
                batch = []

        # Process remaining batch
        for batch_item in batch:
            try:
                chunks = self.index_content(batch_item, force=force)
                if chunks > 0:
                    items_indexed += 1
                    chunks_indexed += chunks
            except Exception as e:
                logger.error(f"Failed to index {batch_item.content_id}: {e}")

        return items_indexed, chunks_indexed

    def close(self):
        """Close connections."""
        self.vector_store.close()


def index_single(content_id: str, text: str, title: str, content_type: str, metadata: dict = None):
    """
    Convenience function to index a single piece of content.

    Call this from your ingest pipeline after saving content.

    Example:
        from modules.ask.indexer import index_single

        # After saving a podcast transcript
        index_single(
            content_id=f"podcast:{slug}:{episode_id}",
            text=transcript_text,
            title=episode_title,
            content_type="podcast",
            metadata={"slug": slug}
        )
    """
    indexer = ContentIndexer()
    try:
        item = ContentItem(
            content_id=content_id,
            content_type=content_type,
            title=title,
            text=text,
            source_path=Path("."),  # Not used for direct indexing
            metadata=metadata or {},
        )
        return indexer.index_content(item)
    finally:
        indexer.close()


def main():
    """CLI entry point."""
    import argparse
    import sys
    import os

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s: %(message)s"
    )

    parser = argparse.ArgumentParser(description="Index Atlas content")
    parser.add_argument("--all", action="store_true", help="Index all content types")
    parser.add_argument("--type", dest="content_type", choices=["podcasts", "articles", "newsletters", "stratechery"], help="Index specific type")
    parser.add_argument("--force", action="store_true", help="Re-index existing content")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be indexed")
    parser.add_argument("--batch-size", type=int, default=50, help="Batch size for indexing")

    args = parser.parse_args()

    if not args.all and not args.content_type:
        parser.print_help()
        return 1

    if not os.getenv("OPENROUTER_API_KEY"):
        print("OPENROUTER_API_KEY not set.")
        print("Run with: ./scripts/run_with_secrets.sh python -m modules.ask.indexer ...")
        return 1

    content_types = None
    if args.content_type:
        content_types = [args.content_type]

    indexer = ContentIndexer()
    try:
        items, chunks = indexer.index_all(
            content_types=content_types,
            force=args.force,
            dry_run=args.dry_run,
            batch_size=args.batch_size,
        )

        if args.dry_run:
            print(f"\nWould index {items} items")
        else:
            print(f"\nIndexed {items} items ({chunks} chunks)")

            stats = indexer.vector_store.get_stats()
            print(f"\nVector store: {stats['total_chunks']} total chunks, {stats['total_content']} content items")

    finally:
        indexer.close()

    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
