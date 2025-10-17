# Master Execution Controller

This system provides a single command that executes all 208 Atlas tasks automatically with dependency management, context loading, quality gates, and progress tracking.

## Single Command Execution

### **Primary Command**
```bash
/execute-atlas-production-system
```

This command:
1. **Validates Prerequisites** - Ensures all setup requirements are met
2. **Loads Task Database** - Imports all 208 tasks with dependencies
3. **Starts Execution Engine** - Begins automatic task execution
4. **Manages Dependencies** - Only starts tasks when prerequisites complete
5. **Handles Context** - Automatically loads required context for each task
6. **Validates Quality** - Runs quality gates after each task
7. **Tracks Progress** - Maintains real-time execution status
8. **Handles Failures** - Automatic recovery and error handling
9. **Updates GitHub** - Commits progress after each successful task

### **Command Options**
```bash
# Full execution (all 208 tasks)
/execute-atlas-production-system

# Start from specific task
/execute-atlas-production-system --start-from=5.3

# Execute specific phase only
/execute-atlas-production-system --phase=1

# Resume from last checkpoint
/execute-atlas-production-system --resume

# Dry run (validate without executing)
/execute-atlas-production-system --dry-run
```

## Automatic Task Management System

### **Task Database Structure**
```json
{
  "tasks": {
    "1.1": {
      "id": "1.1",
      "title": "Write tests for environment validation and configuration loading",
      "type": "TFI",
      "phase": 1,
      "estimated_hours": 2,
      "prerequisites": [],
      "blocks": ["1.2", "1.3", "1.4", "1.5"],
      "context_files": [
        "@.agent-os/product/mission-lite.md",
        "@.agent-os/product/tech-stack.md",
        "helpers/config.py",
        "tests/conftest.py"
      ],
      "acceptance_criteria": [
        "Tests written before implementation",
        "90%+ test coverage for new code",
        "Tests pass consistently",
        "Environment validation logic tested"
      ],
      "quality_gates": ["TFI_1", "TFI_2", "TFI_3", "UNIVERSAL_1", "UNIVERSAL_2"],
      "files_to_modify": ["tests/test_environment.py", "helpers/config.py"],
      "status": "pending"
    }
  },
  "dependencies": {
    "1.2": ["1.1"],
    "2.1": ["1.7"],
    "2.2": [],
    "blocking_tasks": ["2.2", "6.2", "11.8", "19.8"]
  },
  "execution_state": {
    "current_phase": 1,
    "active_tasks": [],
    "completed_tasks": [],
    "failed_tasks": [],
    "last_checkpoint": "2025-08-01T10:30:00Z"
  }
}
```

### **Dependency Resolution Engine**
```python
class DependencyResolver:
    def get_ready_tasks(self) -> List[TaskId]:
        """Return tasks ready for execution (all prerequisites complete)"""

    def get_blocked_tasks(self) -> List[TaskId]:
        """Return tasks blocked by failed dependencies"""

    def validate_execution_order(self) -> bool:
        """Ensure no circular dependencies exist"""

    def get_critical_path(self) -> List[TaskId]:
        """Return critical path tasks that block multiple other tasks"""
```

## Automatic Context Management

### **Context Auto-Loading System**
```python
class ContextLoader:
    def load_task_context(self, task_id: str) -> dict:
        """Automatically load all required context for a task"""
        task = self.task_db.get_task(task_id)
        context = {}

        # Load core context (always required)
        context['mission'] = self.read_file('@.agent-os/product/mission-lite.md')
        context['tech_stack'] = self.read_file('@.agent-os/product/tech-stack.md')
        context['spec_summary'] = self.read_file('@.agent-os/specs/.../spec-lite.md')

        # Load task-specific context
        for file_path in task.context_files:
            context[file_path] = self.read_file(file_path)

        # Load phase-specific context
        phase_context = self.get_phase_context(task.phase)
        context.update(phase_context)

        # Load dependency context (what previous tasks accomplished)
        for prereq_id in task.prerequisites:
            prereq_results = self.get_task_results(prereq_id)
            context[f'task_{prereq_id}_results'] = prereq_results

        return context

    def generate_task_prompt(self, task_id: str, context: dict) -> str:
        """Generate complete execution prompt with all context"""
        task = self.task_db.get_task(task_id)

        prompt = f"""
        # Task Execution: {task.title}

        ## Task Details
        - **ID**: {task.id}
        - **Type**: {task.type}
        - **Phase**: {task.phase}
        - **Estimated Time**: {task.estimated_hours} hours

        ## Context Loaded
        {self.format_context(context)}

        ## Requirements
        {self.format_acceptance_criteria(task.acceptance_criteria)}

        ## Quality Gates
        {self.format_quality_gates(task.quality_gates)}

        ## Files to Modify
        {task.files_to_modify}

        Execute this task following the Task Execution Framework methodology.
        """
        return prompt
```

