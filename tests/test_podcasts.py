"""
Tests for modules.podcasts
"""

import pytest
from datetime import datetime

from modules.podcasts.store import PodcastStore, Podcast, Episode


class TestPodcastStore:
    """Test PodcastStore functionality."""

    def test_store_init(self, temp_db):
        """Test PodcastStore initialization."""
        store = PodcastStore(temp_db)
        from pathlib import Path
        assert Path(temp_db).exists()

    def test_create_podcast(self, temp_db):
        """Test creating a podcast."""
        store = PodcastStore(temp_db)

        podcast = Podcast(
            name="Test Podcast",
            slug="test-podcast",
            rss_url="https://example.com/feed.xml",
            site_url="https://example.com",
            resolver="generic_html",
        )

        podcast_id = store.create_podcast(podcast)
        assert podcast_id > 0

    def test_get_podcast(self, temp_db):
        """Test retrieving a podcast."""
        store = PodcastStore(temp_db)

        podcast = Podcast(
            name="Get Test Podcast",
            slug="get-test-podcast",
            rss_url="https://example.com/feed.xml",
        )

        podcast_id = store.create_podcast(podcast)
        retrieved = store.get_podcast(podcast_id)

        assert retrieved is not None
        assert retrieved.name == "Get Test Podcast"
        assert retrieved.slug == "get-test-podcast"

    def test_get_podcast_by_slug(self, temp_db):
        """Test retrieving a podcast by slug."""
        store = PodcastStore(temp_db)

        podcast = Podcast(
            name="Slug Test Podcast",
            slug="slug-test-podcast",
            rss_url="https://example.com/feed.xml",
        )

        store.create_podcast(podcast)
        retrieved = store.get_podcast_by_slug("slug-test-podcast")

        assert retrieved is not None
        assert retrieved.name == "Slug Test Podcast"

    def test_list_podcasts(self, temp_db):
        """Test listing all podcasts."""
        store = PodcastStore(temp_db)

        for i in range(3):
            podcast = Podcast(
                name=f"List Test Podcast {i}",
                slug=f"list-test-podcast-{i}",
                rss_url=f"https://example.com/feed{i}.xml",
            )
            store.create_podcast(podcast)

        podcasts = store.list_podcasts()
        assert len(podcasts) >= 3

    def test_create_episode(self, temp_db):
        """Test creating an episode."""
        store = PodcastStore(temp_db)

        # First create a podcast
        podcast = Podcast(
            name="Episode Test Podcast",
            slug="episode-test-podcast",
            rss_url="https://example.com/feed.xml",
        )
        podcast_id = store.create_podcast(podcast)

        # Create an episode
        episode = Episode(
            podcast_id=podcast_id,
            guid="episode-guid-123",
            title="Test Episode",
            url="https://example.com/episode1",
            transcript_status="unknown",
        )
        episode_id = store.create_episode(episode)
        assert episode_id > 0

    def test_get_episodes_by_podcast(self, temp_db):
        """Test getting episodes for a podcast."""
        store = PodcastStore(temp_db)

        # Create podcast
        podcast = Podcast(
            name="Episodes Test Podcast",
            slug="episodes-test-podcast",
            rss_url="https://example.com/feed.xml",
        )
        podcast_id = store.create_podcast(podcast)

        # Create episodes
        for i in range(5):
            episode = Episode(
                podcast_id=podcast_id,
                guid=f"episode-guid-{i}",
                title=f"Test Episode {i}",
                url=f"https://example.com/episode{i}",
            )
            store.create_episode(episode)

        episodes = store.get_episodes_by_podcast(podcast_id)
        assert len(episodes) == 5

    def test_update_episode_transcript_status(self, temp_db):
        """Test updating episode transcript status."""
        store = PodcastStore(temp_db)

        # Create podcast and episode
        podcast = Podcast(
            name="Update Test Podcast",
            slug="update-test-podcast",
            rss_url="https://example.com/feed.xml",
        )
        podcast_id = store.create_podcast(podcast)

        episode = Episode(
            podcast_id=podcast_id,
            guid="update-episode-guid",
            title="Update Test Episode",
            url="https://example.com/episode",
            transcript_status="unknown",
        )
        episode_id = store.create_episode(episode)

        # Update status
        store.update_episode_transcript_status(
            episode_id, "found", "/path/to/transcript.txt"
        )

        # Verify (by getting all episodes)
        episodes = store.get_episodes_by_podcast(podcast_id)
        updated = [e for e in episodes if e.id == episode_id][0]
        assert updated.transcript_status == "found"

    def test_get_stats(self, temp_db):
        """Test getting statistics."""
        store = PodcastStore(temp_db)

        # Create some data
        podcast = Podcast(
            name="Stats Test Podcast",
            slug="stats-test-podcast",
            rss_url="https://example.com/feed.xml",
        )
        podcast_id = store.create_podcast(podcast)

        for i in range(3):
            episode = Episode(
                podcast_id=podcast_id,
                guid=f"stats-episode-{i}",
                title=f"Stats Episode {i}",
                url=f"https://example.com/episode{i}",
                transcript_status="unknown" if i < 2 else "found",
            )
            store.create_episode(episode)

        stats = store.get_stats()
        assert "total_podcasts" in stats
        assert "episodes_by_status" in stats
        assert stats["total_podcasts"] >= 1
