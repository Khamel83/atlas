"""
Unit tests for the retry_queue module.
"""

import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

import pytest

# Add the project root directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Import the module, but patch the QUEUE_PATH to use a temporary file
import helpers.retry_queue
from helpers.retry_queue import dequeue, enqueue


@pytest.fixture
def temp_queue_dir():
    """Create a temporary directory for the queue file."""
    temp_dir = tempfile.mkdtemp()
    original_queue_path = helpers.retry_queue.QUEUE_PATH

    # Update the module's QUEUE_PATH to use the temporary directory
    helpers.retry_queue.QUEUE_PATH = Path(temp_dir) / "queue.jsonl"

    yield temp_dir

    # Restore the original QUEUE_PATH and clean up
    helpers.retry_queue.QUEUE_PATH = original_queue_path
    shutil.rmtree(temp_dir)


class TestRetryQueue:
    """Test cases for the retry_queue module."""

    def test_enqueue(self, temp_queue_dir):
        """Test enqueueing an item."""
        task = {"type": "test", "url": "https://example.com", "error": "Test error"}
        enqueue(task)

        # Check that the queue file was created
        queue_path = Path(temp_queue_dir) / "queue.jsonl"
        assert queue_path.exists()

        # Check that the task was written to the file
        with open(queue_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
            assert len(lines) == 1
            assert json.loads(lines[0]) == task

    def test_enqueue_multiple(self, temp_queue_dir):
        """Test enqueueing multiple items."""
        tasks = [
            {"type": "test1", "url": "https://example1.com", "error": "Test error 1"},
            {"type": "test2", "url": "https://example2.com", "error": "Test error 2"},
            {"type": "test3", "url": "https://example3.com", "error": "Test error 3"},
        ]

        for task in tasks:
            enqueue(task)

        # Check that all tasks were written to the file
        queue_path = Path(temp_queue_dir) / "queue.jsonl"
        with open(queue_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
            assert len(lines) == 3
            for i, line in enumerate(lines):
                assert json.loads(line) == tasks[i]

    def test_dequeue_empty(self, temp_queue_dir):
        """Test dequeuing from an empty queue."""
        # Queue file doesn't exist yet
        result = dequeue()
        assert result is None

        # Create empty queue file
        queue_path = Path(temp_queue_dir) / "queue.jsonl"
        queue_path.touch()

        # Try to dequeue from empty file
        result = dequeue()
        assert result is None

    def test_dequeue(self, temp_queue_dir):
        """Test dequeuing an item."""
        task = {"type": "test", "url": "https://example.com", "error": "Test error"}

        # Create queue file with one task
        queue_path = Path(temp_queue_dir) / "queue.jsonl"
        with open(queue_path, "w", encoding="utf-8") as f:
            f.write(json.dumps(task) + "\n")

        # Dequeue the task
        result = dequeue()
        assert result == task

        # Check that the queue is now empty
        with open(queue_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
            assert len(lines) == 0

    def test_dequeue_multiple(self, temp_queue_dir):
        """Test dequeuing multiple items."""
        tasks = [
            {"type": "test1", "url": "https://example1.com", "error": "Test error 1"},
            {"type": "test2", "url": "https://example2.com", "error": "Test error 2"},
            {"type": "test3", "url": "https://example3.com", "error": "Test error 3"},
        ]

        # Create queue file with multiple tasks
        queue_path = Path(temp_queue_dir) / "queue.jsonl"
        with open(queue_path, "w", encoding="utf-8") as f:
            for task in tasks:
                f.write(json.dumps(task) + "\n")

        # Dequeue tasks one by one
        for i in range(len(tasks)):
            result = dequeue()
            assert result == tasks[i]

        # Check that the queue is now empty
        result = dequeue()
        assert result is None

    def test_enqueue_dequeue_integration(self, temp_queue_dir):
        """Test enqueueing and dequeuing together."""
        task1 = {
            "type": "test1",
            "url": "https://example1.com",
            "error": "Test error 1",
        }
        task2 = {
            "type": "test2",
            "url": "https://example2.com",
            "error": "Test error 2",
        }

        # Enqueue tasks
        enqueue(task1)
        enqueue(task2)

        # Dequeue tasks
        result1 = dequeue()
        result2 = dequeue()
        result3 = dequeue()  # Should be None

        assert result1 == task1
        assert result2 == task2
        assert result3 is None

    def test_unicode_handling(self, temp_queue_dir):
        """Test handling of Unicode characters in tasks."""
        task = {
            "type": "test",
            "url": "https://example.com/üñîçøðé",
            "error": "Üñîçøðé error",
        }

        # Enqueue and dequeue the task
        enqueue(task)
        result = dequeue()

        assert result == task
