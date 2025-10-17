# Atlas TODO Management System

## Overview

The Atlas TODO Management System provides a **unified single source of truth** for all tasks across the entire project. It solves the critical problem of scattered TODO tracking by automatically synchronizing with all external systems, ensuring no task is ever lost or forgotten.

## Problem Solved

**Before**: TODOs were scattered across multiple systems:
- Cursor TODO system (15 tasks)
- `dev_tasks.json` (5 tasks)
- Documentation files (78+ tasks)
- Inline code comments (TODO/FIXME/XXX/HACK)
- Checklist files (90+ tasks)
- Various roadmap files

**After**: **364+ TODOs** unified in a single system with bidirectional sync to all sources.

## System Architecture

### Single Source of Truth
- **`master_todos.json`** - Central repository for all TODOs
- **`scripts/unified_todo_manager.py`** - Core management system
- **`scripts/todo_api.py`** - CLI interface for external systems
- **`scripts/todo_helpers.py`** - Helper functions for programmatic access
- **Bidirectional sync** - Changes in any system automatically update all others

### Integration Points

The system automatically synchronizes with:

1. **Dev Workflow** (`dev_tasks.json`) - Development tasks and project milestones
2. **Documentation** - Task references in markdown files across docs/
3. **Checklists** - Unchecked items in YAML and markdown checklist files
4. **Inline Code** - TODO/FIXME/XXX/HACK comments in source code
5. **Health Checks** - Issues found by system monitoring and health checks
6. **Cursor System** - Tasks visible in Cursor's TODO UI
7. **Roadmap Files** - Tasks mentioned in various roadmap documents

## Core Features

### Intelligent Deduplication
- Prevents duplicate TODOs across systems
- Uses content similarity matching
- Maintains cross-references between systems
- Handles variations in task descriptions

### Priority Detection
- Automatically assigns priority based on keywords
- **Critical**: "critical", "urgent", "blocker", "broken"
- **High**: "important", "high", "priority", "bug"
- **Medium**: Default priority for most tasks
- **Low**: "nice to have", "optional", "future"

### Comprehensive Search & Filtering
- Filter by status (pending, completed, cancelled)
- Filter by priority (critical, high, medium, low)
- Filter by category (foundation, enhancement, cognitive, etc.)
- Filter by source system
- Full-text search across task content

### Status Tracking
- **pending**: Not yet started
- **in_progress**: Currently being worked on
- **completed**: Finished successfully
- **cancelled**: No longer needed

## Usage Examples

### Command Line Interface

```bash
# Add a new TODO
python3 scripts/todo_api.py add "Fix parser bug" --priority critical

# Complete a TODO
python3 scripts/todo_api.py complete TODO-123 --notes "Fixed regex pattern"

# List all TODOs
python3 scripts/todo_api.py list

# Search for specific TODOs
python3 scripts/todo_api.py search "authentication"

# View dashboard
python3 scripts/unified_todo_manager.py --dashboard

# Import from all external systems
python3 scripts/unified_todo_manager.py --import

# Export to external systems
python3 scripts/unified_todo_manager.py --export
```

### Programmatic Interface

```python
from scripts.todo_helpers import add_todo, complete_todo, get_todos

# Add a new TODO
todo_id = add_todo("Fix bug in article fetcher", priority="critical")

# Complete a TODO
complete_todo(todo_id, "Fixed by updating regex pattern")

# Get all TODOs
todos = get_todos()

# Get TODOs by status
pending_todos = get_todos(status="pending")

# Get TODOs by priority
critical_todos = get_todos(priority="critical")
```

### Interactive Management

```bash
# Launch interactive TODO manager
python3 scripts/unified_todo_manager.py --interactive

# Available commands in interactive mode:
# - list: Show all TODOs
# - add: Add new TODO
# - complete: Mark TODO as complete
# - search: Search TODOs
# - dashboard: Show status dashboard
# - help: Show available commands
# - exit: Exit interactive mode
```

## System Integration

### Integration with run_atlas.sh

The main Atlas workflow automatically uses the unified TODO system:

```bash
# Pre-development: Import and consolidate all TODOs
python3 scripts/unified_todo_manager.py --import

# Development options include:
# - View unified dashboard
# - Run automated development
# - Interactive development
# - Interactive TODO management

# Post-development: Sync changes back to all systems
python3 scripts/unified_todo_manager.py --export

# Post-pipeline: Capture new issues and sync
python3 scripts/unified_todo_manager.py --import
```

### Integration with Health Checks

The system automatically captures issues found by health monitoring:

```python
# Health check integration
from scripts.todo_helpers import add_todo

def health_check_callback(issue):
    """Automatically add health check issues as TODOs"""
    todo_id = add_todo(
        f"Health Check Issue: {issue['description']}",
        priority="high",
        category="health"
    )
    return todo_id
```

## File Structure

```
scripts/
├── unified_todo_manager.py    # Core management system
├── todo_api.py               # CLI interface
├── todo_helpers.py           # Helper functions
└── todo_consolidator.py      # Legacy consolidation (deprecated)

master_todos.json             # Central TODO repository
dev_tasks.json               # Development workflow integration
```

## Data Format

### master_todos.json Structure

