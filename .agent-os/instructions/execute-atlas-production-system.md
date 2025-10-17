---
description: Execute All 208 Atlas Production Tasks Automatically
globs:
alwaysApply: false
version: 1.0
encoding: UTF-8
---

# Execute Atlas Production System

<ai_meta>
  <rules>Execute all 208 tasks sequentially with dependency management and quality gates</rules>
  <format>UTF-8, LF, 2-space indent, automated execution</format>
</ai_meta>

## Overview

Execute all 208 Atlas production tasks automatically from current state to fully production-ready system. This command handles dependency resolution, context loading, quality gates, GitHub automation, and progress tracking.

<execution_flow>

<step number="1" name="initialization">

### Step 1: System Initialization

<step_metadata>
  <validates>Prerequisites and environment setup</validates>
  <loads>Task database and execution state</loads>
</step_metadata>

<prerequisite_validation>
  <required_files>
    - @.agent-os/specs/2025-08-01-atlas-production-ready-system/tasks.md
    - @.agent-os/specs/2025-08-01-atlas-production-ready-system/sub-specs/dependency-map.md
    - @.agent-os/specs/2025-08-01-atlas-production-ready-system/sub-specs/prerequisites-setup-guide.md
  </required_files>
  <environment_checks>
    - Python 3.9+ available
    - Git repository initialized
    - Virtual environment activated
    - Development dependencies installed
  </environment_checks>
</prerequisite_validation>

<initialization_tasks>
  1. **Load Task Database**: Parse all 208 tasks from specification
  2. **Build Dependency Graph**: Create task dependency mapping
  3. **Validate Environment**: Ensure all prerequisites are met
  4. **Initialize Progress Tracker**: Set up execution state management
  5. **Configure Quality Gates**: Load quality validation system
  6. **Setup Git Automation**: Prepare automated commit workflow
</initialization_tasks>

<instructions>
  ACTION: Validate all prerequisites are met
  LOAD: Complete task database from specifications
  BUILD: Dependency resolution system
  INITIALIZE: Progress tracking and quality systems
</instructions>

</step>

<step number="2" name="execution_planning">

### Step 2: Execution Planning

<step_metadata>
  <analyzes>Task dependencies and execution order</analyzes>
  <creates>Optimized execution plan</creates>
</step_metadata>

<planning_analysis>
  <critical_path_identification>
    - Task 2.2: pytest configuration fix (blocks ALL development)
    - Task 6.2: Redis installation (blocks performance features)
    - Task 11.8: API framework (blocks integration features)
    - Task 19.8: Deployment automation (blocks production readiness)
  </critical_path_identification>

  <parallel_opportunities>
    - Phase 1: Tasks 3, 4, 5 can run simultaneously
    - Phase 3: Tasks 13, 14, 15 (API endpoints) can be parallel
    - Phase 4: Tasks 17, 18 (production concerns) can be parallel
  </parallel_opportunities>

  <resource_planning>
    - External service dependencies (OpenRouter, Redis, Meilisearch)
    - Hardware requirements (Raspberry Pi for deployment testing)
    - Network dependencies (content ingestion testing)
  </resource_planning>
</planning_analysis>

<execution_strategy>
  <phase_approach>
    SEQUENTIAL: Phases must complete in order (1→2→3→4→5→6)
    PARALLEL: Within phases, execute independent tasks simultaneously
    BLOCKING: Critical path tasks get priority execution
    RECOVERY: Failed tasks trigger automatic recovery attempts
  </phase_approach>
</execution_strategy>

<instructions>
  ACTION: Analyze all task dependencies
  IDENTIFY: Critical path and blocking tasks
  PLAN: Optimal execution order with parallelization
  PREPARE: Resource and recovery strategies
</instructions>

</step>

<step number="3" name="automated_execution">

### Step 3: Automated Task Execution

<step_metadata>
  <executes>All 208 tasks with full automation</executes>
  <manages>Dependencies, context, quality, and progress</manages>
</step_metadata>

