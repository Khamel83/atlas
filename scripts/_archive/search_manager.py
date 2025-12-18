#!/usr/bin/env python3
"""
Search Manager CLI

This script provides command-line tools for managing the full-text search system
including index setup, content indexing, and search testing.
"""

import argparse
import sys
import time
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.progress import (BarColumn, Progress, SpinnerColumn,
                           TaskProgressColumn, TextColumn)
from rich.table import Table

# Add project root to path for imports
sys.path.append(str(Path(__file__).parent.parent))

try:
    from helpers.metadata_manager import ContentType
    from helpers.search_engine import MEILISEARCH_AVAILABLE, get_search_engine
except ImportError as e:
    print(f"Error importing search modules: {e}")
    print("Make sure you're running from the Atlas root directory")
    sys.exit(1)

console = Console()


class SearchManagerCLI:
    """Command-line interface for search management."""

    def __init__(self):
        """Initialize search manager CLI."""
        if not MEILISEARCH_AVAILABLE:
            console.print("[red]✗[/red] Meilisearch client not available")
            console.print("Install with: [cyan]pip install meilisearch[/cyan]")
            sys.exit(1)

        try:
            self.search_engine = get_search_engine()
            console.print("[green]✓[/green] Search engine initialized")
        except Exception as e:
            console.print(f"[red]✗[/red] Failed to initialize search engine: {e}")
            console.print("\nTroubleshooting:")
            console.print(
                "1. Make sure Meilisearch server is running: [cyan]docker run -p 7700:7700 getmeili/meilisearch[/cyan]"
            )
            console.print("2. Check your configuration in .env file")
            console.print("3. Verify MEILISEARCH_HOST and MEILISEARCH_API_KEY settings")
            sys.exit(1)

    def health_check(self):
        """Check search service health."""
        console.print("\n[bold blue]🏥 Search Service Health Check[/bold blue]")

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            progress.add_task("Checking search service health...", total=None)
            health = self.search_engine.health_check()

        if health["status"] == "healthy":
            console.print("[green]✓ Search service is healthy[/green]")

            # Display service information
            info_table = Table(title="Service Information")
            info_table.add_column("Property", style="cyan")
            info_table.add_column("Value", style="magenta")

            info_table.add_row("Status", "Healthy")
            info_table.add_row("Host", health.get("host", "Unknown"))
            info_table.add_row("Index Name", health.get("index_name", "Unknown"))

            if "index_stats" in health:
                stats = health["index_stats"]
                info_table.add_row("Documents", str(stats.get("numberOfDocuments", 0)))
                info_table.add_row("Indexing", str(stats.get("isIndexing", False)))

            console.print(info_table)
        else:
            console.print("[red]✗ Search service is unhealthy[/red]")
            console.print(f"Error: {health.get('error', 'Unknown error')}")

            console.print("\n[yellow]Troubleshooting tips:[/yellow]")
            console.print("1. Ensure Meilisearch server is running")
            console.print("2. Check connection settings in configuration")
            console.print("3. Verify API key if authentication is enabled")

    def setup_index(self, reset: bool = False):
        """Set up the search index."""
        mode = "RESET & SETUP" if reset else "SETUP"
        console.print(f"\n[bold yellow]🔧 Search Index {mode}[/bold yellow]")

        if reset:
            confirm = console.input(
                "\n[bold red]⚠ This will delete the existing index and all data. Continue? (y/N): [/bold red]"
            )
            if confirm.lower() != "y":
                console.print("Setup cancelled.")
                return

        try:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
            ) as progress:
                progress.add_task("Setting up search index...", total=None)
                success = self.search_engine.setup_index(reset=reset)

            if success:
                console.print(
                    "[green]✓[/green] Search index setup completed successfully"
                )

                # Show index statistics
                self._show_index_stats()

                if not reset:  # For new setups, suggest indexing content
                    console.print(
                        "\n[yellow]💡 Next step: Index your content with:[/yellow]"
                    )
                    console.print(
                        "   [cyan]python scripts/search_manager.py index[/cyan]"
                    )
            else:
                console.print("[red]✗[/red] Failed to setup search index")

        except Exception as e:
            console.print(f"[red]✗[/red] Error during setup: {e}")

    def index_content(self, content_type: str = None, batch_size: int = None):
        """Index content for search."""
        console.print("\n[bold blue]📇 Indexing Content for Search[/bold blue]")

        if content_type:
            console.print(f"Content Type Filter: {content_type}")
            try:
                content_type_enum = ContentType(content_type)
            except ValueError:
                console.print(f"[red]✗[/red] Invalid content type: {content_type}")
                console.print("Valid types: article, youtube, podcast, instapaper")
                return
        else:
            content_type_enum = None
            console.print("Indexing all content types")

        if batch_size:
            console.print(f"Batch Size: {batch_size}")

        try:
            start_time = time.time()

            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TaskProgressColumn(),
                console=console,
            ) as progress:
                progress.add_task("Indexing content...", total=None)

                result = self.search_engine.index_content(
                    content_type=content_type_enum, batch_size=batch_size
                )

            duration = time.time() - start_time

            # Display results
            results_table = Table(title="Indexing Results")
            results_table.add_column("Metric", style="cyan")
            results_table.add_column("Count", justify="right", style="magenta")

            results_table.add_row("Documents Indexed", str(result["indexed_count"]))
            results_table.add_row("Errors", str(result["error_count"]))
            results_table.add_row("Processing Time", f"{duration:.2f}s")
            results_table.add_row(
                "Rate",
                (
                    f"{result['indexed_count']/duration:.1f} docs/sec"
                    if duration > 0
                    else "N/A"
                ),
            )

            console.print(results_table)

            # Show content types processed
            if result["content_types_processed"]:
                console.print(
                    f"\nContent Types: {', '.join(result['content_types_processed'])}"
                )

            # Show errors if any
            if result["errors"]:
                console.print(f"\n[red]Errors ({len(result['errors'])}):[/red]")
                for error in result["errors"][:5]:  # Show first 5 errors
                    console.print(f"  [red]•[/red] {error}")
                if len(result["errors"]) > 5:
                    console.print(
                        f"  [dim]... and {len(result['errors']) - 5} more[/dim]"
                    )

            # Show updated index stats
            console.print()
            self._show_index_stats()

        except Exception as e:
            console.print(f"[red]✗[/red] Error during indexing: {e}")

    def search_interactive(self, query: str = None):
        """Interactive search interface."""
        console.print("\n[bold blue]🔍 Interactive Search[/bold blue]")
        console.print("Type your search queries (or 'quit' to exit)")

        if query:
            self._perform_search(query)

        while True:
            try:
                user_query = console.input("\n[cyan]Search:[/cyan] ")
                if user_query.lower() in ["quit", "exit", "q"]:
                    break
                if user_query.strip():
                    self._perform_search(user_query)
            except KeyboardInterrupt:
                break

        console.print("\n[yellow]Search session ended[/yellow]")

    def _perform_search(self, query: str):
        """Perform a single search and display results."""
        try:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
            ) as progress:
                progress.add_task(f"Searching for '{query}'...", total=None)
                results = self.search_engine.search(query, limit=10)

            # Display search metadata
            console.print(
                f"\n[dim]Found {results['total_hits']} results in {results['search_time']:.0f}ms[/dim]"
            )

            if not results["hits"]:
                console.print("[yellow]No results found[/yellow]")

                # Suggest similar terms
                suggestions = self.search_engine.suggest(query)
                if suggestions:
                    console.print("\n[dim]Did you mean?[/dim]")
                    for suggestion in suggestions[:3]:
                        console.print(f"  [cyan]{suggestion}[/cyan]")
                return

            # Display results
            for i, hit in enumerate(results["hits"][:5], 1):  # Show top 5 results
                title = hit.get("title", "Untitled")
                content_type = hit.get("content_type", "unknown")
                uid = hit.get("uid", "unknown")

                # Create result panel
                content_preview = hit.get("content", "")[:200]
                if len(hit.get("content", "")) > 200:
                    content_preview += "..."

                result_text = f"[bold]{title}[/bold]\n"
                result_text += f"[dim]Type: {content_type} | ID: {uid}[/dim]\n"
                if content_preview:
                    result_text += f"\n{content_preview}"

                # Add highlights if available
                if "_formatted" in hit and hit["_formatted"].get("title"):
                    highlighted_title = hit["_formatted"]["title"]
                    result_text = result_text.replace(title, highlighted_title)

                panel = Panel(result_text, title=f"Result {i}", border_style="blue")
                console.print(panel)

            if results["total_hits"] > 5:
                console.print(
                    f"\n[dim]... and {results['total_hits'] - 5} more results[/dim]"
                )

        except Exception as e:
            console.print(f"[red]✗[/red] Search error: {e}")

    def show_stats(self):
        """Show search index statistics."""
        console.print("\n[bold blue]📊 Search Index Statistics[/bold blue]")
        self._show_index_stats()

        try:
            # Get additional statistics
            facets = self.search_engine.get_facets("")

            if facets:
                console.print("\n[bold]Content Distribution:[/bold]")

                for facet_name, distribution in facets.items():
                    if distribution:  # Only show non-empty facets
                        facet_table = Table(title=facet_name.replace("_", " ").title())
                        facet_table.add_column("Value", style="cyan")
                        facet_table.add_column(
                            "Count", justify="right", style="magenta"
                        )

                        # Sort by count descending
                        sorted_items = sorted(
                            distribution.items(), key=lambda x: x[1], reverse=True
                        )

                        for value, count in sorted_items[:10]:  # Show top 10
                            facet_table.add_row(str(value), str(count))

                        console.print(facet_table)

                        if len(distribution) > 10:
                            console.print(
                                f"[dim]... and {len(distribution) - 10} more values[/dim]"
                            )
        except Exception as e:
            console.print(
                f"[yellow]⚠[/yellow] Could not retrieve detailed statistics: {e}"
            )

    def _show_index_stats(self):
        """Show basic index statistics."""
        try:
            stats = self.search_engine.get_stats()

            if "error" in stats:
                console.print(f"[red]Error getting stats: {stats['error']}[/red]")
                return

            index_stats = stats.get("index_stats", {})

            stats_table = Table(title="Index Statistics")
            stats_table.add_column("Metric", style="cyan")
            stats_table.add_column("Value", style="magenta")

            stats_table.add_row(
                "Total Documents", str(index_stats.get("numberOfDocuments", 0))
            )
            stats_table.add_row(
                "Currently Indexing", str(index_stats.get("isIndexing", False))
            )
            stats_table.add_row("Index Name", stats.get("index_name", "Unknown"))

            if "fieldDistribution" in index_stats:
                field_count = len(index_stats["fieldDistribution"])
                stats_table.add_row("Searchable Fields", str(field_count))

            console.print(stats_table)

        except Exception as e:
            console.print(f"[yellow]⚠[/yellow] Could not retrieve statistics: {e}")

    def clear_index(self):
        """Clear all documents from search index."""
        console.print("\n[bold red]🗑️  Clear Search Index[/bold red]")

        confirm = console.input(
            "\n[bold red]⚠ This will permanently delete all search data. Continue? (y/N): [/bold red]"
        )
        if confirm.lower() != "y":
            console.print("Clear operation cancelled.")
            return

        try:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
            ) as progress:
                progress.add_task("Clearing search index...", total=None)
                success = self.search_engine.clear_index()

            if success:
                console.print("[green]✓[/green] Search index cleared successfully")
            else:
                console.print("[red]✗[/red] Failed to clear search index")

        except Exception as e:
            console.print(f"[red]✗[/red] Error clearing index: {e}")

    def test_search(self):
        """Run search functionality tests."""
        console.print("\n[bold blue]🧪 Search Functionality Tests[/bold blue]")

        test_queries = [
            "python",
            "tutorial",
            "javascript",
            "testing",
            "machine learning",
        ]

        results_table = Table(title="Search Tests")
        results_table.add_column("Query", style="cyan")
        results_table.add_column("Results", justify="right", style="magenta")
        results_table.add_column("Time (ms)", justify="right", style="yellow")
        results_table.add_column("Status", style="green")

        total_time = 0
        successful_tests = 0

        for query in test_queries:
            try:
                start_time = time.time()
                result = self.search_engine.search(query, limit=5)
                duration = (time.time() - start_time) * 1000

                total_time += duration
                successful_tests += 1

                results_table.add_row(
                    query, str(result["total_hits"]), f"{duration:.1f}", "✓ PASS"
                )

            except Exception as e:
                results_table.add_row(query, "0", "N/A", f"✗ FAIL: {str(e)[:30]}")

        console.print(results_table)

        # Summary
        console.print("\n[bold]Test Summary:[/bold]")
        console.print(f"Successful: {successful_tests}/{len(test_queries)}")
        if successful_tests > 0:
            console.print(f"Average Response Time: {total_time/successful_tests:.1f}ms")


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Atlas Search Manager - Manage full-text search functionality"
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Health command


    # Setup command
    setup_parser = subparsers.add_parser("setup", help="Set up search index")
    setup_parser.add_argument(
        "--reset",
        action="store_true",
        help="Reset existing index (destroys current data)",
    )

    # Index command
    index_parser = subparsers.add_parser("index", help="Index content for search")
    index_parser.add_argument(
        "--type",
        choices=["article", "youtube", "podcast"],
        help="Index specific content type only",
    )
    index_parser.add_argument(
        "--batch-size", type=int, default=100, help="Batch size for indexing"
    )

    # Search command
    search_parser = subparsers.add_parser("search", help="Interactive search interface")
    search_parser.add_argument("query", nargs="?", help="Initial search query")

    # Stats command
    stats_parser = subparsers.add_parser("stats", help="Show index statistics")

    # Clear command
    clear_parser = subparsers.add_parser("clear", help="Clear search index")

    # Health command
    health_parser = subparsers.add_parser("health", help="Check search service health")
    subparsers.add_parser("test", help="Test search functionality")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    try:
        cli = SearchManagerCLI()

        if args.command == "health":
            cli.health_check()
        elif args.command == "setup":
            cli.setup_index(args.reset)
        elif args.command == "index":
            cli.index_content(args.type, args.batch_size)
        elif args.command == "search":
            cli.search_interactive(args.query)
        elif args.command == "stats":
            cli.show_stats()
        elif args.command == "clear":
            cli.clear_index()
        elif args.command == "test":
            cli.test_search()

    except KeyboardInterrupt:
        console.print("\n[yellow]Operation cancelled[/yellow]")
    except Exception as e:
        console.print(f"\n[red]Error: {e}[/red]")
        sys.exit(1)


if __name__ == "__main__":
    main()
