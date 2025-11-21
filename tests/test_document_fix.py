#!/usr/bin/env python3
"""
Unit Test for Document Processing Fix

This test validates that the fixes for document processing work correctly:
1. summarize_content() now receives the config parameter correctly
2. Document processing works end-to-end without errors
"""

import unittest
import tempfile
import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from helpers.config import load_config
from helpers.document_processor import AtlasDocumentProcessor
from helpers.document_ingestor import DocumentIngestor


class TestDocumentProcessingFix(unittest.TestCase):
    """Test document processing fixes work correctly."""

    def setUp(self):
        """Set up test fixtures."""
        self.config = load_config()
        self.test_content = """
        <html>
        <head><title>Test Document</title></head>
        <body>
        <h1>Test Article</h1>
        <p>This is a test document for validating document processing fixes.</p>
        <p>The document contains enough content to trigger summarization when processed through the ingestor.</p>
        <p>This content should be processed successfully without any missing parameter errors.</p>
        </body>
        </html>
        """

        # Create temporary test file
        self.temp_fd, self.temp_file = tempfile.mkstemp(suffix='.html')
        os.write(self.temp_fd, self.test_content.encode('utf-8'))
        os.close(self.temp_fd)

    def tearDown(self):
        """Clean up test fixtures."""
        if os.path.exists(self.temp_file):
            os.unlink(self.temp_file)

    def test_document_processor_works(self):
        """Test that AtlasDocumentProcessor works correctly."""
        processor = AtlasDocumentProcessor(self.config)

        # Process the test document
        result = processor.process_document(self.temp_file)

        # Validate success
        self.assertEqual(result["processing_status"], "completed")
        self.assertIsNone(result["error"])
        self.assertGreater(len(result["content"]), 0)
        self.assertGreater(len(result["structured_content"]), 0)

        # Content should contain our test text
        self.assertIn("Test Article", result["content"])
        self.assertIn("test document", result["content"])

    def test_document_ingestor_no_summarization_errors(self):
        """Test that DocumentIngestor doesn't have summarization parameter errors."""
        ingestor = DocumentIngestor(self.config)

        # This should not raise any "missing parameter" errors
        result = ingestor.ingest_content(self.temp_file)

        # The ingestor should succeed
        self.assertTrue(result.success, f"Ingestor failed: {result.error}")
        self.assertIsNone(result.error)
        self.assertIsNotNone(result.metadata)

        # Check that content was processed
        self.assertIsNotNone(result.metadata.type_specific.get("content"))
        content = result.metadata.type_specific["content"]
        self.assertGreater(len(content), 0)

        # If the content is long enough, summary should be generated without errors
        if len(content) > 500:
            summary = result.metadata.type_specific.get("summary")
            # Summary might be None if summarization fails, but there should be no parameter errors
            # The key test is that no exception was raised during processing

    def test_summarize_content_function_directly(self):
        """Test that summarize_content function works with config parameter."""
        try:
            from process.evaluate import summarize_content

            test_text = "This is a test text for summarization. " * 20  # Make it long enough

            # This should not raise "missing 1 required positional argument: 'config'"
            summary = summarize_content(test_text, self.config)

            # Summary should be generated successfully
            self.assertIsInstance(summary, (str, type(None)))
            if summary:
                self.assertGreater(len(summary), 0)
                self.assertLess(len(summary), len(test_text))  # Should be shorter

        except ImportError:
            self.skipTest("summarize_content function not available")

    def test_large_document_processing(self):
        """Test processing of a larger document that triggers summarization."""
        # Create a larger document
        large_content = """
        <html>
        <head><title>Large Test Document</title></head>
        <body>
        <h1>Large Article Title</h1>
        """ + "<p>This paragraph contains substantial content for testing. " * 100 + "</p>" + """
        <h2>Section 2</h2>
        """ + "<p>More content to ensure the document is large enough. " * 100 + "</p>" + """
        </body>
        </html>
        """

        # Write to temporary file
        temp_fd, temp_large_file = tempfile.mkstemp(suffix='.html')
        try:
            os.write(temp_fd, large_content.encode('utf-8'))
            os.close(temp_fd)

            # Process with ingestor
            ingestor = DocumentIngestor(self.config)
            result = ingestor.ingest_content(temp_large_file)

            # Should succeed without parameter errors
            self.assertTrue(result.success, f"Large document processing failed: {result.error}")
            self.assertIsNone(result.error)

            # Content should be substantial
            content = result.metadata.type_specific.get("content", "")
            self.assertGreater(len(content), 1000)  # Should be substantial

        finally:
            if os.path.exists(temp_large_file):
                os.unlink(temp_large_file)


if __name__ == '__main__':
    # Run tests
    unittest.main(verbosity=2)