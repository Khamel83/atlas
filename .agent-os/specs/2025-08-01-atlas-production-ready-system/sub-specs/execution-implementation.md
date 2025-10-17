# Atlas Master Execution Implementation

This document provides the actual implementation files and scripts that enable single-command execution of all 208 Atlas tasks.

## Implementation Files Structure

```
.agent-os/
├── execution/
│   ├── atlas_controller.py       # Main execution controller
│   ├── task_database.py          # Task definitions and management
│   ├── dependency_resolver.py    # Dependency management
│   ├── context_loader.py         # Automatic context loading
│   ├── quality_gates.py          # Quality validation system
│   ├── progress_tracker.py       # Progress and state management
│   ├── git_automation.py         # Git workflow automation
│   └── recovery_system.py        # Failure handling and recovery
├── data/
│   ├── tasks.json                # Complete task database
│   ├── dependencies.json         # Task dependency mapping
│   ├── quality_gates.json        # Quality gate definitions
│   └── execution_state.json      # Current execution state
└── commands/
    └── execute-atlas-production-system.md  # Main command interface
```

## Task Database Implementation

### **Complete Task Database (tasks.json)**
```json
{
  "metadata": {
    "version": "1.0",
    "total_tasks": 208,
    "phases": 6,
    "estimated_weeks": 16
  },
  "tasks": {
    "1.1": {
      "id": "1.1",
      "title": "Write tests for environment validation and configuration loading",
      "description": "Create comprehensive test cases for environment setup and configuration loading functionality before implementing the actual features.",
      "type": "TFI",
      "phase": 1,
      "estimated_hours": 2,
      "prerequisites": [],
      "blocks": ["1.2", "1.3", "1.4", "1.5"],
      "context_files": [
        "@.agent-os/product/mission-lite.md",
        "@.agent-os/product/tech-stack.md",
        "helpers/config.py",
        "tests/conftest.py",
        "@.agent-os/specs/2025-08-01-atlas-production-ready-system/sub-specs/task-execution-framework.md"
      ],
      "acceptance_criteria": [
        "Tests written before any implementation",
        "Test coverage of 90%+ for environment validation logic",
        "Tests pass consistently when run multiple times",
        "Tests cover edge cases and error conditions",
        "Tests validate configuration loading from multiple sources",
        "Tests verify environment variable processing",
        "Tests check for missing or invalid configuration"
      ],
      "quality_gates": ["TFI_1", "TFI_2", "TFI_3", "UNIVERSAL_1", "UNIVERSAL_2", "UNIVERSAL_3", "UNIVERSAL_4", "UNIVERSAL_5"],
      "files_to_create": ["tests/test_environment_validation.py"],
      "files_to_modify": ["helpers/config.py"],
      "expected_outcomes": [
        "Comprehensive test suite for environment validation",
        "Clear test cases for configuration edge cases",
        "Foundation for implementing environment setup automation"
      ],
      "status": "pending",
      "assigned_to": null,
      "started_at": null,
      "completed_at": null,
      "results": null
    },
    "1.2": {
      "id": "1.2",
      "title": "Create automated .env file generation script from template",
      "description": "Build a script that automatically generates a working .env file from the template, with intelligent defaults and user prompts for required values.",
      "type": "CAS",
      "phase": 1,
      "estimated_hours": 3,
      "prerequisites": ["1.1"],
      "blocks": ["1.3", "1.4", "1.5", "1.6"],
      "context_files": [
        "@.agent-os/product/mission-lite.md",
        "@.agent-os/product/tech-stack.md",
        ".env.example",
        "helpers/config.py",
        "tests/test_environment_validation.py"
      ],
      "acceptance_criteria": [
        "Script generates working .env from .env.example",
        "Intelligent defaults for all optional settings",
        "User prompts for required values only",
        "Validation of user inputs before writing file",
        "Backup existing .env before overwriting",
        "Clear success/failure messages",
        "Works on fresh system with no existing configuration"
      ],
      "quality_gates": ["CAS_1", "CAS_2", "CAS_3", "UNIVERSAL_1", "UNIVERSAL_2", "UNIVERSAL_3", "UNIVERSAL_4", "UNIVERSAL_5"],
      "files_to_create": ["scripts/generate_env.py"],
      "files_to_modify": ["helpers/config.py"],
      "expected_outcomes": [
        "Automated .env generation script",
        "User-friendly setup experience",
        "Reduced configuration errors"
      ],
      "status": "pending"
    }
  }
}
```

