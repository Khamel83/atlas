from datetime import datetime, timedelta
from unittest.mock import MagicMock

import pytest

from ask.proactive.surfacer import ProactiveSurfacer


class FakeContentMetadata:
    def __init__(self, title, updated_at):
        self.title = title
        self.updated_at = updated_at


@pytest.fixture
def fake_metadata_manager():
    mgr = MagicMock()
    now = datetime.now()
    items = [
        FakeContentMetadata("Oldest", (now - timedelta(days=40)).isoformat()),
        FakeContentMetadata("Middle", (now - timedelta(days=20)).isoformat()),
        FakeContentMetadata("Newest", (now - timedelta(days=5)).isoformat()),
    ]
    mgr.get_forgotten_content.return_value = items
    mgr.save_metadata = MagicMock()
    return mgr


def test_surface_forgotten_content(fake_metadata_manager):
    surfacer = ProactiveSurfacer(fake_metadata_manager)
    results = surfacer.surface_forgotten_content(n=2, cutoff_days=10)
    assert len(results) == 2
    assert results[0].title == "Oldest"
    assert results[1].title == "Middle"


def test_mark_surfaced(fake_metadata_manager):
    surfacer = ProactiveSurfacer(fake_metadata_manager)
    item = FakeContentMetadata(
        "Test", (datetime.now() - timedelta(days=50)).isoformat()
    )
    surfacer.mark_surfaced(item)
    # Should call save_metadata with updated_at very recent
    fake_metadata_manager.save_metadata.assert_called_once()
    updated_item = fake_metadata_manager.save_metadata.call_args[0][0]
    now = datetime.now()
    updated_time = datetime.fromisoformat(updated_item.updated_at)
    assert (now - updated_time).total_seconds() < 5
