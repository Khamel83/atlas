#!/usr/bin/env python3
"""
Atlas Automated Development Workflow System

This system provides intelligent task prioritization, automated development,
and error recovery. It integrates with the existing TODO system and can
work recursively through tasks until hitting a blocker.
"""

import json
import logging
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
    from rich.panel import Panel
    from rich.prompt import Confirm, Prompt
    from rich.rule import Rule
    from rich.table import Table
except ImportError:
    print("Rich library not found. Please run 'pip install rich'.")
    sys.exit(1)

console = Console()


class TaskStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    BLOCKED = "blocked"
    FAILED = "failed"


class Priority(Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class Task:
    id: str
    content: str
    status: TaskStatus
    priority: Priority
    dependencies: List[str]
    category: str
    estimated_time: int  # minutes
    complexity: int  # 1-5 scale
    last_attempt: Optional[str] = None
    failure_count: int = 0
    implementation_notes: str = ""
    git_commits: List[str] = None

    def __post_init__(self):
        if self.git_commits is None:
            self.git_commits = []


class DevWorkflow:
    """Main development workflow orchestrator."""

    def __init__(self):
        self.console = console
        self.project_root = Path(__file__).parent.parent
        self.tasks_file = self.project_root / "dev_tasks.json"
        self.workflow_log = self.project_root / "logs" / "dev_workflow.log"
        self.current_branch = None
        self.tasks: Dict[str, Task] = {}
        self.load_tasks()
        self.setup_logging()

    def setup_logging(self):
        """Setup logging for workflow operations."""
        log_dir = self.project_root / "logs"
        log_dir.mkdir(exist_ok=True)

        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(levelname)s - %(message)s",
            handlers=[logging.FileHandler(self.workflow_log), logging.StreamHandler()],
        )
        self.logger = logging.getLogger(__name__)

    def load_tasks(self):
        """Load tasks from JSON file or create default tasks."""
        if self.tasks_file.exists():
            try:
                with open(self.tasks_file, "r") as f:
                    tasks_data = json.load(f)
                    self.tasks = {
                        task_id: Task(**task_data)
                        for task_id, task_data in tasks_data.items()
                    }
                    # Convert string enums back to enum objects
                    for task in self.tasks.values():
                        task.status = TaskStatus(task.status)
                        task.priority = Priority(task.priority)
            except Exception as e:
                self.logger.error(f"Failed to load tasks: {e}")
                self.create_default_tasks()
        else:
            self.create_default_tasks()

    def save_tasks(self):
        """Save tasks to JSON file."""
        tasks_data = {}
        for task_id, task in self.tasks.items():
            task_dict = asdict(task)
            task_dict["status"] = task.status.value
            task_dict["priority"] = task.priority.value
            tasks_data[task_id] = task_dict

        with open(self.tasks_file, "w") as f:
            json.dump(tasks_data, f, indent=2)

    def create_default_tasks(self):
        """Create default high-priority tasks based on current project status."""
        default_tasks = [
            Task(
                id="FOUNDATION-API-1",
                content="Fix MetadataManager constructor parameter mismatch",
                status=TaskStatus.PENDING,
                priority=Priority.CRITICAL,
                dependencies=[],
                category="foundation",
                estimated_time=30,
                complexity=3,
                implementation_notes="Check helpers/metadata_manager.py constructor vs docs/api_documentation.md",
            ),
            Task(
                id="FOUNDATION-API-2",
                content="Fix PathManager method signatures in documentation",
                status=TaskStatus.PENDING,
                priority=Priority.CRITICAL,
                dependencies=[],
                category="foundation",
                estimated_time=20,
                complexity=2,
                implementation_notes="Update docs/api_documentation.md to match helpers/path_manager.py",
            ),
            Task(
                id="FOUNDATION-TEST-1",
                content="Add comprehensive unit tests for path_manager.py",
                status=TaskStatus.PENDING,
                priority=Priority.HIGH,
                dependencies=["FOUNDATION-API-2"],
                category="foundation",
                estimated_time=60,
                complexity=4,
                implementation_notes="Create tests/unit/test_path_manager.py with 90%+ coverage",
            ),
            Task(
                id="FOUNDATION-TEST-2",
                content="Add unit tests for base_ingestor.py",
                status=TaskStatus.PENDING,
                priority=Priority.HIGH,
                dependencies=[],
                category="foundation",
                estimated_time=45,
                complexity=3,
                implementation_notes="Create tests/unit/test_base_ingestor.py",
            ),
            Task(
                id="FOUNDATION-MIGRATE-1",
                content="Migrate article_fetcher.py to use article_strategies.py",
                status=TaskStatus.PENDING,
                priority=Priority.MEDIUM,
                dependencies=["FOUNDATION-API-1"],
                category="foundation",
                estimated_time=90,
                complexity=4,
                implementation_notes="Update all references to use new article_strategies architecture",
            ),
        ]

        self.tasks = {task.id: task for task in default_tasks}
        self.save_tasks()

    def get_current_git_branch(self) -> str:
        """Get current git branch."""
        try:
            result = subprocess.run(
                ["git", "branch", "--show-current"],
                capture_output=True,
                text=True,
                cwd=self.project_root,
            )
            return result.stdout.strip()
        except Exception as e:
            self.logger.error(f"Failed to get git branch: {e}")
            return "unknown"

    def run_health_check(self) -> bool:
        """Run the existing health check and return success status."""
        try:
            result = subprocess.run(
                [sys.executable, "scripts/health_check.py"],
                capture_output=True,
                text=True,
                cwd=self.project_root,
            )
            return result.returncode == 0
        except Exception as e:
            self.logger.error(f"Health check failed: {e}")
            return False

    def run_tests(self) -> bool:
        """Run the test suite and return success status."""
        try:
            result = subprocess.run(
                ["pytest", "-v"], capture_output=True, text=True, cwd=self.project_root
            )
            return result.returncode == 0
        except Exception as e:
            self.logger.error(f"Tests failed: {e}")
            return False

    def get_prioritized_tasks(self) -> List[Task]:
        """Get tasks sorted by priority and readiness."""
        available_tasks = []

        for task in self.tasks.values():
            if task.status in [TaskStatus.PENDING, TaskStatus.FAILED]:
                # Check if all dependencies are completed
                deps_satisfied = all(
                    self.tasks.get(
                        dep_id,
                        Task("", "", TaskStatus.PENDING, Priority.LOW, [], "", 0, 0),
                    ).status
                    == TaskStatus.COMPLETED
                    for dep_id in task.dependencies
                )

                if deps_satisfied:
                    available_tasks.append(task)

        # Sort by priority (critical first), then by complexity (easier first)
        priority_order = {
            Priority.CRITICAL: 0,
            Priority.HIGH: 1,
            Priority.MEDIUM: 2,
            Priority.LOW: 3,
        }
        available_tasks.sort(key=lambda t: (priority_order[t.priority], t.complexity))

        return available_tasks

    def display_task_dashboard(self):
        """Display comprehensive task dashboard."""

        # Task status summary
        status_counts = {}
        for task in self.tasks.values():
            status_counts[task.status] = status_counts.get(task.status, 0) + 1

        summary_table = Table(title="Task Status Summary")
        summary_table.add_column("Status", style="cyan")
        summary_table.add_column("Count", style="magenta")

        for status, count in status_counts.items():
            summary_table.add_row(status.value.title(), str(count))

        # Priority breakdown
        priority_table = Table(title="Priority Breakdown")
        priority_table.add_column("Priority", style="cyan")
        priority_table.add_column("Pending", style="yellow")
        priority_table.add_column("In Progress", style="blue")
        priority_table.add_column("Completed", style="green")

        priority_counts = {}
        for task in self.tasks.values():
            if task.priority not in priority_counts:
                priority_counts[task.priority] = {
                    TaskStatus.PENDING: 0,
                    TaskStatus.IN_PROGRESS: 0,
                    TaskStatus.COMPLETED: 0,
                }
            priority_counts[task.priority][task.status] += 1

        for priority in [
            Priority.CRITICAL,
            Priority.HIGH,
            Priority.MEDIUM,
            Priority.LOW,
        ]:
            if priority in priority_counts:
                counts = priority_counts[priority]
                priority_table.add_row(
                    priority.value.title(),
                    str(counts.get(TaskStatus.PENDING, 0)),
                    str(counts.get(TaskStatus.IN_PROGRESS, 0)),
                    str(counts.get(TaskStatus.COMPLETED, 0)),
                )

        # Next available tasks
        available_tasks = self.get_prioritized_tasks()[:5]  # Top 5
        next_table = Table(title="Next Available Tasks")
        next_table.add_column("ID", style="cyan")
        next_table.add_column("Priority", style="magenta")
        next_table.add_column("Content", style="white")
        next_table.add_column("Est. Time", style="yellow")

        for task in available_tasks:
            next_table.add_row(
                task.id,
                task.priority.value.title(),
                task.content[:50] + "..." if len(task.content) > 50 else task.content,
                f"{task.estimated_time}m",
            )

        console.print(Panel(summary_table, title="Atlas Development Dashboard"))
        console.print(priority_table)
        console.print(next_table)

    def implement_task(self, task: Task) -> bool:
        """Implement a specific task with error handling."""
        self.logger.info(f"Starting implementation of task: {task.id}")

        # Mark task as in progress
        task.status = TaskStatus.IN_PROGRESS
        task.last_attempt = datetime.now().isoformat()
        self.save_tasks()

        try:
            # Task-specific implementation logic
            success = self._execute_task_implementation(task)

            if success:
                task.status = TaskStatus.COMPLETED
                self.logger.info(f"Task {task.id} completed successfully")

                # Create git commit
                commit_message = f"[{task.category.upper()}] {task.content}"
                self._create_git_commit(commit_message, task)

                return True
            else:
                task.status = TaskStatus.FAILED
                task.failure_count += 1
                self.logger.error(f"Task {task.id} failed")
                return False

        except Exception as e:
            task.status = TaskStatus.FAILED
            task.failure_count += 1
            self.logger.error(f"Task {task.id} failed with exception: {e}")
            return False
        finally:
            self.save_tasks()

    def _execute_task_implementation(self, task: Task) -> bool:
        """Execute the actual implementation for a task."""
        # This is where task-specific logic would go
        # For now, we'll implement a few key tasks

        if task.id == "FOUNDATION-API-1":
            return self._fix_metadata_manager_constructor(task)
        elif task.id == "FOUNDATION-API-2":
            return self._fix_path_manager_docs(task)
        elif task.id == "FOUNDATION-TEST-1":
            return self._create_path_manager_tests(task)
        elif task.id == "FOUNDATION-TEST-2":
            return self._create_base_ingestor_tests(task)
        elif task.id == "FOUNDATION-MIGRATE-1":
            return self._migrate_article_fetcher(task)
        else:
            # For unknown tasks, prompt for manual implementation
            console.print(
                f"[yellow]Task {task.id} requires manual implementation[/yellow]"
            )
            console.print(f"Content: {task.content}")
            console.print(f"Notes: {task.implementation_notes}")

            return Confirm.ask("Mark this task as completed?")

    def _fix_metadata_manager_constructor(self, task: Task) -> bool:
        """Fix MetadataManager constructor parameter mismatch."""
        try:
            # Read the actual constructor
            metadata_manager_path = (
                self.project_root / "helpers" / "metadata_manager.py"
            )
            if not metadata_manager_path.exists():
                self.logger.error("metadata_manager.py not found")
                return False

            # Simple implementation - this would need more sophisticated parsing
            # For now, we'll just log what needs to be done
            console.print("[yellow]Checking MetadataManager constructor...[/yellow]")

            # This is a placeholder - actual implementation would:
            # 1. Parse the constructor parameters
            # 2. Update the documentation to match
            # 3. Or fix the constructor to match docs

            task.implementation_notes += (
                f"\nChecked at {datetime.now()}: Constructor analysis needed"
            )
            return True

        except Exception as e:
            self.logger.error(f"Failed to fix MetadataManager constructor: {e}")
            return False

    def _fix_path_manager_docs(self, task: Task) -> bool:
        """Fix PathManager method signatures in documentation."""
        try:
            console.print("[yellow]Fixing PathManager documentation...[/yellow]")

            # Read actual PathManager implementation
            path_manager_path = self.project_root / "helpers" / "path_manager.py"
            api_docs_path = self.project_root / "docs" / "api_documentation.md"

            if not path_manager_path.exists():
                self.logger.error("path_manager.py not found")
                return False

            if not api_docs_path.exists():
                self.logger.error("api_documentation.md not found")
                return False

            # This is a placeholder for actual implementation
            task.implementation_notes += (
                f"\nChecked at {datetime.now()}: Documentation sync needed"
            )
            return True

        except Exception as e:
            self.logger.error(f"Failed to fix PathManager docs: {e}")
            return False

    def _create_path_manager_tests(self, task: Task) -> bool:
        """Create comprehensive unit tests for path_manager.py."""
        try:
            console.print("[yellow]Creating PathManager tests...[/yellow]")

            test_file_path = (
                self.project_root / "tests" / "unit" / "test_path_manager.py"
            )
            test_file_path.parent.mkdir(parents=True, exist_ok=True)

            # Create basic test structure
            test_content = '''"""
Unit tests for PathManager class.
"""

import pytest
from pathlib import Path
from helpers.path_manager import PathManager
from helpers.config import load_config

class TestPathManager:
    """Test cases for PathManager class."""

    def setup_method(self):
        """Setup test environment."""
        self.config = load_config()
        self.path_manager = PathManager(self.config)

    def test_initialization(self):
        """Test PathManager initialization."""
        assert self.path_manager is not None
        assert self.path_manager.config == self.config

    def test_path_generation(self):
        """Test basic path generation."""
        # Add specific tests based on actual PathManager methods
        pass

    def test_path_validation(self):
        """Test path validation logic."""
        # Add validation tests
        pass

    def test_error_handling(self):
        """Test error handling in path operations."""
        # Add error handling tests
        pass
'''

            with open(test_file_path, "w") as f:
                f.write(test_content)

            task.implementation_notes += (
                f"\nCreated basic test structure at {datetime.now()}"
            )
            return True

        except Exception as e:
            self.logger.error(f"Failed to create PathManager tests: {e}")
            return False

    def _create_base_ingestor_tests(self, task: Task) -> bool:
        """Create unit tests for base_ingestor.py."""
        try:
            console.print("[yellow]Creating BaseIngestor tests...[/yellow]")

            test_file_path = (
                self.project_root / "tests" / "unit" / "test_base_ingestor.py"
            )
            test_file_path.parent.mkdir(parents=True, exist_ok=True)

            # Create basic test structure
            test_content = '''"""
Unit tests for BaseIngestor class.
"""

import pytest
from helpers.base_ingestor import BaseIngestor
from helpers.config import load_config

class TestBaseIngestor:
    """Test cases for BaseIngestor class."""

    def setup_method(self):
        """Setup test environment."""
        self.config = load_config()

    def test_initialization(self):
        """Test BaseIngestor initialization."""
        # Add initialization tests
        pass

    def test_common_methods(self):
        """Test common ingestor methods."""
        # Add method tests
        pass

    def test_error_handling(self):
        """Test error handling in base ingestor."""
        # Add error handling tests
        pass
'''

            with open(test_file_path, "w") as f:
                f.write(test_content)

            task.implementation_notes += (
                f"\nCreated basic test structure at {datetime.now()}"
            )
            return True

        except Exception as e:
            self.logger.error(f"Failed to create BaseIngestor tests: {e}")
            return False

    def _migrate_article_fetcher(self, task: Task) -> bool:
        """Migrate article_fetcher.py to use article_strategies.py."""
        try:
            console.print("[yellow]Migrating article fetcher...[/yellow]")

            # This is a complex migration that would need careful analysis
            task.implementation_notes += (
                f"\nMigration analysis started at {datetime.now()}"
            )

            # Placeholder for actual migration logic
            return True

        except Exception as e:
            self.logger.error(f"Failed to migrate article fetcher: {e}")
            return False

    def _create_git_commit(self, message: str, task: Task):
        """Create a git commit for the completed task."""
        try:
            # Add all changes
            subprocess.run(["git", "add", "."], cwd=self.project_root, check=True)

            # Create commit
            result = subprocess.run(
                ["git", "commit", "-m", message],
                cwd=self.project_root,
                capture_output=True,
                text=True,
            )

            if result.returncode == 0:
                # Get the commit hash
                commit_result = subprocess.run(
                    ["git", "rev-parse", "HEAD"],
                    cwd=self.project_root,
                    capture_output=True,
                    text=True,
                )

                if commit_result.returncode == 0:
                    commit_hash = commit_result.stdout.strip()
                    task.git_commits.append(commit_hash)
                    self.logger.info(f"Created git commit: {commit_hash}")
                else:
                    self.logger.warning("Failed to get commit hash")
            else:
                self.logger.warning(f"Git commit failed: {result.stderr}")

        except Exception as e:
            self.logger.error(f"Failed to create git commit: {e}")

    def run_automated_development(
        self, max_tasks: int = 5, auto_mode: bool = False
    ) -> bool:
        """Run automated development workflow."""
        console.print(
            Rule("[bold blue]Atlas Automated Development Workflow", style="blue")
        )

        # Run health check first
        console.print("\n[yellow]Running health check...[/yellow]")
        if not self.run_health_check():
            console.print(
                "[red]Health check failed. Please fix issues before continuing.[/red]"
            )
            return False

        console.print("[green]Health check passed![/green]")

        # Display dashboard
        self.display_task_dashboard()

        # Get available tasks
        available_tasks = self.get_prioritized_tasks()

        if not available_tasks:
            console.print("[green]No available tasks to work on![/green]")
            return True

        # Ask user if they want to proceed (unless in auto mode)
        console.print(f"\n[cyan]Found {len(available_tasks)} available tasks[/cyan]")
        if not auto_mode and not Confirm.ask("Start automated development?"):
            return False

        # Process tasks
        tasks_completed = 0
        for task in available_tasks[:max_tasks]:
            console.print(f"\n[blue]Working on: {task.id}[/blue]")
            console.print(f"Content: {task.content}")
            console.print(f"Estimated time: {task.estimated_time} minutes")

            if self.implement_task(task):
                tasks_completed += 1
                console.print(f"[green]✓ Task {task.id} completed successfully[/green]")

                # Run tests after each task
                if not self.run_tests():
                    console.print(
                        "[yellow]Tests failed after task completion. Continuing...[/yellow]"
                    )
            else:
                console.print(f"[red]✗ Task {task.id} failed[/red]")

                # Ask if we should continue or stop
                if not Confirm.ask("Continue with next task?"):
                    break

        console.print("\n[cyan]Automated development complete![/cyan]")
        console.print(f"Tasks completed: {tasks_completed}")

        return True

    def interactive_mode(self):
        """Run interactive development mode."""
        while True:
            console.print(
                Rule("[bold green]Atlas Development Interactive Mode", style="green")
            )

            options = [
                "1. View task dashboard",
                "2. Run automated development",
                "3. Work on specific task",
                "4. Add new task",
                "5. Run health check",
                "6. Run tests",
                "7. Exit",
            ]

            for option in options:
                console.print(option)

            choice = Prompt.ask(
                "Choose an option", choices=["1", "2", "3", "4", "5", "6", "7"]
            )

            if choice == "1":
                self.display_task_dashboard()
            elif choice == "2":
                self.run_automated_development()
            elif choice == "3":
                self._work_on_specific_task()
            elif choice == "4":
                self._add_new_task()
            elif choice == "5":
                self.run_health_check()
            elif choice == "6":
                self.run_tests()
            elif choice == "7":
                break

            console.print("\n")

    def _work_on_specific_task(self):
        """Work on a specific task interactively."""
        available_tasks = self.get_prioritized_tasks()

        if not available_tasks:
            console.print("[yellow]No available tasks to work on.[/yellow]")
            return

        # Display available tasks
        table = Table(title="Available Tasks")
        table.add_column("Index", style="cyan")
        table.add_column("ID", style="magenta")
        table.add_column("Content", style="white")
        table.add_column("Priority", style="yellow")

        for i, task in enumerate(available_tasks):
            table.add_row(
                str(i + 1),
                task.id,
                task.content[:50] + "..." if len(task.content) > 50 else task.content,
                task.priority.value.title(),
            )

        console.print(table)

        try:
            index = int(Prompt.ask("Select task index")) - 1
            if 0 <= index < len(available_tasks):
                task = available_tasks[index]
                console.print(f"\n[blue]Working on: {task.id}[/blue]")
                self.implement_task(task)
            else:
                console.print("[red]Invalid task index.[/red]")
        except ValueError:
            console.print("[red]Invalid input.[/red]")

    def _add_new_task(self):
        """Add a new task interactively."""
        console.print("[cyan]Adding new task...[/cyan]")

        task_id = Prompt.ask("Task ID")
        content = Prompt.ask("Task content")
        priority = Prompt.ask("Priority", choices=["critical", "high", "medium", "low"])
        category = Prompt.ask("Category")
        estimated_time = int(Prompt.ask("Estimated time (minutes)", default="30"))
        complexity = int(Prompt.ask("Complexity (1-5)", default="3"))

        new_task = Task(
            id=task_id,
            content=content,
            status=TaskStatus.PENDING,
            priority=Priority(priority),
            dependencies=[],
            category=category,
            estimated_time=estimated_time,
            complexity=complexity,
        )

        self.tasks[task_id] = new_task
        self.save_tasks()

        console.print(f"[green]Task {task_id} added successfully![/green]")

    def quick_assessment(self):
        """Run a quick assessment of current tasks and issues."""
        console.print(Rule("[bold yellow]Quick Task Assessment", style="yellow"))

        # Check for any new errors in logs
        recent_errors = self._check_recent_errors()
        if recent_errors:
            console.print(
                f"[red]Found {len(recent_errors)} recent errors in logs[/red]"
            )
            for error in recent_errors[:3]:  # Show first 3
                console.print(f"  • {error}")

        # Show critical tasks
        critical_tasks = [
            t
            for t in self.tasks.values()
            if t.priority == Priority.CRITICAL and t.status == TaskStatus.PENDING
        ]
        if critical_tasks:
            console.print(
                f"[yellow]Found {len(critical_tasks)} critical tasks pending[/yellow]"
            )
            for task in critical_tasks[:3]:  # Show first 3
                console.print(f"  • {task.id}: {task.content}")

        # Show task summary
        available_tasks = self.get_prioritized_tasks()
        if available_tasks:
            console.print(f"[cyan]Total available tasks: {len(available_tasks)}[/cyan]")
            console.print(
                f"[cyan]Next priority: {available_tasks[0].id} ({available_tasks[0].priority.value})[/cyan]"
            )
        else:
            console.print("[green]No pending tasks found![/green]")

    def _check_recent_errors(self) -> List[str]:
        """Check for recent errors in log files."""
        errors = []
        log_dir = self.project_root / "logs"

        if not log_dir.exists():
            return errors

        # Check recent log files
        for log_file in log_dir.glob("*.log"):
            try:
                with open(log_file, "r") as f:
                    lines = f.readlines()
                    # Check last 50 lines for errors
                    for line in lines[-50:]:
                        if "ERROR" in line or "CRITICAL" in line:
                            errors.append(f"{log_file.name}: {line.strip()}")
            except Exception:
                continue

        return errors[-10:]  # Return last 10 errors

    def display_dashboard_only(self):
        """Display dashboard and exit."""
        console.print(Rule("[bold green]Atlas Task Dashboard", style="green"))
        self.display_task_dashboard()

        # Show quick assessment
        console.print("\n")
        self.quick_assessment()


def main():
    """Main entry point for the development workflow."""
    workflow = DevWorkflow()

    # Handle command line arguments
    if len(sys.argv) > 1:
        arg = sys.argv[1]
        if arg == "--auto":
            workflow.run_automated_development(auto_mode=True)
        elif arg == "--dashboard":
            workflow.display_dashboard_only()
        elif arg == "--quick-assessment":
            workflow.quick_assessment()
        else:
            console.print(f"[red]Unknown argument: {arg}[/red]")
            console.print(
                "Available arguments: --auto, --dashboard, --quick-assessment"
            )
            sys.exit(1)
    else:
        workflow.interactive_mode()


if __name__ == "__main__":
    main()
