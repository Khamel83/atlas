"""
Tests for the API endpoints.
"""

import pytest
from fastapi.testclient import TestClient

from api.main import app

client = TestClient(app)


class TestHealthEndpoints:
    """Test health check endpoints."""

    def test_api_info(self):
        """Test API info endpoint."""
        response = client.get("/api/info")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Atlas API"
        assert "version" in data

    def test_health(self):
        """Test health endpoint."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data

    def test_metrics(self):
        """Test metrics endpoint."""
        response = client.get("/metrics")
        assert response.status_code == 200
        data = response.json()
        assert "timestamp" in data


class TestPodcastEndpoints:
    """Test podcast endpoints."""

    def test_list_podcasts(self):
        """Test listing podcasts."""
        response = client.get("/api/podcasts/")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_get_stats(self):
        """Test getting podcast stats."""
        response = client.get("/api/podcasts/stats")
        assert response.status_code == 200
        data = response.json()
        assert "total_podcasts" in data
        assert "episodes_by_status" in data

    def test_get_nonexistent_podcast(self):
        """Test getting a podcast that doesn't exist."""
        response = client.get("/api/podcasts/99999")
        assert response.status_code == 404


class TestContentEndpoints:
    """Test content endpoints."""

    def test_list_content(self):
        """Test listing content."""
        response = client.get("/api/content/")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data

    def test_get_content_stats(self):
        """Test getting content stats."""
        response = client.get("/api/content/stats")
        assert response.status_code == 200

    def test_get_nonexistent_content(self):
        """Test getting content that doesn't exist."""
        response = client.get("/api/content/nonexistent123")
        assert response.status_code == 404


class TestSearchEndpoints:
    """Test search endpoints."""

    def test_search_requires_query(self):
        """Test that search requires a query parameter."""
        response = client.get("/api/search/")
        assert response.status_code == 422  # Validation error

    def test_search_with_query(self):
        """Test searching with a query."""
        response = client.get("/api/search/?q=test")
        assert response.status_code == 200
        data = response.json()
        assert data["query"] == "test"
        assert "results" in data
        assert "total" in data
