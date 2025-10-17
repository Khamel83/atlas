#!/usr/bin/env python3
"""
Unit tests for Siri Shortcuts functionality
"""

import pytest
import json
import tempfile
import os
from unittest.mock import patch, mock_open
from apple_shortcuts.siri_shortcuts import (
    SiriShortcut,
    ActionType,
    ShortcutTemplate,
    SiriShortcutManager
)


class TestSiriShortcut:
    """Test SiriShortcut dataclass"""

    def test_valid_shortcut_creation(self):
        """Test creating a valid shortcut"""
        shortcut = SiriShortcut(
            name="Test Shortcut",
            phrase="test phrase",
            action=ActionType.LOG_ENTRY,
            parameters={"type": "note"},
            content_types=["text"]
        )

        assert shortcut.name == "Test Shortcut"
        assert shortcut.phrase == "test phrase"
        assert shortcut.action == ActionType.LOG_ENTRY
        assert shortcut.parameters == {"type": "note"}
        assert shortcut.content_types == ["text"]

    def test_empty_name_validation(self):
        """Test validation fails for empty name"""
        with pytest.raises(ValueError, match="Name must be a non-empty string"):
            SiriShortcut(
                name="",
                phrase="test phrase",
                action=ActionType.LOG_ENTRY,
                parameters={},
                content_types=["text"]
            )

    def test_empty_phrase_validation(self):
        """Test validation fails for empty phrase"""
        with pytest.raises(ValueError, match="Phrase must be a non-empty string"):
            SiriShortcut(
                name="Test",
                phrase="",
                action=ActionType.LOG_ENTRY,
                parameters={},
                content_types=["text"]
            )

    def test_invalid_content_type(self):
        """Test validation fails for invalid content type"""
        with pytest.raises(ValueError, match="Invalid content type"):
            SiriShortcut(
                name="Test",
                phrase="test phrase",
                action=ActionType.LOG_ENTRY,
                parameters={},
                content_types=["invalid_type"]
            )

    def test_valid_content_types(self):
        """Test all valid content types work"""
        valid_types = ["URL", "text", "voice", "image", "file", "clipboard", "location", "contact"]

        for content_type in valid_types:
            shortcut = SiriShortcut(
                name=f"Test {content_type}",
                phrase="test phrase",
                action=ActionType.LOG_ENTRY,
                parameters={"type": "note"},
                content_types=[content_type]
            )
            assert content_type in shortcut.content_types

    def test_name_length_validation(self):
        """Test name length validation"""
        with pytest.raises(ValueError, match="Name must be 100 characters or less"):
            SiriShortcut(
                name="a" * 101,  # 101 characters
                phrase="test phrase",
                action=ActionType.LOG_ENTRY,
                parameters={},
                content_types=["text"]
            )

    def test_phrase_length_validation(self):
        """Test phrase length validation"""
        with pytest.raises(ValueError, match="Phrase must be 200 characters or less"):
            SiriShortcut(
                name="Test",
                phrase="a" * 201,  # 201 characters
                action=ActionType.LOG_ENTRY,
                parameters={},
                content_types=["text"]
            )

    def test_log_entry_parameters(self):
        """Test LOG_ENTRY action parameter validation"""
        with pytest.raises(ValueError, match="LOG_ENTRY action requires 'type' parameter"):
            SiriShortcut(
                name="Test",
                phrase="test phrase",
                action=ActionType.LOG_ENTRY,
                parameters={},  # Missing 'type'
                content_types=["text"]
            )

    def test_timer_duration_validation(self):
        """Test START_TIMER duration parameter validation"""
        with pytest.raises(ValueError, match="START_TIMER duration must be a number"):
            SiriShortcut(
                name="Test",
                phrase="test phrase",
                action=ActionType.START_TIMER,
                parameters={"duration": "not_a_number"},
                content_types=["text"]
            )

    def test_voice_memo_transcription_validation(self):
        """Test VOICE_MEMO transcription parameter validation"""
        with pytest.raises(ValueError, match="VOICE_MEMO transcription parameter must be a boolean"):
            SiriShortcut(
                name="Test",
                phrase="test phrase",
                action=ActionType.VOICE_MEMO,
                parameters={"transcription": "not_a_boolean"},
                content_types=["voice"]
            )

    def test_to_dict_conversion(self):
        """Test converting shortcut to dictionary"""
        shortcut = SiriShortcut(
            name="Test",
            phrase="test phrase",
            action=ActionType.LOG_ENTRY,
            parameters={"type": "note"},
            content_types=["text"]
        )

        data = shortcut.to_dict()

        assert data["name"] == "Test"
        assert data["phrase"] == "test phrase"
        assert data["action"] == "log_entry"  # Enum value
        assert data["parameters"] == {"type": "note"}
        assert data["content_types"] == ["text"]