### **Smart Context Caching**
- **Cache loaded files** to avoid re-reading same content
- **Update cache** when files change during execution
- **Context versioning** to track when context becomes stale
- **Selective context loading** based on task type and dependencies

## Automatic Quality Gate System

### **Quality Gate Executor**
```python
class QualityGateValidator:
    def validate_task_completion(self, task_id: str) -> QualityResult:
        """Run all quality gates for a completed task"""
        task = self.task_db.get_task(task_id)
        results = QualityResult()

        # Run universal quality gates
        results.add(self.validate_universal_gates(task))

        # Run task-type specific gates
        if task.type == "TFI":
            results.add(self.validate_tfi_gates(task))
        elif task.type == "CAS":
            results.add(self.validate_cas_gates(task))
        # ... etc

        # Run phase-specific gates
        results.add(self.validate_phase_gates(task))

        return results

    def validate_universal_gates(self, task: Task) -> GateResults:
        """Universal quality gates that all tasks must pass"""
        results = GateResults()

        # Gate 1: Requirements Validation
        results.add("requirements_met", self.check_acceptance_criteria(task))
        results.add("scope_respected", self.check_scope_boundaries(task))

        # Gate 2: Code Quality Standards
        results.add("type_annotations", self.run_mypy_check())
        results.add("code_formatting", self.run_black_check())
        results.add("import_organization", self.run_isort_check())

        # Gate 3: Testing Requirements
        results.add("test_coverage", self.check_test_coverage(task, min_coverage=90))
        results.add("test_reliability", self.run_tests_multiple_times(3))

        # Gate 4: Documentation Standards
        results.add("documentation_updated", self.check_documentation_sync(task))

        # Gate 5: Git Workflow Standards
        results.add("clean_commits", self.validate_git_history())
        results.add("github_sync", self.verify_github_push())

        return results
```

### **Automatic Quality Recovery**
```python
class QualityRecovery:
    def handle_quality_failure(self, task_id: str, failed_gates: List[str]) -> bool:
        """Attempt automatic recovery from quality gate failures"""

        for gate in failed_gates:
            if gate == "code_formatting":
                self.run_black_fix()
            elif gate == "import_organization":
                self.run_isort_fix()
            elif gate == "test_coverage":
                self.generate_missing_tests(task_id)
            elif gate == "documentation_updated":
                self.update_documentation(task_id)
            # ... etc

        # Re-run quality gates after fixes
        return self.validate_task_completion(task_id).all_passed()
```

## Progress Tracking & Recovery

### **Execution State Management**
```python
class ExecutionTracker:
    def save_checkpoint(self):
        """Save current execution state"""
        state = {
            'timestamp': datetime.utcnow().isoformat(),
            'completed_tasks': self.completed_tasks,
            'failed_tasks': self.failed_tasks,
            'active_tasks': self.active_tasks,
            'current_phase': self.current_phase,
            'context_cache': self.context_cache.serialize(),
            'quality_results': self.quality_results
        }
        self.save_state(state)

    def load_checkpoint(self) -> bool:
        """Resume from last checkpoint"""
        state = self.load_state()
        if state:
            self.completed_tasks = state['completed_tasks']
            self.failed_tasks = state['failed_tasks']
            self.active_tasks = state['active_tasks']
            self.current_phase = state['current_phase']
            self.context_cache.deserialize(state['context_cache'])
            return True
        return False

    def generate_progress_report(self) -> str:
        """Generate human-readable progress report"""
        total_tasks = 208
        completed = len(self.completed_tasks)
        failed = len(self.failed_tasks)
        remaining = total_tasks - completed - failed

        return f"""
        # Atlas Production System - Execution Progress

        **Overall Progress**: {completed}/{total_tasks} tasks ({completed/total_tasks*100:.1f}%)

        ## Phase Breakdown
        {self.generate_phase_breakdown()}

        ## Current Status
        - **Active Tasks**: {len(self.active_tasks)}
        - **Completed**: {completed}
        - **Failed**: {failed}
        - **Remaining**: {remaining}

        ## Next Steps
        {self.get_next_ready_tasks()}

        ## Estimated Completion
        {self.estimate_completion_time()}
        """
```

