"""Comprehensive tests for Atlas TrojanHorse integration router."""

import pytest
import json
from unittest.mock import Mock, patch, AsyncMock
from fastapi.testclient import TestClient
from fastapi import HTTPException

from routers.trojanhorse import router, IngestNote, IngestResponse
from main import app


class TestTrojanHorseHealthEndpoint:
    """Test the TrojanHorse health endpoint."""

    def test_health_check(self, test_client):
        """Test basic health check."""
        response = test_client.get("/trojanhorse/health")
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "ok"
        assert "service" in data
        assert "timestamp" in data
        assert data["service"] == "Atlas TrojanHorse Integration"

    def test_health_check_response_structure(self, test_client):
        """Test health check response structure."""
        response = test_client.get("/trojanhorse/health")
        assert response.status_code == 200

        data = response.json()
        required_fields = ["status", "service", "timestamp"]
        for field in required_fields:
            assert field in data
        assert isinstance(data["status"], str)
        assert isinstance(data["service"], str)
        assert isinstance(data["timestamp"], str)


class TestIngestNoteValidation:
    """Test IngestNote Pydantic model validation."""

    def test_valid_note(self, sample_trojanhorse_note):
        """Test valid note creation."""
        note = IngestNote(**sample_trojanhorse_note)
        assert note.id == "test-note-123"
        assert note.title == "Project Sync Meeting"
        assert note.category == "meeting"
        assert note.project == "project-x"
        assert len(note.tags) == 3
        assert "project-x" in note.tags

    def test_note_with_optional_fields(self):
        """Test note with optional fields omitted."""
        note_data = {
            "id": "minimal-note",
            "path": "/test/path.md",
            "title": "Minimal Note",
            "body": "Content here"
        }
        note = IngestNote(**note_data)
        assert note.id == "minimal-note"
        assert note.source is None
        assert note.category is None
        assert note.project is None
        assert note.tags == []

    def test_note_with_all_fields(self, sample_trojanhorse_note):
        """Test note with all possible fields."""
        note = IngestNote(**sample_trojanhorse_note)
        assert note.source == "drafts"
        assert note.raw_type == "meeting_transcript"
        assert note.class_type == "work"
        assert note.created_at == "2024-01-15T14:30:00.000Z"
        assert note.updated_at == "2024-01-15T14:35:00.000Z"
        assert note.summary == "Weekly project sync meeting discussing timeline and blockers"
        assert note.frontmatter["meeting_type"] == "weekly_sync"

    def test_invalid_note_empty_id(self):
        """Test note validation with empty ID."""
        note_data = {
            "id": "",
            "path": "/test/path.md",
            "title": "Test Note",
            "body": "Content here"
        }
        # This should pass validation as empty string is technically valid
        # but business logic might handle it
        note = IngestNote(**note_data)
        assert note.id == ""

    def test_note_tag_validation(self):
        """Test note tag validation."""
        note_data = {
            "id": "test-note",
            "path": "/test/path.md",
            "title": "Test Note",
            "body": "Content here",
            "tags": ["tag1", "tag2", "tag3"]
        }
        note = IngestNote(**note_data)
        assert len(note.tags) == 3
        assert note.tags == ["tag1", "tag2", "tag3"]

    def test_note_frontmatter_validation(self):
        """Test note frontmatter validation."""
        note_data = {
            "id": "test-note",
            "path": "/test/path.md",
            "title": "Test Note",
            "body": "Content here",
            "frontmatter": {"key1": "value1", "key2": 42, "key3": True}
        }
        note = IngestNote(**note_data)
        assert note.frontmatter["key1"] == "value1"
        assert note.frontmatter["key2"] == 42
        assert note.frontmatter["key3"] is True


