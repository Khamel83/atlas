#!/usr/bin/env python3
"""
Atlas Podcast Transcript Sourcing CLI

Main command-line interface for managing podcast transcript discovery and fetching.
"""

import argparse
import sys
import logging
from pathlib import Path
import time
import csv
from datetime import datetime
from typing import Dict, Any

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent))

from modules.podcasts.store import PodcastStore, Podcast, Episode, DiscoveryRun
from modules.podcasts.rss import RSSParser
from modules.podcasts.matchers import load_mapping_config, create_slug
from modules.podcasts.export import TranscriptExporter
from modules.podcasts.resolvers.rss_link import RSSLinkResolver
from modules.podcasts.resolvers.generic_html import GenericHTMLResolver
from modules.podcasts.resolvers.pattern import PatternResolver
from modules.podcasts.resolvers.youtube_transcript import YouTubeTranscriptResolver
from modules.podcasts.resolvers.network_transcripts import NetworkTranscriptResolver

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class AtlasPodCLI:
    """Main CLI application"""

    def __init__(self):
        self.store = None
        self.rss_parser = RSSParser()
        self.exporter = TranscriptExporter()
        # Priority order: highest accuracy first
        self.resolvers = {
            "youtube_transcript": YouTubeTranscriptResolver(),
            "network_transcripts": NetworkTranscriptResolver(),
            "rss_link": RSSLinkResolver(),
            "generic_html": GenericHTMLResolver(),
            "pattern": PatternResolver(),
        }

    def init_store(self, db_path: str = "data/podcasts/atlas_podcasts.db"):
        """Initialize database store"""
        self.store = PodcastStore(db_path)
        logger.info(f"Initialized database at {db_path}")

    def cmd_init(self, args):
        """Initialize the podcast database"""
        db_path = args.db_path or "data/podcasts/atlas_podcasts.db"

        # Create directory if needed
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)

        # Initialize store
        self.init_store(db_path)

        print(f"✅ Initialized Atlas podcast database at {db_path}")

        # Show initial stats
        stats = self.store.get_stats()
        print(f"📊 Total podcasts: {stats['total_podcasts']}")

    def cmd_validate(self, args):
        """Validate podcast configuration CSV"""
        csv_path = args.csv

        if not Path(csv_path).exists():
            print(f"❌ CSV file not found: {csv_path}")
            return False

        try:
            with open(csv_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                podcasts = list(reader)

            print(f"📋 Validating {len(podcasts)} podcasts from {csv_path}")

            valid_count = 0
            errors = []

            for i, row in enumerate(podcasts, 1):
                # Check required fields
                name = row.get("Podcast Name", "").strip()
                rss_url = row.get("RSS URL", "").strip()

                if not name:
                    errors.append(f"Row {i}: Missing podcast name")
                    continue

                if not rss_url:
                    errors.append(f"Row {i}: Missing RSS URL for '{name}'")
                    continue

                # Check URL format
                if not rss_url.startswith(("http://", "https://")):
                    errors.append(f"Row {i}: Invalid RSS URL for '{name}': {rss_url}")
                    continue

                valid_count += 1

            if errors:
                print(f"❌ Validation failed with {len(errors)} errors:")
                for error in errors[:10]:  # Show first 10 errors
                    print(f"   {error}")
                if len(errors) > 10:
                    print(f"   ... and {len(errors) - 10} more errors")
                return False
            else:
                print(f"✅ Validation passed: {valid_count} valid podcasts")
                return True

        except Exception as e:
            print(f"❌ Error reading CSV: {e}")
            return False

    def cmd_register(self, args):
        """Register podcasts from CSV configuration"""
        if not self.store:
            self.init_store()

        csv_path = args.csv

        # Validate first
        if not self.cmd_validate(args):
            return False

        try:
            with open(csv_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                podcasts = list(reader)

            # Load mapping config if it exists
            mapping_config = {}
            mapping_path = Path("config/mapping.yml")
            if mapping_path.exists():
                mapping_config = load_mapping_config(str(mapping_path))

            registered_count = 0
            skipped_count = 0

            for row in podcasts:
                name = row.get("Podcast Name", "").strip()
                exclude = row.get("Exclude", "0").strip()

                # Skip excluded podcasts
                if exclude == "1":
                    skipped_count += 1
                    continue

                slug = create_slug(name)

                # Check if already registered
                existing = self.store.get_podcast_by_slug(slug)
                if existing:
                    logger.info(f"Podcast already registered: {name}")
                    continue

                # Get RSS URL and other config
                rss_url = row.get("RSS URL", "").strip()
                site_url = row.get("Site URL", "").strip()

                # Get mapping config for this podcast
                podcast_config = mapping_config.get(slug, {})

                podcast = Podcast(
                    name=name,
                    slug=slug,
                    rss_url=rss_url,
                    site_url=site_url or podcast_config.get("site_url", ""),
                    resolver=podcast_config.get("resolver", "generic_html"),
                    episode_selector=podcast_config.get("episode_selector", ""),
                    transcript_selector=podcast_config.get("transcript_selector", ""),
                    config=podcast_config,
                )

                podcast_id = self.store.create_podcast(podcast)
                logger.info(f"Registered podcast: {name} (ID: {podcast_id})")
                registered_count += 1

            print(f"✅ Registered {registered_count} podcasts")
            if skipped_count:
                print(f"⏭️  Skipped {skipped_count} excluded podcasts")

            return True

        except Exception as e:
            print(f"❌ Error registering podcasts: {e}")
            return False

    def cmd_discover(self, args):
        """Discover episodes and transcript sources"""
        if not self.store:
            self.init_store()

        # Get podcasts to process
        if args.all:
            podcasts = self.store.list_podcasts()
        elif args.slug:
            podcast = self.store.get_podcast_by_slug(args.slug)
            podcasts = [podcast] if podcast else []
        else:
            print("❌ Must specify --all or --slug")
            return False

        if not podcasts:
            print("❌ No podcasts found to discover")
            return False

        print(f"🔍 Starting discovery for {len(podcasts)} podcasts...")

        total_episodes = 0
        total_transcripts = 0

        for podcast in podcasts:
            print(f"📡 Discovering episodes for: {podcast.name}")

            start_time = time.time()
            run = DiscoveryRun(
                podcast_id=podcast.id,
                resolver="rss",
                started_at=datetime.now().isoformat(),
            )
            run_id = self.store.create_discovery_run(run)

            try:
                # Parse RSS feed
                episodes = self.rss_parser.parse_feed(podcast.rss_url)
                episodes_found = 0
                transcripts_found = 0
                errors = 0

                for rss_episode in episodes:
                    try:
                        # Create episode record
                        episode = Episode(
                            podcast_id=podcast.id,
                            guid=rss_episode.guid,
                            title=rss_episode.title,
                            url=rss_episode.url,
                            publish_date=(
                                rss_episode.publish_date.isoformat()
                                if rss_episode.publish_date
                                else None
                            ),
                            transcript_status="unknown",
                            metadata={
                                "description": rss_episode.description,
                                "duration": rss_episode.duration,
                                "audio_url": rss_episode.audio_url,
                                "transcript_links": rss_episode.transcript_links,
                            },
                        )

                        # Check for transcript links
                        if rss_episode.transcript_links:
                            episode.transcript_status = "found"
                            episode.transcript_url = rss_episode.transcript_links[
                                0
                            ]  # Use first link
                            transcripts_found += 1

                        self.store.create_episode(episode)
                        episodes_found += 1

                    except Exception as e:
                        logger.error(
                            f"Error processing episode {rss_episode.title}: {e}"
                        )
                        errors += 1

                # Complete discovery run
                duration = time.time() - start_time
                self.store.complete_discovery_run(
                    run_id, episodes_found, transcripts_found, errors, duration
                )

                print(
                    f"   📊 Found {episodes_found} episodes, {transcripts_found} with transcripts"
                )
                total_episodes += episodes_found
                total_transcripts += transcripts_found

            except Exception as e:
                logger.error(f"Error discovering episodes for {podcast.name}: {e}")
                duration = time.time() - start_time
                self.store.complete_discovery_run(run_id, 0, 0, 1, duration, "failed")

        print(
            f"✅ Discovery complete: {total_episodes} episodes, {total_transcripts} transcripts found"
        )
        return True

    def cmd_fetch_transcripts(self, args):
        """Fetch transcript content"""
        if not self.store:
            self.init_store()

        # Get podcasts to process
        if args.all:
            podcasts = self.store.list_podcasts()
        elif args.slug:
            podcast = self.store.get_podcast_by_slug(args.slug)
            podcasts = [podcast] if podcast else []
        else:
            print("❌ Must specify --all or --slug")
            return False

        if not podcasts:
            print("❌ No podcasts found to process")
            return False

        print(f"📥 Starting transcript fetching for {len(podcasts)} podcasts...")

        # Load mapping config
        mapping_config = {}
        mapping_path = Path("config/mapping.yml")
        if mapping_path.exists():
            mapping_config = load_mapping_config(str(mapping_path))

        total_fetched = 0
        total_failed = 0

        for podcast in podcasts:
            print(f"📥 Fetching transcripts for: {podcast.name}")

            # Get episodes that need transcript fetching
            episodes = self.store.get_episodes_by_podcast(podcast.id)
            episodes_to_fetch = [
                ep for ep in episodes if ep.transcript_status == "found"
            ]

            if not episodes_to_fetch:
                print("   ℹ️  No episodes with transcript sources to fetch")
                continue

            print(
                f"   📊 Processing {len(episodes_to_fetch)} episodes with transcript sources"
            )

            podcast_config = mapping_config.get(podcast.slug, {})
            podcast_config.update(
                {
                    "rss_url": podcast.rss_url,
                    "site_url": podcast.site_url,
                    "resolver": podcast.resolver,
                }
            )

            fetched_count = 0
            failed_count = 0

            for episode in episodes_to_fetch:
                try:
                    success = self._fetch_episode_transcript(
                        episode, podcast, podcast_config
                    )
                    if success:
                        fetched_count += 1
                        total_fetched += 1
                    else:
                        failed_count += 1
                        total_failed += 1

                except Exception as e:
                    logger.error(f"Error fetching transcript for {episode.title}: {e}")
                    failed_count += 1
                    total_failed += 1

            print(f"   ✅ Fetched {fetched_count} transcripts, {failed_count} failed")

        print(
            f"🎯 Transcript fetching complete: {total_fetched} fetched, {total_failed} failed"
        )
        return True

    def _fetch_episode_transcript(
        self, episode: Episode, podcast: Podcast, podcast_config: Dict[str, Any]
    ) -> bool:
        """Fetch transcript for a single episode"""
        try:
            # Use resolvers to get transcript content
            all_sources = []

            # Try each resolver
            for resolver_name, resolver in self.resolvers.items():
                try:
                    sources = resolver.resolve(episode, podcast_config)
                    all_sources.extend(sources)
                except Exception as e:
                    logger.error(f"Error in {resolver_name} resolver: {e}")

            if not all_sources:
                logger.warning(f"No transcript sources found for: {episode.title}")
                self.store.update_episode_transcript_status(episode.id, "failed")
                return False

            # Sort by confidence and try each source
            all_sources.sort(key=lambda x: x["confidence"], reverse=True)

            for source in all_sources:
                try:
                    # Check if source already contains content
                    if "content" in source["metadata"]:
                        content = source["metadata"]["content"]

                        if content and len(content) > 100:
                            # Export transcript
                            transcript_path = self.exporter.export_transcript(
                                podcast,
                                episode,
                                content,
                                source["url"],
                                source["metadata"],
                            )

                            # Update episode status
                            self.store.update_episode_transcript_status(
                                episode.id, "fetched", transcript_path
                            )

                            logger.info(f"Fetched transcript for: {episode.title}")
                            return True

                except Exception as e:
                    logger.error(f"Error processing source {source['url']}: {e}")
                    continue

            # If no sources worked, mark as failed
            self.store.update_episode_transcript_status(episode.id, "failed")
            return False

        except Exception as e:
            logger.error(f"Error fetching transcript for {episode.title}: {e}")
            self.store.update_episode_transcript_status(episode.id, "failed")
            return False

    def cmd_watch(self, args):
        """Watch mode for continuous discovery"""
        print("👀 Watch mode not yet implemented")
        print(f"📋 This will run discovery every {args.interval} minutes")
        return True

    def cmd_doctor(self, args):
        """Diagnostic information"""
        if not self.store:
            self.init_store()

        print("🏥 Atlas Podcast System Diagnostics")
        print("=" * 40)

        # Database stats
        stats = self.store.get_stats()
        print("📊 Database Statistics:")
        print(f"   Total podcasts: {stats['total_podcasts']}")

        if stats["episodes_by_status"]:
            print("   Episodes by status:")
            for status, count in stats["episodes_by_status"].items():
                print(f"     {status}: {count}")

        # Recent runs
        if stats["recent_runs"]:
            print("\n🔄 Recent Discovery Runs:")
            for run in stats["recent_runs"][:5]:
                print(
                    f"   Podcast {run['podcast_id']}: {run['episodes_found']} episodes, "
                    f"{run['transcripts_found']} transcripts ({run['status']})"
                )

        # File system check
        print("\n📁 File System:")
        data_dir = Path("data/podcasts")
        if data_dir.exists():
            print(f"   Data directory: ✅ {data_dir}")
        else:
            print(f"   Data directory: ❌ {data_dir} (not found)")

        config_dir = Path("config")
        if config_dir.exists():
            print(f"   Config directory: ✅ {config_dir}")
            mapping_file = config_dir / "mapping.yml"
            if mapping_file.exists():
                print(f"   Mapping config: ✅ {mapping_file}")
            else:
                print(f"   Mapping config: ❌ {mapping_file} (not found)")
        else:
            print(f"   Config directory: ❌ {config_dir} (not found)")

        return True


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="Atlas Podcast Transcript Sourcing CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    # Global options
    parser.add_argument(
        "--db-path", help="Database path (default: data/podcasts/atlas_podcasts.db)"
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose logging")

    # Subcommands
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # init command
    init_parser = subparsers.add_parser("init", help="Initialize podcast database")

    # validate command
    validate_parser = subparsers.add_parser("validate", help="Validate podcast CSV")
    validate_parser.add_argument(
        "--csv", required=True, help="Path to podcast CSV file"
    )

    # register command
    register_parser = subparsers.add_parser(
        "register", help="Register podcasts from CSV"
    )
    register_parser.add_argument(
        "--csv", required=True, help="Path to podcast CSV file"
    )

    # discover command
    discover_parser = subparsers.add_parser(
        "discover", help="Discover episodes and transcripts"
    )
    discover_group = discover_parser.add_mutually_exclusive_group(required=True)
    discover_group.add_argument(
        "--all", action="store_true", help="Process all podcasts"
    )
    discover_group.add_argument("--slug", help="Process specific podcast by slug")

    # fetch-transcripts command
    fetch_parser = subparsers.add_parser(
        "fetch-transcripts", help="Fetch transcript content"
    )
    fetch_group = fetch_parser.add_mutually_exclusive_group(required=True)
    fetch_group.add_argument(
        "--all", action="store_true", help="Fetch all available transcripts"
    )
    fetch_group.add_argument("--slug", help="Fetch transcripts for specific podcast")

    # watch command
    watch_parser = subparsers.add_parser(
        "watch", help="Watch mode for continuous discovery"
    )
    watch_parser.add_argument("--all", action="store_true", help="Watch all podcasts")
    watch_parser.add_argument(
        "--interval", default="30m", help="Discovery interval (default: 30m)"
    )

    # doctor command
    doctor_parser = subparsers.add_parser("doctor", help="System diagnostics")

    # Parse arguments
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    # Set logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Create CLI instance and run command
    cli = AtlasPodCLI()

    try:
        # Map commands to methods
        command_map = {
            "init": cli.cmd_init,
            "validate": cli.cmd_validate,
            "register": cli.cmd_register,
            "discover": cli.cmd_discover,
            "fetch-transcripts": cli.cmd_fetch_transcripts,
            "watch": cli.cmd_watch,
            "doctor": cli.cmd_doctor,
        }

        if args.command in command_map:
            success = command_map[args.command](args)
            return 0 if success else 1
        else:
            print(f"❌ Unknown command: {args.command}")
            return 1

    except KeyboardInterrupt:
        print("\n⚠️  Interrupted by user")
        return 1
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        if args.verbose:
            import traceback

            traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