### **Task Database Manager (task_database.py)**
```python
import json
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime

@dataclass
class Task:
    id: str
    title: str
    description: str
    type: str
    phase: int
    estimated_hours: int
    prerequisites: List[str]
    blocks: List[str]
    context_files: List[str]
    acceptance_criteria: List[str]
    quality_gates: List[str]
    files_to_create: List[str]
    files_to_modify: List[str]
    expected_outcomes: List[str]
    status: str = "pending"
    assigned_to: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    results: Optional[Dict] = None

class TaskDatabase:
    def __init__(self, db_path: str = ".agent-os/data/tasks.json"):
        self.db_path = Path(db_path)
        self.tasks: Dict[str, Task] = {}
        self.load_tasks()

    def load_tasks(self):
        """Load all tasks from JSON database"""
        if self.db_path.exists():
            with open(self.db_path, 'r') as f:
                data = json.load(f)
                for task_id, task_data in data['tasks'].items():
                    self.tasks[task_id] = Task(**task_data)

    def save_tasks(self):
        """Save all tasks to JSON database"""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "metadata": {
                "version": "1.0",
                "total_tasks": len(self.tasks),
                "last_updated": datetime.utcnow().isoformat()
            },
            "tasks": {}
        }

        for task_id, task in self.tasks.items():
            task_dict = task.__dict__.copy()
            # Convert datetime objects to ISO strings
            if task_dict['started_at']:
                task_dict['started_at'] = task_dict['started_at'].isoformat()
            if task_dict['completed_at']:
                task_dict['completed_at'] = task_dict['completed_at'].isoformat()
            data['tasks'][task_id] = task_dict

        with open(self.db_path, 'w') as f:
            json.dump(data, f, indent=2)

    def get_task(self, task_id: str) -> Optional[Task]:
        """Get task by ID"""
        return self.tasks.get(task_id)

    def get_tasks_by_status(self, status: str) -> List[Task]:
        """Get all tasks with specific status"""
        return [task for task in self.tasks.values() if task.status == status]

    def get_tasks_by_phase(self, phase: int) -> List[Task]:
        """Get all tasks in specific phase"""
        return [task for task in self.tasks.values() if task.phase == phase]

    def mark_task_started(self, task_id: str):
        """Mark task as started"""
        if task_id in self.tasks:
            self.tasks[task_id].status = "in_progress"
            self.tasks[task_id].started_at = datetime.utcnow()
            self.save_tasks()

    def mark_task_completed(self, task_id: str, results: Dict = None):
        """Mark task as completed"""
        if task_id in self.tasks:
            self.tasks[task_id].status = "completed"
            self.tasks[task_id].completed_at = datetime.utcnow()
            self.tasks[task_id].results = results
            self.save_tasks()

    def mark_task_failed(self, task_id: str, error: str):
        """Mark task as failed"""
        if task_id in self.tasks:
            self.tasks[task_id].status = "failed"
            self.tasks[task_id].results = {"error": error, "failed_at": datetime.utcnow().isoformat()}
            self.save_tasks()
```

## Dependency Resolution Implementation