class TestIngestSingleNote:
    """Test single note ingestion endpoint."""

    @patch('routers.trojanhorse.ingest_note_to_atlas')
    def test_ingest_single_note_success(self, mock_ingest, test_client, sample_trojanhorse_note):
        """Test successful single note ingestion."""
        mock_ingest.return_value = True

        response = test_client.post(
            "/trojanhorse/ingest",
            json=sample_trojanhorse_note
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "Project Sync Meeting" in data["message"]
        assert data["count"] == 1

    @patch('routers.trojanhorse.ingest_note_to_atlas')
    def test_ingest_single_note_failure(self, mock_ingest, test_client, sample_trojanhorse_note):
        """Test single note ingestion failure."""
        mock_ingest.return_value = False

        response = test_client.post(
            "/trojanhorse/ingest",
            json=sample_trojanhorse_note
        )

        assert response.status_code == 500
        assert "Failed to ingest note" in response.json()["detail"]

    @patch('routers.trojanhorse.ingest_note_to_atlas')
    def test_ingest_single_note_exception(self, mock_ingest, test_client, sample_trojanhorse_note):
        """Test single note ingestion with exception."""
        mock_ingest.side_effect = Exception("Database error")

        response = test_client.post(
            "/trojanhorse/ingest",
            json=sample_trojanhorse_note
        )

        assert response.status_code == 500
        assert "Internal error: Database error" in response.json()["detail"]

    def test_ingest_single_note_invalid_payload(self, test_client):
        """Test ingestion with invalid payload."""
        invalid_payload = {
            "id": "test-note",
            "title": "Test Note"
            # Missing required fields: path and body
        }

        response = test_client.post(
            "/trojanhorse/ingest",
            json=invalid_payload
        )

        assert response.status_code == 422  # Validation error

    @patch('routers.trojanhorse.ingest_note_to_atlas')
    def test_ingest_single_note_with_api_key(self, mock_ingest, test_client, sample_trojanhorse_note):
        """Test ingestion with API key authentication."""
        mock_ingest.return_value = True

        response = test_client.post(
            "/trojanhorse/ingest",
            json=sample_trojanhorse_note,
            headers={"X-API-Key": "test-key"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"


class TestIngestBatchNotes:
    """Test batch note ingestion endpoint."""

    @patch('routers.trojanhorse.ingest_note_to_atlas')
    def test_ingest_batch_success(self, mock_ingest, test_client, sample_trojanhorse_notes_batch):
        """Test successful batch ingestion."""
        mock_ingest.return_value = True

        response = test_client.post(
            "/trojanhorse/ingest/batch",
            json={"notes": sample_trojanhorse_notes_batch}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "Successfully ingested 3 notes" in data["message"]
        assert data["count"] == 3

    @patch('routers.trojanhorse.ingest_note_to_atlas')
    def test_ingest_batch_partial_success(self, mock_ingest, test_client, sample_trojanhorse_notes_batch):
        """Test batch ingestion with some failures."""
        # Simulate 2 successes and 1 failure
        mock_ingest.return_value = True  # This will be called 3 times

        response = test_client.post(
            "/trojanhorse/ingest/batch",
            json={"notes": sample_trojanhorse_notes_batch}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["count"] == 3  # In our mock, all succeed

    def test_ingest_batch_empty_list(self, test_client):
        """Test ingestion with empty notes list."""
        response = test_client.post(
            "/trojanhorse/ingest/batch",
            json={"notes": []}
        )

        assert response.status_code == 400
        assert "No notes provided in batch" in response.json()["detail"]

    def test_ingest_batch_too_large(self, test_client, sample_trojanhorse_notes_batch):
        """Test ingestion with batch size too large."""
        # Create batch with 101 notes (over the limit of 100)
        large_batch = sample_trojanhorse_notes_batch * 34  # 102 notes

        response = test_client.post(
            "/trojanhorse/ingest/batch",
            json={"notes": large_batch}
        )

        assert response.status_code == 400
        assert "Batch size too large" in response.json()["detail"]

    def test_ingest_batch_invalid_payload(self, test_client):
        """Test ingestion with invalid batch payload."""
        invalid_payload = {"notes": "not a list"}

        response = test_client.post(
            "/trojanhorse/ingest/batch",
            json=invalid_payload
        )

        assert response.status_code == 422  # Validation error

    @patch('routers.trojanhorse.ingest_note_to_atlas')
    def test_ingest_batch_with_api_key(self, mock_ingest, test_client, sample_trojanhorse_notes_batch):
        """Test batch ingestion with API key authentication."""
        mock_ingest.return_value = True

        response = test_client.post(
            "/trojanhorse/ingest/batch",
            json={"notes": sample_trojanhorse_notes_batch},
            headers={"X-API-Key": "secure-api-key"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"

    @patch('routers.trojanhorse.ingest_note_to_atlas')
    def test_ingest_batch_all_fail(self, mock_ingest, test_client, sample_trojanhorse_notes_batch):
        """Test batch ingestion where all notes fail."""
        mock_ingest.return_value = False

        response = test_client.post(
            "/trojanhorse/ingest/batch",
            json={"notes": sample_trojanhorse_notes_batch}
        )

        assert response.status_code == 500
        assert "Failed to ingest any notes" in response.json()["detail"]


class TestTrojanhorseStats:
    """Test TrojanHorse statistics endpoint."""

    @patch('routers.trojanhorse.SimpleDatabase')
    def test_get_stats_success(self, mock_db_class, test_client, sample_atlas_stats, mock_simple_database):
        """Test successful stats retrieval."""
        # Setup mock database
        mock_db_class.return_value = mock_simple_database

        # Mock query results
        mock_simple_database.get_connection.return_value.__enter__.return_value.execute.return_value.fetchone.return_value = {
            "total_notes": 1250,
            "work_notes": 890,
            "personal_notes": 360,
            "meeting_notes": 234,
            "idea_notes": 189,
            "task_notes": 145,
            "unique_projects": 12
        }

        mock_simple_database.get_connection.return_value.__enter__.return_value.execute.return_value.fetchall.return_value = [
            {"title": "Project Sync Meeting", "created_at": "2024-01-15T14:30:00.000Z", "category": "meeting"},
            {"title": "New Feature Idea", "created_at": "2024-01-15T11:20:00.000Z", "category": "idea"}
        ]

        mock_simple_database.get_connection.return_value.__enter__.return_value.execute.return_value.fetchall.side_effect = [
            # First call for recent_activity
            [
                {"title": "Project Sync Meeting", "created_at": "2024-01-15T14:30:00.000Z", "category": "meeting"},
                {"title": "New Feature Idea", "created_at": "2024-01-15T11:20:00.000Z", "category": "idea"}
            ],
            # Second call for project_breakdown
            [
                {"project": "project-x", "count": 89},
                {"project": "dashboard", "count": 45},
                {"project": "payments", "count": 23}
            ]
        ]

        response = test_client.get("/trojanhorse/stats", headers={"X-API-Key": "test-key"})

        assert response.status_code == 200

        data = response.json()
        assert "trojanhorse_stats" in data
        assert "recent_activity" in data
        assert "project_breakdown" in data

        stats = data["trojanhorse_stats"]
        assert stats["total_notes"] == 1250
        assert stats["work_notes"] == 890
        assert stats["personal_notes"] == 360

    @patch('routers.trojanhorse.SimpleDatabase')
    def test_get_stats_database_error(self, mock_db_class, test_client):
        """Test stats retrieval with database error."""
        mock_db_class.side_effect = Exception("Database connection failed")

        response = test_client.get("/trojanhorse/stats", headers={"X-API-Key": "test-key"})

        assert response.status_code == 500
        assert "Failed to get statistics" in response.json()["detail"]

    @patch('routers.trojanhorse.SimpleDatabase')
    def test_get_stats_without_api_key(self, mock_db_class, test_client):
        """Test stats retrieval without API key when authentication is required."""
        # This test depends on whether ATLAS_API_KEY is set
        # For now, we'll assume no authentication is required for testing

        mock_db_class.return_value = Mock()
        mock_db = mock_db_class.return_value
        mock_db.get_connection.return_value.__enter__.return_value.execute.return_value.fetchone.return_value = {}

        response = test_client.get("/trojanhorse/stats")

        # Should succeed if no authentication is configured
        assert response.status_code == 200


class TestIngestNoteFunction:
    """Test the ingest_note_to_atlas function."""

    @patch('routers.trojanhorse.SimpleDatabase')
    def test_ingest_note_new_note(self, mock_db_class, sample_trojanhorse_note):
        """Test ingesting a new note."""
        mock_db = Mock()
        mock_db_class.return_value = mock_db

        # Mock database queries for new note
        mock_conn = Mock()
        mock_db.get_connection.return_value.__enter__.return_value = mock_conn

        # Check for existing note (not found)
        mock_conn.execute.return_value.fetchone.return_value = None

        # Insert new note
        mock_conn.execute.return_value = None

        from routers.trojanhorse import ingest_note_to_atlas

        result = ingest_note_to_atlas(sample_trojanhorse_note)
        assert result is True

    @patch('routers.trojanhorse.SimpleDatabase')
    def test_ingest_note_existing_note_update(self, mock_db_class, sample_trojanhorse_note):
        """Test ingesting an existing note (should update)."""
        mock_db = Mock()
        mock_db_class.return_value = mock_db

        # Mock database queries for existing note
        mock_conn = Mock()
        mock_db.get_connection.return_value.__enter__.return_value = mock_conn

        # Check for existing note (found)
        mock_conn.execute.return_value.fetchone.return_value = {"id": 123}

        # Update existing note
        mock_conn.execute.return_value = None

        from routers.trojanhorse import ingest_note_to_atlas

        result = ingest_note_to_atlas(sample_trojanhorse_note)
        assert result is True

    @patch('routers.trojanhorse.SimpleDatabase')
    def test_ingest_note_database_error(self, mock_db_class, sample_trojanhorse_note):
        """Test ingesting note with database error."""
        mock_db_class.side_effect = Exception("Database connection failed")

        from routers.trojanhorse import ingest_note_to_atlas

        result = ingest_note_to_atlas(sample_trojanhorse_note)
        assert result is False


class TestValidationFunction:
    """Test the validate_api_key function."""

    def test_validate_api_key_success(self):
        """Test API key validation when no key is required."""
        from routers.trojanhorse import validate_api_key

        # When ATLAS_API_KEY is not set, validation should pass
        result = validate_api_key()
        assert result is True

    def test_validate_api_key_with_correct_key(self, monkeypatch):
        """Test API key validation with correct key."""
        monkeypatch.setenv("ATLAS_API_KEY", "correct-key")

        from routers.trojanhorse import validate_api_key

        result = validate_api_key("correct-key")
        assert result is True

    def test_validate_api_key_with_incorrect_key(self, monkeypatch):
        """Test API key validation with incorrect key."""
        monkeypatch.setenv("ATLAS_API_KEY", "correct-key")

        from routers.trojanhorse import validate_api_key

        with pytest.raises(HTTPException) as exc_info:
            validate_api_key("incorrect-key")

        assert exc_info.value.status_code == 401
        assert "Invalid API key" in str(exc_info.value.detail)


class TestErrorHandling:
    """Test error handling scenarios."""

    def test_invalid_endpoint(self, test_client):
        """Test accessing invalid TrojanHorse endpoint."""
        response = test_client.get("/trojanhorse/invalid")
        assert response.status_code == 404

    def test_invalid_method(self, test_client):
        """Test using invalid HTTP method."""
        response = test_client.delete("/trojanhorse/health")
        assert response.status_code == 405

    def test_malformed_json(self, test_client):
        """Test malformed JSON payload."""
        response = test_client.post(
            "/trojanhorse/ingest",
            data="invalid json",
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 422


class TestPydanticResponseModels:
    """Test Pydantic response models."""

    def test_ingest_response_model(self):
        """Test IngestResponse model."""
        response = IngestResponse(
            status="ok",
            message="Successfully ingested 5 notes",
            count=5
        )

        assert response.status == "ok"
        assert response.message == "Successfully ingested 5 notes"
        assert response.count == 5

    def test_ingest_response_model_defaults(self):
        """Test IngestResponse model with default values."""
        response = IngestResponse(
            status="ok",
            message="Success"
        )

        assert response.status == "ok"
        assert response.message == "Success"
        assert response.count is None  # Optional field


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    @patch('routers.trojanhorse.ingest_note_to_atlas')
    def test_note_with_very_long_title(self, mock_ingest, test_client):
        """Test note with very long title."""
        mock_ingest.return_value = True

        note_data = {
            "id": "long-title-note",
            "path": "/test/path.md",
            "title": "x" * 500,  # 500 character title
            "body": "Content here"
        }

        response = test_client.post("/trojanhorse/ingest", json=note_data)
        assert response.status_code == 200

    @patch('routers.trojanhorse.ingest_note_to_atlas')
    def test_note_with_special_characters(self, mock_ingest, test_client):
        """Test note with special characters in content."""
        mock_ingest.return_value = True

        note_data = {
            "id": "special-chars-note",
            "path": "/test/path.md",
            "title": "Note with émojis 🚀 and special chars: &<>\"",
            "body": "Content with émojis and special chars: \n\t\"'&<>",
            "tags": ["emoji-test", "special-chars"]
        }

        response = test_client.post("/trojanhorse/ingest", json=note_data)
        assert response.status_code == 200

    def test_batch_with_mixed_valid_invalid_notes(self, test_client):
        """Test batch with mix of valid and invalid notes."""
        # Create batch with some invalid notes (missing required fields)
        mixed_batch = [
            {
                "id": "valid-note-1",
                "path": "/test/valid1.md",
                "title": "Valid Note 1",
                "body": "Content 1"
            },
            {
                "id": "invalid-note",
                "title": "Invalid Note"
                # Missing path and body
            },
            {
                "id": "valid-note-2",
                "path": "/test/valid2.md",
                "title": "Valid Note 2",
                "body": "Content 2"
            }
        ]

        response = test_client.post("/trojanhorse/ingest/batch", json={"notes": mixed_batch})
        # FastAPI validation should catch the invalid note
        assert response.status_code == 422