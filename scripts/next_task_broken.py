#!/usr/bin/env python3
import re, sys, json, pathlib, yaml
from collections import defaultdict

ROOT = pathlib.Path(__file__).resolve().parent.parent
TASKS_MD = ROOT / "tasks.md"

HDR = re.compile(r"^### \*\*(?P<id>ATLAS-COMPLETE-\d+):\s*(?P<title>[^*]+)\*\*$")

PRIO_ORDER = {"P0":0,"P1":1,"P2":2,"P3":3}
STATUS_DONE = {"done", "completed"}
STATUS_READY = {"todo","in_progress"}

def slug(s):
    s = s.lower().strip()
    s = re.sub(r"[^a-z0-9]+","-",s).strip("-")
    return s[:60] or "task"

def parse_tasks(text):
    lines = text.splitlines()
    tasks = []
    current_task = None
    in_yaml_block = False
    yaml_lines = []

    for line in lines:
        # Check for task header
        m = HDR.match(line.strip())
        if m:
            # Save previous task if exists
            if current_task and yaml_lines:
                try:
                    yaml_content = '\n'.join(yaml_lines)
                    yaml_data = yaml.safe_load(yaml_content)
                    if yaml_data:
                        current_task.update(yaml_data)
                        # Normalize fields
                        current_task["status"] = current_task.get("status", "todo").strip().lower()
                        deps = current_task.get("depends_on", [])
                        if isinstance(deps, str):
                            deps = [d.strip() for d in deps.split(",") if d.strip()]
                        elif deps is None:
                            deps = []
                        current_task["deps"] = deps
                        current_task["priority"] = current_task.get("priority", "P2").upper().strip()
                        tasks.append(current_task)
                except yaml.YAMLError:
                    pass  # Skip malformed YAML

            # Start new task
            current_task = {
                "id": m.group("id").strip(),
                "title": m.group("title").strip(),
                "slug": slug(m.group("title"))
            }
            in_yaml_block = False
            yaml_lines = []

        # Check for YAML block start
        elif line.strip() == "```yaml" and current_task:
            in_yaml_block = True
            yaml_lines = []

        # Check for YAML block end
        elif line.strip() == "```" and in_yaml_block:
            in_yaml_block = False

        # Collect YAML lines
        elif in_yaml_block:
            yaml_lines.append(line)

    # Don't forget the last task
    if current_task and yaml_lines:
        try:
            yaml_content = '\n'.join(yaml_lines)
            yaml_data = yaml.safe_load(yaml_content)
            if yaml_data:
                current_task.update(yaml_data)
                current_task["status"] = current_task.get("status", "todo").strip().lower()
                deps = current_task.get("depends_on", [])
                if isinstance(deps, str):
                    deps = [d.strip() for d in deps.split(",") if d.strip()]
                elif deps is None:
                    deps = []
                current_task["deps"] = deps
                current_task["priority"] = current_task.get("priority", "P2").upper().strip()
                tasks.append(current_task)
        except yaml.YAMLError:
            pass

    return tasks

def topo_ready(tasks):
    by_id = {t["id"]: t for t in tasks}
    done = {t["id"] for t in tasks if t.get("status", "todo") in STATUS_DONE}

    # Find tasks that are ready (all dependencies done)
    runnable = []
    for t in tasks:
        if t.get("status", "todo") in STATUS_READY:
            deps = t.get("deps", [])
            if all(d in done for d in deps):
                runnable.append(t)

    # Sort by priority
    def score(t):
        prio = PRIO_ORDER.get(t.get("priority", "P2"), 2)
        return prio

    runnable.sort(key=score)
    return runnable

def pick(tasks, n=1):
    ready = topo_ready(tasks)
    return ready[:n]

def main():
    if not TASKS_MD.exists():
        print("tasks.md not found", file=sys.stderr)
        sys.exit(2)

    tasks = parse_tasks(TASKS_MD.read_text(encoding="utf-8"))

    if len(sys.argv) == 1 or sys.argv[1] in {"pick","next"}:
        n = int(sys.argv[2]) if len(sys.argv) > 2 else 1
        sel = pick(tasks, n=n)
        if not sel:
            print("NO-READY-TASK", file=sys.stderr)
            sys.exit(3)

        # Return machine-friendly JSON for agents
        out = [{
            "id": t["id"],
            "slug": t["slug"],
            "title": t["title"],
            "priority": t.get("priority", "P2")
        } for t in sel]
        print(json.dumps(out))

    elif sys.argv[1] == "list":
        out = [{
            "id": t["id"],
            "title": t["title"],
            "status": t.get("status", "todo"),
            "deps": t.get("deps", []),
            "priority": t.get("priority", "P2")
        } for t in tasks]
        print(json.dumps(out, indent=2))

    else:
        print("Usage: next_task.py [pick [N]|list]", file=sys.stderr)
        sys.exit(2)

if __name__ == "__main__":
    main()