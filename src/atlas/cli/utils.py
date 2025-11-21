"""
CLI utility functions for Atlas v4.

Provides helper functions for CLI operations including formatting,
progress display, and user interaction.
"""

import sys
import time
from typing import Any, Dict, List, Optional, Callable
from datetime import datetime
import json


def format_size(size_bytes: int) -> str:
    """
    Format byte size as human-readable string.

    Args:
        size_bytes: Size in bytes

    Returns:
        Formatted size string
    """
    if size_bytes == 0:
        return "0B"

    size_names = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    size = float(size_bytes)

    while size >= 1024.0 and i < len(size_names) - 1:
        size /= 1024.0
        i += 1

    return f"{size:.1f}{size_names[i]}"


def format_duration(seconds: float) -> str:
    """
    Format duration as human-readable string.

    Args:
        seconds: Duration in seconds

    Returns:
        Formatted duration string
    """
    if seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        minutes = seconds / 60
        return f"{minutes:.1f}m"
    else:
        hours = seconds / 3600
        return f"{hours:.1f}h"


def format_timestamp(timestamp: str) -> str:
    """
    Format ISO timestamp for display.

    Args:
        timestamp: ISO timestamp string

    Returns:
        Formatted timestamp string
    """
    try:
        dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except ValueError:
        return timestamp


def truncate_string(text: str, max_length: int = 50, suffix: str = "...") -> str:
    """
    Truncate string to maximum length.

    Args:
        text: Text to truncate
        max_length: Maximum length
        suffix: Suffix to add if truncated

    Returns:
        Truncated string
    """
    if len(text) <= max_length:
        return text

    return text[:max_length - len(suffix)] + suffix


def print_table(headers: List[str], rows: List[List[str]], max_width: Optional[int] = None) -> None:
    """
    Print data as formatted table.

    Args:
        headers: Column headers
        rows: Table rows
        max_width: Maximum total width
    """
    if not rows:
        print("No data to display")
        return

    # Calculate column widths
    col_widths = []
    for i, header in enumerate(headers):
        max_col_width = len(header)
        for row in rows:
            if i < len(row):
                max_col_width = max(max_col_width, len(str(row[i])))
        col_widths.append(max_col_width)

    # Apply width limit if specified
    if max_width:
        total_width = sum(col_widths) + len(col_widths) - 1
        if total_width > max_width:
            # Proportionally reduce column widths
            factor = max_width / total_width
            col_widths = [max(5, int(w * factor)) for w in col_widths]

    # Print header
    header_line = " | ".join(header.ljust(col_widths[i]) for i, header in enumerate(headers))
    print(header_line)
    print("-" * len(header_line))

    # Print rows
    for row in rows:
        row_cells = []
        for i, cell in enumerate(row):
            if i < len(col_widths):
                cell_str = str(cell)
                if len(cell_str) > col_widths[i]:
                    cell_str = truncate_string(cell_str, col_widths[i])
                row_cells.append(cell_str.ljust(col_widths[i]))
            else:
                row_cells.append(str(cell))

        print(" | ".join(row_cells))


def confirm_action(message: str, default: bool = False) -> bool:
    """
    Ask user for confirmation.

    Args:
        message: Confirmation message
        default: Default response if user just presses Enter

    Returns:
        True if user confirms, False otherwise
    """
    suffix = " [Y/n]" if default else " [y/N]"
    full_message = message + suffix

    while True:
        response = input(full_message + " ").strip().lower()

        if not response:
            return default

        if response in ['y', 'yes', 'ok', 'sure']:
            return True
        elif response in ['n', 'no', 'cancel']:
            return False
        else:
            print("Please enter 'yes' or 'no'")


def select_option(options: List[str], message: str = "Select an option:") -> Optional[int]:
    """
    Ask user to select from a list of options.

    Args:
        options: List of option strings
        message: Prompt message

    Returns:
        Selected index (0-based) or None if cancelled
    """
    print(message)
    for i, option in enumerate(options, 1):
        print(f"  {i}. {option}")

    while True:
        try:
            response = input("Enter option number (or 'cancel'): ").strip()

            if response.lower() in ['cancel', 'c', '']:
                return None

            option_num = int(response)
            if 1 <= option_num <= len(options):
                return option_num - 1
            else:
                print(f"Please enter a number between 1 and {len(options)}")

        except ValueError:
            print("Please enter a valid number")


class ProgressIndicator:
    """Simple progress indicator for long-running operations."""

    def __init__(self, message: str = "Processing...", interval: float = 1.0):
        """
        Initialize progress indicator.

        Args:
            message: Progress message
            interval: Update interval in seconds
        """
        self.message = message
        self.interval = interval
        self.start_time = None
        self.last_update = None
        self.symbols = ["|", "/", "-", "\\"]
        self.symbol_index = 0

    def start(self):
        """Start progress indication."""
        self.start_time = time.time()
        self.last_update = time.time()
        self._update_display()

    def update(self, message: Optional[str] = None):
        """Update progress message."""
        current_time = time.time()
        if current_time - self.last_update >= self.interval:
            if message:
                self.message = message
            self._update_display()
            self.last_update = current_time

    def finish(self, message: str = "Complete"):
        """Finish progress indication."""
        duration = time.time() - self.start_time if self.start_time else 0
        print(f"\r{message} ({format_duration(duration)})")
        sys.stdout.flush()

    def _update_display(self):
        """Update progress display."""
        symbol = self.symbols[self.symbol_index]
        self.symbol_index = (self.symbol_index + 1) % len(self.symbols)

        duration = time.time() - self.start_time if self.start_time else 0
        display = f"\r{symbol} {self.message} ({format_duration(duration)})"
        sys.stdout.write(display)
        sys.stdout.flush()


