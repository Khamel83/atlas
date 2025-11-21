#!/usr/bin/env python3
"""
Enhanced Task Manager for Atlas
Extends existing Agent OS task system with AI agent automation
"""

import json
import os
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path
from helpers.bulletproof_process_manager import get_manager, create_managed_process

class AtlasTaskManager:
    """Enhanced task manager that works with existing Agent OS structure"""

    def __init__(self, base_path: str = "/home/ubuntu/dev/atlas"):
        self.base_path = Path(base_path)
        self.task_files = [
            self.base_path / "dev_tasks.json",
            self.base_path / "master_todos.json",
            self.base_path / "unified_todos.json"
        ]
        self.agent_os_specs = self.base_path / ".agent-os" / "specs"

    def load_all_tasks(self) -> Dict[str, Any]:
        """Load tasks from all existing JSON files"""
        all_tasks = {}

        for task_file in self.task_files:
            if task_file.exists():
                try:
                    with open(task_file, 'r') as f:
                        tasks = json.load(f)
                        all_tasks.update(tasks)
                        print(f"Loaded {len(tasks)} tasks from {task_file.name}")
                except Exception as e:
                    print(f"Error loading {task_file}: {e}")

        return all_tasks

    def enhance_task_for_ai_agent(self, task_id: str, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Enhance existing task with AI agent context"""
        enhanced_task = task_data.copy()

        # Add AI agent context if missing
        if "ai_context" not in enhanced_task:
            enhanced_task["ai_context"] = self._generate_ai_context(task_data)

        # Add validation scripts if missing
        if "validation_scripts" not in enhanced_task:
            enhanced_task["validation_scripts"] = self._generate_validation_scripts(task_data)

        # Add recovery instructions if missing
        if "recovery_instructions" not in enhanced_task:
            enhanced_task["recovery_instructions"] = self._generate_recovery_instructions(task_data)

        return enhanced_task

    def _generate_ai_context(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate AI context for a task"""
        category = task_data.get("category", "general")

        context = {
            "required_files": self._get_required_files(task_data),
            "system_overview": "Atlas is a local-first content ingestion and cognitive amplification platform",
            "task_purpose": task_data.get("content", ""),
            "architectural_context": self._get_architectural_context(category),
            "success_patterns": [
                "Follow existing code patterns in the helpers/ directory",
                "Add comprehensive tests with 90%+ coverage",
                "Update documentation when adding new features",
                "Use type hints and proper error handling"
            ],
            "common_pitfalls": [
                "Not activating virtual environment before running commands",
                "Missing proper imports for new modules",
                "Not handling edge cases in error scenarios",
                "Forgetting to update configuration files"
            ]
        }

        return context

    def _get_required_files(self, task_data: Dict[str, Any]) -> List[str]:
        """Determine required files based on task content"""
        content = task_data.get("content", "").lower()
        files = []

        # Core Atlas files always needed
        files.extend([
            "helpers/config.py",
            "PROJECT_ROADMAP.md",
            ".agent-os/product/mission-lite.md"
        ])

        # Add specific files based on task content
        if "test" in content:
            files.extend([
                "tests/conftest.py",
                "pytest.ini"
            ])

        if "metadata" in content:
            files.append("helpers/metadata_manager.py")

        if "path" in content:
            files.append("helpers/path_manager.py")

        if "web" in content or "api" in content:
            files.append("web/app.py")

        return files

    def _get_architectural_context(self, category: str) -> str:
        """Get architectural context based on task category"""
        contexts = {
            "foundation": "Core infrastructure that all other components depend on",
            "feature": "User-facing functionality built on foundation components",
            "test": "Quality assurance ensuring system reliability and correctness",
            "documentation": "Knowledge capture and user guidance",
            "performance": "System optimization and resource efficiency"
        }

        return contexts.get(category, "General system component")

    def _generate_validation_scripts(self, task_data: Dict[str, Any]) -> List[Dict[str, str]]:
        """Generate validation scripts for task completion"""
        scripts = []
        content = task_data.get("content", "").lower()

        # Always run basic validation
        scripts.append({
            "name": "basic_validation",
            "command": "source venv/bin/activate && python -m pytest --tb=short",
            "description": "Run basic test suite to ensure no regressions"
        })

        # Add specific validations based on task type
        if "test" in content:
            scripts.append({
                "name": "coverage_check",
                "command": "source venv/bin/activate && python -m pytest --cov=helpers --cov-report=term-missing",
                "description": "Verify test coverage meets 90% requirement"
            })

        if "lint" in content or "format" in content:
            scripts.append({
                "name": "code_quality",
                "command": "source venv/bin/activate && python -m ruff check .",
                "description": "Check code quality and formatting"
            })

        return scripts

    def _generate_recovery_instructions(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate recovery instructions for common failures"""
        return {
            "common_failures": [
                {
                    "failure": "Import errors or module not found",
                    "solution": "Check virtual environment activation and PYTHONPATH"
                },
                {
                    "failure": "Tests failing after changes",
                    "solution": "Review test output, fix implementation, ensure all dependencies updated"
                },
                {
                    "failure": "Configuration errors",
                    "solution": "Verify .env file exists and has required variables"
                }
            ],
            "rollback_commands": [
                "git stash",
                "git reset --hard HEAD~1"
            ],
            "escalation_triggers": [
                "More than 3 consecutive failures",
                "Unable to understand task requirements",
                "External dependencies unavailable"
            ]
        }

    def create_agent_instruction_package(self, task_id: str) -> Dict[str, Any]:
        """Create complete instruction package for AI agent"""
        all_tasks = self.load_all_tasks()

        if task_id not in all_tasks:
            raise ValueError(f"Task {task_id} not found")

        task_data = all_tasks[task_id]
        enhanced_task = self.enhance_task_for_ai_agent(task_id, task_data)

        # Create complete instruction package
        package = {
            "task_id": task_id,
            "task_data": enhanced_task,
            "execution_instructions": self._create_execution_instructions(enhanced_task),
            "quality_gates": self._create_quality_gates(enhanced_task),
            "context_files": enhanced_task["ai_context"]["required_files"],
            "validation_scripts": enhanced_task["validation_scripts"],
            "recovery_instructions": enhanced_task["recovery_instructions"]
        }

        return package

    def _create_execution_instructions(self, task_data: Dict[str, Any]) -> List[str]:
        """Create step-by-step execution instructions"""
        return [
            "1. Read and understand task requirements",
            "2. Load required context files",
            "3. Examine existing code patterns and tests",
            "4. Plan implementation approach",
            "5. Implement solution following Atlas conventions",
            "6. Run validation scripts to verify success",
            "7. Update documentation if needed",
            "8. Commit changes with descriptive message"
        ]

    def _create_quality_gates(self, task_data: Dict[str, Any]) -> List[Dict[str, str]]:
        """Create quality gates that must pass before completion"""
        return [
            {
                "gate": "tests_pass",
                "description": "All tests must pass",
                "command": "python -m pytest",
                "required": True
            },
            {
                "gate": "code_quality",
                "description": "Code must meet quality standards",
                "command": "python -m ruff check .",
                "required": True
            },
            {
                "gate": "no_syntax_errors",
                "description": "No Python syntax errors",
                "command": "python -m py_compile",
                "required": True
            }
        ]

    def get_next_available_task(self, agent_capabilities: List[str] = None) -> Optional[str]:
        """Get next task ready for execution"""
        all_tasks = self.load_all_tasks()

        # Find pending tasks with no blocking dependencies
        for task_id, task_data in all_tasks.items():
            if task_data.get("status") == "pending":
                dependencies = task_data.get("dependencies", [])

                # Check if all dependencies are completed
                deps_completed = all(
                    all_tasks.get(dep_id, {}).get("status") == "completed"
                    for dep_id in dependencies
                )

                if deps_completed:
                    return task_id

        return None

def demo_enhanced_task_manager():
    """Demonstrate the enhanced task manager"""
    manager = AtlasTaskManager()

    print("🤖 Atlas Enhanced Task Manager Demo")
    print("=" * 40)

    # Load all tasks
    all_tasks = manager.load_all_tasks()
    print(f"📊 Total tasks loaded: {len(all_tasks)}")

    # Show status breakdown
    statuses = {}
    for task in all_tasks.values():
        status = task.get("status", "unknown")
        statuses[status] = statuses.get(status, 0) + 1

    print("\n📈 Task Status Breakdown:")
    for status, count in statuses.items():
        print(f"   {status}: {count}")

    # Get next available task
    next_task = manager.get_next_available_task()
    if next_task:
        print(f"\n🎯 Next available task: {next_task}")

        # Create instruction package
        package = manager.create_agent_instruction_package(next_task)
        print(f"📦 Instruction package created with {len(package['context_files'])} context files")
        print(f"✅ Quality gates: {len(package['quality_gates'])}")
        print(f"🔧 Validation scripts: {len(package['validation_scripts'])}")
    else:
        print("\n✅ No tasks available (all completed or blocked)")

if __name__ == "__main__":
    demo_enhanced_task_manager()