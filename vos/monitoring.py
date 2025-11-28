import os
from pathlib import Path
from typing import Optional


def queue_summary(queue_root: Optional[Path] = None) -> dict[str, int]:
    root = queue_root or Path(os.getenv("QUEUE_ROOT", "data/queue"))
    summary: dict[str, int] = {}
    for sub in ("inbox", "processing", "completed", "failed"):
        path = root / sub
        path.mkdir(parents=True, exist_ok=True)
        summary[sub] = len(list(path.glob("*.json")))
    return summary
