#!/usr/bin/env python3
"""
Atlas Unified TODO Management System

This system acts as the single source of truth for all TODOs across the project.
It provides bidirectional sync with all TODO sources and ensures consistency.
When a TODO is added/modified/completed anywhere, it's reflected everywhere.
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
    from rich.prompt import Prompt
    from rich.rule import Rule
    from rich.table import Table
except ImportError:
    print("Rich library not found. Please run 'pip install rich'.")
    sys.exit(1)

console = Console()


class TodoSource(Enum):
    MASTER = "master"  # The unified system (single source of truth)
    DEV_WORKFLOW = "dev_workflow"  # dev_tasks.json
    INLINE_CODE = "inline_code"  # TODO comments in code
    DOCUMENTATION = "documentation"  # Task references in docs
    CHECKLIST = "checklist"  # Checklist items
    HEALTH_CHECK = "health_check"  # Issues found by health check


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
    category: str
    file_path: Optional[str] = None
    line_number: Optional[int] = None
    estimated_time: Optional[int] = None  # minutes
    dependencies: List[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    completed_at: Optional[str] = None
    notes: Optional[str] = None
    tags: List[str] = None

    def __post_init__(self):
        if self.dependencies is None:
            self.dependencies = []
        if self.tags is None:
            self.tags = []
        if self.created_at is None:
            self.created_at = datetime.now().isoformat()
        if self.updated_at is None:
            self.updated_at = datetime.now().isoformat()


class UnifiedTodoManager:
    """Unified TODO management system - single source of truth."""

    def __init__(self):
        self.console = console
        self.project_root = Path(__file__).parent.parent
        self.master_todos_file = self.project_root / "master_todos.json"
        self.sync_log_file = self.project_root / "logs" / "todo_sync.log"
        self.todos: Dict[str, UnifiedTodo] = {}

        # Ensure logs directory exists
        self.sync_log_file.parent.mkdir(exist_ok=True)

        self.setup_logging()
        self.load_master_todos()

    def setup_logging(self):
        """Setup logging for sync operations."""
        import logging

        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(levelname)s - %(message)s",
            handlers=[logging.FileHandler(self.sync_log_file), logging.StreamHandler()],
        )
        self.logger = logging.getLogger(__name__)

    def load_master_todos(self):
        """Load master TODOs from the single source of truth."""
        if self.master_todos_file.exists():
            try:
                with open(self.master_todos_file, "r") as f:
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
                self.logger.error(f"Error loading master todos: {e}")
                self.todos = {}
        else:
            # Initialize with empty master todos
            self.todos = {}
            self.save_master_todos()

    def save_master_todos(self):
        """Save master TODOs to the single source of truth."""
        todos_data = {}
        for todo_id, todo in self.todos.items():
            todo_dict = asdict(todo)
            todo_dict["status"] = todo.status.value
            todo_dict["priority"] = todo.priority.value
            todo_dict["source"] = todo.source.value
            todo_dict["updated_at"] = datetime.now().isoformat()
            todos_data[todo_id] = todo_dict

        with open(self.master_todos_file, "w") as f:
            json.dump(todos_data, f, indent=2)

        self.logger.info(f"Saved {len(todos_data)} todos to master file")

    def generate_todo_id(
        self, content: str, source: TodoSource, file_path: str = None
    ) -> str:
        """Generate a unique TODO ID based on content and source."""
        import hashlib

        # Create a hash of the content for uniqueness
        content_hash = hashlib.md5(content.encode()).hexdigest()[:8]

        # Use source prefix
        source_prefix = {
            TodoSource.MASTER: "MASTER",
            TodoSource.DEV_WORKFLOW: "DEV",
            TodoSource.INLINE_CODE: "CODE",
            TodoSource.DOCUMENTATION: "DOC",
            TodoSource.CHECKLIST: "CHECK",
            TodoSource.HEALTH_CHECK: "HEALTH",
        }

        prefix = source_prefix.get(source, "TODO")

        # Include file reference if available
        if file_path:
            file_ref = Path(file_path).stem.replace(".", "_")[:10]
            return f"{prefix}-{file_ref}-{content_hash}"
        else:
            return f"{prefix}-{content_hash}"

    def add_todo(
        self,
        content: str,
        priority: TodoPriority = TodoPriority.MEDIUM,
        source: TodoSource = TodoSource.MASTER,
        category: str = "general",
        file_path: str = None,
        line_number: int = None,
        estimated_time: int = None,
        dependencies: List[str] = None,
        tags: List[str] = None,
        notes: str = None,
    ) -> str:
        """Add a new TODO to the unified system."""

        # Check for duplicates
        existing_id = self.find_duplicate(content)
        if existing_id:
            self.logger.warning(f"Duplicate TODO found: {existing_id}")
            return existing_id

        # Generate unique ID
        todo_id = self.generate_todo_id(content, source, file_path)

        # Create the TODO
        todo = UnifiedTodo(
            id=todo_id,
            content=content,
            status=TodoStatus.PENDING,
            priority=priority,
            source=source,
            category=category,
            file_path=file_path,
            line_number=line_number,
            estimated_time=estimated_time,
            dependencies=dependencies or [],
            tags=tags or [],
            notes=notes,
        )

        self.todos[todo_id] = todo
        self.save_master_todos()

        # Sync to all other systems
        self.sync_todo_to_systems(todo)

        self.logger.info(f"Added TODO: {todo_id} - {content[:50]}...")
        return todo_id

    def update_todo(self, todo_id: str, **kwargs) -> bool:
        """Update a TODO in the unified system."""
        if todo_id not in self.todos:
            self.logger.error(f"TODO not found: {todo_id}")
            return False

        todo = self.todos[todo_id]

        # Update fields
        for key, value in kwargs.items():
            if hasattr(todo, key):
                if key == "status" and isinstance(value, str):
                    todo.status = TodoStatus(value)
                elif key == "priority" and isinstance(value, str):
                    todo.priority = TodoPriority(value)
                elif key == "source" and isinstance(value, str):
                    todo.source = TodoSource(value)
                else:
                    setattr(todo, key, value)

        todo.updated_at = datetime.now().isoformat()

        # Set completion time if marked as completed
        if todo.status == TodoStatus.COMPLETED and not todo.completed_at:
            todo.completed_at = datetime.now().isoformat()

        self.save_master_todos()

        # Sync to all other systems
        self.sync_todo_to_systems(todo)

        self.logger.info(f"Updated TODO: {todo_id}")
        return True

    def complete_todo(self, todo_id: str, notes: str = None) -> bool:
        """Mark a TODO as completed."""
        return self.update_todo(
            todo_id,
            status=TodoStatus.COMPLETED,
            completed_at=datetime.now().isoformat(),
            notes=f"{self.todos[todo_id].notes or ''}\nCompleted: {notes or 'No notes'}",
        )

    def delete_todo(self, todo_id: str) -> bool:
        """Delete a TODO from the unified system."""
        if todo_id not in self.todos:
            self.logger.error(f"TODO not found: {todo_id}")
            return False

        todo = self.todos[todo_id]

        # Remove from all systems
        self.remove_todo_from_systems(todo)

        # Remove from master
        del self.todos[todo_id]
        self.save_master_todos()

        self.logger.info(f"Deleted TODO: {todo_id}")
        return True

    def find_duplicate(self, content: str) -> Optional[str]:
        """Find if a TODO with similar content already exists."""
        content_lower = content.lower().strip()

        for todo_id, todo in self.todos.items():
            if todo.content.lower().strip() == content_lower:
                return todo_id

            # Check for significant overlap (70% word similarity)
            words1 = set(content_lower.split())
            words2 = set(todo.content.lower().split())

            if len(words1) > 0 and len(words2) > 0:
                overlap = len(words1.intersection(words2))
                min_words = min(len(words1), len(words2))
                if overlap / min_words > 0.7:
                    return todo_id

        return None

    def sync_todo_to_systems(self, todo: UnifiedTodo):
        """Sync a TODO to all relevant external systems."""
        if todo.source == TodoSource.DEV_WORKFLOW or todo.category == "foundation":
            self.sync_to_dev_workflow(todo)

        if todo.source == TodoSource.INLINE_CODE:
            self.sync_to_inline_code(todo)

        if todo.source == TodoSource.DOCUMENTATION:
            self.sync_to_documentation(todo)

        if todo.source == TodoSource.CHECKLIST:
            self.sync_to_checklist(todo)

    def sync_to_dev_workflow(self, todo: UnifiedTodo):
        """Sync TODO to dev_tasks.json."""
        dev_tasks_file = self.project_root / "dev_tasks.json"

        try:
            if dev_tasks_file.exists():
                with open(dev_tasks_file, "r") as f:
                    dev_tasks = json.load(f)
            else:
                dev_tasks = {}

            # Update or add the task
            dev_tasks[todo.id] = {
                "id": todo.id,
                "content": todo.content,
                "status": todo.status.value,
                "priority": todo.priority.value,
                "dependencies": todo.dependencies,
                "category": todo.category,
                "estimated_time": todo.estimated_time or 30,
                "complexity": 3,  # Default
                "implementation_notes": todo.notes or "",
                "git_commits": [],
                "last_attempt": None,
                "failure_count": 0,
            }

            with open(dev_tasks_file, "w") as f:
                json.dump(dev_tasks, f, indent=2)

            self.logger.info(f"Synced TODO {todo.id} to dev_workflow")

        except Exception as e:
            self.logger.error(f"Failed to sync to dev_workflow: {e}")

    def sync_to_inline_code(self, todo: UnifiedTodo):
        """Sync TODO to inline code comments."""
        if not todo.file_path or not todo.line_number:
            return

        file_path = self.project_root / todo.file_path
        if not file_path.exists():
            return

        try:
            with open(file_path, "r") as f:
                lines = f.readlines()

            # Update the TODO comment
            if todo.line_number <= len(lines):
                line = lines[todo.line_number - 1]
                if todo.status == TodoStatus.COMPLETED:
                    # Comment out or mark as done
                    if "TODO:" in line:
                        lines[todo.line_number - 1] = line.replace("TODO:", "DONE:")
                    elif "FIXME:" in line:
                        lines[todo.line_number - 1] = line.replace("FIXME:", "FIXED:")

                with open(file_path, "w") as f:
                    f.writelines(lines)

                self.logger.info(f"Synced TODO {todo.id} to inline code")

        except Exception as e:
            self.logger.error(f"Failed to sync to inline code: {e}")

    def sync_to_documentation(self, todo: UnifiedTodo):
        """Sync TODO to documentation files."""
        if not todo.file_path:
            return

        file_path = self.project_root / todo.file_path
        if not file_path.exists():
            return

        try:
            with open(file_path, "r") as f:
                content = f.read()

            # Update documentation based on status
            if todo.status == TodoStatus.COMPLETED:
                # Mark as completed in documentation
                patterns = [
                    (rf"- \[ \] {re.escape(todo.content)}", f"- [x] {todo.content}"),
                    (rf"pending \({todo.id}\)", f"completed ({todo.id})"),
                    (rf"TODO: {re.escape(todo.content)}", f"DONE: {todo.content}"),
                ]

                for pattern, replacement in patterns:
                    content = re.sub(pattern, replacement, content, flags=re.MULTILINE)

                with open(file_path, "w") as f:
                    f.write(content)

                self.logger.info(f"Synced TODO {todo.id} to documentation")

        except Exception as e:
            self.logger.error(f"Failed to sync to documentation: {e}")

    def sync_to_checklist(self, todo: UnifiedTodo):
        """Sync TODO to checklist files."""
        if not todo.file_path:
            return

        file_path = self.project_root / todo.file_path
        if not file_path.exists():
            return

        try:
            with open(file_path, "r") as f:
                content = f.read()

            # Update checklist based on status
            if todo.status == TodoStatus.COMPLETED:
                # Mark as checked
                pattern = rf"- \[ \] {re.escape(todo.content)}"
                replacement = f"- [x] {todo.content}"
                content = re.sub(pattern, replacement, content, flags=re.MULTILINE)

                with open(file_path, "w") as f:
                    f.write(content)

                self.logger.info(f"Synced TODO {todo.id} to checklist")

        except Exception as e:
            self.logger.error(f"Failed to sync to checklist: {e}")

    def remove_todo_from_systems(self, todo: UnifiedTodo):
        """Remove a TODO from all external systems."""
        # Remove from dev_workflow
        if todo.source == TodoSource.DEV_WORKFLOW:
            dev_tasks_file = self.project_root / "dev_tasks.json"
            if dev_tasks_file.exists():
                try:
                    with open(dev_tasks_file, "r") as f:
                        dev_tasks = json.load(f)

                    if todo.id in dev_tasks:
                        del dev_tasks[todo.id]

                        with open(dev_tasks_file, "w") as f:
                            json.dump(dev_tasks, f, indent=2)

                        self.logger.info(f"Removed TODO {todo.id} from dev_workflow")
                except Exception as e:
                    self.logger.error(f"Failed to remove from dev_workflow: {e}")

    def import_from_external_systems(self):
        """Import TODOs from all external systems into the unified system."""
        console.print("[cyan]Importing TODOs from external systems...[/cyan]")

        imported_count = 0

        # Import from dev_tasks.json
        imported_count += self.import_from_dev_workflow()

        # Import from inline code
        imported_count += self.import_from_inline_code()

        # Import from documentation
        imported_count += self.import_from_documentation()

        # Import from checklists
        imported_count += self.import_from_checklists()

        self.save_master_todos()

        console.print(
            f"[green]Imported {imported_count} TODOs from external systems[/green]"
        )
        return imported_count

    def import_from_dev_workflow(self) -> int:
        """Import TODOs from dev_tasks.json."""
        dev_tasks_file = self.project_root / "dev_tasks.json"
        if not dev_tasks_file.exists():
            return 0

        imported = 0
        try:
            with open(dev_tasks_file, "r") as f:
                dev_tasks = json.load(f)

            for task_id, task_data in dev_tasks.items():
                if task_id not in self.todos:
                    todo = UnifiedTodo(
                        id=task_id,
                        content=task_data.get("content", ""),
                        status=TodoStatus(task_data.get("status", "pending")),
                        priority=TodoPriority(task_data.get("priority", "medium")),
                        source=TodoSource.DEV_WORKFLOW,
                        category=task_data.get("category", "foundation"),
                        estimated_time=task_data.get("estimated_time"),
                        dependencies=task_data.get("dependencies", []),
                        notes=task_data.get("implementation_notes", ""),
                    )
                    self.todos[task_id] = todo
                    imported += 1

        except Exception as e:
            self.logger.error(f"Failed to import from dev_workflow: {e}")

        return imported

    def import_from_inline_code(self) -> int:
        """Import TODOs from inline code comments."""
        imported = 0

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

                        todo_id = self.generate_todo_id(
                            comment, TodoSource.INLINE_CODE, file_path
                        )

                        if todo_id not in self.todos:
                            priority = TodoPriority.MEDIUM
                            if (
                                "CRITICAL" in comment.upper()
                                or "URGENT" in comment.upper()
                            ):
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
                                category="code_improvement",
                                file_path=file_path,
                                line_number=int(line_num),
                            )
                            self.todos[todo_id] = todo
                            imported += 1

        except Exception as e:
            self.logger.warning(f"Could not import from inline code: {e}")

        return imported

    def import_from_documentation(self) -> int:
        """Import TODOs from documentation files."""
        imported = 0

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
                    ]

                    for pattern in patterns:
                        matches = re.finditer(
                            pattern, content, re.MULTILINE | re.IGNORECASE
                        )
                        for match in matches:
                            if pattern.startswith("(?:"):  # Task ID pattern
                                task_id = match.group(0)
                                content_text = f"Task {task_id}"
                                todo_id = task_id  # Use the task ID directly
                            else:
                                content_text = (
                                    match.group(1) if match.groups() else match.group(0)
                                )
                                todo_id = self.generate_todo_id(
                                    content_text, TodoSource.DOCUMENTATION, doc_file
                                )

                            if todo_id not in self.todos:
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
                                    word in content_text.upper()
                                    for word in ["LOW", "NICE"]
                                ):
                                    priority = TodoPriority.LOW

                                todo = UnifiedTodo(
                                    id=todo_id,
                                    content=content_text,
                                    status=TodoStatus.PENDING,
                                    priority=priority,
                                    source=TodoSource.DOCUMENTATION,
                                    category="documentation",
                                    file_path=doc_file,
                                )
                                self.todos[todo_id] = todo
                                imported += 1

                except Exception as e:
                    self.logger.warning(f"Could not import from {doc_file}: {e}")

        return imported

    def import_from_checklists(self) -> int:
        """Import TODOs from checklist files."""
        imported = 0

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
                        for match in matches:
                            content_text = match.group(1)
                            todo_id = self.generate_todo_id(
                                content_text, TodoSource.CHECKLIST, checklist_file
                            )

                            if todo_id not in self.todos:
                                todo = UnifiedTodo(
                                    id=todo_id,
                                    content=content_text,
                                    status=TodoStatus.PENDING,
                                    priority=TodoPriority.MEDIUM,
                                    source=TodoSource.CHECKLIST,
                                    category="checklist",
                                    file_path=checklist_file,
                                )
                                self.todos[todo_id] = todo
                                imported += 1

                except Exception as e:
                    self.logger.warning(f"Could not import from {checklist_file}: {e}")

        return imported

    def display_unified_dashboard(self):
        """Display comprehensive unified TODO dashboard."""
        console.print(
            Rule("[bold blue]Unified TODO Management Dashboard", style="blue")
        )

        total_todos = len(self.todos)
        if total_todos == 0:
            console.print(
                "[yellow]No TODOs found. Run import to sync from external systems.[/yellow]"
            )
            return

        # Summary statistics
        status_counts = {}
        priority_counts = {}
        source_counts = {}
        category_counts = {}

        for todo in self.todos.values():
            status_counts[todo.status] = status_counts.get(todo.status, 0) + 1
            priority_counts[todo.priority] = priority_counts.get(todo.priority, 0) + 1
            source_counts[todo.source] = source_counts.get(todo.source, 0) + 1
            category_counts[todo.category] = category_counts.get(todo.category, 0) + 1

        # Status summary
        status_table = Table(title=f"TODO Status Summary ({total_todos} total)")
        status_table.add_column("Status", style="cyan")
        status_table.add_column("Count", style="magenta")
        status_table.add_column("Percentage", style="yellow")

        for status, count in status_counts.items():
            percentage = (count / total_todos) * 100
            status_table.add_row(status.value.title(), str(count), f"{percentage:.1f}%")

        console.print(status_table)

        # Priority breakdown
        priority_table = Table(title="Priority Breakdown")
        priority_table.add_column("Priority", style="cyan")
        priority_table.add_column("Pending", style="yellow")
        priority_table.add_column("In Progress", style="blue")
        priority_table.add_column("Completed", style="green")
        priority_table.add_column("Total", style="magenta")

        for priority in [
            TodoPriority.CRITICAL,
            TodoPriority.HIGH,
            TodoPriority.MEDIUM,
            TodoPriority.LOW,
        ]:
            priority_todos = [t for t in self.todos.values() if t.priority == priority]
            pending = len([t for t in priority_todos if t.status == TodoStatus.PENDING])
            in_progress = len(
                [t for t in priority_todos if t.status == TodoStatus.IN_PROGRESS]
            )
            completed = len(
                [t for t in priority_todos if t.status == TodoStatus.COMPLETED]
            )
            total = len(priority_todos)

            priority_table.add_row(
                priority.value.title(),
                str(pending),
                str(in_progress),
                str(completed),
                str(total),
            )

        console.print(priority_table)

        # Next priority tasks
        pending_todos = [
            t for t in self.todos.values() if t.status == TodoStatus.PENDING
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

        next_table = Table(title="Next Priority Tasks (Top 15)")
        next_table.add_column("ID", style="cyan")
        next_table.add_column("Priority", style="magenta")
        next_table.add_column("Content", style="white")
        next_table.add_column("Category", style="yellow")
        next_table.add_column("Source", style="blue")

        for todo in pending_todos[:15]:
            next_table.add_row(
                todo.id,
                todo.priority.value.title(),
                todo.content[:40] + "..." if len(todo.content) > 40 else todo.content,
                todo.category,
                todo.source.value.replace("_", " ").title(),
            )

        console.print(next_table)

        # Critical warnings
        critical_todos = [
            t
            for t in self.todos.values()
            if t.priority == TodoPriority.CRITICAL and t.status == TodoStatus.PENDING
        ]
        if critical_todos:
            console.print(
                f"\n[bold red]⚠️  {len(critical_todos)} CRITICAL TODOs require immediate attention![/bold red]"
            )
            for todo in critical_todos:
                console.print(f"  • {todo.id}: {todo.content}")

    def interactive_mode(self):
        """Run interactive TODO management mode."""
        while True:
            console.print(Rule("[bold green]Unified TODO Management", style="green"))

            options = [
                "1. View unified dashboard",
                "2. Import from external systems",
                "3. Add new TODO",
                "4. Update TODO status",
                "5. Complete TODO",
                "6. Search TODOs",
                "7. Sync all systems",
                "8. Export to external systems",
                "9. Exit",
            ]

            for option in options:
                console.print(option)

            choice = Prompt.ask(
                "Choose an option",
                choices=["1", "2", "3", "4", "5", "6", "7", "8", "9"],
            )

            if choice == "1":
                self.display_unified_dashboard()
            elif choice == "2":
                self.import_from_external_systems()
            elif choice == "3":
                self._add_todo_interactive()
            elif choice == "4":
                self._update_todo_interactive()
            elif choice == "5":
                self._complete_todo_interactive()
            elif choice == "6":
                self._search_todos_interactive()
            elif choice == "7":
                self._sync_all_systems()
            elif choice == "8":
                self._export_to_external_systems()
            elif choice == "9":
                break

            console.print("\n")

    def _add_todo_interactive(self):
        """Add a TODO interactively."""
        console.print("[cyan]Adding new TODO...[/cyan]")

        content = Prompt.ask("TODO content")
        priority = Prompt.ask(
            "Priority", choices=["critical", "high", "medium", "low"], default="medium"
        )
        category = Prompt.ask("Category", default="general")
        source = Prompt.ask(
            "Source",
            choices=["master", "dev_workflow", "documentation", "checklist"],
            default="master",
        )

        estimated_time = Prompt.ask("Estimated time (minutes)", default="30")
        try:
            estimated_time = int(estimated_time)
        except ValueError:
            estimated_time = 30

        notes = Prompt.ask("Notes (optional)", default="")

        todo_id = self.add_todo(
            content=content,
            priority=TodoPriority(priority),
            source=TodoSource(source),
            category=category,
            estimated_time=estimated_time,
            notes=notes if notes else None,
        )

        console.print(f"[green]Added TODO: {todo_id}[/green]")

    def _update_todo_interactive(self):
        """Update a TODO interactively."""
        todo_id = Prompt.ask("TODO ID to update")

        if todo_id not in self.todos:
            console.print(f"[red]TODO {todo_id} not found[/red]")
            return

        todo = self.todos[todo_id]
        console.print(f"Current TODO: {todo.content}")
        console.print(f"Current status: {todo.status.value}")
        console.print(f"Current priority: {todo.priority.value}")

        new_status = Prompt.ask(
            "New status",
            choices=["pending", "in_progress", "completed", "cancelled", "blocked"],
            default=todo.status.value,
        )
        new_priority = Prompt.ask(
            "New priority",
            choices=["critical", "high", "medium", "low"],
            default=todo.priority.value,
        )

        self.update_todo(todo_id, status=new_status, priority=new_priority)
        console.print(f"[green]Updated TODO: {todo_id}[/green]")

    def _complete_todo_interactive(self):
        """Complete a TODO interactively."""
        todo_id = Prompt.ask("TODO ID to complete")

        if todo_id not in self.todos:
            console.print(f"[red]TODO {todo_id} not found[/red]")
            return

        notes = Prompt.ask("Completion notes (optional)", default="")

        if self.complete_todo(todo_id, notes if notes else None):
            console.print(f"[green]Completed TODO: {todo_id}[/green]")
        else:
            console.print(f"[red]Failed to complete TODO: {todo_id}[/red]")

    def _search_todos_interactive(self):
        """Search TODOs interactively."""
        query = Prompt.ask("Search query")

        results = []
        for todo in self.todos.values():
            if (
                query.lower() in todo.content.lower()
                or query.lower() in todo.category.lower()
            ):
                results.append(todo)

        if results:
            table = Table(title=f"Search Results ({len(results)} found)")
            table.add_column("ID", style="cyan")
            table.add_column("Content", style="white")
            table.add_column("Status", style="magenta")
            table.add_column("Priority", style="yellow")

            for todo in results:
                table.add_row(
                    todo.id,
                    (
                        todo.content[:50] + "..."
                        if len(todo.content) > 50
                        else todo.content
                    ),
                    todo.status.value,
                    todo.priority.value,
                )

            console.print(table)
        else:
            console.print("[yellow]No TODOs found matching your query[/yellow]")

    def _sync_all_systems(self):
        """Sync all TODOs to all systems."""
        console.print("[cyan]Syncing all TODOs to external systems...[/cyan]")

        for todo in self.todos.values():
            self.sync_todo_to_systems(todo)

        console.print("[green]All TODOs synced to external systems[/green]")

    def _export_to_external_systems(self):
        """Export TODOs to external systems."""
        console.print("[cyan]Exporting TODOs to external systems...[/cyan]")

        # Export to dev_workflow
        dev_todos = [
            t
            for t in self.todos.values()
            if t.source == TodoSource.DEV_WORKFLOW or t.category == "foundation"
        ]
        for todo in dev_todos:
            self.sync_to_dev_workflow(todo)

        console.print(f"[green]Exported {len(dev_todos)} TODOs to dev_workflow[/green]")


def main():
    """Main entry point for unified TODO management."""
    manager = UnifiedTodoManager()

    if len(sys.argv) > 1:
        arg = sys.argv[1]
        if arg == "--import":
            manager.import_from_external_systems()
        elif arg == "--dashboard":
            manager.display_unified_dashboard()
        elif arg == "--sync":
            manager._sync_all_systems()
        elif arg == "--export":
            manager._export_to_external_systems()
        elif arg == "--interactive":
            manager.interactive_mode()
        else:
            console.print(f"[red]Unknown argument: {arg}[/red]")
            console.print(
                "Available arguments: --import, --dashboard, --sync, --export, --interactive"
            )
            sys.exit(1)
    else:
        # Default to interactive mode
        manager.interactive_mode()


if __name__ == "__main__":
    main()