### **Dependency Resolver (dependency_resolver.py)**
```python
from typing import List, Set, Dict
from collections import defaultdict, deque

class DependencyResolver:
    def __init__(self, task_db):
        self.task_db = task_db
        self.dependency_graph = self._build_dependency_graph()

    def _build_dependency_graph(self) -> Dict[str, List[str]]:
        """Build dependency graph from task database"""
        graph = defaultdict(list)
        for task in self.task_db.tasks.values():
            for prereq in task.prerequisites:
                graph[prereq].append(task.id)
        return dict(graph)

    def get_ready_tasks(self) -> List[str]:
        """Get tasks that are ready to execute (all prerequisites complete)"""
        ready = []

        for task in self.task_db.tasks.values():
            if task.status == "pending":
                # Check if all prerequisites are complete
                prereqs_complete = all(
                    self.task_db.get_task(prereq_id).status == "completed"
                    for prereq_id in task.prerequisites
                )
                if prereqs_complete:
                    ready.append(task.id)

        return ready

    def get_blocked_tasks(self) -> List[str]:
        """Get tasks blocked by failed dependencies"""
        blocked = []
        failed_tasks = {task.id for task in self.task_db.get_tasks_by_status("failed")}

        def is_blocked_by_failure(task_id: str, visited: Set[str] = None) -> bool:
            if visited is None:
                visited = set()
            if task_id in visited:
                return False  # Avoid cycles
            visited.add(task_id)

            task = self.task_db.get_task(task_id)
            if not task:
                return False

            # Check direct prerequisites
            for prereq in task.prerequisites:
                if prereq in failed_tasks:
                    return True
                if is_blocked_by_failure(prereq, visited):
                    return True
            return False

        for task in self.task_db.tasks.values():
            if task.status == "pending" and is_blocked_by_failure(task.id):
                blocked.append(task.id)

        return blocked

    def validate_no_cycles(self) -> bool:
        """Validate that dependency graph has no cycles"""
        visited = set()
        rec_stack = set()

        def has_cycle(node: str) -> bool:
            visited.add(node)
            rec_stack.add(node)

            for neighbor in self.dependency_graph.get(node, []):
                if neighbor not in visited:
                    if has_cycle(neighbor):
                        return True
                elif neighbor in rec_stack:
                    return True

            rec_stack.remove(node)
            return False

        for task_id in self.task_db.tasks:
            if task_id not in visited:
                if has_cycle(task_id):
                    return False
        return True

    def get_critical_path(self) -> List[str]:
        """Get critical path tasks that block the most other tasks"""
        blocking_counts = defaultdict(int)

        def count_blocked_tasks(task_id: str, visited: Set[str] = None) -> int:
            if visited is None:
                visited = set()
            if task_id in visited:
                return 0
            visited.add(task_id)

            count = 1  # Count this task
            for blocked_task in self.dependency_graph.get(task_id, []):
                count += count_blocked_tasks(blocked_task, visited)

            return count

        for task_id in self.task_db.tasks:
            blocking_counts[task_id] = count_blocked_tasks(task_id)

        # Return tasks sorted by how many other tasks they block
        return sorted(blocking_counts.keys(), key=lambda x: blocking_counts[x], reverse=True)
```

## Context Loading Implementation