<execution_loop>
  WHILE tasks_remaining():

    # Get ready tasks (prerequisites complete)
    ready_tasks = dependency_resolver.get_ready_tasks()

    FOR EACH task_id in ready_tasks:

      # Load complete context for task
      context = context_loader.load_task_context(task_id)

      # Generate execution prompt with context
      prompt = context_loader.generate_task_prompt(task_id, context)

      # Execute task using Agent OS execute-task workflow
      result = execute_single_task(task_id, prompt)

      # Validate quality gates
      quality_result = quality_validator.validate_task_completion(task_id)

      IF quality_result.all_passed():
        # Commit changes to Git
        git_automation.commit_task_completion(task_id, result)

        # Mark task complete
        task_database.mark_task_completed(task_id, result)

        # Update progress tracking
        progress_tracker.task_completed(task_id)

      ELSE:
        # Attempt automatic quality recovery
        recovery_success = quality_recovery.attempt_fixes(task_id, quality_result)

        IF NOT recovery_success:
          # Mark task as failed, continue with other tasks
          task_database.mark_task_failed(task_id, quality_result.failures)

    # Save execution checkpoint
    progress_tracker.save_checkpoint()

    # Generate progress report
    progress_report = progress_tracker.generate_progress_report()

    # Update documentation
    git_automation.update_progress_documentation(progress_report)

</execution_loop>

<task_execution_detail>
  <context_loading>
    CORE_CONTEXT: mission-lite.md, tech-stack.md, spec-lite.md
    TASK_CONTEXT: Files specific to current task
    PHASE_CONTEXT: Phase-specific technical specifications
    DEPENDENCY_CONTEXT: Results from prerequisite tasks
  </context_loading>

  <quality_validation>
    UNIVERSAL_GATES: Requirements, code quality, testing, documentation, git workflow
    TYPE_SPECIFIC_GATES: TFI, CAS, IAC, or DAP specific validation
    PHASE_GATES: Phase-specific quality requirements
    AUTOMATIC_RECOVERY: Attempt fixes for common quality failures
  </quality_validation>

  <git_automation>
    COMMIT_MESSAGE: Structured commit with task ID, results, and quality metrics
    BRANCH_MANAGEMENT: Feature branches for complex tasks, direct commits for simple ones
    PROGRESS_UPDATES: Automatic README and documentation updates
    GITHUB_SYNC: Push all changes immediately after successful completion
  </git_automation>
</task_execution_detail>

<instructions>
  ACTION: Execute main automation loop
  MANAGE: Dependencies, context, quality, and progress for each task
  HANDLE: Failures with automatic recovery and continuation
  TRACK: Complete progress with real-time updates
</instructions>

</step>

<step number="4" name="progress_monitoring">

### Step 4: Progress Monitoring & Recovery

<step_metadata>
  <monitors>Real-time execution progress and system health</monitors>
  <handles>Failures, blockers, and recovery scenarios</handles>
</step_metadata>

<monitoring_systems>
  <progress_tracking>
    TASK_STATUS: pending → in_progress → completed/failed
    PHASE_PROGRESS: Completion percentage by phase
    QUALITY_METRICS: Test coverage, code quality scores
    TIME_TRACKING: Actual vs estimated completion times
  </progress_tracking>

  <failure_detection>
    DEPENDENCY_FAILURES: Tasks blocked by failed prerequisites
    QUALITY_GATE_FAILURES: Tasks failing validation requirements
    EXTERNAL_SERVICE_FAILURES: API or service connectivity issues
    RESOURCE_CONSTRAINTS: Memory, disk, or network limitations
  </failure_detection>

  <recovery_strategies>
    RETRY_WITH_BACKOFF: Temporary failures get automatic retry
    QUALITY_AUTO_FIX: Common quality issues fixed automatically
    DEPENDENCY_SKIP: Continue with other tasks when blocked
    MANUAL_INTERVENTION: Complex failures flagged for human review
  </recovery_strategies>
</monitoring_systems>

<progress_reporting>
  <real_time_updates>
    CONSOLE_OUTPUT: Live progress updates during execution
    PROGRESS_PERCENTAGE: Overall completion status
    CURRENT_TASK: Which task is currently executing
    ESTIMATED_COMPLETION: Time remaining based on current pace
  </real_time_updates>

  <detailed_reports>
    PHASE_BREAKDOWN: Progress by each of 6 phases
    QUALITY_SUMMARY: Overall quality metrics and trends
    FAILURE_ANALYSIS: Failed tasks with root cause analysis
    PERFORMANCE_METRICS: Execution speed and efficiency
  </detailed_reports>
</progress_reporting>

<instructions>
  ACTION: Monitor execution progress continuously
  DETECT: Failures and blockers as they occur
  RECOVER: Automatically handle common failure scenarios
  REPORT: Provide clear progress updates and status
</instructions>

</step>

