#!/usr/bin/env python3
"""
Atlas TODO Rationalization Script

This script cleans up and rationalizes the TODO system by:
1. Fixing malformed TODO content
2. Removing duplicates
3. Ensuring all TODOs have proper structure
4. Consolidating related TODOs
5. Validating critical TODOs have proper descriptions
"""

import json
import re
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.progress import Progress, SpinnerColumn, TextColumn
    from rich.table import Table
except ImportError:
    print("Rich library not found. Please run 'pip install rich'.")
    sys.exit(1)

console = Console()


class TodoRationalizer:
    """Rationalizes and cleans up the TODO system."""

    def __init__(self):
        self.console = console
        self.project_root = Path(__file__).parent.parent
        self.todos_file = self.project_root / "unified_todos.json"
        self.backup_file = self.project_root / "unified_todos_backup.json"
        self.todos: Dict = {}
        self.rationalized_todos: Dict = {}
        self.stats = {
            "original_count": 0,
            "malformed_fixed": 0,
            "duplicates_removed": 0,
            "final_count": 0,
        }

    def load_todos(self):
        """Load TODOs from file."""
        if not self.todos_file.exists():
            console.print("[red]No unified_todos.json file found![/red]")
            return False

        try:
            with open(self.todos_file, "r") as f:
                self.todos = json.load(f)
            self.stats["original_count"] = len(self.todos)
            console.print(f"[green]Loaded {len(self.todos)} TODOs[/green]")
            return True
        except Exception as e:
            console.print(f"[red]Error loading TODOs: {e}[/red]")
            return False

    def backup_todos(self):
        """Create backup of original TODOs."""
        try:
            with open(self.backup_file, "w") as f:
                json.dump(self.todos, f, indent=2)
            console.print(f"[green]Backup created: {self.backup_file}[/green]")
        except Exception as e:
            console.print(f"[red]Error creating backup: {e}[/red]")

    def fix_malformed_content(self, todo_id: str, todo: Dict) -> Dict:
        """Fix malformed TODO content."""
        original_content = todo.get("content", "")

        # Fix common malformed patterns
        fixed_content = original_content

        # Fix emoji/symbol artifacts
        fixed_content = re.sub(r"^\*\* [⚠️🔶🔸🔹🔷🔴🟡🟢⭐] ", "", fixed_content)
        fixed_content = re.sub(r"^\*\* ", "", fixed_content)

        # Fix incomplete content
        if fixed_content in ["CRITICAL", "HIGH", "MEDIUM", "LOW"]:
            # Extract from ID if possible
            if "FOUNDATION-API" in todo_id:
                fixed_content = f"Fix API consistency issues in {todo_id.replace('FOUNDATION-API-', '').replace('-', ' ')}"
            elif "FOUNDATION-TEST" in todo_id:
                fixed_content = f"Add comprehensive unit tests for {todo_id.replace('FOUNDATION-TEST-', '').replace('-', ' ')}"
            elif "FOUNDATION-MIGRATE" in todo_id:
                fixed_content = f"Migrate legacy module {todo_id.replace('FOUNDATION-MIGRATE-', '').replace('-', ' ')}"
            elif "CAPTURE" in todo_id:
                fixed_content = f"Implement capture system component {todo_id}"
            else:
                fixed_content = f"Complete task {todo_id}"

        # Fix truncated content
        if fixed_content.endswith("..."):
            # Try to extract from notes or reconstruct
            notes = todo.get("notes", "")
            if notes and len(notes) > len(fixed_content):
                # Extract first meaningful line from notes
                lines = notes.split("\n")
                for line in lines:
                    if line.strip() and not line.startswith("[") and len(line) > 10:
                        fixed_content = line.strip()
                        break

        # Fix single characters or very short content
        if len(fixed_content.strip()) <= 3:
            if "FOUNDATION" in todo_id:
                fixed_content = f"Complete Foundation task {todo_id}"
            elif "COGNITIVE" in todo_id:
                fixed_content = f"Implement cognitive amplification feature {todo_id}"
            elif "CAPTURE" in todo_id:
                fixed_content = f"Implement capture system {todo_id}"
            else:
                fixed_content = f"Complete task {todo_id}"

        # Update stats if content was fixed
        if fixed_content != original_content:
            self.stats["malformed_fixed"] += 1

        # Create fixed TODO
        fixed_todo = todo.copy()
        fixed_todo["content"] = fixed_content.strip()
        fixed_todo["updated_at"] = datetime.now().isoformat()

        return fixed_todo

    def identify_duplicates(self) -> Dict[str, List[str]]:
        """Identify duplicate TODOs based on content similarity."""
        duplicates = defaultdict(list)
        content_map = {}

        for todo_id, todo in self.todos.items():
            content = todo.get("content", "").strip().lower()

            # Normalize content for comparison
            normalized = re.sub(r"[^\w\s]", "", content)
            normalized = re.sub(r"\s+", " ", normalized)

            # Check for exact matches
            if normalized in content_map:
                duplicates[content_map[normalized]].append(todo_id)
            else:
                content_map[normalized] = todo_id

        # Remove single-item groups
        duplicates = {k: v for k, v in duplicates.items() if v}

        return duplicates

    def merge_duplicates(self, duplicates: Dict[str, List[str]]):
        """Merge duplicate TODOs."""
        for primary_id, duplicate_ids in duplicates.items():
            primary_todo = self.todos[primary_id]

            # Merge information from duplicates
            all_notes = [primary_todo.get("notes", "")]
            all_sources = [primary_todo.get("source", "")]

            for dup_id in duplicate_ids:
                if dup_id in self.todos:
                    dup_todo = self.todos[dup_id]
                    if dup_todo.get("notes"):
                        all_notes.append(dup_todo["notes"])
                    if dup_todo.get("source"):
                        all_sources.append(dup_todo["source"])

                    # Remove duplicate
                    del self.todos[dup_id]
                    self.stats["duplicates_removed"] += 1

            # Update primary with merged info
            primary_todo["notes"] = "\n".join(filter(None, all_notes))
            primary_todo["source"] = ", ".join(set(filter(None, all_sources)))

    def validate_critical_todos(self):
        """Ensure critical TODOs have proper descriptions."""
        critical_todos = {
            todo_id: todo
            for todo_id, todo in self.todos.items()
            if todo.get("priority") == "critical"
        }

        console.print(
            f"\n[yellow]Validating {len(critical_todos)} critical TODOs...[/yellow]"
        )

        for todo_id, todo in critical_todos.items():
            content = todo.get("content", "").strip()

            if (
                len(content) < 10
                or content.startswith("**")
                or content in ["CRITICAL", "HIGH", "MEDIUM", "LOW"]
            ):
                console.print(
                    f"[red]Critical TODO needs better description: {todo_id}[/red]"
                )
                console.print(f"Current content: '{content}'")

                # Try to provide better description based on ID
                if "API" in todo_id:
                    todo["content"] = (
                        "Fix critical API consistency issues preventing proper system operation"
                    )
                elif "CAPTURE" in todo_id:
                    todo["content"] = (
                        "Implement critical capture system component to prevent data loss"
                    )
                elif "FOUNDATION" in todo_id:
                    todo["content"] = (
                        "Complete critical foundation task required for system stability"
                    )
                else:
                    todo["content"] = (
                        f"Complete critical task {todo_id} required for system operation"
                    )

                self.stats["malformed_fixed"] += 1

    def rationalize_todos(self):
        """Main rationalization process."""
        console.print("\n[bold blue]Starting TODO Rationalization Process[/bold blue]")

        # Step 1: Fix malformed content
        console.print("\n[yellow]Step 1: Fixing malformed content...[/yellow]")
        with Progress(
            SpinnerColumn(), TextColumn("[progress.description]{task.description}")
        ) as progress:
            task = progress.add_task("Fixing malformed TODOs...", total=len(self.todos))

            for todo_id, todo in list(self.todos.items()):
                self.todos[todo_id] = self.fix_malformed_content(todo_id, todo)
                progress.advance(task)

        # Step 2: Identify and merge duplicates
        console.print("\n[yellow]Step 2: Identifying duplicates...[/yellow]")
        duplicates = self.identify_duplicates()

        if duplicates:
            console.print(f"[red]Found {len(duplicates)} groups of duplicates[/red]")
            for primary_id, duplicate_ids in duplicates.items():
                console.print(f"  {primary_id} has duplicates: {duplicate_ids}")

            console.print("[yellow]Automatically merging duplicates...[/yellow]")
            self.merge_duplicates(duplicates)

        # Step 3: Validate critical TODOs
        console.print("\n[yellow]Step 3: Validating critical TODOs...[/yellow]")
        self.validate_critical_todos()

        # Step 4: Clean up structure
        console.print("\n[yellow]Step 4: Cleaning up structure...[/yellow]")
        for todo_id, todo in self.todos.items():
            # Ensure all required fields exist
            todo.setdefault("id", todo_id)
            todo.setdefault("status", "pending")
            todo.setdefault("priority", "medium")
            todo.setdefault("category", "general")
            todo.setdefault("dependencies", [])
            todo.setdefault("created_at", datetime.now().isoformat())
            todo.setdefault("updated_at", datetime.now().isoformat())

            # Clean up notes
            notes = todo.get("notes", "")
            if notes:
                # Remove excessive duplication in notes
                lines = notes.split("\n")
                unique_lines = []
                seen = set()
                for line in lines:
                    if line.strip() and line not in seen:
                        unique_lines.append(line)
                        seen.add(line)
                todo["notes"] = "\n".join(unique_lines)

        self.stats["final_count"] = len(self.todos)

    def save_rationalized_todos(self):
        """Save the rationalized TODOs."""
        try:
            with open(self.todos_file, "w") as f:
                json.dump(self.todos, f, indent=2)
            console.print(f"[green]Saved {len(self.todos)} rationalized TODOs[/green]")
        except Exception as e:
            console.print(f"[red]Error saving TODOs: {e}[/red]")

    def print_summary(self):
        """Print rationalization summary."""
        console.print("\n[bold green]Rationalization Summary[/bold green]")

        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Metric", style="cyan")
        table.add_column("Count", style="green")
        table.add_column("Change", style="yellow")

        table.add_row("Original TODOs", str(self.stats["original_count"]), "")
        table.add_row("Malformed Fixed", str(self.stats["malformed_fixed"]), "✓")
        table.add_row("Duplicates Removed", str(self.stats["duplicates_removed"]), "✓")
        table.add_row(
            "Final TODOs",
            str(self.stats["final_count"]),
            f"{self.stats['final_count'] - self.stats['original_count']:+d}",
        )

        console.print(table)

        # Show critical TODOs
        critical_todos = {
            todo_id: todo
            for todo_id, todo in self.todos.items()
            if todo.get("priority") == "critical"
        }

        if critical_todos:
            console.print(
                f"\n[bold red]Critical TODOs ({len(critical_todos)}):[/bold red]"
            )
            for todo_id, todo in critical_todos.items():
                console.print(f"  • {todo_id}: {todo['content']}")

    def run(self):
        """Run the complete rationalization process."""
        console.print(
            Panel.fit(
                "[bold blue]Atlas TODO Rationalization[/bold blue]\n"
                "This will clean up and rationalize the TODO system",
                title="TODO Rationalization",
            )
        )

        if not self.load_todos():
            return False

        self.backup_todos()
        self.rationalize_todos()
        self.save_rationalized_todos()
        self.print_summary()

        return True


def main():
    """Main entry point."""
    rationalizer = TodoRationalizer()
    success = rationalizer.run()

    if success:
        console.print(
            "\n[bold green]TODO rationalization completed successfully![/bold green]"
        )
        console.print(
            "Run 'python3 scripts/unified_todo_manager.py --dashboard' to see the cleaned results."
        )
    else:
        console.print("\n[bold red]TODO rationalization failed![/bold red]")
        sys.exit(1)


if __name__ == "__main__":
    main()