### **Failure Recovery System**
```python
class FailureRecovery:
    def handle_task_failure(self, task_id: str, error: Exception) -> RecoveryAction:
        """Determine recovery action for task failure"""

        if isinstance(error, DependencyError):
            return RecoveryAction.WAIT_FOR_DEPENDENCY
        elif isinstance(error, QualityGateError):
            return RecoveryAction.ATTEMPT_QUALITY_FIX
        elif isinstance(error, NetworkError):
            return RecoveryAction.RETRY_WITH_BACKOFF
        elif isinstance(error, ConfigurationError):
            return RecoveryAction.RECONFIGURE_ENVIRONMENT
        else:
            return RecoveryAction.MANUAL_INTERVENTION_REQUIRED

    def attempt_recovery(self, task_id: str, action: RecoveryAction) -> bool:
        """Execute recovery action"""
        if action == RecoveryAction.RETRY_WITH_BACKOFF:
            time.sleep(self.calculate_backoff(task_id))
            return self.retry_task(task_id)
        elif action == RecoveryAction.ATTEMPT_QUALITY_FIX:
            return self.quality_recovery.fix_quality_issues(task_id)
        # ... etc
```

## GitHub Integration & Automation

### **Automatic Git Workflow**
```python
class GitAutomation:
    def commit_task_completion(self, task_id: str, results: TaskResult):
        """Automatically commit task completion with proper message"""

        # Stage modified files
        for file_path in results.modified_files:
            self.git.add(file_path)

        # Generate commit message
        commit_msg = f"""
        task {task_id}: {results.task_title}

        - Completed: {results.completion_time}
        - Quality Gates: {len(results.passed_gates)}/{len(results.total_gates)} passed
        - Files Modified: {len(results.modified_files)}
        - Test Coverage: {results.test_coverage}%

        🤖 Generated with [Claude Code](https://claude.ai/code)

        Co-Authored-By: Claude <noreply@anthropic.com>
        """

        # Commit and push
        self.git.commit(commit_msg)
        self.git.push()

    def update_progress_documentation(self):
        """Update README and progress docs with current status"""
        progress = self.tracker.generate_progress_report()

        # Update README with progress
        self.update_readme_progress_section(progress)

        # Update roadmap with completed tasks
        self.update_roadmap_completion_status()

        # Commit documentation updates
        self.commit_documentation_updates()
```

## Execution Command Implementation

### **Master Controller CLI**
```python
#!/usr/bin/env python3
"""
Master Execution Controller for Atlas Production System
Usage: python execute_atlas.py [options]
"""

class AtlasExecutionController:
    def __init__(self):
        self.task_db = TaskDatabase()
        self.dependency_resolver = DependencyResolver()
        self.context_loader = ContextLoader()
        self.quality_validator = QualityGateValidator()
        self.progress_tracker = ExecutionTracker()
        self.git_automation = GitAutomation()

    def execute_all_tasks(self, start_from=None, phase=None, resume=False):
        """Execute all 208 tasks automatically"""

        # Initialize execution
        if resume:
            self.progress_tracker.load_checkpoint()
        else:
            self.validate_prerequisites()
            self.task_db.load_all_tasks()

        # Main execution loop
        while not self.all_tasks_complete():
            # Get ready tasks
            ready_tasks = self.dependency_resolver.get_ready_tasks()

            # Execute ready tasks (potentially in parallel)
            for task_id in ready_tasks:
                success = self.execute_single_task(task_id)
                if not success:
                    self.handle_failure(task_id)

            # Save checkpoint after each batch
            self.progress_tracker.save_checkpoint()

            # Update progress
            self.generate_progress_update()

        # Final validation
        self.validate_complete_system()
        self.generate_final_report()

    def execute_single_task(self, task_id: str) -> bool:
        """Execute a single task with full automation"""

        # Load context
        context = self.context_loader.load_task_context(task_id)

        # Generate execution prompt
        prompt = self.context_loader.generate_task_prompt(task_id, context)

        # Execute task (this would call the actual AI agent)
        result = self.execute_task_with_ai_agent(prompt, task_id)

        # Validate quality gates
        quality_result = self.quality_validator.validate_task_completion(task_id)

        if quality_result.all_passed():
            # Commit changes
            self.git_automation.commit_task_completion(task_id, result)

            # Mark task complete
            self.task_db.mark_task_complete(task_id)

            # Update progress
            self.progress_tracker.task_completed(task_id)

            return True
        else:
            # Attempt quality recovery
            recovery_success = self.quality_validator.attempt_recovery(task_id, quality_result)
            return recovery_success
```

This Master Execution Controller provides the **single command that executes all 208 tasks automatically** with full dependency management, context loading, quality validation, and progress tracking.