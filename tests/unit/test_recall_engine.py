from datetime import datetime, timedelta
from unittest.mock import MagicMock

import pytest

from ask.recall.recall_engine import RecallEngine


class FakeContentMetadata:
    def __init__(self, title, updated_at, last_reviewed=None, review_count=0):
        self.title = title
        self.updated_at = updated_at
        self.type_specific = (
            {"last_reviewed": last_reviewed, "review_count": review_count}
            if last_reviewed
            else {}
        )


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
    # 3 items: one overdue by 10 days (review_count=0), one due in 2 days (review_count=1), one not due (review_count=2)
    items = [
        FakeContentMetadata(
            "A",
            (now - timedelta(days=20)).isoformat(),
            (now - timedelta(days=10)).isoformat(),
            0,
        ),
        FakeContentMetadata(
            "B",
            (now - timedelta(days=10)).isoformat(),
            (now - timedelta(days=1)).isoformat(),
            1,
        ),
        FakeContentMetadata("C", now.isoformat(), None, 2),
    ]
    mgr.get_all_metadata.side_effect = lambda ct: items if ct == "article" else []
    mgr.save_metadata = MagicMock()
    return mgr


def test_schedule_spaced_repetition(fake_metadata_manager):
    engine = RecallEngine(fake_metadata_manager)
    due = engine.schedule_spaced_repetition(n=2)
    # Only A should be overdue (10 days overdue), B not yet due, C not due (no last_reviewed, 5 days < 7 days interval)
    assert len(due) == 1
    assert due[0].title == "A"


def test_mark_reviewed(fake_metadata_manager):
    engine = RecallEngine(fake_metadata_manager)
    item = FakeContentMetadata(
        "Test", (datetime.now() - timedelta(days=50)).isoformat(), None, 0
    )
    engine.mark_reviewed(item)
    fake_metadata_manager.save_metadata.assert_called_once()
    updated_item = fake_metadata_manager.save_metadata.call_args[0][0]
    now = datetime.now()
    last_reviewed = updated_item.type_specific["last_reviewed"]
    reviewed_time = datetime.fromisoformat(last_reviewed)
    assert (now - reviewed_time).total_seconds() < 5
    assert updated_item.type_specific["review_count"] == 1
