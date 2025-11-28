import json
import logging
import os
import time
import traceback
from pathlib import Path
from typing import Optional

import requests
from bs4 import BeautifulSoup
from readability import Document

from vos.search.whoosh_search import index_document
from vos.storage.archive import archive_html, archive_text
from vos.storage.database import (
    get_connection,
    init_db,
    insert_content,
    log_queue_audit,
)

logger = logging.getLogger("vos.worker")
logging.basicConfig(level=logging.INFO)

QUEUE_ROOT = Path(os.getenv("QUEUE_ROOT", "data/queue"))
ARCHIVE_ROOT = Path(os.getenv("ARCHIVE_ROOT", "data/archives"))
DATABASE_PATH = Path(os.getenv("DATABASE_PATH", "data/atlas_vos.db"))
WHOOSH_INDEX_PATH = Path(os.getenv("WHOOSH_INDEX_PATH", "data/search_index"))
SLEEP_SECONDS = int(os.getenv("PROCESSOR_SLEEP_SECONDS", "60"))
PRIORITY = {"rss_item": 1, "email": 1, "trojanhorse": 2, "url": 2, "backlog": 3}


def ensure_dirs():
    for sub in ("inbox", "processing", "completed", "failed"):
        (QUEUE_ROOT / sub).mkdir(parents=True, exist_ok=True)


def pick_next_job(inbox: Path):
    job_entries = []
    for job_path in inbox.glob("*.json"):
        try:
            job = json.loads(job_path.read_text(encoding="utf-8"))
        except Exception:
            job_entries.append(
                (PRIORITY.get("backlog", 10), job_path.stat().st_mtime, job_path, None)
            )
            continue
        priority = PRIORITY.get(job.get("type"), 5)
        job_entries.append((priority, job_path.stat().st_mtime, job_path, job))
    if not job_entries:
        return None, None
    job_entries.sort()
    return job_entries[0][2], job_entries[0][3]


def extract_url(job: dict) -> Optional[str]:
    payload = job.get("payload", {})
    if "url" in payload:
        return payload["url"]
    if "row" in payload and isinstance(payload["row"], dict):
        return payload["row"].get("url")
    if "entry" in payload and isinstance(payload["entry"], dict):
        return payload["entry"].get("link") or payload["entry"].get("url")
    if "entry" in payload and isinstance(payload["entry"], str):
        return payload["entry"]
    return None


def fetch_and_extract(url: str) -> tuple[str, str]:
    headers = {"User-Agent": "Atlas-vOS/1.0"}
    resp = requests.get(url, headers=headers, timeout=15)
    resp.raise_for_status()
    html = resp.text
    doc = Document(html)
    summary = doc.summary()
    soup = BeautifulSoup(summary, "html.parser")
    text = soup.get_text(separator="\n").strip()
    return html, text


def build_record(job: dict, html: str, text: str):
    now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    payload = job.get("payload", {})
    record = {
        "id": job["id"],
        "url": extract_url(job) or payload.get("source_path", "backlog"),
        "title": payload.get("title")
        or payload.get("row", {}).get("title")
        or job["source"],
        "source": job["source"],
        "content_type": job["type"],
        "html_path": str(ARCHIVE_ROOT / job["id"] / "content.html"),
        "text_path": str(ARCHIVE_ROOT / job["id"] / "content.txt"),
        "metadata": payload,
        "created_at": now,
    }
    return record


def process_job(job: dict):
    job_id = job["id"]
    url = extract_url(job)
    if url:
        html, text = fetch_and_extract(url)
    else:
        payload = job.get("payload", {})
        html = payload.get("html", "") or "<html></html>"
        text = payload.get("text", "") or str(payload)
    archive_dir = ARCHIVE_ROOT / job_id
    archive_html(html, archive_dir)
    archive_text(text, archive_dir)
    record = build_record(job, html, text)
    conn = get_connection(str(DATABASE_PATH))
    insert_content(conn, record)
    index_document(
        WHOOSH_INDEX_PATH, {"id": job_id, "title": record["title"], "body": text}
    )
    conn.close()
    return record


def move_job(job_path: Path, target_dir: Path):
    target_dir.mkdir(parents=True, exist_ok=True)
    destination = target_dir / job_path.name
    return job_path.replace(destination)


def run(max_iterations: Optional[int] = None):
    ensure_dirs()
    init_db(str(DATABASE_PATH))
    conn = get_connection(str(DATABASE_PATH))
    inbox = QUEUE_ROOT / "inbox"
    processing = QUEUE_ROOT / "processing"
    iteration = 0
    while True:
        if max_iterations is not None and iteration >= max_iterations:
            break
        job_path, job_data = pick_next_job(inbox)
        if not job_path:
            time.sleep(SLEEP_SECONDS)
            continue
        try:
            move_job(job_path, processing)
            job_content = job_data or json.loads(
                (processing / job_path.name).read_text(encoding="utf-8")
            )
            record = process_job(job_content)
            log_queue_audit(conn, job_path.stem, "completed")
            move_job(processing / job_path.name, QUEUE_ROOT / "completed")
            logger.info("processed job %s %s", job_path.name, record["url"])
        except Exception as exc:  # noqa: BLE001
            tb = traceback.format_exc()
            log_queue_audit(conn, job_path.stem, "failed", tb)
            move_job(processing / job_path.name, QUEUE_ROOT / "failed")
            (QUEUE_ROOT / "failed" / job_path.name).with_suffix(
                ".error.txt"
            ).write_text(tb)
            logger.error("job %s failed: %s", job_path.name, exc)
        iteration += 1
