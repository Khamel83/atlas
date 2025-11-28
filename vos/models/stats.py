from dataclasses import dataclass
from typing import Dict

@dataclass
class StatsSnapshot:
    total_content: int
    queue_depth: Dict[str, int]
    failures_last_hour: int
