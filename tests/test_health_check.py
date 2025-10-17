import unittest
from unittest.mock import patch, MagicMock
import shutil
from lib.health_check import run_health_check, Colors

class TestHealthCheck(unittest.TestCase):

    @patch('shutil.which')
    @patch('builtins.print')
    def test_health_check_all_ok(self, mock_print, mock_which):
        """Test the health check when all dependencies are found."""
        # Arrange: Mock that all executables are found
        mock_which.side_effect = lambda cmd: f'/usr/bin/{cmd}' # Return a path for any command

        # Act
        exit_code = run_health_check()

        # Assert
        self.assertEqual(exit_code, 0)
        mock_print.assert_any_call(f"{Colors.GREEN}[OK]{Colors.END} python")
        mock_print.assert_any_call(f"{Colors.GREEN}[OK]{Colors.END} git")
        mock_print.assert_any_call(f"{Colors.GREEN}[OK]{Colors.END} op (1Password CLI)")

    @patch('shutil.which')
    @patch('builtins.print')
    def test_health_check_one_missing(self, mock_print, mock_which):
        """Test the health check when one dependency is missing."""
        # Arrange: Mock that 'op' is not found
        def which_se(cmd):
            if cmd == 'op':
                return None
            return f'/usr/bin/{cmd}'
        mock_which.side_effect = which_se

        # Act
        exit_code = run_health_check()

        # Assert
        self.assertEqual(exit_code, 1)
        mock_print.assert_any_call(f"{Colors.GREEN}[OK]{Colors.END} python")
        mock_print.assert_any_call(f"{Colors.GREEN}[OK]{Colors.END} git")
        mock_print.assert_any_call(f"{Colors.RED}[FAIL]{Colors.END} op (1Password CLI)")

if __name__ == '__main__':
    unittest.main()