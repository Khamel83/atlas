from datetime import datetime, timedelta
from unittest.mock import MagicMock

import pytest

from ask.temporal.temporal_engine import TemporalEngine


class FakeContentMetadata:
    def __init__(self, title, created_at):
        self.title = title
        self.created_at = created_at


@pytest.fixture
def fake_metadata_manager():
    mgr = MagicMock()

    # Simulate ContentType enum
    class FakeContentType:
        ARTICLE = "article"
        PODCAST = "podcast"
        YOUTUBE = "youtube"
        INSTAPAPER = "instapaper"

        def __iter__(self):
            return iter([self.ARTICLE, self.PODCAST, self.YOUTUBE, self.INSTAPAPER])

    mgr.ContentType = FakeContentType()
    now = datetime.now()
    # 3 items: 0 days, 1 day, 3 days apart
    items = [
        FakeContentMetadata("A", (now - timedelta(days=5)).isoformat()),
        FakeContentMetadata("B", (now - timedelta(days=4)).isoformat()),
        FakeContentMetadata("C", (now - timedelta(days=1)).isoformat()),
    ]
    mgr.get_all_metadata.side_effect = lambda ct: items if ct == "article" else []
    return mgr


def test_get_time_aware_relationships(fake_metadata_manager):
    engine = TemporalEngine(fake_metadata_manager)
    rels = engine.get_time_aware_relationships(max_delta_days=1)
    assert len(rels) == 1
    a, b, d = rels[0]
    assert a.title == "A"
    assert b.title == "B"
    assert d == 1
    # Now test with larger window
    rels = engine.get_time_aware_relationships(max_delta_days=5)
    assert len(rels) == 2
    assert rels[1][0].title == "B"
    assert rels[1][1].title == "C"
    assert rels[1][2] == 3