### **Context Loader (context_loader.py)**
```python
import os
from pathlib import Path
from typing import Dict, List
import hashlib
import json
from datetime import datetime

class ContextLoader:
    def __init__(self, cache_dir: str = ".agent-os/cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.file_cache = {}
        self.context_cache = {}

    def read_file(self, file_path: str) -> str:
        """Read file with caching"""
        # Convert @.agent-os paths to absolute paths
        if file_path.startswith('@.agent-os'):
            file_path = file_path.replace('@.agent-os', '.agent-os')

        abs_path = Path(file_path).resolve()

        # Check cache
        cache_key = str(abs_path)
        if cache_key in self.file_cache:
            cached_mtime, cached_content = self.file_cache[cache_key]
            current_mtime = abs_path.stat().st_mtime
            if current_mtime == cached_mtime:
                return cached_content

        # Read file and cache
        try:
            with open(abs_path, 'r', encoding='utf-8') as f:
                content = f.read()
                self.file_cache[cache_key] = (abs_path.stat().st_mtime, content)
                return content
        except FileNotFoundError:
            return f"# File not found: {file_path}"
        except Exception as e:
            return f"# Error reading {file_path}: {str(e)}"

    def load_task_context(self, task_id: str) -> Dict[str, str]:
        """Load all required context for a task"""
        task = self.task_db.get_task(task_id)
        if not task:
            return {}

        context = {}

        # Core context (always required)
        core_files = [
            '@.agent-os/product/mission-lite.md',
            '@.agent-os/product/tech-stack.md',
            '@.agent-os/specs/2025-08-01-atlas-production-ready-system/spec-lite.md'
        ]

        for file_path in core_files:
            context[f'core_{Path(file_path).stem}'] = self.read_file(file_path)

        # Task-specific context files
        for file_path in task.context_files:
            context[f'context_{Path(file_path).stem}'] = self.read_file(file_path)

        # Phase-specific context
        phase_context = self.get_phase_context(task.phase)
        context.update(phase_context)

        # Dependency context (results from prerequisite tasks)
        for prereq_id in task.prerequisites:
            prereq_results = self.get_task_results(prereq_id)
            if prereq_results:
                context[f'prereq_{prereq_id}_results'] = json.dumps(prereq_results, indent=2)

        return context

    def get_phase_context(self, phase: int) -> Dict[str, str]:
        """Get phase-specific context files"""
        phase_files = {
            1: ['@.agent-os/specs/.../sub-specs/technical-spec.md'],
            2: ['@.agent-os/specs/.../sub-specs/technical-spec.md'],
            3: ['@.agent-os/specs/.../sub-specs/api-spec.md'],
            4: ['@.agent-os/specs/.../sub-specs/reliability-best-practices.md'],
            5: ['@.agent-os/specs/.../sub-specs/github-automation.md'],
            6: []  # Phase 6 needs all previous context
        }

        context = {}
        for file_path in phase_files.get(phase, []):
            context[f'phase_{phase}_{Path(file_path).stem}'] = self.read_file(file_path)

        return context

    def generate_task_prompt(self, task_id: str, context: Dict[str, str]) -> str:
        """Generate complete execution prompt with all context"""
        task = self.task_db.get_task(task_id)
        if not task:
            return ""

        prompt = f"""# Atlas Task Execution: {task.title}

## Task Details
- **Task ID**: {task.id}
- **Type**: {task.type}
- **Phase**: {task.phase}
- **Estimated Time**: {task.estimated_hours} hours
- **Prerequisites**: {', '.join(task.prerequisites) if task.prerequisites else 'None'}

## Task Description
{task.description}

## Acceptance Criteria
{chr(10).join(f'- {criteria}' for criteria in task.acceptance_criteria)}

## Expected Outcomes
{chr(10).join(f'- {outcome}' for outcome in task.expected_outcomes)}

## Files to Create
{chr(10).join(f'- {file}' for file in task.files_to_create)}

## Files to Modify
{chr(10).join(f'- {file}' for file in task.files_to_modify)}

## Context Information

### Core Context
{self.format_context_section(context, 'core_')}

### Task-Specific Context
{self.format_context_section(context, 'context_')}

### Phase Context
{self.format_context_section(context, f'phase_{task.phase}_')}

### Prerequisite Results
{self.format_context_section(context, 'prereq_')}

## Execution Instructions

Follow the Task Execution Framework for {task.type} tasks:

1. **Load Required Context**: All context has been loaded above
2. **Follow Task Type Pattern**: Use {task.type} execution methodology
3. **Meet Quality Gates**: Task must pass {len(task.quality_gates)} quality gates
4. **Complete Acceptance Criteria**: All criteria must be met
5. **Update Documentation**: Keep docs in sync with changes

## Quality Gates Required
This task must pass the following quality gates:
{chr(10).join(f'- {gate}' for gate in task.quality_gates)}

Execute this task following Atlas principles and quality standards.
"""
        return prompt

    def format_context_section(self, context: Dict[str, str], prefix: str) -> str:
        """Format a section of context for display"""
        section_items = {k: v for k, v in context.items() if k.startswith(prefix)}
        if not section_items:
            return "No additional context for this section."

        formatted = ""
        for key, content in section_items.items():
            clean_key = key.replace(prefix, '').replace('_', ' ').title()
            formatted += f"\n#### {clean_key}\n```\n{content[:1000]}...\n```\n"

        return formatted
```

This implementation provides the foundation for automatic execution of all 208 tasks with proper context loading, dependency management, and quality validation.