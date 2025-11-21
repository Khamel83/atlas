#!/usr/bin/env python3
"""
Demonstration of how another AI agent would execute Atlas tasks
Shows the complete context and instructions an agent would receive
"""

import json
from enhanced_task_manager import AtlasTaskManager

def create_agent_context_package(task_id: str = None):
    """Create a complete context package for an AI agent"""
    manager = AtlasTaskManager()

    # Get next available task or specific task
    if not task_id:
        task_id = manager.get_next_available_task()
        if not task_id:
            print("No tasks available for execution")
            return None

    # Create instruction package
    package = manager.create_agent_instruction_package(task_id)

    return package

def format_agent_instructions(package: dict) -> str:
    """Format instructions for an AI agent"""
    task_data = package["task_data"]

    instructions = f"""
# ATLAS TASK EXECUTION INSTRUCTIONS
**Task ID**: {package['task_id']}
**Title**: {task_data.get('content', 'Unknown')}
**Priority**: {task_data.get('priority', 'medium')}
**Estimated Time**: {task_data.get('estimated_time', 'unknown')} minutes
**Category**: {task_data.get('category', 'general')}

## SYSTEM OVERVIEW
{task_data.get('ai_context', {}).get('system_overview', 'Atlas cognitive amplification platform')}

## TASK PURPOSE
{task_data.get('ai_context', {}).get('task_purpose', task_data.get('content', ''))}

## ARCHITECTURAL CONTEXT
{task_data.get('ai_context', {}).get('architectural_context', 'General system component')}

## REQUIRED CONTEXT FILES
Before starting, read these files to understand the system:
"""

    for file_path in package.get("context_files", []):
        instructions += f"- `{file_path}`\n"

    instructions += f"""
## EXECUTION STEPS
"""

    for step in package.get("execution_instructions", []):
        instructions += f"{step}\n"

    instructions += f"""
## SUCCESS PATTERNS (Follow These)
"""

    for pattern in task_data.get('ai_context', {}).get('success_patterns', []):
        instructions += f"✅ {pattern}\n"

    instructions += f"""
## COMMON PITFALLS (Avoid These)
"""

    for pitfall in task_data.get('ai_context', {}).get('common_pitfalls', []):
        instructions += f"⚠️ {pitfall}\n"

    instructions += f"""
## VALIDATION SCRIPTS
Run these to verify your work:
"""

    for script in package.get("validation_scripts", []):
        instructions += f"""
**{script['name']}**:
```bash
{script['command']}
```
{script.get('description', '')}
"""

    instructions += f"""
## QUALITY GATES
All of these must pass before marking task complete:
"""

    for gate in package.get("quality_gates", []):
        required = "REQUIRED" if gate.get("required") else "OPTIONAL"
        instructions += f"- **{gate['gate']}** ({required}): {gate['description']}\n"
        instructions += f"  Command: `{gate['command']}`\n"

    instructions += f"""
## RECOVERY INSTRUCTIONS
If something goes wrong:

**Common Failures:**
"""

    for failure in task_data.get('recovery_instructions', {}).get('common_failures', []):
        instructions += f"- **{failure['failure']}**: {failure['solution']}\n"

    instructions += f"""
**Emergency Rollback:**
```bash
{'; '.join(task_data.get('recovery_instructions', {}).get('rollback_commands', []))}
```

## COMPLETION CRITERIA
Mark task as complete only when:
1. All validation scripts pass
2. All quality gates are satisfied
3. Code follows Atlas conventions
4. Documentation is updated (if applicable)
5. Changes are committed to git

**Dependencies**: {', '.join(task_data.get('dependencies', [])) or 'None'}
**Blocks**: {', '.join(task_data.get('blocks', [])) or 'None'}
"""

    return instructions

def demo_agent_task_package():
    """Show what an AI agent would receive for task execution"""
    print("🤖 AI Agent Task Execution Demo")
    print("=" * 50)

    # Create context package
    package = create_agent_context_package()

    if not package:
        return

    # Format instructions
    instructions = format_agent_instructions(package)

    print("📋 COMPLETE AGENT INSTRUCTIONS:")
    print("=" * 50)
    print(instructions)

    # Show JSON package structure
    print("\n" + "=" * 50)
    print("📦 FULL CONTEXT PACKAGE (JSON):")
    print("=" * 50)
    print(json.dumps({
        "task_id": package["task_id"],
        "priority": package["task_data"].get("priority"),
        "estimated_time": package["task_data"].get("estimated_time"),
        "dependencies": package["task_data"].get("dependencies"),
        "validation_count": len(package["validation_scripts"]),
        "quality_gates_count": len(package["quality_gates"]),
        "context_files_count": len(package["context_files"])
    }, indent=2))

def show_available_tasks():
    """Show all available tasks ready for execution"""
    manager = AtlasTaskManager()
    all_tasks = manager.load_all_tasks()

    print("📋 Available Tasks for AI Agent Execution")
    print("=" * 50)

    available_count = 0
    for task_id, task_data in all_tasks.items():
        if task_data.get("status") == "pending":
            dependencies = task_data.get("dependencies", [])

            # Check if dependencies are met
            deps_completed = all(
                all_tasks.get(dep_id, {}).get("status") == "completed"
                for dep_id in dependencies
            )

            if deps_completed:
                available_count += 1
                priority = task_data.get("priority", "medium")
                category = task_data.get("category", "general")
                time_est = task_data.get("estimated_time", "unknown")

                print(f"🎯 {task_id}")
                print(f"   Title: {task_data.get('content', 'Unknown')}")
                print(f"   Priority: {priority} | Category: {category} | Time: {time_est}min")
                print(f"   Dependencies: {len(dependencies)} (all met)")
                print()

    print(f"📊 Total available tasks: {available_count}")

if __name__ == "__main__":
    print("Choose demo mode:")
    print("1. Show complete agent instruction package")
    print("2. Show all available tasks")
    print()

    choice = input("Enter choice (1 or 2): ").strip()

    if choice == "1":
        demo_agent_task_package()
    elif choice == "2":
        show_available_tasks()
    else:
        print("Running both demos...")
        show_available_tasks()
        print("\n" + "="*80 + "\n")
        demo_agent_task_package()