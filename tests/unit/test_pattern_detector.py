from unittest.mock import MagicMock

import pytest

from ask.insights.pattern_detector import PatternDetector


class FakeContentMetadata:
    def __init__(self, tags, source):
        self.tags = tags
        self.source = source


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
    items = [
        FakeContentMetadata(["science", "ai"], "source1"),
        FakeContentMetadata(["ai", "ethics"], "source2"),
        FakeContentMetadata(["science", "ethics"], "source1"),
        FakeContentMetadata(["ai"], "source3"),
    ]
    mgr.get_all_metadata.side_effect = lambda ct: items if ct == "article" else []
    return mgr


def test_find_patterns(fake_metadata_manager):
    detector = PatternDetector(fake_metadata_manager)
    patterns = detector.find_patterns(n=2)
    assert patterns["top_tags"][0][0] == "ai"
    assert patterns["top_tags"][0][1] == 3
    assert patterns["top_tags"][1][0] == "science"
    assert patterns["top_tags"][1][1] == 2
    assert patterns["top_sources"][0][0] == "source1"
    assert patterns["top_sources"][0][1] == 2
