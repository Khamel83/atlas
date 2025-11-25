"""Pytest configuration and fixtures for Atlas API tests."""

import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, AsyncMock
import json
from datetime import datetime

# Add web/api to Python path
import sys
web_api_path = Path(__file__).parent.parent / "web" / "api"
sys.path.insert(0, str(web_api_path))

@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    temp_path = tempfile.mkdtemp()
    yield Path(temp_path)
    shutil.rmtree(temp_path)


@pytest.fixture
def sample_trojanhorse_note():
    """Sample TrojanHorse note for testing."""
    return {
        "id": "test-note-123",
        "path": "/Users/user/WorkVault/Processed/work/meetings/2024/test-note.md",
        "title": "Project Sync Meeting",
        "source": "drafts",
        "raw_type": "meeting_transcript",
        "class_type": "work",
        "category": "meeting",
        "project": "project-x",
        "tags": ["project-x", "sync", "weekly"],
        "created_at": "2024-01-15T14:30:00.000Z",
        "updated_at": "2024-01-15T14:35:00.000Z",
        "summary": "Weekly project sync meeting discussing timeline and blockers",
        "body": "# Project Sync Meeting\n\n## Attendees\n- John (PM)\n- Sarah (Dev)\n- Mike (Designer)\n\n## Discussion\nDiscussed the Q1 roadmap and timeline for the payment integration project.",
        "frontmatter": {
            "meeting_type": "weekly_sync",
            "duration_minutes": 45,
            "priority": "high",
            "attendees": ["John", "Sarah", "Mike"]
        }
    }


@pytest.fixture
def sample_trojanhorse_notes_batch():
    """Sample batch of TrojanHorse notes for testing."""
    return [
        {
            "id": "note-1",
            "title": "Meeting: Project Planning",
            "body": "# Project Planning Meeting\n\nDiscussed Q1 objectives and timeline.",
            "category": "meeting",
            "project": "project-x",
            "tags": ["planning", "q1"],
            "class_type": "work",
            "source": "drafts"
        },
        {
            "id": "note-2",
            "title": "Idea: Mobile App Feature",
            "body": "# Mobile App Idea\n\nAdd real-time notifications to improve user engagement.",
            "category": "idea",
            "project": "mobile-app",
            "tags": ["idea", "mobile", "notifications"],
            "class_type": "work",
            "source": "macwhisper"
        },
        {
            "id": "note-3",
            "title": "Task: Fix Payment Bug",
            "body": "# Payment Bug Fix\n\nCritical issue in payment processing needs immediate attention.",
            "category": "task",
            "project": "payments",
            "tags": ["bug", "urgent", "payments"],
            "class_type": "work",
            "source": "clipboard"
        }
    ]


@pytest.fixture
def mock_simple_database():
    """Mock SimpleDatabase for testing."""
    db = Mock()

    # Mock connection context manager
    mock_conn = Mock()
    mock_cursor = Mock()

    def get_connection():
        from contextlib import contextmanager

        @contextmanager
        def _context():
            yield mock_conn
        return _context()

    db.get_connection = get_connection
    mock_conn.__enter__ = Mock(return_value=mock_conn)
    mock_conn.__exit__ = Mock(return_value=None)
    mock_conn.execute = Mock(return_value=mock_cursor)
    mock_cursor.fetchone = Mock()
    mock_cursor.fetchall = Mock()

    return db


@pytest.fixture
def mock_env_vars(monkeypatch):
    """Mock environment variables for testing."""
    monkeypatch.setenv("ATLAS_API_KEY", "test-api-key")
    monkeypatch.setenv("ATLAS_VAULT", "/test/atlas")
    return monkeypatch


@pytest.fixture
def test_client():
    """Create a test client for Atlas FastAPI app."""
    from fastapi.testclient import TestClient
    from main import app

    # Mock database dependencies
    with patch('helpers.simple_database.SimpleDatabase'):
        return TestClient(app)


@pytest.fixture
async def async_test_client():
    """Create an async test client for Atlas FastAPI app."""
    import httpx
    from main import app

    # Mock database dependencies
    with patch('helpers.simple_database.SimpleDatabase'):
        async with httpx.AsyncClient(app=app, base_url="http://test") as client:
            yield client


@pytest.fixture
def sample_atlas_stats():
    """Sample Atlas statistics response."""
    return {
        "trojanhorse_stats": {
            "total_notes": 1250,
            "work_notes": 890,
            "personal_notes": 360,
            "meeting_notes": 234,
            "idea_notes": 189,
            "task_notes": 145,
            "unique_projects": 12
        },
        "recent_activity": [
            {
                "title": "Project Sync Meeting",
                "created_at": "2024-01-15T14:30:00.000Z",
                "category": "meeting"
            },
            {
                "title": "New Feature Idea",
                "created_at": "2024-01-15T11:20:00.000Z",
                "category": "idea"
            }
        ],
        "project_breakdown": [
            {
                "project": "project-x",
                "count": 89
            },
            {
                "project": "dashboard",
                "count": 45
            },
            {
                "project": "payments",
                "count": 23
            }
        ]
    }


@pytest.fixture
def create_test_file(temp_dir):
    """Helper function to create test files."""
    def _create_file(filename: str, content: str = "Test content"):
        file_path = temp_dir / filename
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content)
        return file_path
    return _create_file


@pytest.fixture
def invalid_trojanhorse_note():
    """Invalid TrojanHorse note for validation testing."""
    return {
        "id": "",  # Empty ID should fail validation
        "title": "Test Note",
        "body": "Content here",
        "category": "test",
        "project": "test"
    }


@pytest.fixture
def oversized_trojanhorse_note():
    """Oversized TrojanHorse note for size limit testing."""
    return {
        "id": "oversized-note",
        "title": "Oversized Note",
        "body": "x" * 2000000,  # 2MB+ content should fail validation
        "category": "test",
        "project": "test"
    }


@pytest.fixture
def trojanhorse_note_with_many_tags():
    """TrojanHorse note with too many tags for validation testing."""
    return {
        "id": "many-tags-note",
        "title": "Note with Many Tags",
        "body": "Content here",
        "category": "test",
        "project": "test",
        "tags": [f"tag-{i}" for i in range(100)]  # 100 tags should fail validation
    }


# Mock the SimpleDatabase import for all tests
@pytest.fixture(autouse=True)
def mock_database_import():
    """Automatically mock SimpleDatabase import for all tests."""
    with patch('helpers.simple_database.SimpleDatabase'):
        yield
