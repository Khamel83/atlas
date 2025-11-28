from typing import Any, Optional

from vos.ingestion.utils import create_job


def enqueue_url(
    url: str,
    source: Optional[str] = "manual",
    metadata: Optional[dict[str, Any]] = None,
):
    payload: dict[str, Any] = {"url": url}
    if metadata:
        payload.update(metadata)
    return create_job("url", source or "manual", payload)