```json
{
  "todos": [
    {
      "id": "TODO-001",
      "content": "Fix MetadataManager constructor parameter mismatch",
      "status": "pending",
      "priority": "critical",
      "category": "foundation",
      "source": "documentation",
      "dependencies": [],
      "created_at": "2024-12-01T10:00:00Z",
      "updated_at": "2024-12-01T10:00:00Z",
      "notes": "Prevents accurate API documentation and proper testing",
      "estimated_time": "30 minutes",
      "complexity": 3
    }
  ],
  "metadata": {
    "total_count": 364,
    "last_updated": "2024-12-01T10:00:00Z",
    "sources": ["documentation", "code", "checklists", "dev_workflow", "health_checks"]
  }
}
```

## Advanced Features

### Dependency Tracking
- Track prerequisite relationships between TODOs
- Prevent completion of dependent tasks
- Visualize dependency chains
- Automatic dependency resolution

### Time Estimation
- Estimate time required for each task
- Track actual time spent
- Improve estimation accuracy over time
- Resource planning and scheduling

### Complexity Scoring
- Rate task complexity (1-5 scale)
- Use for prioritization and assignment
- Track completion patterns by complexity
- Identify areas needing simplification

### Batch Operations
- Complete multiple related TODOs
- Bulk priority updates
- Mass category reassignment
- Batch import/export operations

## Monitoring & Analytics

### Dashboard Metrics
- Total TODOs by status
- Priority distribution
- Source system breakdown
- Completion velocity
- Average time to completion

### Reporting
- Daily/weekly status reports
- Progress tracking over time
- Bottleneck identification
- Productivity metrics

### Alerts
- Overdue TODO notifications
- High-priority task alerts
- Dependency blocking warnings
- System sync failures

## Best Practices

### Adding TODOs
1. Use descriptive, actionable titles
2. Include context and implementation details
3. Set appropriate priority levels
4. Add dependencies when relevant
5. Estimate time and complexity

### Managing TODOs
1. Review and update regularly
2. Complete TODOs immediately when done
3. Add completion notes for future reference
4. Keep the system synchronized
5. Use categories for organization

### System Maintenance
1. Regular imports to catch new TODOs
2. Periodic cleanup of completed items
3. Dependency validation
4. Performance monitoring
5. Backup of master_todos.json

## Troubleshooting

### Common Issues

**Sync Problems**:
- Run `python3 scripts/unified_todo_manager.py --import` to force sync
- Check file permissions on master_todos.json
- Verify external system files are accessible

**Duplicate TODOs**:
- System automatically deduplicates based on content similarity
- Manual duplicates can be merged using the CLI
- Review deduplication settings if issues persist

**Performance Issues**:
- Large TODO counts (1000+) may slow operations
- Archive completed TODOs periodically
- Use filtering to reduce result sets

### Error Recovery
- Automatic backup before major operations
- Rollback capability for failed imports
- Validation checks prevent data corruption
- Detailed error logging for debugging

## Migration Guide

### From Legacy Systems
1. Export existing TODOs to standard format
2. Run initial import: `python3 scripts/unified_todo_manager.py --import`
3. Verify all TODOs captured correctly
4. Update workflows to use unified system
5. Deprecate old TODO tracking methods

### Upgrading the System
1. Backup master_todos.json
2. Update system scripts
3. Run migration scripts if needed
4. Verify system functionality
5. Update documentation references

## API Reference

### Core Functions

```python
# TODO Management
add_todo(content, priority="medium", category="general", dependencies=[])
complete_todo(todo_id, notes="")
update_todo(todo_id, **kwargs)
delete_todo(todo_id)

# Querying
get_todos(status=None, priority=None, category=None, source=None)
search_todos(query, **filters)
get_todo_by_id(todo_id)

# System Operations
import_from_external_systems()
export_to_external_systems()
validate_todo_integrity()
generate_dashboard_report()
```

### CLI Commands

```bash
# Basic Operations
todo_api.py add "Task description" [--priority PRIORITY] [--category CATEGORY]
todo_api.py complete TODO_ID [--notes "Completion notes"]
todo_api.py list [--status STATUS] [--priority PRIORITY]
todo_api.py search "query" [--category CATEGORY]

# System Operations
unified_todo_manager.py --dashboard
unified_todo_manager.py --import
unified_todo_manager.py --export
unified_todo_manager.py --interactive
```

## Integration Examples

### Git Hook Integration
```bash
# .git/hooks/post-commit
#!/bin/bash
# Auto-import TODOs after each commit
python3 scripts/unified_todo_manager.py --import --quiet
```

### CI/CD Integration
```yaml
# .github/workflows/todo-sync.yml
name: TODO Sync
on: [push, pull_request]
jobs:
  sync-todos:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Sync TODOs
        run: python3 scripts/unified_todo_manager.py --import --validate
```

### Editor Integration
```json
// .vscode/tasks.json
{
  "tasks": [
    {
      "label": "Add TODO",
      "type": "shell",
      "command": "python3 scripts/todo_api.py add '${input:todoContent}'"
    }
  ]
}
```

The Atlas TODO Management System ensures that no task is ever lost or forgotten, providing a comprehensive, unified approach to project task management with seamless integration across all development workflows.