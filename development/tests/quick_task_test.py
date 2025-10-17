#!/usr/bin/env python3
import re, yaml
from pathlib import Path

content = Path("TASKS.md").read_text()
lines = content.splitlines()

HDR = re.compile(r"^### \*\*(?P<id>ATLAS-COMPLETE-\d+):\s*(?P<title>[^*]+)\*\*$")

tasks = []
current_task = None
in_yaml_block = False
yaml_lines = []

for i, line in enumerate(lines):
    # Check for task header
    m = HDR.match(line.strip())
    if m:
        print(f"Found task: {m.group('id')} - {m.group('title')}")
        # Save previous task
        if current_task and yaml_lines:
            try:
                yaml_content = '\n'.join(yaml_lines)
                print(f"  YAML: {yaml_content[:100]}...")
                yaml_data = yaml.safe_load(yaml_content)
                current_task.update(yaml_data)
                tasks.append(current_task)
                print(f"  Task saved: {current_task}")
            except Exception as e:
                print(f"  YAML error: {e}")

        current_task = {"id": m.group("id"), "title": m.group("title")}
        in_yaml_block = False
        yaml_lines = []

    elif line.strip() == "```yaml" and current_task:
        print(f"  Starting YAML block")
        in_yaml_block = True
        yaml_lines = []

    elif line.strip() == "```" and in_yaml_block:
        print(f"  Ending YAML block with {len(yaml_lines)} lines")
        in_yaml_block = False

    elif in_yaml_block:
        yaml_lines.append(line)

# Don't forget last task
if current_task and yaml_lines:
    try:
        yaml_content = '\n'.join(yaml_lines)
        yaml_data = yaml.safe_load(yaml_content)
        current_task.update(yaml_data)
        tasks.append(current_task)
    except Exception as e:
        print(f"Final YAML error: {e}")

print(f"\nFound {len(tasks)} tasks:")
for task in tasks:
    print(f"  {task['id']}: {task.get('status', 'unknown')} - {task.get('title', 'no title')}")
    print(f"    deps: {task.get('depends_on', [])}")

# Find ready tasks
ready_tasks = []
done_ids = {t['id'] for t in tasks if t.get('status') == 'done'}
print(f"\nDone tasks: {done_ids}")

for task in tasks:
    if task.get('status') in ['todo', 'in_progress']:
        deps = task.get('depends_on', [])
        if not deps or all(dep in done_ids for dep in deps):
            ready_tasks.append(task)

print(f"\nReady tasks: {len(ready_tasks)}")
for task in ready_tasks:
    print(f"  {task['id']}: {task.get('title', 'no title')}")