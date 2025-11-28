import importlib
import json
import os
import sqlite3
from datetime import datetime
from pathlib import Path

import pytest

JOB_TEMPLATE = {
    "id": "testjob",
    "type": "backlog",
    "source": "unittest",
    "payload": {"html": "<p>test</p>", "text": "test"},
    "created_at": datetime.utcnow().isoformat() + "Z",
}


def test_worker_process_backlog(tmp_path, monkeypatch):
    queue_root = tmp_path / "queue"
    archive_root = tmp_path / "archives"
    db_path = tmp_path / "atlas_vos.db"
    index_path = tmp_path / "search_index"

    monkeypatch.setenv("QUEUE_ROOT", str(queue_root))
    monkeypatch.setenv("ARCHIVE_ROOT", str(archive_root))
    monkeypatch.setenv("DATABASE_PATH", str(db_path))
    monkeypatch.setenv("WHOOSH_INDEX_PATH", str(index_path))
    monkeypatch.setenv("PROCESSOR_SLEEP_SECONDS", "0")

    from vos.worker import processor

    importlib.reload(processor)

    inbox = queue_root / "inbox"
    inbox.mkdir(parents=True, exist_ok=True)
    job_path = inbox / f"{JOB_TEMPLATE['id']}.json"
    with job_path.open("w", encoding="utf-8") as fh:
        json.dump(JOB_TEMPLATE, fh)

    processor.run(max_iterations=1)

    completed = list((queue_root / "completed").glob("*.json"))
    assert len(completed) == 1

    conn = sqlite3.connect(str(db_path))
    cursor = conn.execute("SELECT id, url FROM content WHERE id = ?", (JOB_TEMPLATE["id"],))
    row = cursor.fetchone()
    conn.close()
    assert row is not None
    assert row[0] == JOB_TEMPLATE["id"]