class TestShortcutTemplate:
    """Test ShortcutTemplate class"""

    def test_template_initialization(self):
        """Test template class initializes correctly"""
        template = ShortcutTemplate()
        assert template is not None

    def test_shortcut_file_generation(self):
        """Test generating .shortcut file structure"""
        template = ShortcutTemplate()
        shortcut = SiriShortcut(
            name="Test",
            phrase="test phrase",
            action=ActionType.LOG_ENTRY,
            parameters={"type": "note"},
            content_types=["text"]
        )

        shortcut_data = template.generate_shortcut_file(shortcut)

        assert "WFWorkflowActions" in shortcut_data
        assert "WFWorkflowIcon" in shortcut_data
        assert "WFWorkflowInputContentItemClasses" in shortcut_data
        assert len(shortcut_data["WFWorkflowActions"]) > 0

    def test_voice_capture_template(self):
        """Test voice capture template generation"""
        template = ShortcutTemplate()
        voice_template = template.generate_voice_capture_template()

        assert "WFWorkflowActions" in voice_template
        assert len(voice_template["WFWorkflowActions"]) >= 2
        assert voice_template["WFWorkflowName"] == "Hey Siri, save to Atlas"

    @patch("builtins.open", new_callable=mock_open)
    @patch("json.dump")
    def test_save_shortcut_file(self, mock_json_dump, mock_file):
        """Test saving shortcut to file"""
        template = ShortcutTemplate()
        shortcut = SiriShortcut(
            name="Test",
            phrase="test phrase",
            action=ActionType.LOG_ENTRY,
            parameters={"type": "note"},
            content_types=["text"]
        )

        filepath = template.save_shortcut_file(shortcut, "test.shortcut")

        mock_file.assert_called_once_with("test.shortcut", "w")
        mock_json_dump.assert_called_once()
        assert filepath == "test.shortcut"

    @patch("builtins.open", new_callable=mock_open)
    @patch("json.dump")
    def test_save_voice_template(self, mock_json_dump, mock_file):
        """Test saving voice template to file"""
        template = ShortcutTemplate()

        filepath = template.save_voice_template("voice.shortcut")

        mock_file.assert_called_once_with("voice.shortcut", "w")
        mock_json_dump.assert_called_once()
        assert filepath == "voice.shortcut"


class TestSiriShortcutManager:
    """Test SiriShortcutManager class"""

    def test_manager_initialization(self):
        """Test manager initializes with shortcuts directory"""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = SiriShortcutManager(temp_dir)
            assert manager.shortcuts_dir == temp_dir
            assert os.path.exists(temp_dir)

    @patch("os.makedirs")
    def test_create_shortcut_success(self, mock_makedirs):
        """Test successful shortcut creation"""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = SiriShortcutManager(temp_dir)

            filepath = manager.create_shortcut(
                name="TestShortcut",
                phrase="test phrase",
                action=ActionType.LOG_ENTRY,
                parameters={"type": "note"},
                content_types=["text"]
            )

            assert filepath.endswith("TestShortcut.json")
            assert os.path.exists(filepath)

    def test_create_shortcut_invalid_parameters(self):
        """Test shortcut creation with invalid parameters"""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = SiriShortcutManager(temp_dir)

            with pytest.raises(ValueError):
                manager.create_shortcut(
                    name="",  # Invalid empty name
                    phrase="test phrase",
                    action=ActionType.LOG_ENTRY
                )

    def test_create_voice_capture_shortcut(self):
        """Test voice capture shortcut creation"""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = SiriShortcutManager(temp_dir)

            filepath = manager.create_voice_capture_shortcut()

            assert filepath.endswith("hey_siri_save_to_atlas.shortcut")
            assert os.path.exists(filepath)

    def test_list_shortcuts_empty(self):
        """Test listing shortcuts when none exist"""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = SiriShortcutManager(temp_dir)

            shortcuts = manager.list_shortcuts()

            assert shortcuts == {}

    def test_list_shortcuts_with_data(self):
        """Test listing shortcuts when some exist"""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = SiriShortcutManager(temp_dir)

            # Create a test shortcut
            manager.create_shortcut(
                name="TestShortcut",
                phrase="test phrase",
                action=ActionType.LOG_ENTRY,
                parameters={"type": "note"},
                content_types=["text"]
            )

            shortcuts = manager.list_shortcuts()

            assert "TestShortcut" in shortcuts
            assert shortcuts["TestShortcut"]["name"] == "TestShortcut"

    def test_validate_shortcut_file_missing(self):
        """Test validating non-existent shortcut"""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = SiriShortcutManager(temp_dir)

            result = manager.validate_shortcut_file("nonexistent")

            assert result["valid"] is False
            assert "not found" in result["error"]

    def test_validate_shortcut_file_valid(self):
        """Test validating valid shortcut file"""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = SiriShortcutManager(temp_dir)

            # Create valid shortcut
            manager.create_shortcut(
                name="ValidShortcut",
                phrase="test phrase",
                action=ActionType.LOG_ENTRY,
                parameters={"type": "note"},
                content_types=["text"]
            )

            result = manager.validate_shortcut_file("ValidShortcut")

            assert result["valid"] is True
            assert "valid" in result["message"].lower()

    @patch("os.getenv")
    def test_process_voice_memo_no_transcription(self, mock_getenv):
        """Test voice memo processing without transcription services"""
        mock_getenv.return_value = None  # No API keys

        with tempfile.TemporaryDirectory() as temp_dir:
            manager = SiriShortcutManager(temp_dir)

            # Create dummy audio data
            audio_data = b"fake_audio_data" * 100

            result = manager.process_voice_memo(audio_data)

            assert "status" in result
            assert "transcript" in result
            assert "confidence" in result

    def test_categorize_speech_content(self):
        """Test speech content categorization"""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = SiriShortcutManager(temp_dir)

            # Test meeting content
            meeting_transcript = "We need to schedule a meeting to discuss the project"
            categories = manager._categorize_speech_content(meeting_transcript)
            assert "meeting" in categories
            assert "work" in categories

            # Test personal content
            personal_transcript = "I need to call my family tonight"
            categories = manager._categorize_speech_content(personal_transcript)
            assert "personal" in categories

            # Test empty transcript
            categories = manager._categorize_speech_content("")
            assert categories == ["personal"]  # Default category


if __name__ == "__main__":
    pytest.main([__file__, "-v"])