import json
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from vos.storage.queue import write_job

QUEUE_ROOT = Path(os.getenv("QUEUE_ROOT", "data/queue"))
RAW_ROOT = Path(os.getenv("RAW_ROOT", "data/raw"))
BACKLOG_ROOT = Path(os.getenv("BACKLOG_ROOT", "data/backlog"))


def iso_now() -> str:
    return datetime.utcnow().isoformat() + "Z"


def sanitize_label(label: str) -> str:
    return label.lower().replace(" ", "_")


def create_job(
    job_type: str,
    source: str,
    payload: Dict[str, Any],
    origin_manifest_id: Optional[str] = None,
    notes: Optional[str] = None,
    queue_dir: str = "inbox",
) -> Path:
    job = {
        "id": uuid.uuid4().hex,
        "type": job_type,
        "source": source,
        "payload": payload,
        "origin_manifest_id": origin_manifest_id,
        "notes": notes,
        "created_at": iso_now(),
    }
    dest = QUEUE_ROOT / queue_dir
    return write_job(job, dest)


def save_raw_email(message_bytes: bytes, label: str) -> Path:
    target = RAW_ROOT / "emails" / sanitize_label(label)
    target.mkdir(parents=True, exist_ok=True)
    path = target / f"{uuid.uuid4().hex}.eml"
    path.write_bytes(message_bytes)
    return path


def save_raw_feed(entry: Dict[str, Any], feed_name: str) -> Path:
    target = RAW_ROOT / "feeds" / sanitize_label(feed_name)
    target.mkdir(parents=True, exist_ok=True)
    path = target / f"{uuid.uuid4().hex}.json"
    with path.open("w", encoding="utf-8") as fh:
        json.dump(entry, fh, indent=2)
    return path


def save_backlog_payload(payload: Dict[str, Any], source_name: str) -> Path:
    target = BACKLOG_ROOT / "payloads" / sanitize_label(source_name)
    target.mkdir(parents=True, exist_ok=True)
    path = target / f"{uuid.uuid4().hex}.json"
    with path.open("w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2)
    return path
