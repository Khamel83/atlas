"""Test web interface endpoints for Atlas."""

import pytest
import httpx
import asyncio
from fastapi.testclient import TestClient
import sys
import os
import tempfile
import sqlite3

# Add Atlas to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Create test database before importing web app
test_db_path = 'test_web_atlas.db'
conn = sqlite3.connect(test_db_path)
cursor = conn.cursor()

# Create content table
cursor.execute('''
    CREATE TABLE IF NOT EXISTS content (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        url TEXT UNIQUE,
        title TEXT,
        content TEXT,
        content_type TEXT,
        source TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        tags TEXT,
        archived INTEGER DEFAULT 0,
        metadata TEXT
    )
''')

# Insert test data
cursor.execute('''
    INSERT OR IGNORE INTO content (url, title, content, content_type, source)
    VALUES (?, ?, ?, ?, ?)
''', ('https://example.com/test', 'Test Article', 'Test content', 'article', 'test'))

conn.commit()
conn.close()

# Set environment for test
os.environ['ATLAS_DB_PATH'] = test_db_path
os.environ['TESTING'] = 'true'

from web.app import app

client = TestClient(app)

class TestWebEndpoints:

    def test_mobile_dashboard_loads(self):
        """Test mobile dashboard loads without errors."""
        response = client.get("/mobile")
        assert response.status_code == 200
        assert "Atlas - Cognitive AI" in response.text

    def test_desktop_dashboard_loads(self):
        """Test desktop dashboard loads without errors."""
        response = client.get("/ask/html")
        assert response.status_code == 200

    def test_mobile_proactive_feature(self):
        """Test proactive feature doesn't crash."""
        response = client.get("/mobile?feature=proactive")
        assert response.status_code == 200
        assert "Proactive Content Surfacer" in response.text

    def test_mobile_temporal_feature(self):
        """Test temporal feature doesn't crash."""
        response = client.get("/mobile?feature=temporal")
        assert response.status_code == 200
        assert "Temporal Relationships" in response.text

    def test_mobile_recall_feature(self):
        """Test recall feature doesn't crash."""
        response = client.get("/mobile?feature=recall")
        assert response.status_code == 200
        assert "Active Recall" in response.text

    def test_mobile_patterns_feature(self):
        """Test patterns feature doesn't crash."""
        response = client.get("/mobile?feature=patterns")
        assert response.status_code == 200
        assert "Pattern Detection" in response.text

    def test_mobile_socratic_feature(self):
        """Test socratic feature doesn't crash."""
        response = client.get("/mobile?feature=socratic")
        assert response.status_code == 200
        assert "Socratic Question Generator" in response.text

    def test_mobile_browse_feature(self):
        """Test browse feature doesn't crash."""
        response = client.get("/mobile?feature=browse")
        assert response.status_code == 200
        assert "Browse Content" in response.text

    def test_content_search_with_filters(self):
        """Test content search with various filters."""
        # Test with search query
        response = client.get("/mobile?feature=browse&search=test")
        assert response.status_code == 200

        # Test with date filter
        response = client.get("/mobile?feature=browse&date_filter=week")
        assert response.status_code == 200

        # Test with type filter
        response = client.get("/mobile?feature=browse&type_filter=article")
        assert response.status_code == 200

    def test_content_management_apis_exist(self):
        """Test content management API endpoints exist."""
        # These should return method not allowed or specific error, not 404
        response = client.delete("/mobile/content/999")
        assert response.status_code != 404

        response = client.post("/mobile/content/999/archive")
        assert response.status_code != 404

    def test_socratic_post_endpoint(self):
        """Test socratic question generation endpoint."""
        response = client.post("/mobile", data={"feature": "socratic", "content": "Test content for questions"})
        assert response.status_code == 200

    def test_jobs_interface(self):
        """Test jobs management interface."""
        response = client.get("/jobs/html")
        assert response.status_code == 200

    def test_api_endpoints(self):
        """Test API endpoints return JSON."""
        response = client.get("/ask/proactive")
        assert response.status_code == 200
        assert response.headers.get("content-type") == "application/json"

        response = client.get("/ask/patterns")
        assert response.status_code == 200
        assert response.headers.get("content-type") == "application/json"

class TestMobileInterface:

    def test_mobile_responsiveness(self):
        """Test mobile interface has responsive design."""
        response = client.get("/mobile")
        assert response.status_code == 200
        assert "viewport" in response.text
        assert "mobile-first" in response.text.lower()

    def test_touch_optimized_elements(self):
        """Test mobile interface has touch-optimized elements."""
        response = client.get("/mobile")
        assert response.status_code == 200
        assert "action-btn" in response.text
        assert "nav-tab" in response.text

    def test_filter_persistence(self):
        """Test that filters maintain state."""
        response = client.get("/mobile?feature=browse&type_filter=article")
        assert response.status_code == 200
        assert 'selected' in response.text or 'article' in response.text

if __name__ == "__main__":
    pytest.main([__file__, "-v"])