def safe_input(prompt: str, default: Optional[str] = None) -> str:
    """
    Safe input function with default value support.

    Args:
        prompt: Input prompt
        default: Default value if user just presses Enter

    Returns:
        User input or default value
    """
    if default is not None:
        full_prompt = f"{prompt} [{default}]: "
    else:
        full_prompt = f"{prompt}: "

    response = input(full_prompt).strip()
    return response if response else (default or "")


def validate_file_path(path: str, must_exist: bool = False) -> bool:
    """
    Validate file path.

    Args:
        path: File path to validate
        must_exist: Whether file must exist

    Returns:
        True if valid, False otherwise
    """
    from pathlib import Path

    try:
        file_path = Path(path)

        if must_exist and not file_path.exists():
            return False

        # Check if parent directory exists or can be created
        parent = file_path.parent
        return parent.exists() or parent.parent.exists()

    except Exception:
        return False


def get_editor_command() -> Optional[str]:
    """
    Get user's preferred text editor command.

    Returns:
        Editor command or None if not found
    """
    import os

    # Check environment variables
    editor = os.getenv('EDITOR')
    if editor:
        return editor

    # Try common editors
    common_editors = ['nano', 'vim', 'emacs', 'code', 'subl', 'atom']
    for editor in common_editors:
        if os.system(f"which {editor} > /dev/null 2>&1") == 0:
            return editor

    return None


def open_file_in_editor(file_path: str) -> bool:
    """
    Open file in user's preferred editor.

    Args:
        file_path: Path to file to open

    Returns:
        True if successful, False otherwise
    """
    import os
    import subprocess

    editor = get_editor_command()
    if not editor:
        print("No suitable text editor found")
        return False

    try:
        subprocess.run([editor, file_path], check=True)
        return True
    except subprocess.CalledProcessError:
        print(f"Failed to open editor: {editor}")
        return False
    except FileNotFoundError:
        print(f"Editor not found: {editor}")
        return False


def paginate_output(text: str, lines_per_page: int = 20):
    """
    Paginate long text output.

    Args:
        text: Text to paginate
        lines_per_page: Lines per page
    """
    lines = text.split('\n')
    total_lines = len(lines)

    for i in range(0, total_lines, lines_per_page):
        # Print page
        page_lines = lines[i:i + lines_per_page]
        print('\n'.join(page_lines))

        # Check if this is the last page
        if i + lines_per_page >= total_lines:
            break

        # Prompt for continuation
        print(f"\n-- More ({i + lines_per_page}/{total_lines}) --")
        response = input("Press Enter to continue, 'q' to quit: ").strip().lower()
        if response in ['q', 'quit', 'exit']:
            break


def format_json_output(data: Any, indent: int = 2) -> str:
    """
    Format data as pretty-printed JSON.

    Args:
        data: Data to format
        indent: Indentation level

    Returns:
        Formatted JSON string
    """
    try:
        return json.dumps(data, indent=indent, default=str, ensure_ascii=False)
    except (TypeError, ValueError):
        return str(data)


def parse_date_string(date_str: str) -> Optional[datetime]:
    """
    Parse various date string formats.

    Args:
        date_str: Date string to parse

    Returns:
        Parsed datetime or None if parsing failed
    """
    from datetime import datetime

    # Common date formats to try
    date_formats = [
        "%Y-%m-%d",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%dT%H:%M:%S%z",
        "%d/%m/%Y",
        "%m/%d/%Y",
        "%B %d, %Y",
        "%d %B %Y"
    ]

    for fmt in date_formats:
        try:
            return datetime.strptime(date_str.strip(), fmt)
        except ValueError:
            continue

    return None


def create_spinner():
    """Create a simple spinner animation function."""
    spinner_chars = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
    index = 0

    def spinner():
        nonlocal index
        char = spinner_chars[index]
        index = (index + 1) % len(spinner_chars)
        return char

    return spinner


def ensure_vault_initialized(vault_path: str) -> bool:
    """
    Ensure vault is properly initialized.

    Args:
        vault_path: Path to vault directory

    Returns:
        True if vault is ready, False otherwise
    """
    from pathlib import Path
    from ..storage import StorageManager

    try:
        vault_dir = Path(vault_path)
        if not vault_dir.exists():
            print(f"Vault directory does not exist: {vault_path}")
            return False

        storage = StorageManager(vault_path)
        return storage.initialize_vault()

    except Exception as e:
        print(f"Failed to initialize vault: {str(e)}")
        return False


def get_config_files() -> List[str]:
    """
    Get list of possible configuration file locations.

    Returns:
        List of configuration file paths
    """
    import os
    from pathlib import Path

    config_files = []

    # Current directory
    if Path.cwd().joinpath("atlas.yaml").exists():
        config_files.append(str(Path.cwd() / "atlas.yaml"))
    if Path.cwd().joinpath("atlas.json").exists():
        config_files.append(str(Path.cwd() / "atlas.json"))

    # Home directory
    home = Path.home()
    home_configs = [
        home / ".atlas" / "config.yaml",
        home / ".atlas" / "config.json",
        home / ".atlas.yaml",
        home / ".atlas.json"
    ]

    for config_path in home_configs:
        if config_path.exists():
            config_files.append(str(config_path))

    # Environment variable
    env_config = os.getenv("ATLAS_CONFIG")
    if env_config and Path(env_config).exists():
        config_files.append(env_config)

    return config_files


def merge_dicts(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    """
    Recursively merge two dictionaries.

    Args:
        base: Base dictionary
        override: Dictionary with override values

    Returns:
        Merged dictionary
    """
    result = base.copy()

    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = merge_dicts(result[key], value)
        else:
            result[key] = value

    return result