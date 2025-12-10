#!/usr/bin/env python3
"""
OOS Log-Stream Logger
Simple, reliable append-only logging for the OOS system
Event format: timestamp|event_type|content_type|source|item_id|data
"""

import json
import threading
import time
from datetime import datetime
from typing import Dict, Any, Optional
import sys
import os

class OOSLogger:
    """Simple, reliable logger for OOS event streaming"""

    def __init__(self, log_file: str = "oos.log", pipe_output: bool = True):
        self.log_file = log_file
        self.pipe_output = pipe_output
        self.lock = threading.Lock()

        # Ensure log directory exists
        os.makedirs(os.path.dirname(log_file) if os.path.dirname(log_file) else '.', exist_ok=True)

        # Event types validation
        self.valid_event_types = {
            'DISCOVER', 'PROCESS', 'COMPLETE', 'FAIL',
            'SKIP', 'RETRY', 'METRICS'
        }

        # Content types validation
        self.valid_content_types = {
            'podcast', 'article', 'email', 'video',
            'documentation', 'url', 'audio', 'system'
        }

    def _generate_timestamp(self) -> str:
        """Generate ISO 8601 timestamp with millisecond precision"""
        return datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'

    def _validate_event(self, event_type: str, content_type: str, source: str, item_id: str, data: Dict[str, Any]) -> bool:
        """Validate event parameters"""
        if event_type not in self.valid_event_types:
            print(f"Warning: Invalid event_type: {event_type}", file=sys.stderr)
            return False

        if content_type not in self.valid_content_types:
            print(f"Warning: Invalid content_type: {content_type}", file=sys.stderr)
            return False

        if not source or not isinstance(source, str):
            print(f"Warning: Invalid source: {source}", file=sys.stderr)
            return False

        if not item_id or not isinstance(item_id, str):
            print(f"Warning: Invalid item_id: {item_id}", file=sys.stderr)
            return False

        return True

    def log_event(self, event_type: str, content_type: str, source: str, item_id: str, data: Optional[Dict[str, Any]] = None):
        """
        Log an event to both file and stdout

        Args:
            event_type: Type of event (DISCOVER, PROCESS, COMPLETE, etc.)
            content_type: Type of content (podcast, article, etc.)
            source: Source system or feed
            item_id: Unique identifier for the content item
            data: Additional event data as dictionary
        """
        if data is None:
            data = {}

        # Validate event parameters
        if not self._validate_event(event_type, content_type, source, item_id, data):
            return False

        # Generate timestamp
        timestamp = self._generate_timestamp()

        # Serialize data to JSON string
        try:
            data_json = json.dumps(data, separators=(',', ':'), ensure_ascii=False)
        except (TypeError, ValueError) as e:
            print(f"Warning: Failed to serialize data: {e}", file=sys.stderr)
            data_json = '{}'

        # Create event line
        event_line = f"{timestamp}|{event_type}|{content_type}|{source}|{item_id}|{data_json}"

        # Thread-safe write to file
        with self.lock:
            try:
                with open(self.log_file, 'a', encoding='utf-8') as f:
                    f.write(event_line + '\n')
                    f.flush()  # Ensure immediate write
            except IOError as e:
                print(f"Error writing to log file: {e}", file=sys.stderr)
                return False

        # Output to stdout for piping
        if self.pipe_output:
            print(event_line, flush=True)

        return True

    # Convenience methods for common event types
    def discover(self, content_type: str, source: str, item_id: str, data: Optional[Dict[str, Any]] = None):
        """Log a DISCOVER event"""
        return self.log_event('DISCOVER', content_type, source, item_id, data)

    def process(self, content_type: str, source: str, item_id: str, data: Optional[Dict[str, Any]] = None):
        """Log a PROCESS event"""
        return self.log_event('PROCESS', content_type, source, item_id, data)

    def complete(self, content_type: str, source: str, item_id: str, data: Optional[Dict[str, Any]] = None):
        """Log a COMPLETE event"""
        return self.log_event('COMPLETE', content_type, source, item_id, data)

    def fail(self, content_type: str, source: str, item_id: str, data: Optional[Dict[str, Any]] = None):
        """Log a FAIL event"""
        return self.log_event('FAIL', content_type, source, item_id, data)

    def skip(self, content_type: str, source: str, item_id: str, data: Optional[Dict[str, Any]] = None):
        """Log a SKIP event"""
        return self.log_event('SKIP', content_type, source, item_id, data)

    def retry(self, content_type: str, source: str, item_id: str, data: Optional[Dict[str, Any]] = None):
        """Log a RETRY event"""
        return self.log_event('RETRY', content_type, source, item_id, data)

    def metrics(self, source: str, item_id: str, data: Optional[Dict[str, Any]] = None):
        """Log a METRICS event"""
        return self.log_event('METRICS', 'system', source, item_id, data)

# Global logger instance
_logger = None

def get_logger(log_file: str = "oos.log", pipe_output: bool = True) -> OOSLogger:
    """Get or create the global logger instance"""
    global _logger
    if _logger is None:
        _logger = OOSLogger(log_file, pipe_output)
    return _logger

# Convenience functions for direct use
def log_event(event_type: str, content_type: str, source: str, item_id: str, data: Optional[Dict[str, Any]] = None):
    """Log an event using the global logger"""
    logger = get_logger()
    return logger.log_event(event_type, content_type, source, item_id, data)

def discover(content_type: str, source: str, item_id: str, data: Optional[Dict[str, Any]] = None):
    """Log a DISCOVER event"""
    return log_event('DISCOVER', content_type, source, item_id, data)

def process(content_type: str, source: str, item_id: str, data: Optional[Dict[str, Any]] = None):
    """Log a PROCESS event"""
    return log_event('PROCESS', content_type, source, item_id, data)

def complete(content_type: str, source: str, item_id: str, data: Optional[Dict[str, Any]] = None):
    """Log a COMPLETE event"""
    return log_event('COMPLETE', content_type, source, item_id, data)

def fail(content_type: str, source: str, item_id: str, data: Optional[Dict[str, Any]] = None):
    """Log a FAIL event"""
    return log_event('FAIL', content_type, source, item_id, data)

if __name__ == "__main__":
    # Simple test
    logger = get_logger("test_oos.log")

    # Test different event types
    logger.discover("podcast", "Asianometry", "test_001", {"url": "https://example.com", "title": "Test Episode"})
    logger.process("podcast", "Asianometry", "test_001", {"source": "atp"})
    logger.complete("podcast", "Asianometry", "test_001", {"transcript_file": "test.txt", "word_count": 1500})
    logger.fail("podcast", "TestPodcast", "test_002", {"error": "network_timeout"})

    print("✅ OOS Logger test completed")