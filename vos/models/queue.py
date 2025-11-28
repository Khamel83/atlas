from dataclasses import dataclass
from typing import Any, Dict, Optional



@dataclass
class QueueJob:
    id: str
    type: str
    source: str
    payload: Dict[str, Any]
    created_at: str
    origin_manifest_id: Optional[str] = None
    notes: Optional[str] = None
