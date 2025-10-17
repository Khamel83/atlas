"""
CLI command implementations for Atlas v4.

Provides command classes for all CLI operations with proper
argument handling and execution logic.
"""

import argparse
import json
import sys
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional
from abc import ABC, abstractmethod

# Ingestors imported lazily to avoid dependency issues
from ..core.queue import FailureQueue, QueueProcessor
from ..core.retry import RetryHandler
from ..core.recovery import ErrorAnalyzer, RecoveryManager


class BaseCommand(ABC):
    """Base class for CLI commands."""

    def __init__(self):
        self.logger = logging.getLogger(f"atlas.cli.{self.__class__.__name__}")

    @classmethod
    @abstractmethod
    def configure_parser(cls, parser: argparse.ArgumentParser) -> None:
        """Configure command-specific arguments."""
        pass

    @abstractmethod
    def execute(self, args: argparse.Namespace, context: Dict[str, Any]) -> int:
        """
        Execute the command.

        Args:
            args: Parsed command-line arguments
            context: Command context (config, storage, etc.)

        Returns:
            Exit code
        """
        pass


class IngestCommand(BaseCommand):
    """Command for ingesting content from various sources."""

    @classmethod
    def configure_parser(cls, parser: argparse.ArgumentParser) -> None:
        """Configure ingest command arguments."""
        parser.add_argument(
            "--source",
            choices=["gmail", "rss", "youtube"],
            required=True,
            help="Source type to ingest from"
        )
        parser.add_argument(
            "--config",
            type=str,
            required=True,
            help="Path to source-specific configuration file"
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be ingested without actually processing"
        )
        parser.add_argument(
            "--limit",
            type=int,
            help="Maximum number of items to ingest"
        )
        parser.add_argument(
            "--since",
            type=str,
            help="Ingest items newer than this date (ISO format)"
        )
        parser.add_argument(
            "--retry-failures",
            action="store_true",
            help="Retry failed items from failure queue"
        )

    def execute(self, args: argparse.Namespace, context: Dict[str, Any]) -> int:
        """Execute ingest command."""
        try:
            # Load source configuration
            source_config = self._load_source_config(args.config)
            if not source_config:
                self.logger.error(f"Failed to load source configuration: {args.config}")
                return 1

            # Create appropriate ingestor
            ingestor = self._create_ingestor(args.source, source_config)
            if not ingestor:
                self.logger.error(f"Unknown source type: {args.source}")
                return 1

            # Handle retry failures if requested
            if args.retry_failures:
                return self._retry_failures(context)

            # Run ingestion
            if args.dry_run:
                return self._dry_run(ingestor, args)

            result = ingestor.run()

            # Report results
            print(f"Ingestion completed:")
            print(f"  Success: {result.success}")
            print(f"  Items processed: {result.items_processed}")
            print(f"  Errors: {len(result.errors)}")

            if result.errors:
                print("\nErrors:")
                for error in result.errors[:5]:  # Show first 5 errors
                    print(f"  - {error}")
                if len(result.errors) > 5:
                    print(f"  ... and {len(result.errors) - 5} more")

            return 0 if result.success else 1

        except Exception as e:
            self.logger.error(f"Ingestion failed: {str(e)}")
            return 1

    def _load_source_config(self, config_path: str) -> Optional[Dict[str, Any]]:
        """Load source-specific configuration."""
        try:
            from ..config import load_config
            return load_config(config_path)
        except Exception as e:
            self.logger.error(f"Failed to load source config: {str(e)}")
            return None

    def _create_ingestor(self, source_type: str, config: Dict[str, Any]):
        """Create appropriate ingestor for source type."""
        try:
            if source_type == "gmail":
                from ..ingest.gmail import GmailIngestor
                return GmailIngestor(config)
            elif source_type == "rss":
                from ..ingest.rss import RSSIngestor
                return RSSIngestor(config)
            elif source_type == "youtube":
                from ..ingest.youtube import YouTubeIngestor
                return YouTubeIngestor(config)
            else:
                return None
        except Exception as e:
            self.logger.error(f"Failed to create ingestor: {str(e)}")
            return None

    def _dry_run(self, ingestor, args: argparse.Namespace) -> int:
        """Perform dry run of ingestion."""
        print(f"DRY RUN: Would ingest from {args.source}")
        print(f"  Config: {args.config}")
        if args.limit:
            print(f"  Limit: {args.limit} items")
        if args.since:
            print(f"  Since: {args.since}")
        return 0

    def _retry_failures(self, context: Dict[str, Any]) -> int:
        """Retry failed items from failure queue."""
        vault_root = context['vault_root']
        queue_path = vault_root / ".atlas" / "failure_queue.db"

        if not queue_path.exists():
            print("No failure queue found")
            return 0

        failure_queue = FailureQueue(queue_path)
        queue_processor = QueueProcessor(failure_queue)

        # Register processors
        queue_processor.register_processor("articles", self._process_article)
        queue_processor.register_processor("newsletters", self._process_newsletter)
        queue_processor.register_processor("podcasts", self._process_podcast)
        queue_processor.register_processor("youtube", self._process_youtube)
        queue_processor.register_processor("emails", self._process_email)

        # Process items
        stats = queue_processor.process_items()

        print(f"Retry processing completed:")
        print(f"  Processed: {stats['processed']}")
        print(f"  Completed: {stats['completed']}")
        print(f"  Failed: {stats['failed']}")
        print(f"  No processor: {stats['no_processor']}")

        return 0

    def _process_article(self, data: Dict[str, Any], context: Dict[str, Any]) -> bool:
        """Process article item from failure queue."""
        # Placeholder implementation
        return True

    def _process_newsletter(self, data: Dict[str, Any], context: Dict[str, Any]) -> bool:
        """Process newsletter item from failure queue."""
        # Placeholder implementation
        return True

    def _process_podcast(self, data: Dict[str, Any], context: Dict[str, Any]) -> bool:
        """Process podcast item from failure queue."""
        # Placeholder implementation
        return True

    def _process_youtube(self, data: Dict[str, Any], context: Dict[str, Any]) -> bool:
        """Process YouTube item from failure queue."""
        # Placeholder implementation
        return True

    def _process_email(self, data: Dict[str, Any], context: Dict[str, Any]) -> bool:
        """Process email item from failure queue."""
        # Placeholder implementation
        return True


