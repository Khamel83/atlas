#!/usr/bin/env python3
"""
Simple task picker for Qwen autonomous execution
Returns the next ready task that has no dependencies or all dependencies done
"""
import json

# Manual list of ready tasks (no dependencies or dependencies completed)
READY_TASKS = [
    {
        "id": "ATLAS-COMPLETE-005",
        "slug": "validate-core-features",
        "title": "Validate all cognitive features and infrastructure work",
        "priority": "medium"
    },
    {
        "id": "ATLAS-COMPLETE-030",
        "slug": "make-all-tasks-qwen-compatible",
        "title": "Restructure all tasks for autonomous Qwen execution",
        "priority": "critical"
    }
]

def main():
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "list":
        print(json.dumps(READY_TASKS, indent=2))
    else:
        # Return first ready task
        if READY_TASKS:
            print(json.dumps([READY_TASKS[0]]))
        else:
            print("NO-READY-TASK", file=sys.stderr)
            sys.exit(3)

if __name__ == "__main__":
    main()