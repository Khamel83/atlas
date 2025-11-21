#!/usr/bin/env python3
"""
Atlas TODO Consolidation System

This system scans all sources of TODOs across the project and maintains
a unified tracking system. It integrates with the existing dev_workflow.py
but provides comprehensive coverage across all TODO sources.
"""

import json
import re
import subprocess
import sys
from dataclasses import asdict, dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

try:
    from rich.console import Console
    from rich.progress import Progress, SpinnerColumn, TextColumn
    from rich.rule import Rule
    from rich.table import Table
except ImportError:
    print("Rich library not found. Please run 'pip install rich'.")
    sys.exit(1)

console = Console()


class TodoSource(Enum):
    CURSOR_SYSTEM = "cursor_system"
    DEV_TASKS_JSON = "dev_tasks_json"
    DOCUMENTATION = "documentation"
    INLINE_CODE = "inline_code"
    ROADMAP_FILES = "roadmap_files"
    CHECKLIST_FILES = "checklist_files"
    ISSUE_TRACKER = "issue_tracker"


class TodoStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    BLOCKED = "blocked"


class TodoPriority(Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class UnifiedTodo:
    id: str
    content: str
    status: TodoStatus
    priority: TodoPriority
    source: TodoSource
    file_path: Optional[str] = None
    line_number: Optional[int] = None
    category: Optional[str] = None
    estimated_time: Optional[int] = None  # minutes
    dependencies: List[str] = None
    last_updated: Optional[str] = None
    notes: Optional[str] = None

    def __post_init__(self):
        if self.dependencies is None:
            self.dependencies = []
        if self.last_updated is None:
            self.last_updated = datetime.now().isoformat()


class TodoConsolidator:
    """Consolidates TODOs from all sources across the project."""

    def __init__(self):
        self.console = console
        self.project_root = Path(__file__).parent.parent
        self.unified_todos_file = self.project_root / "unified_todos.json"
        self.todos: Dict[str, UnifiedTodo] = {}
        self.load_unified_todos()

    def load_unified_todos(self):
        """Load existing unified todos from file."""
        if self.unified_todos_file.exists():
            try:
                with open(self.unified_todos_file, "r") as f:
                    todos_data = json.load(f)
                    self.todos = {
                        todo_id: UnifiedTodo(**todo_data)
                        for todo_id, todo_data in todos_data.items()
                    }
                    # Convert string enums back to enum objects
                    for todo in self.todos.values():
                        todo.status = TodoStatus(todo.status)
                        todo.priority = TodoPriority(todo.priority)
                        todo.source = TodoSource(todo.source)
            except Exception as e:
                console.print(f"[red]Error loading unified todos: {e}[/red]")
                self.todos = {}

    def save_unified_todos(self):
        """Save unified todos to file."""
        todos_data = {}
        for todo_id, todo in self.todos.items():
            todo_dict = asdict(todo)
            todo_dict["status"] = todo.status.value
            todo_dict["priority"] = todo.priority.value
            todo_dict["source"] = todo.source.value
            todos_data[todo_id] = todo_dict

        with open(self.unified_todos_file, "w") as f:
            json.dump(todos_data, f, indent=2)

    def scan_cursor_system_todos(self) -> List[UnifiedTodo]:
        """Extract TODOs from Cursor's TODO system (if accessible)."""
        todos = []

        # Try to read from .cursor/todos.json or similar
        # This is a placeholder - actual implementation would depend on Cursor's format
        cursor_files = [
            self.project_root / ".cursor" / "todos.json",
            self.project_root / ".vscode" / "todos.json",
            self.project_root / "todos.json",
        ]

        for cursor_file in cursor_files:
            if cursor_file.exists():
                try:
                    with open(cursor_file, "r") as f:
                        cursor_data = json.load(f)
                        # Parse cursor TODO format
                        for i, todo_data in enumerate(cursor_data.get("todos", [])):
                            todo_id = f"CURSOR-{i+1}"
                            todo = UnifiedTodo(
                                id=todo_id,
                                content=todo_data.get("content", ""),
                                status=TodoStatus.PENDING,  # Default
                                priority=TodoPriority.MEDIUM,  # Default
                                source=TodoSource.CURSOR_SYSTEM,
                                file_path=str(cursor_file),
                                category=todo_data.get("category", "general"),
                            )
                            todos.append(todo)
                except Exception as e:
                    console.print(
                        f"[yellow]Could not parse cursor file {cursor_file}: {e}[/yellow]"
                    )

        return todos

    def scan_dev_tasks_json(self) -> List[UnifiedTodo]:
        """Extract TODOs from dev_tasks.json."""
        todos = []
        dev_tasks_file = self.project_root / "dev_tasks.json"

        if dev_tasks_file.exists():
            try:
                with open(dev_tasks_file, "r") as f:
                    dev_tasks = json.load(f)

                for task_id, task_data in dev_tasks.items():
                    todo = UnifiedTodo(
                        id=task_id,
                        content=task_data.get("content", ""),
                        status=TodoStatus(task_data.get("status", "pending")),
                        priority=TodoPriority(task_data.get("priority", "medium")),
                        source=TodoSource.DEV_TASKS_JSON,
                        file_path=str(dev_tasks_file),
                        category=task_data.get("category", "foundation"),
                        estimated_time=task_data.get("estimated_time"),
                        dependencies=task_data.get("dependencies", []),
                        notes=task_data.get("implementation_notes", ""),
                    )
                    todos.append(todo)
            except Exception as e:
                console.print(f"[red]Error parsing dev_tasks.json: {e}[/red]")

        return todos

    def scan_inline_code_todos(self) -> List[UnifiedTodo]:
        """Scan for TODO/FIXME comments in code."""
        todos = []

        try:
            # Use ripgrep to find TODO/FIXME comments
            cmd = [
                "rg",
                "-i",
                r"(TODO|FIXME|XXX|HACK)",
                "-g",
                "*.py",
                "-g",
                "!__pycache__",
                "-g",
                "!.venv",
                "-g",
                "!venv",
                "--no-ignore",
                "--vimgrep",
            ]
            result = subprocess.run(
                cmd, capture_output=True, text=True, cwd=self.project_root
            )

            if result.returncode == 0 and result.stdout:
                lines = result.stdout.strip().split("\n")
                for line in lines:
                    parts = line.split(":", 3)
                    if len(parts) == 4:
                        file_path, line_num, _, comment = parts

                        # Create unique ID based on file and line
                        todo_id = f"CODE-{file_path.replace('/', '_')}-{line_num}"

                        # Extract priority from comment
                        priority = TodoPriority.MEDIUM
                        if "CRITICAL" in comment.upper() or "URGENT" in comment.upper():
                            priority = TodoPriority.CRITICAL
                        elif "HIGH" in comment.upper():
                            priority = TodoPriority.HIGH
                        elif "LOW" in comment.upper():
                            priority = TodoPriority.LOW

                        todo = UnifiedTodo(
                            id=todo_id,
                            content=comment.strip(),
                            status=TodoStatus.PENDING,
                            priority=priority,
                            source=TodoSource.INLINE_CODE,
                            file_path=file_path,
                            line_number=int(line_num),
                            category="code_improvement",
                        )
                        todos.append(todo)
        except Exception as e:
            console.print(f"[yellow]Could not scan inline code TODOs: {e}[/yellow]")

        return todos

    def scan_documentation_todos(self) -> List[UnifiedTodo]:
        """Scan documentation files for TODO references."""
        todos = []

        doc_files = [
            "docs/remaining_tasks.md",
            "docs/project_status_and_roadmap.md",
            "docs/CURRENT_STATUS_SUMMARY.md",
            "docs/NEXT_CONTEXT_HANDOFF.md",
            "docs/MASTER_ROADMAP.md",
            "docs/implementation_plan.md",
            "docs/instapaper_ingestion_design.md",
        ]

        for doc_file in doc_files:
            file_path = self.project_root / doc_file
            if file_path.exists():
                try:
                    with open(file_path, "r") as f:
                        content = f.read()

                    # Look for task patterns
                    patterns = [
                        r"(?:FOUNDATION|COGNITIVE|ARCH|CAPTURE|ASK|SELF-HEAL|REALTIME|ADVANCED)-\w+(?:-\d+)?",
                        r"- \[ \] (.+)",  # Markdown checkboxes
                        r"TODO: (.+)",
                        r"### (.+) \((.+)\)",  # Task headers
                    ]

                    for pattern in patterns:
                        matches = re.finditer(
                            pattern, content, re.MULTILINE | re.IGNORECASE
                        )
                        for match in matches:
                            if pattern.startswith("(?:"):  # Task ID pattern
                                task_id = match.group(0)
                                # Try to find the description on the same line or next line
                                lines = content.split("\n")
                                for i, line in enumerate(lines):
                                    if task_id in line:
                                        content_text = line.split(task_id)[-1].strip(
                                            " :-"
                                        )
                                        if not content_text and i + 1 < len(lines):
                                            content_text = lines[i + 1].strip(" -")
                                        break
                                else:
                                    content_text = f"Task {task_id}"
                            else:
                                content_text = (
                                    match.group(1) if match.groups() else match.group(0)
                                )
                                task_id = (
                                    f"DOC-{doc_file.replace('/', '_')}-{len(todos)+1}"
                                )

                            # Determine priority from content
                            priority = TodoPriority.MEDIUM
                            if any(
                                word in content_text.upper()
                                for word in ["CRITICAL", "URGENT", "MUST"]
                            ):
                                priority = TodoPriority.CRITICAL
                            elif any(
                                word in content_text.upper()
                                for word in ["HIGH", "IMPORTANT"]
                            ):
                                priority = TodoPriority.HIGH
                            elif any(
                                word in content_text.upper() for word in ["LOW", "NICE"]
                            ):
                                priority = TodoPriority.LOW

                            todo = UnifiedTodo(
                                id=task_id,
                                content=content_text,
                                status=TodoStatus.PENDING,
                                priority=priority,
                                source=TodoSource.DOCUMENTATION,
                                file_path=doc_file,
                                category="documentation",
                            )
                            todos.append(todo)

                except Exception as e:
                    console.print(f"[yellow]Could not scan {doc_file}: {e}[/yellow]")

        return todos

    def scan_checklist_files(self) -> List[UnifiedTodo]:
        """Scan checklist files for TODOs."""
        todos = []

        checklist_files = [
            "checklists/checkcheckit.yaml",
            "docs/troubleshooting_checklist.md",
        ]

        for checklist_file in checklist_files:
            file_path = self.project_root / checklist_file
            if file_path.exists():
                try:
                    with open(file_path, "r") as f:
                        content = f.read()

                    # Look for unchecked items
                    patterns = [
                        r"- \[ \] (.+)",  # Markdown unchecked
                        r"- (.+)",  # YAML list items
                    ]

                    for pattern in patterns:
                        matches = re.finditer(pattern, content, re.MULTILINE)
                        for i, match in enumerate(matches):
                            task_id = (
                                f"CHECKLIST-{checklist_file.replace('/', '_')}-{i+1}"
                            )
                            content_text = match.group(1)

                            todo = UnifiedTodo(
                                id=task_id,
                                content=content_text,
                                status=TodoStatus.PENDING,
                                priority=TodoPriority.MEDIUM,
                                source=TodoSource.CHECKLIST_FILES,
                                file_path=checklist_file,
                                category="checklist",
                            )
                            todos.append(todo)

                except Exception as e:
                    console.print(
                        f"[yellow]Could not scan {checklist_file}: {e}[/yellow]"
                    )

        return todos

    def consolidate_all_todos(self) -> Dict[str, List[UnifiedTodo]]:
        """Consolidate TODOs from all sources."""
        console.print("[cyan]Consolidating TODOs from all sources...[/cyan]")

        all_todos = {}

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:

            # Scan each source
            sources = [
                ("Cursor System", self.scan_cursor_system_todos),
                ("Dev Tasks JSON", self.scan_dev_tasks_json),
                ("Inline Code", self.scan_inline_code_todos),
                ("Documentation", self.scan_documentation_todos),
                ("Checklist Files", self.scan_checklist_files),
            ]

            for source_name, scan_func in sources:
                task = progress.add_task(f"Scanning {source_name}...", total=None)
                try:
                    todos = scan_func()
                    all_todos[source_name] = todos
                    progress.update(
                        task, description=f"✓ {source_name} ({len(todos)} todos)"
                    )
                except Exception as e:
                    progress.update(task, description=f"✗ {source_name} (error: {e})")
                    all_todos[source_name] = []

        return all_todos

    def merge_and_deduplicate(
        self, all_todos: Dict[str, List[UnifiedTodo]]
    ) -> Dict[str, UnifiedTodo]:
        """Merge todos from all sources and deduplicate."""
        merged = {}

        for source_name, todos in all_todos.items():
            for todo in todos:
                # Check for duplicates based on content similarity
                duplicate_id = None
                for existing_id, existing_todo in merged.items():
                    if self._are_similar_todos(todo, existing_todo):
                        duplicate_id = existing_id
                        break

                if duplicate_id:
                    # Update existing todo with additional info
                    existing_todo = merged[duplicate_id]
                    if todo.source == TodoSource.DEV_TASKS_JSON:
                        # Dev tasks have more detailed info, use it
                        existing_todo.status = todo.status
                        existing_todo.priority = todo.priority
                        existing_todo.estimated_time = todo.estimated_time
                        existing_todo.dependencies = todo.dependencies
                        existing_todo.notes = todo.notes
                    existing_todo.notes = f"{existing_todo.notes or ''}\n[{todo.source.value}] {todo.file_path or 'No file'}"
                else:
                    # New unique todo
                    merged[todo.id] = todo

        return merged

    def _are_similar_todos(self, todo1: UnifiedTodo, todo2: UnifiedTodo) -> bool:
        """Check if two todos are similar enough to be considered duplicates."""
        # Simple similarity check - could be improved with fuzzy matching
        content1 = todo1.content.lower().strip()
        content2 = todo2.content.lower().strip()

        # Check for exact match
        if content1 == content2:
            return True

        # Check for significant overlap
        words1 = set(content1.split())
        words2 = set(content2.split())

        if len(words1) == 0 or len(words2) == 0:
            return False

        overlap = len(words1.intersection(words2))
        min_words = min(len(words1), len(words2))

        return overlap / min_words > 0.7  # 70% word overlap

    def display_consolidated_report(self, merged_todos: Dict[str, UnifiedTodo]):
        """Display comprehensive consolidated TODO report."""
        console.print(
            Rule("[bold blue]Unified TODO Consolidation Report", style="blue")
        )

        # Summary statistics
        total_todos = len(merged_todos)
        status_counts = {}
        priority_counts = {}
        source_counts = {}

        for todo in merged_todos.values():
            status_counts[todo.status] = status_counts.get(todo.status, 0) + 1
            priority_counts[todo.priority] = priority_counts.get(todo.priority, 0) + 1
            source_counts[todo.source] = source_counts.get(todo.source, 0) + 1

        # Summary table
        summary_table = Table(title=f"TODO Summary ({total_todos} total)")
        summary_table.add_column("Metric", style="cyan")
        summary_table.add_column("Count", style="magenta")
        summary_table.add_column("Percentage", style="yellow")

        for status, count in status_counts.items():
            percentage = (count / total_todos) * 100
            summary_table.add_row(
                f"Status: {status.value.title()}", str(count), f"{percentage:.1f}%"
            )

        console.print(summary_table)

        # Priority breakdown
        priority_table = Table(title="Priority Breakdown")
        priority_table.add_column("Priority", style="cyan")
        priority_table.add_column("Count", style="magenta")
        priority_table.add_column("Pending", style="yellow")
        priority_table.add_column("In Progress", style="blue")
        priority_table.add_column("Completed", style="green")

        for priority in [
            TodoPriority.CRITICAL,
            TodoPriority.HIGH,
            TodoPriority.MEDIUM,
            TodoPriority.LOW,
        ]:
            priority_todos = [
                t for t in merged_todos.values() if t.priority == priority
            ]
            total_count = len(priority_todos)
            pending = len([t for t in priority_todos if t.status == TodoStatus.PENDING])
            in_progress = len(
                [t for t in priority_todos if t.status == TodoStatus.IN_PROGRESS]
            )
            completed = len(
                [t for t in priority_todos if t.status == TodoStatus.COMPLETED]
            )

            priority_table.add_row(
                priority.value.title(),
                str(total_count),
                str(pending),
                str(in_progress),
                str(completed),
            )

        console.print(priority_table)

        # Source breakdown
        source_table = Table(title="Source Breakdown")
        source_table.add_column("Source", style="cyan")
        source_table.add_column("Count", style="magenta")
        source_table.add_column("Percentage", style="yellow")

        for source, count in source_counts.items():
            percentage = (count / total_todos) * 100
            source_table.add_row(
                source.value.replace("_", " ").title(), str(count), f"{percentage:.1f}%"
            )

        console.print(source_table)

        # Next priority tasks
        pending_todos = [
            t for t in merged_todos.values() if t.status == TodoStatus.PENDING
        ]
        pending_todos.sort(
            key=lambda t: (
                0
                if t.priority == TodoPriority.CRITICAL
                else (
                    1
                    if t.priority == TodoPriority.HIGH
                    else 2 if t.priority == TodoPriority.MEDIUM else 3
                )
            )
        )

        next_table = Table(title="Next Priority Tasks (Top 10)")
        next_table.add_column("ID", style="cyan")
        next_table.add_column("Priority", style="magenta")
        next_table.add_column("Content", style="white")
        next_table.add_column("Source", style="yellow")
        next_table.add_column("Est. Time", style="blue")

        for todo in pending_todos[:10]:
            next_table.add_row(
                todo.id,
                todo.priority.value.title(),
                todo.content[:50] + "..." if len(todo.content) > 50 else todo.content,
                todo.source.value.replace("_", " ").title(),
                f"{todo.estimated_time}m" if todo.estimated_time else "N/A",
            )

        console.print(next_table)

        # Critical warnings
        critical_todos = [
            t
            for t in merged_todos.values()
            if t.priority == TodoPriority.CRITICAL and t.status == TodoStatus.PENDING
        ]
        if critical_todos:
            console.print(
                f"\n[bold red]⚠️  {len(critical_todos)} CRITICAL TODOs require immediate attention![/bold red]"
            )
            for todo in critical_todos:
                console.print(f"  • {todo.id}: {todo.content}")

    def update_unified_system(self):
        """Update the unified TODO system with latest data."""
        all_todos = self.consolidate_all_todos()
        merged_todos = self.merge_and_deduplicate(all_todos)

        # Update internal state
        self.todos = merged_todos

        # Save to file
        self.save_unified_todos()

        # Display report
        self.display_consolidated_report(merged_todos)

        return merged_todos

    def export_to_dev_workflow(self):
        """Export unified todos to dev_workflow.py format."""
        dev_tasks = {}

        for todo in self.todos.values():
            if todo.source == TodoSource.DEV_TASKS_JSON:
                # Already in dev_workflow format
                dev_tasks[todo.id] = {
                    "id": todo.id,
                    "content": todo.content,
                    "status": todo.status.value,
                    "priority": todo.priority.value,
                    "dependencies": todo.dependencies,
                    "category": todo.category or "general",
                    "estimated_time": todo.estimated_time or 30,
                    "complexity": 3,  # Default
                    "implementation_notes": todo.notes or "",
                    "git_commits": [],
                }

        # Save to dev_tasks.json
        dev_tasks_file = self.project_root / "dev_tasks.json"
        with open(dev_tasks_file, "w") as f:
            json.dump(dev_tasks, f, indent=2)

        console.print(
            f"[green]Exported {len(dev_tasks)} tasks to dev_tasks.json[/green]"
        )


def main():
    """Main entry point for TODO consolidation."""
    consolidator = TodoConsolidator()

    if len(sys.argv) > 1:
        arg = sys.argv[1]
        if arg == "--update":
            consolidator.update_unified_system()
        elif arg == "--export":
            consolidator.export_to_dev_workflow()
        elif arg == "--report":
            consolidator.update_unified_system()
        else:
            console.print(f"[red]Unknown argument: {arg}[/red]")
            console.print("Available arguments: --update, --export, --report")
            sys.exit(1)
    else:
        # Interactive mode
        console.print("[cyan]Atlas TODO Consolidation System[/cyan]")
        console.print("1. Update unified system")
        console.print("2. Export to dev workflow")
        console.print("3. Show report only")

        choice = input("Choose option (1-3): ")

        if choice == "1":
            consolidator.update_unified_system()
        elif choice == "2":
            consolidator.export_to_dev_workflow()
        elif choice == "3":
            consolidator.update_unified_system()
        else:
            console.print("[red]Invalid choice[/red]")


if __name__ == "__main__":
    main()