class QueryCommand(BaseCommand):
    """Command for querying and searching stored content."""

    @classmethod
    def configure_parser(cls, parser: argparse.ArgumentParser) -> None:
        """Configure query command arguments."""
        parser.add_argument(
            "--query",
            type=str,
            help="Search query"
        )
        parser.add_argument(
            "--type",
            choices=["articles", "newsletters", "podcasts", "youtube", "emails"],
            help="Content type to filter by"
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=20,
            help="Maximum number of results (default: 20)"
        )
        parser.add_argument(
            "--format",
            choices=["text", "json", "table"],
            default="text",
            help="Output format (default: text)"
        )
        parser.add_argument(
            "--export",
            type=str,
            help="Export results to file"
        )

    def execute(self, args: argparse.Namespace, context: Dict[str, Any]) -> int:
        """Execute query command."""
        try:
            storage = context['storage']

            # Perform search
            if args.query:
                results = storage.search_content(args.query, args.type)
            else:
                # List by type
                if args.type:
                    results = storage.list_content_by_type(args.type, args.limit)
                else:
                    # List all content
                    results = []
                    for content_type in ["articles", "newsletters", "podcasts", "youtube", "emails"]:
                        type_results = storage.list_content_by_type(content_type, args.limit // 5)
                        results.extend(type_results)

            # Limit results
            if args.limit:
                results = results[:args.limit]

            # Format and display results
            self._display_results(results, args.format, args.export)

            return 0

        except Exception as e:
            self.logger.error(f"Query failed: {str(e)}")
            return 1

    def _display_results(self, results: List[Dict[str, Any]], format_type: str, export_file: Optional[str]) -> None:
        """Display query results in specified format."""
        if not results:
            print("No results found")
            return

        if format_type == "json":
            output = json.dumps(results, indent=2, default=str)
        elif format_type == "table":
            output = self._format_table(results)
        else:  # text
            output = self._format_text(results)

        if export_file:
            Path(export_file).write_text(output, encoding='utf-8')
            print(f"Results exported to: {export_file}")
        else:
            print(output)

    def _format_text(self, results: List[Dict[str, Any]]) -> str:
        """Format results as plain text."""
        lines = []
        for i, result in enumerate(results, 1):
            frontmatter = result.get('frontmatter', {})
            lines.append(f"{i}. {frontmatter.get('title', 'Untitled')}")
            lines.append(f"   Type: {frontmatter.get('type', 'unknown')}")
            lines.append(f"   Source: {frontmatter.get('source', 'unknown')}")
            lines.append(f"   Date: {frontmatter.get('date', 'unknown')}")
            lines.append(f"   Path: {result.get('path', 'unknown')}")
            lines.append("")
        return "\n".join(lines)

    def _format_table(self, results: List[Dict[str, Any]]) -> str:
        """Format results as table."""
        lines = []
        lines.append(f"{'#':<3} {'Title':<40} {'Type':<12} {'Source':<15} {'Date':<12}")
        lines.append("-" * 85)

        for i, result in enumerate(results, 1):
            frontmatter = result.get('frontmatter', {})
            title = frontmatter.get('title', 'Untitled')[:37] + "..." if len(frontmatter.get('title', '')) > 40 else frontmatter.get('title', 'Untitled')
            type_val = frontmatter.get('type', 'unknown')[:10]
            source = frontmatter.get('source', 'unknown')[:13]
            date = frontmatter.get('date', 'unknown')[:10]

            lines.append(f"{i:<3} {title:<40} {type_val:<12} {source:<15} {date:<12}")

        return "\n".join(lines)


class StatusCommand(BaseCommand):
    """Command for showing system status and statistics."""

    @classmethod
    def configure_parser(cls, parser: argparse.ArgumentParser) -> None:
        """Configure status command arguments."""
        parser.add_argument(
            "--detailed",
            action="store_true",
            help="Show detailed status information"
        )
        parser.add_argument(
            "--health",
            action="store_true",
            help="Show system health information"
        )
        parser.add_argument(
            "--format",
            choices=["text", "json"],
            default="text",
            help="Output format (default: text)"
        )

    def execute(self, args: argparse.Namespace, context: Dict[str, Any]) -> int:
        """Execute status command."""
        try:
            storage = context['storage']

            # Get storage statistics
            stats = storage.get_storage_stats()

            # Add system health if requested
            if args.health:
                from ..core.recovery import get_system_health
                health = get_system_health()
                stats['system_health'] = {
                    'cpu_percent': health.cpu_percent,
                    'memory_percent': health.memory_percent,
                    'disk_usage_percent': health.disk_usage_percent,
                    'network_status': health.network_status,
                    'database_status': health.database_status,
                    'active_processes': health.active_processes,
                    'system_uptime': health.system_uptime
                }

            # Add detailed information if requested
            if args.detailed:
                stats['vault_structure_valid'] = len(storage.validate_storage_integrity()) == 0
                stats['collision_stats'] = storage.collision_handler.get_collision_stats()

            # Display results
            if args.format == "json":
                print(json.dumps(stats, indent=2, default=str))
            else:
                self._display_status(stats, args.detailed, args.health)

            return 0

        except Exception as e:
            self.logger.error(f"Status command failed: {str(e)}")
            return 1

    def _display_status(self, stats: Dict[str, Any], detailed: bool, health: bool) -> None:
        """Display status information."""
        print("Atlas v4 System Status")
        print("=" * 50)

        # Storage statistics
        print(f"\nStorage Statistics:")
        print(f"  Total files: {stats.get('total_files', 0)}")
        print(f"  Disk usage: {stats.get('disk_usage', 0):,} bytes")

        if 'content_types' in stats:
            print(f"\nContent by Type:")
            for content_type, count in stats['content_types'].items():
                print(f"  {content_type}: {count}")

        # System health
        if health and 'system_health' in stats:
            health_stats = stats['system_health']
            print(f"\nSystem Health:")
            print(f"  CPU: {health_stats['cpu_percent']:.1f}%")
            print(f"  Memory: {health_stats['memory_percent']:.1f}%")
            print(f"  Disk: {health_stats['disk_usage_percent']:.1f}%")
            print(f"  Network: {'OK' if health_stats['network_status'] else 'ERROR'}")
            print(f"  Database: {'OK' if health_stats['database_status'] else 'ERROR'}")

        # Detailed information
        if detailed:
            print(f"\nDetailed Information:")
            print(f"  Vault path: {stats.get('vault_root', 'unknown')}")
            print(f"  Vault structure valid: {stats.get('vault_structure_valid', False)}")

            if 'collision_stats' in stats:
                collision_stats = stats['collision_stats']
                print(f"  Total collisions: {collision_stats.get('total_collisions', 0)}")

            if 'oldest_file' in stats:
                print(f"  Oldest file: {stats['oldest_file']['path']} ({stats['oldest_file']['date']})")
            if 'newest_file' in stats:
                print(f"  Newest file: {stats['newest_file']['path']} ({stats['newest_file']['date']})")


class ConfigCommand(BaseCommand):
    """Command for managing configuration."""

    @classmethod
    def configure_parser(cls, parser: argparse.ArgumentParser) -> None:
        """Configure config command arguments."""
        parser.add_argument(
            "--validate",
            action="store_true",
            help="Validate configuration file"
        )
        parser.add_argument(
            "--file",
            type=str,
            help="Configuration file to validate"
        )
        parser.add_argument(
            "--show",
            action="store_true",
            help="Show current configuration"
        )
        parser.add_argument(
            "--create-template",
            type=str,
            help="Create configuration template file"
        )

    def execute(self, args: argparse.Namespace, context: Dict[str, Any]) -> int:
        """Execute config command."""
        try:
            if args.create_template:
                return self._create_template(args.create_template)

            if args.validate:
                return self._validate_config(args.file or context['args'].config)

            if args.show:
                return self._show_config(context['config'])

            print("No action specified. Use --validate, --show, or --create-template")
            return 1

        except Exception as e:
            self.logger.error(f"Config command failed: {str(e)}")
            return 1

    def _create_template(self, template_path: str) -> int:
        """Create configuration template."""
        template = {
            "vault": {
                "root": "~/Documents/Atlas",
                "auto_create": True
            },
            "logging": {
                "level": "INFO",
                "file": "atlas.log",
                "max_size": "10MB",
                "backup_count": 5
            },
            "validation": {
                "min_content_length": 100,
                "required_fields": ["title", "content", "date"]
            }
        }

        Path(template_path).parent.mkdir(parents=True, exist_ok=True)
        Path(template_path).write_text(json.dumps(template, indent=2), encoding='utf-8')
        print(f"Configuration template created: {template_path}")
        return 0

    def _validate_config(self, config_path: str) -> int:
        """Validate configuration file."""
        try:
            from ..config import load_config
            config = load_config(config_path)
            print(f"Configuration is valid: {config_path}")
            return 0
        except Exception as e:
            print(f"Configuration validation failed: {str(e)}")
            return 1

    def _show_config(self, config: Dict[str, Any]) -> int:
        """Show current configuration."""
        print("Current Configuration:")
        print(json.dumps(config, indent=2, default=str))
        return 0


class CleanupCommand(BaseCommand):
    """Command for cleaning up old data and optimizing storage."""

    @classmethod
    def configure_parser(cls, parser: argparse.ArgumentParser) -> None:
        """Configure cleanup command arguments."""
        parser.add_argument(
            "--old-days",
            type=int,
            default=30,
            help="Remove items older than N days (default: 30)"
        )
        parser.add_argument(
            "--empty-dirs",
            action="store_true",
            help="Remove empty directories"
        )
        parser.add_argument(
            "--collision-registry",
            action="store_true",
            help="Clean up collision registry"
        )
        parser.add_argument(
            "--all",
            action="store_true",
            help="Perform all cleanup operations"
        )

    def execute(self, args: argparse.Namespace, context: Dict[str, Any]) -> int:
        """Execute cleanup command."""
        try:
            storage = context['storage']
            cleaned_any = False

            # Clean up old items from failure queue
            if args.all:
                vault_root = context['vault_root']
                queue_path = vault_root / ".atlas" / "failure_queue.db"
                if queue_path.exists():
                    from ..core.queue import FailureQueue
                    failure_queue = FailureQueue(queue_path)
                    cleaned_items = failure_queue.cleanup_old_items(args.old_days)
                    if cleaned_items > 0:
                        print(f"Cleaned up {cleaned_items} old queue items")
                        cleaned_any = True

            # Clean up empty directories
            if args.empty_dirs or args.all:
                empty_dirs = storage.organizer.cleanup_empty_directories()
                if empty_dirs:
                    print(f"Removed {len(empty_dirs)} empty directories:")
                    for dir_path in empty_dirs:
                        print(f"  {dir_path}")
                    cleaned_any = True

            # Clean up collision registry
            if args.collision_registry or args.all:
                collision_results = storage.cleanup_storage()
                if collision_results['collision_registry_cleaned'] > 0:
                    print(f"Cleaned up {collision_results['collision_registry_cleaned']} collision registry entries")
                    cleaned_any = True

            if not cleaned_any:
                print("No cleanup needed or no cleanup operations specified")

            return 0

        except Exception as e:
            self.logger.error(f"Cleanup command failed: {str(e)}")
            return 1