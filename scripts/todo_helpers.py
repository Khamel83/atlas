#!/usr/bin/env python3
"""
Atlas TODO Helper Functions

Simple helper functions that other systems can import and use to interact
with the unified TODO system without needing to understand the full API.

Usage:
    from scripts.todo_helpers import add_todo, complete_todo, get_todos

    # Add a TODO
    todo_id = add_todo("Fix bug in parser", priority="critical")

    # Complete a TODO
    complete_todo(todo_id, "Fixed by updating regex")

    # Get pending TODOs
    pending_todos = get_todos(status="pending", priority="critical")
"""

import sys
from pathlib import Path
from typing import Dict, List, Optional

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from scripts.unified_todo_manager import (TodoPriority, TodoSource, TodoStatus,
                                          UnifiedTodoManager)

# Global manager instance
_manager = None


def get_manager():
    """Get or create the global TODO manager instance."""
    global _manager
    if _manager is None:
        _manager = UnifiedTodoManager()
    return _manager


def add_todo(
    content: str,
    priority: str = "medium",
    category: str = "general",
    source: str = "master",
    estimated_time: int = None,
    notes: str = None,
    tags: List[str] = None,
) -> str:
    """
    Add a new TODO to the unified system.

    Args:
        content: The TODO description
        priority: Priority level (critical, high, medium, low)
        category: Category/type of TODO
        source: Source system (master, dev_workflow, documentation, checklist)
        estimated_time: Estimated time in minutes
        notes: Additional notes
        tags: List of tags

    Returns:
        The TODO ID
    """
    manager = get_manager()
    return manager.add_todo(
        content=content,
        priority=TodoPriority(priority),
        source=TodoSource(source),
        category=category,
        estimated_time=estimated_time,
        notes=notes,
        tags=tags or [],
    )


def complete_todo(todo_id: str, notes: str = None) -> bool:
    """
    Mark a TODO as completed.

    Args:
        todo_id: The TODO ID to complete
        notes: Completion notes

    Returns:
        True if successful, False otherwise
    """
    manager = get_manager()
    return manager.complete_todo(todo_id, notes)


def update_todo_status(todo_id: str, status: str, notes: str = None) -> bool:
    """
    Update a TODO's status.

    Args:
        todo_id: The TODO ID to update
        status: New status (pending, in_progress, completed, cancelled, blocked)
        notes: Additional notes

    Returns:
        True if successful, False otherwise
    """
    manager = get_manager()
    return manager.update_todo(todo_id, status=status, notes=notes)


