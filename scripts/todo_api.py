#!/usr/bin/env python3
"""
Atlas TODO API - Simple interface for other systems to interact with unified TODOs

This provides a simple API that other systems can use to:
- Add TODOs
- Update TODO status
- Complete TODOs
- Query TODOs

Usage examples:
    python3 scripts/todo_api.py add "Fix bug in parser" --priority critical
    python3 scripts/todo_api.py complete TODO-123 --notes "Fixed by updating regex"
    python3 scripts/todo_api.py status TODO-123 completed
    python3 scripts/todo_api.py list --status pending --priority critical
"""

import argparse
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from scripts.unified_todo_manager import (TodoPriority, TodoSource, TodoStatus,
                                          UnifiedTodoManager)


def main():
    """Main CLI interface for TODO API."""
    parser = argparse.ArgumentParser(description="Atlas TODO API")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Add TODO command
    add_parser = subparsers.add_parser("add", help="Add a new TODO")
    add_parser.add_argument("content", help="TODO content")
    add_parser.add_argument(
        "--priority", choices=["critical", "high", "medium", "low"], default="medium"
    )
    add_parser.add_argument("--category", default="general")
    add_parser.add_argument(
        "--source",
        choices=["master", "dev_workflow", "documentation", "checklist"],
        default="master",
    )
    add_parser.add_argument("--time", type=int, help="Estimated time in minutes")
    add_parser.add_argument("--notes", help="Additional notes")

    # Update status command
    status_parser = subparsers.add_parser("status", help="Update TODO status")
    status_parser.add_argument("todo_id", help="TODO ID")
    status_parser.add_argument(
        "new_status",
        choices=["pending", "in_progress", "completed", "cancelled", "blocked"],
    )
    status_parser.add_argument("--notes", help="Additional notes")

    # Complete TODO command
    complete_parser = subparsers.add_parser("complete", help="Complete a TODO")
    complete_parser.add_argument("todo_id", help="TODO ID")
    complete_parser.add_argument("--notes", help="Completion notes")

    # List TODOs command
    list_parser = subparsers.add_parser("list", help="List TODOs")
    list_parser.add_argument(
        "--status",
        choices=["pending", "in_progress", "completed", "cancelled", "blocked"],
    )
    list_parser.add_argument(
        "--priority", choices=["critical", "high", "medium", "low"]
    )
    list_parser.add_argument("--category")
    list_parser.add_argument("--limit", type=int, default=20)

    # Get TODO command
    get_parser = subparsers.add_parser("get", help="Get TODO details")
    get_parser.add_argument("todo_id", help="TODO ID")

    # Search command
    search_parser = subparsers.add_parser("search", help="Search TODOs")
    search_parser.add_argument("query", help="Search query")

    # Sync command
    sync_parser = subparsers.add_parser("sync", help="Sync with external systems")
    sync_parser.add_argument(
        "--import",
        action="store_true",
        dest="import_flag",
        help="Import from external systems",
    )
    sync_parser.add_argument(
        "--export",
        action="store_true",
        dest="export_flag",
        help="Export to external systems",
    )

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    # Initialize manager
    manager = UnifiedTodoManager()

    # Handle commands
    if args.command == "add":
        todo_id = manager.add_todo(
            content=args.content,
            priority=TodoPriority(args.priority),
            source=TodoSource(args.source),
            category=args.category,
            estimated_time=args.time,
            notes=args.notes,
        )
        print(f"Added TODO: {todo_id}")

    elif args.command == "status":
        if manager.update_todo(args.todo_id, status=args.new_status, notes=args.notes):
            print(f"Updated TODO {args.todo_id} status to {args.new_status}")
        else:
            print(f"Failed to update TODO {args.todo_id}")
            sys.exit(1)

    elif args.command == "complete":
        if manager.complete_todo(args.todo_id, args.notes):
            print(f"Completed TODO: {args.todo_id}")
        else:
            print(f"Failed to complete TODO {args.todo_id}")
            sys.exit(1)

    elif args.command == "list":
        todos = list(manager.todos.values())

        # Apply filters
        if args.status:
            todos = [t for t in todos if t.status == TodoStatus(args.status)]
        if args.priority:
            todos = [t for t in todos if t.priority == TodoPriority(args.priority)]
        if args.category:
            todos = [t for t in todos if t.category == args.category]

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

        # Limit results
        todos = todos[: args.limit]

        if todos:
            print(f"Found {len(todos)} TODOs:")
            for todo in todos:
                print(
                    f"  {todo.id}: {todo.content} [{todo.status.value}] [{todo.priority.value}]"
                )
        else:
            print("No TODOs found matching criteria")

    elif args.command == "get":
        if args.todo_id in manager.todos:
            todo = manager.todos[args.todo_id]
            print(f"ID: {todo.id}")
            print(f"Content: {todo.content}")
            print(f"Status: {todo.status.value}")
            print(f"Priority: {todo.priority.value}")
            print(f"Category: {todo.category}")
            print(f"Source: {todo.source.value}")
            if todo.estimated_time:
                print(f"Estimated time: {todo.estimated_time} minutes")
            if todo.dependencies:
                print(f"Dependencies: {', '.join(todo.dependencies)}")
            if todo.notes:
                print(f"Notes: {todo.notes}")
            print(f"Created: {todo.created_at}")
            print(f"Updated: {todo.updated_at}")
            if todo.completed_at:
                print(f"Completed: {todo.completed_at}")
        else:
            print(f"TODO {args.todo_id} not found")
            sys.exit(1)

    elif args.command == "search":
        results = []
        for todo in manager.todos.values():
            if (
                args.query.lower() in todo.content.lower()
                or args.query.lower() in todo.category.lower()
            ):
                results.append(todo)

        if results:
            print(f"Found {len(results)} TODOs matching '{args.query}':")
            for todo in results:
                print(f"  {todo.id}: {todo.content} [{todo.status.value}]")
        else:
            print(f"No TODOs found matching '{args.query}'")

    elif args.command == "sync":
        if args.import_flag:
            count = manager.import_from_external_systems()
            print(f"Imported {count} TODOs from external systems")
        elif args.export_flag:
            manager._export_to_external_systems()
            print("Exported TODOs to external systems")
        else:
            # Default: sync both ways
            count = manager.import_from_external_systems()
            print(f"Imported {count} TODOs from external systems")
            manager._sync_all_systems()
            print("Synced all TODOs to external systems")


if __name__ == "__main__":
    main()
