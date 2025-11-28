import os
from typing import Any, Optional

from fastapi import FastAPI, Header, HTTPException, Query

from vos.api.dashboard import render_dashboard
from vos.ingestion.gmail import poll_gmail
from vos.ingestion.rss import poll_rss
from vos.ingestion.trojanhorse import enqueue_trojanhorse
from vos.ingestion.url import enqueue_url
from vos.monitoring import queue_summary as queue_summary_stats
from vos.search.whoosh_search import search

app = FastAPI(title="Atlas vOS")

API_KEY = os.getenv("ATLAS_API_KEY")
WHOOSH_INDEX_PATH = Path(os.getenv("WHOOSH_INDEX_PATH", "data/search_index"))


def verify_api_key(x_api_key: Optional[str] = Header(None)):
    if API_KEY and x_api_key != API_KEY:
        raise HTTPException(status_code=403, detail="Invalid API key")


@app.get("/vos/health")
def health():
    return {"status": "ok"}


@app.post("/vos/ingest/url")
def api_ingest_url(payload: dict[str, Any], x_api_key: Optional[str] = Header(None)):
    verify_api_key(x_api_key)
    url = payload.get("url")
    if not url:
        raise HTTPException(status_code=400, detail="url is required")
    enqueue_url(url, payload.get("source", "api"))
    return {"queued": True, "url": url}


@app.post("/vos/trojanhorse/ingest")
def api_trojanhorse(payload: dict[str, Any], x_api_key: Optional[str] = Header(None)):
    verify_api_key(x_api_key)
    enqueue_trojanhorse(payload)
    return {"queued": True, "note_id": payload.get("id")}


@app.post("/vos/gmail/poll")
def api_gmail_poll(x_api_key: Optional[str] = Header(None)):
    verify_api_key(x_api_key)
    count = poll_gmail()
    return {"processed": count}


@app.post("/vos/rss/poll")
def api_rss_poll(x_api_key: Optional[str] = Header(None)):
    verify_api_key(x_api_key)
    count = poll_rss()
    return {"processed": count}


@app.get("/vos/search")
def api_search(
    q: str = Query(..., min_length=1),
    limit: int = Query(10, ge=1, le=50),
):
    results = search(WHOOSH_INDEX_PATH, q, limit=limit)
    return {"query": q, "results": results}


@app.get("/vos/status")
def status():
    summary = queue_summary_stats()
    return {"queue": summary}


@app.get("/vos/dashboard")
def dashboard():
    summary = queue_summary_stats()
    content = render_dashboard(summary, [])
    return content
