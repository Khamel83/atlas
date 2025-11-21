#!/usr/bin/env python3
"""
Atlas Enhanced Task Specification Schema
Defines atomic tasks with complete context for AI agent execution
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Optional, Any
from datetime import datetime
import json

class TaskComplexity(Enum):
    SMALL = "S"      # 1-3 hours
    MEDIUM = "M"     # 3-8 hours
    LARGE = "L"      # 8+ hours

class TaskType(Enum):
    TEST_FIRST = "TFI"           # Test-First Implementation
    CONFIG_SETUP = "CAS"         # Configuration & Setup
    INTEGRATION = "IAC"          # Integration & Connection
    DOCUMENTATION = "DAP"        # Documentation & Process

class TaskStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    COMPLETED = "completed"
    FAILED = "failed"

@dataclass
class ValidationScript:
    """Automated validation for task completion"""
    name: str
    command: str
    expected_output: str
    timeout_seconds: int = 30
    working_directory: str = "/home/ubuntu/dev/atlas"

@dataclass
class FileReference:
    """Reference to relevant files for the task"""
    path: str
    line_start: Optional[int] = None
    line_end: Optional[int] = None
    description: str = ""
    is_primary: bool = False

@dataclass
class CodeExample:
    """Working code example to guide implementation"""
    title: str
    description: str
    code: str
    file_path: Optional[str] = None
    language: str = "python"

@dataclass
class ContextPackage:
    """Complete context for AI agent execution"""
    system_overview: str
    task_purpose: str
    architectural_context: str
    file_references: List[FileReference]
    code_examples: List[CodeExample]
    common_pitfalls: List[str]
    success_patterns: List[str]
    related_documentation: List[str]

@dataclass
class AcceptanceCriteria:
    """Specific, testable requirements for task completion"""
    requirements: List[str]
    test_cases: List[str]
    quality_metrics: Dict[str, Any]
    performance_requirements: Optional[Dict[str, Any]] = None

@dataclass
class RecoveryInstructions:
    """What to do if the task fails"""
    common_failures: List[Dict[str, str]]  # failure_type -> solution
    rollback_commands: List[str]
    escalation_triggers: List[str]
    alternative_approaches: List[str]

@dataclass
class AtomicTask:
    """Complete specification for an atomic, AI-executable task"""

    # Core identification
    id: str
    title: str
    description: str
    task_type: TaskType
    complexity: TaskComplexity
    estimated_hours: float

    # Dependencies and scheduling
    dependencies: List[str] = field(default_factory=list)
    blocks: List[str] = field(default_factory=list)
    priority: int = 5  # 1-10, higher = more important

    # AI Agent Context
    context_package: ContextPackage = None
    acceptance_criteria: AcceptanceCriteria = None
    validation_scripts: List[ValidationScript] = field(default_factory=list)
    recovery_instructions: RecoveryInstructions = None

    # Execution tracking
    status: TaskStatus = TaskStatus.PENDING
    assigned_agent: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    last_attempt: Optional[datetime] = None
    failure_count: int = 0

    # Results and artifacts
    git_commits: List[str] = field(default_factory=list)
    artifacts_created: List[str] = field(default_factory=list)
    execution_notes: str = ""
    agent_feedback: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "task_type": self.task_type.value if self.task_type else None,
            "complexity": self.complexity.value if self.complexity else None,
            "estimated_hours": self.estimated_hours,
            "dependencies": self.dependencies,
            "blocks": self.blocks,
            "priority": self.priority,
            "status": self.status.value if self.status else None,
            "assigned_agent": self.assigned_agent,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "last_attempt": self.last_attempt.isoformat() if self.last_attempt else None,
            "failure_count": self.failure_count,
            "git_commits": self.git_commits,
            "artifacts_created": self.artifacts_created,
            "execution_notes": self.execution_notes,
            "agent_feedback": self.agent_feedback,
            # Context package serialization
            "context_package": self._serialize_context_package(),
            "acceptance_criteria": self._serialize_acceptance_criteria(),
            "validation_scripts": self._serialize_validation_scripts(),
            "recovery_instructions": self._serialize_recovery_instructions()
        }

    def _serialize_context_package(self) -> Optional[Dict]:
        if not self.context_package:
            return None
        return {
            "system_overview": self.context_package.system_overview,
            "task_purpose": self.context_package.task_purpose,
            "architectural_context": self.context_package.architectural_context,
            "file_references": [
                {
                    "path": ref.path,
                    "line_start": ref.line_start,
                    "line_end": ref.line_end,
                    "description": ref.description,
                    "is_primary": ref.is_primary
                } for ref in self.context_package.file_references
            ],
            "code_examples": [
                {
                    "title": ex.title,
                    "description": ex.description,
                    "code": ex.code,
                    "file_path": ex.file_path,
                    "language": ex.language
                } for ex in self.context_package.code_examples
            ],
            "common_pitfalls": self.context_package.common_pitfalls,
            "success_patterns": self.context_package.success_patterns,
            "related_documentation": self.context_package.related_documentation
        }

    def _serialize_acceptance_criteria(self) -> Optional[Dict]:
        if not self.acceptance_criteria:
            return None
        return {
            "requirements": self.acceptance_criteria.requirements,
            "test_cases": self.acceptance_criteria.test_cases,
            "quality_metrics": self.acceptance_criteria.quality_metrics,
            "performance_requirements": self.acceptance_criteria.performance_requirements
        }

    def _serialize_validation_scripts(self) -> List[Dict]:
        return [
            {
                "name": script.name,
                "command": script.command,
                "expected_output": script.expected_output,
                "timeout_seconds": script.timeout_seconds,
                "working_directory": script.working_directory
            } for script in self.validation_scripts
        ]

    def _serialize_recovery_instructions(self) -> Optional[Dict]:
        if not self.recovery_instructions:
            return None
        return {
            "common_failures": self.recovery_instructions.common_failures,
            "rollback_commands": self.recovery_instructions.rollback_commands,
            "escalation_triggers": self.recovery_instructions.escalation_triggers,
            "alternative_approaches": self.recovery_instructions.alternative_approaches
        }

def create_task_template(task_id: str, title: str, task_type: TaskType, complexity: TaskComplexity) -> AtomicTask:
    """Create a basic task template with minimal required fields"""
    return AtomicTask(
        id=task_id,
        title=title,
        description=f"Template for {title}",
        task_type=task_type,
        complexity=complexity,
        estimated_hours=1.0 if complexity == TaskComplexity.SMALL else
                       5.0 if complexity == TaskComplexity.MEDIUM else 12.0
    )

def load_task_from_dict(data: Dict[str, Any]) -> AtomicTask:
    """Load task from dictionary (reverse of to_dict)"""
    # This would be the inverse of to_dict - implement as needed
    pass

if __name__ == "__main__":
    # Example usage
    example_task = create_task_template(
        "ATLAS-TEST-001",
        "Add unit tests for path_manager.py",
        TaskType.TEST_FIRST,
        TaskComplexity.MEDIUM
    )

    print("Example task schema:")
    print(json.dumps(example_task.to_dict(), indent=2))