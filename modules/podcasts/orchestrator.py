#!/usr/bin/env python3
"""
Podcast Transcript Orchestrator - The Engine

Processes podcasts from the registry using the appropriate crawler for each.
Can run continuously, processing podcasts one at a time with progress tracking.

Usage:
    python -m modules.podcasts.orchestrator          # Show status
    python -m modules.podcasts.orchestrator --run    # Start crawling
    python -m modules.podcasts.orchestrator --run --method podscripts  # Only Podscripts
    python -m modules.podcasts.orchestrator --run --podcast all-in     # Single podcast
"""

import asyncio
import logging
import json
import time
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional

from .registry import (
    PODCASTS, Podcast, CrawlMethod, CrawlStatus,
    get_ready_podcasts, get_podcast_stats, TranscriptSource
)

logger = logging.getLogger(__name__)


class Orchestrator:
    """Main orchestrator for podcast transcript crawling"""

    def __init__(self, output_dir: str = "data/podcasts", state_file: str = "data/orchestrator_state.json"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.state_file = Path(state_file)
        self.state = self._load_state()

    def _load_state(self) -> Dict[str, Any]:
        """Load orchestrator state from disk"""
        if self.state_file.exists():
            with open(self.state_file) as f:
                return json.load(f)
        return {
            "last_run": None,
            "podcasts_processed": {},
            "total_transcripts": 0,
            "errors": [],
        }

    def _save_state(self):
        """Save orchestrator state to disk"""
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.state_file, 'w') as f:
            json.dump(self.state, f, indent=2, default=str)

    def get_transcript_count(self, podcast_slug: str) -> int:
        """Count existing transcripts for a podcast"""
        transcript_dir = self.output_dir / podcast_slug / "transcripts"
        if transcript_dir.exists():
            return len(list(transcript_dir.glob("*.md")))
        return 0

    def get_total_transcripts(self) -> int:
        """Get total transcript count across all podcasts"""
        total = 0
        for podcast_dir in self.output_dir.iterdir():
            if podcast_dir.is_dir():
                transcript_dir = podcast_dir / "transcripts"
                if transcript_dir.exists():
                    total += len(list(transcript_dir.glob("*.md")))
        return total

    def get_total_size_mb(self) -> float:
        """Get total size of all transcripts in MB"""
        total_bytes = 0
        for podcast_dir in self.output_dir.iterdir():
            if podcast_dir.is_dir():
                transcript_dir = podcast_dir / "transcripts"
                if transcript_dir.exists():
                    for f in transcript_dir.glob("*.md"):
                        total_bytes += f.stat().st_size
        return total_bytes / (1024 * 1024)

    async def crawl_podcast(self, podcast: Podcast, max_episodes: int = 0) -> Dict[str, Any]:
        """Crawl a single podcast using its primary source"""
        source = podcast.primary_source
        if not source:
            return {"error": f"No source configured for {podcast.name}"}

        result = {
            "podcast": podcast.name,
            "slug": podcast.slug,
            "method": source.method.value,
            "started_at": datetime.now().isoformat(),
            "transcripts_before": self.get_transcript_count(podcast.slug),
            "transcripts_after": 0,
            "new_transcripts": 0,
            "errors": [],
        }

        print(f"\n{'='*60}")
        print(f"CRAWLING: {podcast.name}")
        print(f"Method: {source.method.value}")
        print(f"Slug: {source.slug or 'N/A'}")
        print(f"{'='*60}\n")

        try:
            if source.method == CrawlMethod.BULK_CRAWLER:
                result = await self._crawl_bulk(podcast, source, max_episodes, result)

            elif source.method == CrawlMethod.HEADLESS:
                result = await self._crawl_headless(podcast, source, max_episodes, result)

            elif source.method == CrawlMethod.PODSCRIPTS:
                result = await self._crawl_podscripts(podcast, source, max_episodes, result)

            elif source.method == CrawlMethod.TRANSCRIPT_FOREST:
                result = await self._crawl_transcript_forest(podcast, source, max_episodes, result)

            elif source.method == CrawlMethod.NPR_PATTERN:
                result = await self._crawl_npr(podcast, source, max_episodes, result)

            else:
                result["error"] = f"Unsupported method: {source.method.value}"

        except Exception as e:
            result["errors"].append(str(e))
            logger.error(f"Error crawling {podcast.name}: {e}")

        result["transcripts_after"] = self.get_transcript_count(podcast.slug)
        result["new_transcripts"] = result["transcripts_after"] - result["transcripts_before"]
        result["completed_at"] = datetime.now().isoformat()

        # Update state
        self.state["podcasts_processed"][podcast.slug] = {
            "last_crawl": datetime.now().isoformat(),
            "transcripts": result["transcripts_after"],
            "method": source.method.value,
        }
        self._save_state()

        return result

    async def _crawl_bulk(self, podcast: Podcast, source: TranscriptSource,
                          max_episodes: int, result: Dict) -> Dict:
        """Use bulk_crawler for official sites"""
        from .resolvers.bulk_crawler import BulkTranscriptCrawler

        crawler = BulkTranscriptCrawler(str(self.output_dir))

        if source.slug not in crawler.TRANSCRIPT_SITES:
            result["error"] = f"Unknown bulk crawler site: {source.slug}"
            return result

        results = crawler.crawl_site_bulk(source.slug, max_episodes or None)
        saved = crawler.save_transcripts(results, podcast.slug)
        result["new_transcripts"] = saved
        return result

    async def _crawl_headless(self, podcast: Podcast, source: TranscriptSource,
                               max_episodes: int, result: Dict) -> Dict:
        """Use headless browser for JS-rendered sites"""
        from .resolvers.headless_crawler import HeadlessCrawler

        crawler = HeadlessCrawler(str(self.output_dir))

        # Route to appropriate crawler based on slug
        if 'dwarkesh' in source.slug.lower():
            crawl_result = await crawler.crawl_dwarkesh(max_episodes or 100)
        elif '99' in source.slug.lower() or 'invisible' in source.slug.lower():
            crawl_result = await crawler.crawl_99pi(max_episodes or 800, max_pages=66)
        else:
            result["error"] = f"No headless handler for: {source.slug}"
            return result

        result["transcripts_saved"] = crawl_result.get("transcripts_saved", 0)
        if crawl_result.get("errors"):
            result["errors"].extend(crawl_result["errors"])

        return result

    async def _crawl_podscripts(self, podcast: Podcast, source: TranscriptSource,
                                 max_episodes: int, result: Dict) -> Dict:
        """Use Podscripts crawler"""
        from .resolvers.podscripts_crawler import PodscriptsCrawler

        crawler = PodscriptsCrawler(str(self.output_dir))

        # Need to map podcast slug to Podscripts key
        podscripts_key = source.slug
        crawl_result = await crawler.crawl_podcast(podscripts_key, max_episodes or 0)

        result["episodes_found"] = crawl_result.get("episodes_found", 0)
        result["transcripts_saved"] = crawl_result.get("transcripts_saved", 0)
        if crawl_result.get("errors"):
            result["errors"].extend(crawl_result["errors"])

        return result

    async def _crawl_transcript_forest(self, podcast: Podcast, source: TranscriptSource,
                                        max_episodes: int, result: Dict) -> Dict:
        """Use TranscriptForest crawler (to be implemented)"""
        # TODO: Implement TranscriptForest crawler
        result["error"] = "TranscriptForest crawler not yet implemented"
        return result

    async def _crawl_npr(self, podcast: Podcast, source: TranscriptSource,
                          max_episodes: int, result: Dict) -> Dict:
        """Use NPR pattern crawler for NPR network podcasts"""
        from .resolvers.npr_crawler import NPRCrawler, NPR_PODCASTS

        crawler = NPRCrawler(str(self.output_dir))

        # Map podcast slug to NPR crawler key
        npr_key = source.slug
        if npr_key not in NPR_PODCASTS:
            result["error"] = f"Unknown NPR podcast: {npr_key}"
            return result

        crawl_result = await crawler.crawl_podcast(npr_key, max_episodes or 0)

        result["episodes_found"] = crawl_result.get("episodes_found", 0)
        result["transcripts_saved"] = crawl_result.get("transcripts_saved", 0)
        result["skipped_existing"] = crawl_result.get("skipped_existing", 0)
        if crawl_result.get("errors"):
            result["errors"].extend(crawl_result["errors"])

        return result

    async def run_all(self, method_filter: Optional[CrawlMethod] = None,
                      podcast_filter: Optional[str] = None,
                      max_episodes: int = 0) -> List[Dict[str, Any]]:
        """Run crawler on all ready podcasts"""
        results = []
        ready = get_ready_podcasts()

        # Apply filters
        if method_filter:
            ready = [p for p in ready if p.primary_source and p.primary_source.method == method_filter]

        if podcast_filter:
            ready = [p for p in ready if podcast_filter.lower() in p.slug.lower()]

        print(f"\n{'='*70}")
        print(f"PODCAST TRANSCRIPT ORCHESTRATOR")
        print(f"{'='*70}")
        print(f"Ready to crawl: {len(ready)} podcasts")
        if method_filter:
            print(f"Filter: {method_filter.value}")
        if podcast_filter:
            print(f"Podcast filter: {podcast_filter}")
        print(f"{'='*70}\n")

        for i, podcast in enumerate(ready, 1):
            print(f"\n[{i}/{len(ready)}] Processing {podcast.name}...")
            result = await self.crawl_podcast(podcast, max_episodes)
            results.append(result)

            # Brief summary
            if result.get("new_transcripts", 0) > 0:
                print(f"  ✓ Added {result['new_transcripts']} transcripts")
            elif result.get("error"):
                print(f"  ✗ Error: {result['error']}")
            else:
                print(f"  - No new transcripts")

            # Small delay between podcasts
            await asyncio.sleep(2)

        # Final summary
        self._print_summary(results)
        return results

    def _print_summary(self, results: List[Dict[str, Any]]):
        """Print crawl summary"""
        total_new = sum(r.get("new_transcripts", 0) for r in results)
        errors = [r for r in results if r.get("errors") or r.get("error")]

        print(f"\n{'='*70}")
        print("CRAWL SUMMARY")
        print(f"{'='*70}")
        print(f"Podcasts processed: {len(results)}")
        print(f"New transcripts: {total_new}")
        print(f"Total transcripts: {self.get_total_transcripts()}")
        print(f"Total size: {self.get_total_size_mb():.1f} MB")
        if errors:
            print(f"Errors: {len(errors)}")
            for e in errors[:5]:
                print(f"  - {e.get('podcast', 'Unknown')}: {e.get('error', e.get('errors', [])[:1])}")
        print(f"{'='*70}\n")

    def print_status(self):
        """Print current status of all podcasts"""
        stats = get_podcast_stats()

        print(f"\n{'='*70}")
        print("PODCAST TRANSCRIPT STATUS")
        print(f"{'='*70}")
        print(f"\nTotal podcasts in registry: {stats['total_podcasts']}")
        print(f"Estimated total episodes: {stats['estimated_total_episodes']:,}")
        print(f"\nCurrent collection:")
        print(f"  Transcripts: {self.get_total_transcripts():,}")
        print(f"  Size: {self.get_total_size_mb():.1f} MB")

        print(f"\nBy Status:")
        for status, count in stats['by_status'].items():
            print(f"  {status}: {count}")

        # Show per-podcast counts
        print(f"\n{'-'*70}")
        print("PER-PODCAST TRANSCRIPT COUNTS:")
        print(f"{'-'*70}")

        for slug, podcast in sorted(PODCASTS.items(), key=lambda x: x[1].name):
            count = self.get_transcript_count(podcast.slug)
            status_icon = "✓" if podcast.status == CrawlStatus.COMPLETE else "○" if count > 0 else " "
            method = podcast.primary_source.method.value if podcast.primary_source else "none"
            print(f"  {status_icon} {podcast.name:40} {count:5} / ~{podcast.estimated_episodes:5}  [{method}]")

        print(f"\n{'='*70}\n")


def main():
    """CLI entrypoint"""
    import argparse

    parser = argparse.ArgumentParser(description="Podcast Transcript Orchestrator")
    parser.add_argument("--run", action="store_true", help="Start crawling")
    parser.add_argument("--method", type=str, help="Filter by method (bulk_crawler, headless, podscripts, etc)")
    parser.add_argument("--podcast", type=str, help="Filter by podcast slug (partial match)")
    parser.add_argument("--max-episodes", type=int, default=0, help="Max episodes per podcast (0=all)")

    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

    orchestrator = Orchestrator()

    if args.run:
        # Parse method filter
        method_filter = None
        if args.method:
            try:
                method_filter = CrawlMethod(args.method)
            except ValueError:
                print(f"Unknown method: {args.method}")
                print(f"Available: {[m.value for m in CrawlMethod]}")
                return

        asyncio.run(orchestrator.run_all(
            method_filter=method_filter,
            podcast_filter=args.podcast,
            max_episodes=args.max_episodes
        ))
    else:
        orchestrator.print_status()


if __name__ == "__main__":
    main()
