import csv
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

import yaml

from vos.ingestion.utils import create_job as enqueue_job

BACKLOG_ROOT = Path("data/backlog")
MANIFEST_PATH = BACKLOG_ROOT / "source_manifest.jsonl"
LOG_ROOT = BACKLOG_ROOT / "logs"


def load_manifest() -> Dict[str, str]:
    if not MANIFEST_PATH.exists():
        return {}
    manifest_map: Dict[str, str] = {}
    with MANIFEST_PATH.open() as fh:
        for line in fh:
            record = json.loads(line)
            manifest_map[record["relative_path"]] = record["id"]
    return manifest_map


def append_log(source_name: str, message: str):
    LOG_ROOT.mkdir(parents=True, exist_ok=True)
    log_file = LOG_ROOT / f"{source_name}.log"
    with log_file.open("a", encoding="utf-8") as fh:
        fh.write(f"{datetime.utcnow().isoformat()}Z {message}\n")


def enqueue_backlog_job(payload: Dict[str, Any], source_name: str, origin_id: str):
    path = enqueue_job(
        "backlog",
        source_name,
        payload,
        origin_manifest_id=origin_id,
    )
    append_log(
        source_name, f"created job {path.stem} from {payload.get('source_path')}"
    )
    return path


def parse_csv(path: Path, source_name: str, manifest_id: str):
    with path.open(encoding="utf-8", errors="ignore") as fh:
        reader = csv.DictReader(fh)
        count = 0
        for row in reader:
            payload = {"row": row, "source_path": str(path)}
            enqueue_backlog_job(payload, source_name, manifest_id)
            count += 1
    append_log(source_name, f"processed CSV {path.name} ({count} rows)")


def parse_json(path: Path, source_name: str, manifest_id: str):
    with path.open(encoding="utf-8") as fh:
        data = json.load(fh)
    if isinstance(data, list):
        iterable = data
    elif isinstance(data, dict) and "items" in data:
        iterable = data["items"]
    else:
        iterable = [data]
    for entry in iterable:
        payload = {"entry": entry, "source_path": str(path)}
        enqueue_backlog_job(payload, source_name, manifest_id)
    append_log(source_name, f"processed JSON {path.name} ({len(iterable)} entries)")


def parse_text(path: Path, source_name: str, manifest_id: str):
    with path.open(encoding="utf-8") as fh:
        lines = [line.strip() for line in fh if line.strip()]
    for line in lines:
        payload = {"url": line, "source_path": str(path)}
        enqueue_backlog_job(payload, source_name, manifest_id)
    append_log(source_name, f"processed text list {path.name} ({len(lines)} urls)")


def parse_directory(path: Path, source_name: str, manifest_id: str):
    files = list(path.iterdir())
    for file in files:
        payload = {"path": str(file), "source_path": str(path)}
        enqueue_backlog_job(payload, source_name, manifest_id)
    append_log(source_name, f"queued directory {path.name} ({len(files)} files)")


def process_source(source: Dict[str, Any], manifest_map: Dict[str, str]):
    source_path = Path(source["path"])
    source_name = source.get("name", source_path.stem)
    source_type = source.get("type", "text")
    relative = source_path.as_posix()
    manifest_id = manifest_map.get(relative)
    if not manifest_id:
        manifest_id = source.get("manifest_id", "unknown")
    if not source_path.exists():
        append_log(source_name, f"missing source {source_path}")
        return
    if source_type == "csv":
        parse_csv(source_path, source_name, manifest_id)
    elif source_type == "json":
        parse_json(source_path, source_name, manifest_id)
    elif source_type == "text":
        parse_text(source_path, source_name, manifest_id)
    elif source_type == "directory":
        parse_directory(source_path, source_name, manifest_id)
    else:
        append_log(source_name, f"unsupported type {source_type}")


def process_backlog():
    config_path = Path(os.getenv("BACKLOG_CONFIG_PATH", "config/backlog_sources.yaml"))
    with config_path.open() as fh:
        config = yaml.safe_load(fh)
    manifest_map = load_manifest()
    for source in config.get("sources", []):
        process_source(source, manifest_map)
