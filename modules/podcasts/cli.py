#!/usr/bin/env python3
"""
Atlas Podcast Transcript Sourcing CLI

Main command-line interface for managing podcast transcript discovery and fetching.
"""

import argparse
import sys
import logging
import json
from pathlib import Path
import time
import csv
from datetime import datetime
from typing import Dict, Any, Optional

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
from modules.podcasts.resolvers.podscripts import PodscriptsResolver

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
        # Priority order: highest accuracy/reliability first
        self.resolvers = {
            "rss_link": RSSLinkResolver(),           # Best: direct links from RSS
            "network_transcripts": NetworkTranscriptResolver(),  # Good: official network pages
            "podscripts": PodscriptsResolver(),      # Good: AI transcripts, many podcasts
            "youtube_transcript": YouTubeTranscriptResolver(),   # Good but often blocked
            "generic_html": GenericHTMLResolver(),   # Fallback: scrape episode pages
            "pattern": PatternResolver(),            # Last resort: pattern matching
        }

    def init_store(self, db_path: str = "data/podcasts/atlas_podcasts.db"):
        """Initialize database store"""
        self.store = PodcastStore(db_path)
        logger.info(f"Initialized database at {db_path}")

    def _load_limits_config(self) -> Dict[str, Dict]:
        """Load podcast limits from config file"""
        limits_path = Path("config/podcast_limits.json")
        if not limits_path.exists():
            logger.warning(f"No limits config found at {limits_path}")
            return {}

        try:
            with open(limits_path) as f:
                config = json.load(f)
            # Remove comments
            return {k: v for k, v in config.items() if not k.startswith("_")}
        except Exception as e:
            logger.error(f"Error loading limits config: {e}")
            return {}

    def _get_podcast_limit(self, slug: str, limits: Dict) -> Optional[int]:
        """Get episode limit for a podcast, returns None if excluded"""
        config = limits.get(slug, {})
        if config.get("exclude", False):
            return None
        return config.get("limit", 0)

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

        # Load limits config
        limits = self._load_limits_config()
        respect_limits = not getattr(args, 'no_limits', False)

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
        if respect_limits and limits:
            print(f"   Using limits from config/podcast_limits.json")

        total_episodes = 0
        total_transcripts = 0
        skipped_podcasts = 0

        for podcast in podcasts:
            # Check limits
            if respect_limits and limits:
                limit = self._get_podcast_limit(podcast.slug, limits)
                if limit is None:
                    logger.debug(f"Skipping excluded podcast: {podcast.name}")
                    skipped_podcasts += 1
                    continue
                if limit == 0:
                    logger.debug(f"Skipping podcast with limit 0: {podcast.name}")
                    skipped_podcasts += 1
                    continue
            else:
                limit = None  # No limit

            print(f"📡 Discovering episodes for: {podcast.name}" + (f" (limit: {limit})" if limit else ""))

            start_time = time.time()
            run = DiscoveryRun(
                podcast_id=podcast.id,
                resolver="rss",
                started_at=datetime.now().isoformat(),
            )
            run_id = self.store.create_discovery_run(run)

            try:
                # Parse RSS feed
                all_episodes = self.rss_parser.parse_feed(podcast.rss_url)

                # Sort by publish date (most recent first) and apply limit
                all_episodes = sorted(
                    all_episodes,
                    key=lambda e: e.publish_date or datetime.min,
                    reverse=True
                )
                if limit:
                    all_episodes = all_episodes[:limit]
                    logger.debug(f"Limited to {len(all_episodes)} episodes for {podcast.name}")

                episodes_found = 0
                transcripts_found = 0
                errors = 0

                for rss_episode in all_episodes:
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

        summary = f"✅ Discovery complete: {total_episodes} episodes, {total_transcripts} transcripts found"
        if skipped_podcasts > 0:
            summary += f" ({skipped_podcasts} podcasts skipped due to limits)"
        print(summary)
        return True

    def cmd_fetch_transcripts(self, args):
        """Fetch transcript content"""
        if not self.store:
            self.init_store()

        # Load limits config for smart fetching
        limits_config = self._load_limits_config()
        use_limits = bool(limits_config) and not getattr(args, 'no_limits', False)

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

        # Determine which statuses to process
        target_statuses = ["unknown", "found"]  # Default: try unknown AND found
        if hasattr(args, 'status') and args.status:
            target_statuses = [s.strip() for s in args.status.split(",")]

        # Get manual limit if specified (overrides config limits)
        manual_limit = getattr(args, 'limit', None)

        print(f"📥 Starting transcript fetching for {len(podcasts)} podcasts...")
        print(f"   Targeting statuses: {', '.join(target_statuses)}")
        if use_limits:
            print(f"   Using limits from config/podcast_limits.json")
        if manual_limit:
            print(f"   Manual limit: {manual_limit} episodes per podcast")

        # Load mapping config
        mapping_config = {}
        mapping_path = Path("config/mapping.yml")
        if mapping_path.exists():
            mapping_config = load_mapping_config(str(mapping_path))

        total_fetched = 0
        total_failed = 0
        total_skipped = 0
        skipped_podcasts = 0

        for podcast in podcasts:
            # Check limits config for this podcast
            if use_limits:
                config_limit = self._get_podcast_limit(podcast.slug, limits_config)
                if config_limit is None:
                    # Excluded podcast
                    logger.debug(f"Skipping excluded podcast: {podcast.name}")
                    skipped_podcasts += 1
                    continue
                if config_limit == 0:
                    skipped_podcasts += 1
                    continue
            else:
                config_limit = None

            # Get episodes that need transcript fetching
            episodes = self.store.get_episodes_by_podcast(podcast.id)

            # Count already fetched
            already_fetched = len([e for e in episodes if e.transcript_status == "fetched"])

            episodes_to_fetch = [
                ep for ep in episodes if ep.transcript_status in target_statuses
            ]

            # Calculate how many we can still fetch based on limit
            if config_limit and not manual_limit:
                # Use smart limit: only fetch up to (limit - already_fetched)
                remaining_quota = max(0, config_limit - already_fetched)
                if remaining_quota == 0:
                    logger.debug(f"{podcast.name}: already at limit ({already_fetched}/{config_limit})")
                    continue
                if len(episodes_to_fetch) > remaining_quota:
                    total_skipped += len(episodes_to_fetch) - remaining_quota
                    episodes_to_fetch = episodes_to_fetch[:remaining_quota]
            elif manual_limit:
                # Use manual limit
                if len(episodes_to_fetch) > manual_limit:
                    total_skipped += len(episodes_to_fetch) - manual_limit
                    episodes_to_fetch = episodes_to_fetch[:manual_limit]

            if not episodes_to_fetch:
                continue

            limit_info = f" ({already_fetched}/{config_limit or '∞'})" if config_limit else ""
            print(f"📥 {podcast.name}: fetching {len(episodes_to_fetch)} episodes{limit_info}")

            print(
                f"   📊 Processing {len(episodes_to_fetch)} episodes (statuses: {', '.join(target_statuses)})"
            )

            podcast_config = mapping_config.get(podcast.slug, {})
            podcast_config.update(
                {
                    "name": podcast.name,
                    "slug": podcast.slug,
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

        print(f"🎯 Transcript fetching complete:")
        print(f"   ✅ Fetched: {total_fetched}")
        print(f"   ❌ Failed: {total_failed}")
        if total_skipped:
            print(f"   ⏭️  Skipped (over limit): {total_skipped}")
        return True

    def _fetch_episode_transcript(
        self, episode: Episode, podcast: Podcast, podcast_config: Dict[str, Any]
    ) -> bool:
        """Fetch transcript for a single episode"""
        try:
            # Use resolvers to get transcript content
            all_sources = []

            # Define resolver priority - reliable sources first, then fallbacks
            # If podcast has a specific resolver configured, prioritize it
            configured_resolver = podcast_config.get('resolver', '')

            # Base priority order
            base_priority = ['rss_link', 'network_transcripts', 'podscripts', 'generic_html', 'youtube_transcript', 'pattern']

            # If podcast specifies generic_html (like Stratechery with cookies), move it earlier
            if configured_resolver == 'generic_html':
                # Put generic_html right after rss_link for sites with full transcripts
                resolver_priority = ['rss_link', 'generic_html', 'network_transcripts', 'podscripts', 'youtube_transcript', 'pattern']
            else:
                resolver_priority = base_priority

            # Try each resolver in priority order, stop early if we get good content
            for resolver_name in resolver_priority:
                if resolver_name not in self.resolvers:
                    continue
                resolver = self.resolvers[resolver_name]
                try:
                    sources = resolver.resolve(episode, podcast_config)
                    all_sources.extend(sources)

                    # Stop early if we got substantial content (>5000 chars = likely full transcript)
                    # This avoids unnecessary YouTube lookups when we already have the transcript
                    for source in sources:
                        content = source.get('metadata', {}).get('content', '')
                        content_len = len(content) if content else 0
                        confidence = source.get('confidence', 0)

                        # Good enough to stop: either high confidence OR substantial content
                        if confidence >= 0.7 or (confidence >= 0.3 and content_len > 5000):
                            logger.debug(f"Got good source from {resolver_name} ({content_len} chars, conf={confidence:.2f}), skipping remaining resolvers")
                            break
                    else:
                        continue
                    break  # Exit outer loop if inner break was reached

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

    def cmd_sync(self, args):
        """Sync existing transcript files to database"""
        if not self.store:
            self.init_store()

        data_dir = Path("data/podcasts")
        if not data_dir.exists():
            print("❌ Data directory not found")
            return False

        print("🔄 Syncing existing transcript files to database...")

        # Get all podcasts
        podcasts = self.store.list_podcasts()
        podcast_by_slug = {p.slug: p for p in podcasts}

        # Also create fuzzy lookup by normalized name
        podcast_by_normalized = {}
        for p in podcasts:
            normalized = self._normalize_title(p.slug)
            podcast_by_normalized[normalized] = p
            # Also add name-based lookup
            normalized_name = self._normalize_title(p.name)
            podcast_by_normalized[normalized_name] = p

        total_synced = 0
        total_already_synced = 0
        total_orphaned = 0

        # Scan all transcript directories
        for podcast_dir in data_dir.iterdir():
            if not podcast_dir.is_dir():
                continue

            transcript_dir = podcast_dir / "transcripts"
            if not transcript_dir.exists():
                continue

            podcast_slug = podcast_dir.name
            podcast = podcast_by_slug.get(podcast_slug)

            # Try fuzzy matching if exact match fails
            if not podcast:
                normalized_dir = self._normalize_title(podcast_slug)
                podcast = podcast_by_normalized.get(normalized_dir)

                # Try similarity-based matching
                if not podcast:
                    best_match = None
                    best_score = 0.0
                    for p in podcasts:
                        score = self._slug_similarity(podcast_slug, p.slug)
                        if score > best_score and score >= 0.5:
                            best_score = score
                            best_match = p
                        # Also try name
                        name_score = self._slug_similarity(podcast_slug, p.name)
                        if name_score > best_score and name_score >= 0.5:
                            best_score = name_score
                            best_match = p
                    if best_match:
                        podcast = best_match
                        if args.verbose:
                            print(f"   🔗 Matched '{podcast_slug}' → '{podcast.slug}' (score: {best_score:.2f})")

            if not podcast:
                # Count orphaned transcripts (no matching podcast in DB)
                orphan_count = len(list(transcript_dir.glob("*.md")))
                if orphan_count > 0:
                    total_orphaned += orphan_count
                    if args.verbose:
                        print(f"   ⚠️  {podcast_slug}: {orphan_count} orphaned transcripts (no DB entry)")
                continue

            # Get all episodes for this podcast
            episodes = self.store.get_episodes_by_podcast(podcast.id)
            episode_by_guid = {e.guid: e for e in episodes}
            episode_by_title = {}
            for e in episodes:
                # Normalize title for matching
                normalized = self._normalize_title(e.title)
                episode_by_title[normalized] = e

            synced_count = 0
            already_count = 0
            created_count = 0

            for transcript_file in transcript_dir.glob("*.md"):
                # Try to match to an episode
                filename = transcript_file.stem  # e.g., "2025-11-18_googles-gemini-3"

                # Extract title part (after date prefix if present)
                if "_" in filename and filename[:4].isdigit():
                    title_part = filename.split("_", 1)[1]
                else:
                    title_part = filename

                normalized_title = self._normalize_title(title_part)
                episode = episode_by_title.get(normalized_title)

                if not episode:
                    # Try fuzzy matching
                    for ep_title, ep in episode_by_title.items():
                        if normalized_title in ep_title or ep_title in normalized_title:
                            episode = ep
                            break

                if episode:
                    if episode.transcript_status == "fetched" and episode.transcript_path:
                        already_count += 1
                    else:
                        # Update episode with transcript info
                        self.store.update_episode_transcript_status(
                            episode.id,
                            status="fetched",
                            transcript_path=str(transcript_file)
                        )
                        synced_count += 1
                elif args.create_episodes:
                    # Create episode from transcript file
                    from modules.podcasts.store import Episode
                    import uuid
                    from datetime import datetime

                    # Parse title from filename
                    title = title_part.replace("-", " ").replace("_", " ").title()

                    # Try to extract date from filename
                    pub_date = None
                    if "_" in filename and filename[:4].isdigit():
                        try:
                            date_part = filename.split("_")[0]
                            pub_date = datetime.strptime(date_part, "%Y-%m-%d")
                        except ValueError:
                            pass

                    episode = Episode(
                        id=0,
                        podcast_id=podcast.id,
                        guid=str(uuid.uuid4()),
                        title=title,
                        url="",
                        publish_date=pub_date,
                        transcript_status="fetched",
                        transcript_path=str(transcript_file),
                    )

                    try:
                        self.store.create_episode(episode)
                        created_count += 1
                        # Add to lookup for future files
                        episode_by_title[normalized_title] = episode
                    except Exception as e:
                        logger.debug(f"Failed to create episode for {filename}: {e}")

            if synced_count > 0 or created_count > 0 or (args.verbose and already_count > 0):
                parts = []
                if synced_count > 0:
                    parts.append(f"{synced_count} synced")
                if created_count > 0:
                    parts.append(f"{created_count} created")
                if already_count > 0:
                    parts.append(f"{already_count} already synced")
                print(f"   ✅ {podcast.name}: {', '.join(parts)}")

            total_synced += synced_count + created_count
            total_already_synced += already_count

        print(f"\n🎯 Sync complete:")
        print(f"   ✅ Newly synced: {total_synced}")
        print(f"   ✓  Already synced: {total_already_synced}")
        if total_orphaned > 0:
            print(f"   ⚠️  Orphaned (no DB match): {total_orphaned}")

        # Offer to register orphaned podcasts
        if total_orphaned > 0 and args.register_orphans:
            print("\n📝 Registering orphaned podcast directories...")
            registered = self._register_orphaned_dirs(data_dir, podcast_by_slug)
            if registered > 0:
                print(f"   ✅ Registered {registered} new podcasts")
                print("   🔄 Re-running sync...")
                # Re-run sync for newly registered podcasts
                args.register_orphans = False  # Prevent infinite loop
                return self.cmd_sync(args)

        return True

    def _register_orphaned_dirs(self, data_dir: Path, existing_slugs: dict) -> int:
        """Register podcast directories that don't exist in DB"""
        registered = 0

        for podcast_dir in data_dir.iterdir():
            if not podcast_dir.is_dir():
                continue

            transcript_dir = podcast_dir / "transcripts"
            if not transcript_dir.exists():
                continue

            slug = podcast_dir.name
            if slug in existing_slugs:
                continue

            # Count transcripts
            transcript_count = len(list(transcript_dir.glob("*.md")))
            if transcript_count == 0:
                continue

            # Create a basic podcast entry
            name = slug.replace("-", " ").title()

            # Insert into database
            from modules.podcasts.store import Podcast
            podcast = Podcast(
                id=0,
                name=name,
                slug=slug,
                rss_url="",  # Unknown
                site_url="",
                resolver="podscripts",  # Assume came from podscripts
            )

            try:
                self.store.create_podcast(podcast)
                registered += 1
                print(f"   📌 Registered: {name} ({transcript_count} transcripts)")
            except Exception as e:
                logger.warning(f"Failed to register {slug}: {e}")

        return registered

    def _normalize_title(self, title: str) -> str:
        """Normalize title for matching"""
        import re
        # Lowercase, remove special chars, collapse whitespace
        normalized = title.lower()
        normalized = re.sub(r'[^\w\s]', '', normalized)
        normalized = re.sub(r'\s+', ' ', normalized).strip()
        return normalized

    def _slug_similarity(self, slug1: str, slug2: str) -> float:
        """Calculate similarity between two slugs (0.0 to 1.0)"""
        # Normalize both
        s1 = self._normalize_title(slug1).replace(' ', '')
        s2 = self._normalize_title(slug2).replace(' ', '')

        if s1 == s2:
            return 1.0

        # Check if one contains the other
        if s1 in s2 or s2 in s1:
            return 0.8

        # Count common words
        words1 = set(self._normalize_title(slug1).split())
        words2 = set(self._normalize_title(slug2).split())

        if not words1 or not words2:
            return 0.0

        common = words1 & words2
        total = words1 | words2

        # Jaccard similarity
        return len(common) / len(total) if total else 0.0

    def cmd_generate_queue(self, args):
        """Generate static work queue from DB - no locks during processing"""
        if not self.store:
            self.init_store()

        queue_file = Path(args.output or "data/podcasts/work_queue.json")
        queue_file.parent.mkdir(parents=True, exist_ok=True)

        print("📋 Generating work queue from database...")

        # Load limits and mapping
        limits_config = self._load_limits_config()
        mapping_path = Path("config/mapping.yml")
        mapping_config = load_mapping_config(str(mapping_path)) if mapping_path.exists() else {}

        podcasts = self.store.list_podcasts()
        queue_items = []

        for podcast in podcasts:
            # Skip excluded podcasts
            if limits_config:
                config_limit = self._get_podcast_limit(podcast.slug, limits_config)
                if config_limit is None or config_limit == 0:
                    continue
            else:
                config_limit = None

            # Get episodes needing transcripts
            episodes = self.store.get_episodes_by_podcast(podcast.id)
            target_statuses = ["unknown", "found"]
            if args.include_failed:
                target_statuses.append("failed")

            episodes_to_process = [e for e in episodes if e.transcript_status in target_statuses]

            # Apply limit
            if config_limit:
                already_fetched = len([e for e in episodes if e.transcript_status == "fetched"])
                remaining_quota = max(0, config_limit - already_fetched)
                episodes_to_process = episodes_to_process[:remaining_quota]

            # Build queue items
            for ep in episodes_to_process:
                queue_items.append({
                    "episode_id": ep.id,
                    "episode_title": ep.title,
                    "episode_url": ep.url,
                    "episode_guid": ep.guid,
                    "podcast_id": podcast.id,
                    "podcast_name": podcast.name,
                    "podcast_slug": podcast.slug,
                    "resolver": podcast.resolver,
                    "status": "pending"
                })

        # Write queue file
        with open(queue_file, "w") as f:
            json.dump({
                "generated_at": datetime.now().isoformat(),
                "total_items": len(queue_items),
                "items": queue_items
            }, f, indent=2)

        print(f"✅ Generated queue with {len(queue_items)} items")
        print(f"📁 Queue file: {queue_file}")
        print(f"\nRun: python -m modules.podcasts.cli process-queue --file {queue_file}")
        return True

    def cmd_process_queue(self, args):
        """Process episodes from static queue file - minimal DB locks"""
        if not self.store:
            self.init_store()

        queue_file = Path(args.file)
        if not queue_file.exists():
            print(f"❌ Queue file not found: {queue_file}")
            return False

        # Load queue
        with open(queue_file) as f:
            queue_data = json.load(f)

        items = queue_data.get("items", [])
        pending = [i for i in items if i.get("status") == "pending"]

        print(f"📋 Processing {len(pending)} pending items from queue")

        mapping_path = Path("config/mapping.yml")
        mapping_config = load_mapping_config(str(mapping_path)) if mapping_path.exists() else {}
        processed = 0
        succeeded = 0
        failed = 0

        for item in pending:
            # Create minimal Episode/Podcast objects
            episode = Episode(
                id=item["episode_id"],
                podcast_id=item["podcast_id"],
                guid=item["episode_guid"],
                title=item["episode_title"],
                url=item["episode_url"],
            )

            podcast = Podcast(
                id=item["podcast_id"],
                name=item["podcast_name"],
                slug=item["podcast_slug"],
                rss_url="",
                resolver=item.get("resolver", "generic_html"),
            )

            podcast_config = mapping_config.get(podcast.slug, {})
            podcast_config.update({
                "name": podcast.name,
                "slug": podcast.slug,
                "resolver": podcast.resolver,
            })

            # Process
            try:
                success = self._fetch_episode_transcript(episode, podcast, podcast_config)
                if success:
                    item["status"] = "completed"
                    succeeded += 1
                else:
                    item["status"] = "failed"
                    failed += 1
            except Exception as e:
                item["status"] = "error"
                item["error"] = str(e)
                failed += 1
                logger.error(f"Error processing {item['episode_title']}: {e}")

            processed += 1

            # Save progress every 10 items
            if processed % 10 == 0:
                with open(queue_file, "w") as f:
                    json.dump(queue_data, f, indent=2)
                print(f"   Progress: {processed}/{len(pending)} ({succeeded} ok, {failed} failed)")

        # Final save
        with open(queue_file, "w") as f:
            json.dump(queue_data, f, indent=2)

        print(f"\n✅ Queue processing complete:")
        print(f"   ✅ Succeeded: {succeeded}")
        print(f"   ❌ Failed: {failed}")
        return True

    def cmd_status(self, args):
        """Coverage dashboard - shows progress toward 100%"""
        if not self.store:
            self.init_store()

        import sqlite3
        conn = sqlite3.connect(self.store.db_path)
        conn.row_factory = sqlite3.Row

        # Get stats (exclude 'excluded' episodes)
        total = conn.execute('SELECT COUNT(*) FROM episodes WHERE transcript_status != "excluded"').fetchone()[0]
        fetched = conn.execute('SELECT COUNT(*) FROM episodes WHERE transcript_status = "fetched"').fetchone()[0]
        pending = conn.execute('SELECT COUNT(*) FROM episodes WHERE transcript_status IN ("unknown", "found")').fetchone()[0]
        failed = conn.execute('SELECT COUNT(*) FROM episodes WHERE transcript_status = "failed"').fetchone()[0]

        coverage = (fetched / total * 100) if total > 0 else 0

        print('╔════════════════════════════════════════════════════════════╗')
        print('║           ATLAS PODCAST TRANSCRIPT COVERAGE                 ║')
        print('╠════════════════════════════════════════════════════════════╣')
        print(f'║  Total Episodes (in scope):  {total:>6,}                        ║')
        print(f'║  Fetched (done):             {fetched:>6,}  ✅                    ║')
        print(f'║  Pending (to do):            {pending:>6,}  ⏳                    ║')
        print(f'║  Failed (need retry):        {failed:>6,}  ❌                    ║')
        print('╠════════════════════════════════════════════════════════════╣')
        print(f'║  COVERAGE:                   {coverage:>5.1f}%                       ║')
        print('╚════════════════════════════════════════════════════════════╝')

        if pending > 0 or failed > 0:
            # Time estimate: ~5 sec for Podscripts/NPR, ~35 sec for YouTube
            non_yt = int(pending * 0.8)
            yt = int(pending * 0.2)
            time_mins = (non_yt * 5 + yt * 35) / 60
            print()
            print(f'Estimated time to 100%: {time_mins:.0f} min ({time_mins/60:.1f} hrs)')

        if getattr(args, 'verbose', False):
            # Show breakdown by podcast
            rows = conn.execute('''
                SELECT p.name,
                       SUM(CASE WHEN e.transcript_status = 'fetched' THEN 1 ELSE 0 END) as done,
                       SUM(CASE WHEN e.transcript_status IN ('unknown', 'found') THEN 1 ELSE 0 END) as pending
                FROM podcasts p
                JOIN episodes e ON e.podcast_id = p.id
                WHERE e.transcript_status != 'excluded'
                GROUP BY p.id
                HAVING pending > 0
                ORDER BY pending DESC
            ''').fetchall()

            if rows:
                print()
                print('Pending by podcast:')
                for row in rows[:15]:
                    print(f'  {row["pending"]:>4} pending / {row["done"]:>4} done  {row["name"]}')
                if len(rows) > 15:
                    print(f'  ... and {len(rows) - 15} more podcasts')

        conn.close()
        return True

    def cmd_prune(self, args):
        """Prune episodes to match limits from config"""
        if not self.store:
            self.init_store()

        limits = self._load_limits_config()
        if not limits:
            print("❌ No limits config found at config/podcast_limits.json")
            return False

        dry_run = not getattr(args, 'apply', False)
        if dry_run:
            print("🔍 DRY RUN: Showing what would be pruned (use --apply to execute)")
        else:
            print("✂️  Pruning episodes to match limits...")

        podcasts = self.store.list_podcasts()
        total_to_prune = 0
        total_pruned = 0

        for podcast in podcasts:
            limit = self._get_podcast_limit(podcast.slug, limits)

            # Skip excluded podcasts (they'll be handled separately)
            if limit is None:
                continue

            # Get all episodes for this podcast, sorted by date
            episodes = self.store.get_episodes_by_podcast(podcast.id)
            episodes = sorted(
                episodes,
                key=lambda e: e.publish_date or "",
                reverse=True
            )

            # Count episodes that should be pruned
            # But NEVER prune episodes that already have transcripts fetched
            if limit == 0:
                # Prune all episodes (except those with transcripts)
                to_prune = [e for e in episodes if e.transcript_status != "fetched"]
            elif len(episodes) > limit:
                # Keep only the N most recent, but always keep fetched ones
                keep_episodes = []
                prune_candidates = []
                for i, ep in enumerate(episodes):
                    if i < limit or ep.transcript_status == "fetched":
                        keep_episodes.append(ep)
                    else:
                        prune_candidates.append(ep)
                to_prune = prune_candidates
            else:
                to_prune = []

            if to_prune:
                if dry_run:
                    print(f"   {podcast.name}: would prune {len(to_prune)} episodes (keeping {limit})")
                    total_to_prune += len(to_prune)
                else:
                    # Mark as excluded
                    for ep in to_prune:
                        self.store.update_episode_transcript_status(ep.id, "excluded")
                    print(f"   ✂️  {podcast.name}: pruned {len(to_prune)} episodes")
                    total_pruned += len(to_prune)

        if dry_run:
            print(f"\n📊 Total episodes to prune: {total_to_prune}")
            print("   Run with --apply to execute pruning")
        else:
            print(f"\n✅ Pruned {total_pruned} episodes total")

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
    discover_parser.add_argument(
        "--no-limits", action="store_true", dest="no_limits",
        help="Ignore podcast_limits.json and discover all episodes"
    )

    # fetch-transcripts command
    fetch_parser = subparsers.add_parser(
        "fetch-transcripts", help="Fetch transcript content"
    )
    fetch_group = fetch_parser.add_mutually_exclusive_group(required=True)
    fetch_group.add_argument(
        "--all", action="store_true", help="Fetch all available transcripts"
    )
    fetch_group.add_argument("--slug", help="Fetch transcripts for specific podcast")
    fetch_parser.add_argument(
        "--status",
        help="Comma-separated statuses to process (default: unknown,found). Options: unknown,found,failed",
    )
    fetch_parser.add_argument(
        "--limit",
        type=int,
        help="Max episodes to process per podcast (useful for testing)",
    )

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

    # sync command
    sync_parser = subparsers.add_parser(
        "sync", help="Sync existing transcript files to database"
    )
    sync_parser.add_argument(
        "--verbose", "-v", action="store_true", help="Show all podcasts including already synced"
    )
    sync_parser.add_argument(
        "--register-orphans", action="store_true",
        help="Register podcast directories that don't exist in DB"
    )
    sync_parser.add_argument(
        "--create-episodes", action="store_true",
        help="Create episode records from transcript files that don't match existing episodes"
    )

    # prune command
    prune_parser = subparsers.add_parser(
        "prune", help="Prune episodes to match limits from config"
    )
    prune_parser.add_argument(
        "--apply", action="store_true",
        help="Actually prune episodes (default is dry-run)"
    )

    # status command
    status_parser = subparsers.add_parser("status", help="Coverage dashboard")
    status_parser.add_argument(
        "--verbose", "-v", action="store_true",
        help="Show per-podcast breakdown"
    )

    # generate-queue command
    genqueue_parser = subparsers.add_parser(
        "generate-queue", help="Generate static work queue from DB"
    )
    genqueue_parser.add_argument(
        "--output", "-o",
        help="Output file path (default: data/podcasts/work_queue.json)"
    )
    genqueue_parser.add_argument(
        "--include-failed", action="store_true",
        help="Include previously failed episodes in queue"
    )

    # process-queue command
    procqueue_parser = subparsers.add_parser(
        "process-queue", help="Process episodes from static queue file"
    )
    procqueue_parser.add_argument(
        "--file", "-f", required=True,
        help="Path to queue JSON file"
    )

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
            "sync": cli.cmd_sync,
            "prune": cli.cmd_prune,
            "status": cli.cmd_status,
            "generate-queue": cli.cmd_generate_queue,
            "process-queue": cli.cmd_process_queue,
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
