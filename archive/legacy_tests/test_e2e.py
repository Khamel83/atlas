"""End-to-end tests for Atlas system."""

import pytest
import httpx
import asyncio
import time
import subprocess
import signal
import os
import sys

# Add Atlas to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class TestEndToEnd:
    """Test complete workflows in Atlas."""

    @pytest.fixture(scope="class")
    def atlas_server(self):
        """Start Atlas server for testing."""
        # Start server in background
        process = subprocess.Popen([
            sys.executable, "-m", "uvicorn", "web.app:app",
            "--host", "127.0.0.1", "--port", "8004"
        ], cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

        # Wait for server to start
        time.sleep(3)

        yield "http://127.0.0.1:8004"

        # Cleanup
        process.terminate()
        process.wait()

    def test_complete_mobile_workflow(self, atlas_server):
        """Test complete mobile user workflow."""
        base_url = atlas_server

        # Test mobile dashboard loads
        response = httpx.get(f"{base_url}/mobile")
        assert response.status_code == 200
        assert "Atlas - Cognitive AI" in response.text

        # Test each cognitive feature loads
        features = ["proactive", "temporal", "recall", "patterns", "socratic", "browse"]
        for feature in features:
            response = httpx.get(f"{base_url}/mobile?feature={feature}")
            assert response.status_code == 200, f"Feature {feature} failed"

        # Test search functionality
        response = httpx.get(f"{base_url}/mobile?feature=browse&search=test")
        assert response.status_code == 200

        # Test filters
        response = httpx.get(f"{base_url}/mobile?feature=browse&type_filter=article")
        assert response.status_code == 200

    def test_api_workflow(self, atlas_server):
        """Test API endpoint workflow."""
        base_url = atlas_server

        # Test all API endpoints
        api_endpoints = [
            "/ask/proactive",
            "/ask/temporal",
            "/ask/recall",
            "/ask/patterns"
        ]

        for endpoint in api_endpoints:
            response = httpx.get(f"{base_url}{endpoint}")
            assert response.status_code == 200
            assert response.headers.get("content-type") == "application/json"

    def test_content_management_workflow(self, atlas_server):
        """Test content management workflow."""
        base_url = atlas_server

        # Note: These test the endpoints exist and handle requests properly
        # Real content management would require test data

        # Test delete endpoint exists
        response = httpx.delete(f"{base_url}/mobile/content/999")
        # Should not be 404 (endpoint exists) but may be 422/500 (no content)
        assert response.status_code != 404

        # Test archive endpoint exists
        response = httpx.post(f"{base_url}/mobile/content/999/archive")
        assert response.status_code != 404

        # Test tagging endpoint exists
        response = httpx.post(f"{base_url}/mobile/content/999/tags",
                             data={"tags": "test"})
        assert response.status_code != 404

class TestSystemIntegration:
    """Test system-level integration."""

    def test_database_initialization(self):
        """Test database can be initialized."""
        import sqlite3

        # Test database connection
        conn = sqlite3.connect(':memory:')
        cursor = conn.cursor()

        # Test content table creation
        cursor.execute("""
            CREATE TABLE content (
                id INTEGER PRIMARY KEY,
                title TEXT,
                content TEXT,
                content_type TEXT,
                created_at TEXT,
                updated_at TEXT,
                tags TEXT,
                archived INTEGER DEFAULT 0
            )
        """)

        # Test insert
        cursor.execute("""
            INSERT INTO content (title, content, content_type, created_at)
            VALUES (?, ?, ?, ?)
        """, ("Test Title", "Test content", "article", "2025-01-01"))

        # Test select
        cursor.execute("SELECT * FROM content WHERE title = ?", ("Test Title",))
        result = cursor.fetchone()
        assert result is not None
        assert result[1] == "Test Title"

        conn.close()

    def test_configuration_loading(self):
        """Test configuration system."""
        from web.app import get_metadata_manager

        mgr = get_metadata_manager()
        assert mgr is not None
        assert hasattr(mgr, 'config')
        assert isinstance(mgr.config, dict)

if __name__ == "__main__":
    pytest.main([__file__, "-v"])