# OOS v2 Vision: Task Orchestration Framework

## Overview

The vision for OOS v2 is to transform it from a collection of utility scripts into an intelligent task orchestration framework that automatically decomposes projects into executable hierarchies and provides bidirectional status updates.

## Core Architecture

### Four-Level Hierarchy

1. **Projects** (Mission/Vision/Constraints)
   - Complete deliverables
   - Business objectives
   - Success criteria
   - Resource constraints

2. **Workflows** (Business Goals)
   - Collections of orchestrations
   - Business process flows
   - Dependency management
   - Progress tracking

3. **Orchestrations** (Auto-generated Task Groups)
   - Series of related tasks
   - Execution coordination
   - Error handling
   - Resource management

4. **Tasks** (Simple If/Then Operations)
   - Atomic operations
   - "If condition then action else failure"
   - Discrete, executable units
   - Clear success/failure states

### Key Innovation: Bidirectional Flow

**Top-Down (Decomposition):**
- Project mission → Auto-generates workflows
- Workflow goals → Auto-generates orchestrations
- Orchestration needs → Auto-generates tasks

**Bottom-Up (Rollup):**
- Task completion → Updates orchestration status
- Orchestration completion → Updates workflow status
- Workflow completion → Updates project status

### Entry Point Flexibility

Users can enter at any level:
- **Task Level**: "Run this specific task" (assumes project/workflow/orchestration exist)
- **Orchestration Level**: "Accomplish this goal" (auto-generates required tasks)
- **Workflow Level**: "Achieve this business outcome" (auto-generates orchestrations + tasks)
- **Project Level**: "Deliver this complete solution" (auto-generates full hierarchy)

## Implementation Strategy

### Phase 1: Framework Foundation
```python
# Core data structures
class TaskSpec:
    condition: str  # "if this"
    action: str     # "then that"
    failure: str    # "else failure"

class OrchestrationSpec:
    goal: str
    tasks: List[TaskSpec]
    execution_order: List[str]

class WorkflowSpec:
    business_goal: str
    orchestrations: List[OrchestrationSpec]
    dependencies: Dict[str, List[str]]

class ProjectSpec:
    mission: str
    vision: str
    constraints: List[str]
    workflows: List[WorkflowSpec]
```

### Phase 2: AI-Powered Decomposition
```python
class ProjectDecomposer:
    def workflows_from_mission(self, mission: str) -> List[WorkflowSpec]
    def orchestrations_from_goal(self, goal: str) -> List[OrchestrationSpec]
    def tasks_from_orchestration(self, orchestration: str) -> List[TaskSpec]
```

### Phase 3: Universal Application
The framework should work for:
- **Technical Projects**: "Build authentication system"
- **Business Projects**: "Buy house in Fort Collins"
- **Personal Projects**: "Plan vacation to Japan"
- **Development Projects**: "Create e-commerce website"

## Matrix-Based State Management

Think of it as a dynamic spreadsheet where each level tracks:

- **Project Level**: Overall progress, budget, timeline
- **Workflow Level**: Business objectives completion, inter-workflow dependencies
- **Orchestration Level**: Task group status, resource allocation
- **Task Level**: Individual execution status, error states

Each level up aggregates information from the level below, and each level down receives requirements from the level above.

## Benefits Over Current OOS

### Current OOS (v1) Problems:
- 809-line scripts doing simple file operations
- Manual coordination between components
- No automatic decomposition or rollup
- Each script reinvents coordination logic

### OOS v2 Benefits:
- **5-line tasks** instead of 809-line monsters
- **Automatic decomposition** from high-level goals
- **Bidirectional updates** - complete a task, project auto-updates
- **Universal pattern** - works for any project type
- **AI-enhanced** - intelligent task generation using Archon
- **Self-optimizing** - learns from execution patterns

## Real-World Example

**Current OOS v1:**
```bash
# User manually runs 5 separate scripts
./template_manager.sh create my-project
./integrate_to_parent.sh
./security_audit.sh my-project
./diagnose.sh my-project
./performance_monitor.sh my-project
```

**OOS v2:**
```bash
# Single entry point, auto-decomposition
./oos project create "my-project" --mission "web application with auth"
# Auto-generates: workflows → orchestrations → tasks
# Executes all, provides unified status
```

## Next Steps for Implementation

1. **Create framework core** - data structures and decomposition logic
2. **Integrate with existing OOS** - migrate current scripts to task format
3. **Add AI decomposition** - use Archon for intelligent breakdown
4. **Build real-world examples** - demonstrate project → task decomposition
5. **Create migration tools** - convert v1 usage patterns to v2 framework

## Relationship to Existing OOS

The current OOS v1 becomes the "task library" for v2:
- Simple scripts (`simple_diagnose.sh`, etc.) become reusable tasks
- Complex scripts are broken down into orchestration specs
- Integration patterns become workflow templates
- The framework provides the intelligence to compose them automatically

This maintains OOS's "5 lines instead of 500" philosophy while adding the hierarchical intelligence you envisioned.