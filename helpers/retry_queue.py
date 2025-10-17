import json
from pathlib import Path
from typing import Optional

QUEUE_PATH = Path("retries/queue.jsonl")
QUEUE_PATH.parent.mkdir(exist_ok=True, parents=True)


def enqueue(task: dict):
    """Append *task* as JSON line to the retry queue."""
    with QUEUE_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(task, ensure_ascii=False) + "\n")


def dequeue() -> Optional[dict]:
    """Pop the first task from the queue and return it, or None if empty."""
    if not QUEUE_PATH.exists():
        return None
    lines = QUEUE_PATH.read_text(encoding="utf-8").splitlines()
    if not lines:
        return None
    first = json.loads(lines[0])
    with QUEUE_PATH.open("w", encoding="utf-8") as f:
        f.write("\n".join(lines[1:]))
    return first
