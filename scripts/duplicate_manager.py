#!/usr/bin/env python3
"""
Duplicate Manager CLI

This script provides command-line tools for analyzing, detecting, and managing
duplicates in the Atlas content system using the enhanced deduplication features.
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Dict

from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

# Add project root to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from helpers.integrated_dedupe import IntegratedDeduplicator
from helpers.metadata_manager import ContentType

console = Console()


class DuplicateManagerCLI:
    """Command-line interface for duplicate management."""

    def __init__(self):
        """Initialize duplicate manager CLI."""
        try:
            self.deduplicator = IntegratedDeduplicator()
            console.print("[green]✓[/green] Initialized duplicate manager")
        except Exception as e:
            console.print(f"[red]✗[/red] Failed to initialize: {e}")
            sys.exit(1)

    def analyze_duplicates(self, content_type: str = None, detailed: bool = False):
        """Analyze duplicate content in the system."""
        console.print("\n[bold blue]🔍 Analyzing Duplicates[/bold blue]")

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            progress.add_task("Scanning content for duplicates...", total=None)
            stats = self.deduplicator.get_duplicate_statistics()

        # Display overall statistics
        stats_table = Table(title="Duplicate Analysis Summary")
        stats_table.add_column("Metric", style="cyan")
        stats_table.add_column("Count", justify="right", style="magenta")

        stats_table.add_row("Total Items", str(stats["total_items"]))
        stats_table.add_row("Potential Duplicates", str(stats["potential_duplicates"]))
        stats_table.add_row(
            "High Confidence Duplicates", str(stats["high_confidence_duplicates"])
        )

        console.print(stats_table)

        # Display by content type
        if stats.get("content_types"):
            console.print("\n[bold]By Content Type:[/bold]")

            type_table = Table()
            type_table.add_column("Content Type", style="cyan")
            type_table.add_column("Total Items", justify="right")
            type_table.add_column("Potential Duplicates", justify="right")
            type_table.add_column("High Confidence", justify="right", style="red")

            for content_type, type_stats in stats["content_types"].items():
                type_table.add_row(
                    content_type,
                    str(type_stats["total_items"]),
                    str(type_stats["potential_duplicates"]),
                    str(type_stats["high_confidence_duplicates"]),
                )

            console.print(type_table)

        if "error" in stats:
            console.print(f"\n[yellow]⚠ Warning: {stats['error']}[/yellow]")

    def find_similar(self, content_type: str, uid: str, limit: int = 10):
        """Find content similar to a specific item."""
        try:
            content_type_enum = ContentType(content_type)
        except ValueError:
            console.print(f"[red]✗[/red] Invalid content type: {content_type}")
            console.print("Valid types: article, youtube, podcast, instapaper")
            return

        console.print("\n[bold blue]🔎 Finding Similar Content[/bold blue]")
        console.print(f"Content Type: {content_type}")
        console.print(f"UID: {uid}")

        # Get metadata for the specified item
        try:
            all_metadata = self.deduplicator.metadata_manager.get_all_metadata()
            target_item = None
            for item in all_metadata:
                if item.get("uid") == uid:
                    target_item = item
                    break

            if not target_item:
                console.print(f"[red]✗[/red] Item with UID {uid} not found")
                return

            console.print(f"Title: {target_item.get('title', 'No title')}")

        except Exception as e:
            console.print(f"[red]✗[/red] Error retrieving metadata: {e}")
            return

        # Find similar content
        try:
            TextColumn("[progress.description]{task.description}"),
                console=console,
            ) as progress:
                progress.add_task("Finding similar content...", total=None)
                matches = self.deduplicator.find_similar_content(
                    content_type_enum, target_item, limit
                )

            if not matches:
                console.print("[green]✓[/green] No similar content found")
                return

            # Display matches
            matches_table = Table(title=f"Similar Content (Top {len(matches)})")
            matches_table.add_column("UID", style="cyan")
            matches_table.add_column("Similarity", justify="right", style="yellow")
            matches_table.add_column("Match Type", style="magenta")
            matches_table.add_column("Confidence", justify="right", style="red")
            matches_table.add_column("Title Preview", style="dim")

            for match in matches:
                # Get title for the matched item
                matched_item_title = "Unknown"
                for item in all_metadata:
                    if item.get("uid") == match.primary_uid:
                        matched_item_title = item.get("title", "No title")[:50]
                        if len(item.get("title", "")) > 50:
                            matched_item_title += "..."
                        break

                matches_table.add_row(
                    match.primary_uid,
                    f"{match.similarity_score:.3f}",
                    match.match_type,
                    f"{match.confidence:.3f}",
                    matched_item_title,
                )

            console.print(matches_table)

        except Exception as e:
            console.print(f"[red]✗[/red] Error finding similar content: {e}")

    def check_url(
        self, url: str, content_type: str = "article", metadata_file: str = None
    ):
        """Check if a URL would be considered a duplicate."""
        try:
            content_type_enum = ContentType(content_type)
        except ValueError:
            console.print(f"[red]✗[/red] Invalid content type: {content_type}")
            return

        console.print("\n[bold blue]🔍 Checking URL for Duplicates[/bold blue]")
        console.print(f"URL: {url}")
        console.print(f"Content Type: {content_type}")

        # Load metadata if provided
        metadata = None
        if metadata_file:
            try:
                with open(metadata_file, "r") as f:
                    metadata = json.load(f)
                console.print(f"Loaded metadata from: {metadata_file}")
            except Exception as e:
                console.print(f"[yellow]⚠[/yellow] Could not load metadata: {e}")

        # Check for duplicates
        try:
            duplicate_info = self.deduplicator.check_all_duplicates(
                url, content_type_enum, metadata
            )

            # Display results
            result_panel = self._format_duplicate_result(duplicate_info)
            console.print(result_panel)

        except Exception as e:
            console.print(f"[red]✗[/red] Error checking duplicates: {e}")

    def cleanup_duplicates(
        self, dry_run: bool = True, confidence_threshold: float = 0.95
    ):
        """Clean up high-confidence duplicates."""
        mode = "DRY RUN" if dry_run else "LIVE CLEANUP"
        console.print(
            f"\n[bold {'yellow' if dry_run else 'red'}]🧹 Duplicate Cleanup - {mode}[/bold {'yellow' if dry_run else 'red'}]"
        )
        console.print(f"Confidence Threshold: {confidence_threshold}")

        if not dry_run:
            confirm = console.input(
                "\n[bold red]⚠ This will permanently remove duplicate files. Continue? (y/N): [/bold red]"
            )
            if confirm.lower() != "y":
                console.print("Cleanup cancelled.")
                return

        try:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
            ) as progress:
                progress.add_task(
                    "Analyzing duplicates for cleanup...", total=None
                )
                result = self.deduplicator.cleanup_duplicates(
                    dry_run, confidence_threshold
                )

            # Display results
            cleanup_table = Table(
                title=f"Cleanup Results - {'Dry Run' if dry_run else 'Live Run'}"
            )
            cleanup_table.add_column("Metric", style="cyan")
            cleanup_table.add_column("Count", justify="right", style="magenta")

            cleanup_table.add_row("Duplicates Found", str(result["duplicates_found"]))
            cleanup_table.add_row(
                "Duplicates Removed", str(result["duplicates_removed"])
            )

            console.print(cleanup_table)

            # Show by content type
            if result["duplicates_by_type"]:
                console.print("\n[bold]By Content Type:[/bold]")
                for content_type, count in result["duplicates_by_type"].items():
                    console.print(f"  {content_type}: {count} duplicates")

            # Show errors
            if result["errors"]:
                console.print("\n[bold red]Errors:[/bold red]")
                for error in result["errors"]:
                    console.print(f"  [red]•[/red] {error}")

            if dry_run and result["duplicates_found"] > 0:
                console.print(
                    f"\n[yellow]💡 Tip: Use --no-dry-run to actually remove {result['duplicates_found']} duplicates[/yellow]"
                )

        except Exception as e:
            console.print(f"[red]✗[/red] Error during cleanup: {e}")

    def _format_duplicate_result(self, duplicate_info: Dict) -> Panel:
        """Format duplicate check result into a rich panel."""
        is_dup = duplicate_info["is_duplicate"]

        # Choose colors and symbols based on result
        if is_dup:
            color = "red" if duplicate_info["recommendation"] == "skip" else "yellow"
            symbol = "✗" if duplicate_info["recommendation"] == "skip" else "⚠"
            title = f"[{color}]{symbol} DUPLICATE DETECTED[/{color}]"
        else:
            color = "green"
            symbol = "✓"
            title = f"[{color}]{symbol} NO DUPLICATE[/{color}]"

        # Build content
        content_lines = []

        if duplicate_info["url_duplicate"]:
            content_lines.append("[red]• URL-based duplicate detected[/red]")

        if duplicate_info["content_duplicate"]:
            match = duplicate_info["similarity_match"]
            if match:
                content_lines.append("[yellow]• Content similarity detected[/yellow]")
                content_lines.append(
                    f"  Similarity Score: {match.similarity_score:.3f}"
                )
                content_lines.append(f"  Match Type: {match.match_type}")
                content_lines.append(f"  Confidence: {match.confidence:.3f}")
                content_lines.append(f"  Similar to: {match.primary_uid}")

        content_lines.append(
            f"\n[bold]Recommendation: {duplicate_info['recommendation'].upper()}[/bold]"
        )

        if duplicate_info["recommendation"] == "review":
            content_lines.append(
                "[dim]This content may be similar to existing items. Manual review recommended.[/dim]"
            )
        elif duplicate_info["recommendation"] == "skip":
            content_lines.append(
                "[dim]This content appears to be a duplicate and should be skipped.[/dim]"
            )
        elif duplicate_info["recommendation"] == "process_with_warning":
            content_lines.append(
                "[dim]This content has some similarity but should be processed with caution.[/dim]"
            )

        return Panel("\n".join(content_lines), title=title, border_style=color)


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Atlas Duplicate Manager - Analyze and manage content duplicates"
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Analyze command
    analyze_parser = subparsers.add_parser(
        "analyze", help="Analyze duplicates in the system"
    )
    analyze_parser.add_argument(
        "--type",
        choices=["article", "youtube", "podcast"],
        help="Analyze specific content type",
    )
    analyze_parser.add_argument(
        "--detailed", action="store_true", help="Show detailed analysis"
    )

    # Similar command
    similar_parser = subparsers.add_parser(
        "similar", help="Find content similar to a specific item"
    )
    similar_parser.add_argument(
        "content_type",
        choices=["article", "youtube", "podcast"],
        help="Content type of the item",
    )
    similar_parser.add_argument("uid", help="UID of the content item")
    similar_parser.add_argument(
        "--limit", type=int, default=10, help="Maximum number of similar items to show"
    )

    # Check command
    check_parser = subparsers.add_parser(
        "check", help="Check if a URL would be a duplicate"
    )
    check_parser.add_argument("url", help="URL to check")
    check_parser.add_argument(
        "--type",
        choices=["article", "youtube", "podcast"],
        default="article",
        help="Content type",
    )
    check_parser.add_argument("--metadata", help="Path to JSON metadata file")

    # Cleanup command
    cleanup_parser = subparsers.add_parser(
        "cleanup", help="Clean up high-confidence duplicates"
    )
    cleanup_parser.add_argument(
        "--no-dry-run",
        action="store_true",
        help="Actually remove duplicates (default is dry run)",
    )
    cleanup_parser.add_argument(
        "--confidence",
        type=float,
        default=0.95,
        help="Minimum confidence threshold for removal",
    )

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    try:
        cli = DuplicateManagerCLI()

        if args.command == "analyze":
            cli.analyze_duplicates(args.type, args.detailed)
        elif args.command == "similar":
            cli.find_similar(args.content_type, args.uid, args.limit)
        elif args.command == "check":
            cli.check_url(args.url, args.type, args.metadata)
        elif args.command == "cleanup":
            cli.cleanup_duplicates(not args.no_dry_run, args.confidence)

    except KeyboardInterrupt:
        console.print("\n[yellow]Operation cancelled[/yellow]")
    except Exception as e:
        console.print(f"\n[red]Error: {e}[/red]")
        sys.exit(1)


if __name__ == "__main__":
    main()
