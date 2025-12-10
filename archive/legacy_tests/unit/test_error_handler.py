import unittest

from helpers.error_handler import (AtlasError, AtlasErrorHandler,
                                   ErrorCategory, ErrorContext, ErrorSeverity,
                                   FileSystemErrorHandler, NetworkErrorHandler)


class TestErrorHandlers(unittest.TestCase):

    def test_categorize_http_error(self):
        self.assertEqual(
            NetworkErrorHandler.categorize_http_error(404), ErrorSeverity.MEDIUM
        )
        self.assertEqual(
            NetworkErrorHandler.categorize_http_error(500), ErrorSeverity.HIGH
        )
        self.assertEqual(
            NetworkErrorHandler.categorize_http_error(429), ErrorSeverity.LOW
        )

    def test_should_retry_http_error(self):
        self.assertTrue(NetworkErrorHandler.should_retry_http_error(503))
        self.assertFalse(NetworkErrorHandler.should_retry_http_error(404))

    def test_categorize_fs_error(self):
        self.assertEqual(
            FileSystemErrorHandler.categorize_fs_error(PermissionError()),
            ErrorSeverity.HIGH,
        )
        self.assertEqual(
            FileSystemErrorHandler.categorize_fs_error(FileNotFoundError()),
            ErrorSeverity.MEDIUM,
        )

    def test_should_retry_fs_error(self):
        self.assertFalse(
            FileSystemErrorHandler.should_retry_fs_error(PermissionError())
        )
        self.assertTrue(FileSystemErrorHandler.should_retry_fs_error(OSError()))


class TestAtlasErrorHandler(unittest.TestCase):

    def setUp(self):
        self.config = {"data_directory": "output"}
        self.handler = AtlasErrorHandler(self.config)

    def test_create_error(self):
        context = ErrorContext(module="test", function="test_func")
        error = self.handler.create_error(
            message="Test error",
            category=ErrorCategory.UNKNOWN,
            severity=ErrorSeverity.MEDIUM,
            context=context,
        )
        self.assertIsInstance(error, AtlasError)
        self.assertEqual(error.message, "Test error")


if __name__ == "__main__":
    unittest.main()
