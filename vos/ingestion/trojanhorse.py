from typing import Dict, Any

from vos.ingestion.utils import create_job


def enqueue_trojanhorse(payload: Dict[str, Any], source: str = "trojanhorse") -> None:
    create_job("trojanhorse", source, payload)
