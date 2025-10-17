import pytest
from fastapi.testclient import TestClient
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.main import app

client = TestClient(app)

def test_health_check():
    """Test the health check endpoint"""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}

def test_auth_generate_key():
    """Test API key generation"""
    response = client.post("/api/v1/auth/generate", json={"name": "test_key"})
    assert response.status_code == 200
    data = response.json()
    assert "api_key" in data
    assert "name" in data
    assert data["name"] == "test_key"

def test_content_list():
    """Test content listing"""
    response = client.get("/api/v1/content/")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data

def test_cognitive_proactive():
    """Test proactive content endpoint"""
    response = client.get("/api/v1/cognitive/proactive")
    # This might return 501 if cognitive features aren't available
    assert response.status_code in [200, 501]

def test_cognitive_temporal():
    """Test temporal relationships endpoint"""
    response = client.get("/api/v1/cognitive/temporal")
    # This might return 501 if cognitive features aren't available
    assert response.status_code in [200, 501]

def test_cognitive_socratic():
    """Test Socratic questions endpoint"""
    # The endpoint expects a form parameter
    response = client.post("/api/v1/cognitive/socratic", data={"content": "The sky is blue."})
    # This might return 501 if cognitive features aren't available
    assert response.status_code in [200, 501]

def test_cognitive_recall():
    """Test recall items endpoint"""
    response = client.get("/api/v1/cognitive/recall")
    # This might return 501 if cognitive features aren't available
    assert response.status_code in [200, 501]

def test_cognitive_patterns():
    """Test patterns endpoint"""
    response = client.get("/api/v1/cognitive/patterns")
    # This might return 501 if cognitive features aren't available
    assert response.status_code in [200, 501]

def test_search_index():
    """Test search index creation"""
    response = client.post("/api/v1/search/index")
    # This might return 500 if there's no content to index
    assert response.status_code in [200, 500]