import importlib
import json
from pathlib import Path

import pytest


def test_create_job(tmp_path, monkeypatch):
    monkeypatch.setenv("QUEUE_ROOT", str(tmp_path / "queue"))
    import vos.ingestion.utils as utils

    importlib.reload(utils)

    job_path = utils.create_job("url", "test", {"url": "https://example.com"})
    assert job_path.exists()
    data = json.loads(job_path.read_text(encoding="utf-8"))
    assert data["type"] == "url"
    assert job_path.parent.name == "inbox"
    assert "created_at" in data