<step number="5" name="completion_validation">

### Step 5: System Completion Validation

<step_metadata>
  <validates>Complete system functionality and production readiness</validates>
  <certifies>All 208 tasks completed successfully</certifies>
</step_metadata>

<completion_criteria>
  <task_completion>
    ALL_TASKS_COMPLETE: 208 tasks marked as completed
    NO_FAILED_TASKS: All failures resolved or acceptable
    QUALITY_GATES_PASSED: All quality validation successful
    GIT_SYNC_COMPLETE: All changes committed and pushed
  </task_completion>

  <system_validation>
    END_TO_END_TESTING: Complete system functionality verified
    PERFORMANCE_VALIDATION: System meets performance requirements
    PRODUCTION_READINESS: Deployment and operational procedures verified
    DOCUMENTATION_COMPLETE: All documentation accurate and complete
  </system_validation>

  <final_deliverables>
    PRODUCTION_SYSTEM: Fully functional Atlas running on target hardware
    COMPLETE_API: REST API with authentication and comprehensive endpoints
    AUTOMATION_WORKING: GitHub automation and CI/CD pipeline functional
    DOCUMENTATION_SET: Complete setup, usage, and maintenance documentation
  </final_deliverables>
</completion_criteria>

<final_report_generation>
  <executive_summary>
    COMPLETION_STATUS: Overall success/failure status
    TASK_STATISTICS: Completed, failed, and skipped task counts
    QUALITY_METRICS: Final test coverage, code quality, and performance
    TIME_ANALYSIS: Actual vs estimated completion time
  </executive_summary>

  <technical_summary>
    ARCHITECTURE_OVERVIEW: Final system architecture and components
    PERFORMANCE_BENCHMARKS: System performance on target hardware
    SECURITY_VALIDATION: Security measures implemented and tested
    OPERATIONAL_PROCEDURES: Deployment, monitoring, and maintenance
  </technical_summary>

  <handoff_documentation>
    SYSTEM_STATUS: Current state and functionality
    MAINTENANCE_PROCEDURES: How to maintain and extend the system
    TROUBLESHOOTING_GUIDE: Common issues and their solutions
    FUTURE_ROADMAP: Potential enhancements and improvements
  </handoff_documentation>
</final_report_generation>

<instructions>
  ACTION: Validate complete system functionality
  VERIFY: All tasks completed with quality standards met
  GENERATE: Comprehensive final report and documentation
  CERTIFY: System ready for production use
</instructions>

</step>

</execution_flow>

## Error Handling

<error_scenarios>
  <scenario name="critical_task_failure">
    <condition>Critical path task fails (e.g., pytest setup, Redis installation)</condition>
    <action>Attempt automatic recovery, escalate to manual intervention if needed</action>
  </scenario>
  <scenario name="external_service_unavailable">
    <condition>OpenRouter, GitHub, or other external service unreachable</condition>
    <action>Continue with tasks that don't require the service, retry periodically</action>
  </scenario>
  <scenario name="quality_gate_failures">
    <condition>Tasks consistently fail quality validation</condition>
    <action>Automatic quality fixes, then manual review if fixes don't work</action>
  </scenario>
  <scenario name="resource_constraints">
    <condition>System runs out of memory, disk space, or network bandwidth</condition>
    <action>Cleanup temporary files, optimize resource usage, alert for manual intervention</action>
  </scenario>
</error_scenarios>

## Execution Summary

<final_checklist>
  <verify>
    - [ ] All 208 tasks executed with dependency management
    - [ ] Quality gates validated for each completed task
    - [ ] GitHub automation working throughout execution
    - [ ] Progress tracking and reporting functional
    - [ ] System validated as production-ready
    - [ ] Complete documentation generated
    - [ ] Handoff materials prepared for future maintenance
  </verify>
</final_checklist>

<success_criteria>
  <primary_objectives>
    - Complete Atlas production system deployed and functional
    - All cognitive amplification features working as designed
    - REST API available for integration with other personal projects
    - Automated deployment and maintenance procedures in place
  </primary_objectives>

  <quality_standards>
    - 90%+ test coverage across all code
    - All quality gates passing for production readiness
    - Comprehensive documentation for setup and maintenance
    - GitHub automation supporting future development cycles
  </quality_standards>
</success_criteria>

This automated execution system transforms Atlas from its current functional state into a fully production-ready personal cognitive amplification platform through systematic execution of all 208 planned tasks.