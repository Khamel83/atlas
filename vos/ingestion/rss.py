import json
import os
from pathlib import Path
from typing import Dict

import feedparser
import yaml

from vos.ingestion.utils import create_job, save_raw_feed
from vos.storage.database import get_connection, has_processed_entry, mark_processed_entry, update_feed_state

CONFIG_PATH = Path(os.getenv("RSS_CONFIG_PATH", "config/feeds.yaml"))
DATABASE_PATH = Path(os.getenv("DATABASE_PATH", "data/atlas_vos.db"))


def load_feed_config() -> Dict[str, str]:
    if not CONFIG_PATH.exists():
        return {}
    with CONFIG_PATH.open() as fh:
        data = yaml.safe_load(fh)
    return {feed["url"]: feed for feed in data.get("feeds", [])}


def normalize_entry(entry) -> Dict:
    return {key: entry.get(key) for key in entry.keys()}


def poll_rss() -> int:
    config = load_feed_config()
    if not config:
        return 0
    conn = get_connection(str(DATABASE_PATH))
    beacons = 0
    for feed_url, feed in config.items():
        parsed = feedparser.parse(feed_url)
        if parsed.bozo:
            continue
        feed_name = feed.get("name", parsed.feed.get("title", feed_url))
        for entry in parsed.entries:
            guid = entry.get("id") or entry.get("link")
            if not guid or has_processed_entry(conn, feed_url, guid):
                continue
            entry_data = normalize_entry(entry)
            raw_path = save_raw_feed(entry_data, feed_name)
            payload = {
                "entry": entry_data,
                "source_path": str(raw_path),
                "feed_url": feed_url,
            }
            create_job("rss_item", "rss", payload)
            mark_processed_entry(conn, feed_url, guid)
            update_feed_state(conn, feed_url, guid)
            beacons += 1
    conn.close()
    return beacons