def get_todos(
    status: str = None, priority: str = None, category: str = None, limit: int = None
) -> List[Dict]:
    """
    Get TODOs matching the specified criteria.

    Args:
        status: Filter by status (pending, in_progress, completed, cancelled, blocked)
        priority: Filter by priority (critical, high, medium, low)
        category: Filter by category
        limit: Maximum number of results

    Returns:
        List of TODO dictionaries
    """
    manager = get_manager()
    todos = list(manager.todos.values())

    # Apply filters
    if status:
        todos = [t for t in todos if t.status == TodoStatus(status)]
    if priority:
        todos = [t for t in todos if t.priority == TodoPriority(priority)]
    if category:
        todos = [t for t in todos if t.category == category]

    # Sort by priority
    todos.sort(
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

    # Apply limit
    if limit:
        todos = todos[:limit]

    # Convert to dictionaries
    return [
        {
            "id": todo.id,
            "content": todo.content,
            "status": todo.status.value,
            "priority": todo.priority.value,
            "category": todo.category,
            "source": todo.source.value,
            "estimated_time": todo.estimated_time,
            "dependencies": todo.dependencies,
            "created_at": todo.created_at,
            "updated_at": todo.updated_at,
            "completed_at": todo.completed_at,
            "notes": todo.notes,
            "tags": todo.tags,
            "file_path": todo.file_path,
            "line_number": todo.line_number,
        }
        for todo in todos
    ]


def get_todo(todo_id: str) -> Optional[Dict]:
    """
    Get a specific TODO by ID.

    Args:
        todo_id: The TODO ID

    Returns:
        TODO dictionary or None if not found
    """
    manager = get_manager()
    if todo_id in manager.todos:
        todo = manager.todos[todo_id]
        return {
            "id": todo.id,
            "content": todo.content,
            "status": todo.status.value,
            "priority": todo.priority.value,
            "category": todo.category,
            "source": todo.source.value,
            "estimated_time": todo.estimated_time,
            "dependencies": todo.dependencies,
            "created_at": todo.created_at,
            "updated_at": todo.updated_at,
            "completed_at": todo.completed_at,
            "notes": todo.notes,
            "tags": todo.tags,
            "file_path": todo.file_path,
            "line_number": todo.line_number,
        }
    return None


def search_todos(query: str) -> List[Dict]:
    """
    Search TODOs by content or category.

    Args:
        query: Search query

    Returns:
        List of matching TODO dictionaries
    """
    manager = get_manager()
    results = []

    for todo in manager.todos.values():
        if (
            query.lower() in todo.content.lower()
            or query.lower() in todo.category.lower()
        ):
            results.append(
                {
                    "id": todo.id,
                    "content": todo.content,
                    "status": todo.status.value,
                    "priority": todo.priority.value,
                    "category": todo.category,
                    "source": todo.source.value,
                    "estimated_time": todo.estimated_time,
                    "notes": todo.notes,
                    "tags": todo.tags,
                }
            )

    return results


def get_critical_todos() -> List[Dict]:
    """Get all critical TODOs that are pending."""
    return get_todos(status="pending", priority="critical")


def get_pending_todos() -> List[Dict]:
    """Get all pending TODOs."""
    return get_todos(status="pending")


def get_completed_todos() -> List[Dict]:
    """Get all completed TODOs."""
    return get_todos(status="completed")


def sync_todos():
    """Sync TODOs with all external systems."""
    manager = get_manager()
    manager.import_from_external_systems()
    manager._sync_all_systems()


def get_todo_stats() -> Dict:
    """Get TODO statistics."""
    manager = get_manager()
    todos = list(manager.todos.values())

    stats = {
        "total": len(todos),
        "pending": len([t for t in todos if t.status == TodoStatus.PENDING]),
        "in_progress": len([t for t in todos if t.status == TodoStatus.IN_PROGRESS]),
        "completed": len([t for t in todos if t.status == TodoStatus.COMPLETED]),
        "cancelled": len([t for t in todos if t.status == TodoStatus.CANCELLED]),
        "blocked": len([t for t in todos if t.status == TodoStatus.BLOCKED]),
        "critical": len([t for t in todos if t.priority == TodoPriority.CRITICAL]),
        "high": len([t for t in todos if t.priority == TodoPriority.HIGH]),
        "medium": len([t for t in todos if t.priority == TodoPriority.MEDIUM]),
        "low": len([t for t in todos if t.priority == TodoPriority.LOW]),
    }

    return stats


# Convenience functions for common use cases
def add_dev_todo(
    content: str, priority: str = "medium", estimated_time: int = 30
) -> str:
    """Add a development TODO."""
    return add_todo(
        content,
        priority=priority,
        category="development",
        source="dev_workflow",
        estimated_time=estimated_time,
    )


def add_bug_todo(content: str, priority: str = "high") -> str:
    """Add a bug TODO."""
    return add_todo(
        content, priority=priority, category="bug", source="dev_workflow", tags=["bug"]
    )


def add_feature_todo(
    content: str, priority: str = "medium", estimated_time: int = 60
) -> str:
    """Add a feature TODO."""
    return add_todo(
        content,
        priority=priority,
        category="feature",
        source="dev_workflow",
        estimated_time=estimated_time,
        tags=["feature"],
    )


def add_doc_todo(content: str, priority: str = "low") -> str:
    """Add a documentation TODO."""
    return add_todo(
        content,
        priority=priority,
        category="documentation",
        source="documentation",
        tags=["docs"],
    )


def add_health_todo(content: str, priority: str = "medium") -> str:
    """Add a health check TODO."""
    return add_todo(
        content,
        priority=priority,
        category="health",
        source="health_check",
        tags=["health"],
    )


# Example usage functions
def example_usage():
    """Example usage of the TODO helper functions."""
    print("=== TODO Helper Functions Example ===")

    # Add some example TODOs
    bug_id = add_bug_todo("Fix parser regex bug", priority="critical")
    feature_id = add_feature_todo(
        "Add dark mode support", priority="medium", estimated_time=120
    )
    doc_id = add_doc_todo("Update API documentation", priority="low")

    print(f"Added bug TODO: {bug_id}")
    print(f"Added feature TODO: {feature_id}")
    print(f"Added doc TODO: {doc_id}")

    # Get critical TODOs
    critical_todos = get_critical_todos()
    print(f"\nCritical TODOs: {len(critical_todos)}")
    for todo in critical_todos:
        print(f"  - {todo['id']}: {todo['content']}")

    # Get stats
    stats = get_todo_stats()
    print("\nTODO Stats:")
    print(f"  Total: {stats['total']}")
    print(f"  Pending: {stats['pending']}")
    print(f"  Critical: {stats['critical']}")

    # Complete a TODO
    complete_todo(bug_id, "Fixed regex pattern in parser.py")
    print(f"\nCompleted TODO: {bug_id}")

    # Search TODOs
    search_results = search_todos("API")
    print(f"\nSearch results for 'API': {len(search_results)}")
    for todo in search_results:
        print(f"  - {todo['id']}: {todo['content']}")


if __name__ == "__main__":
    example_usage()
