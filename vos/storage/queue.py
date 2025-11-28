import json
from pathlib import Path
from typing import Dict, Any


def ensure_queue_dirs(queue_root: Path):
    for sub in ("inbox", "processing", "completed", "failed"):
        (queue_root / sub).mkdir(parents=True, exist_ok=True)


def write_job(job: Dict[str, Any], queue_root: Path):
    ensure_queue_dirs(queue_root.parent)
    queue_root.mkdir(parents=True, exist_ok=True)
    path = queue_root / f"{job['id']}.json"
    with path.open("w", encoding="utf-8") as f:
        json.dump(job, f, indent=2)
    return path
