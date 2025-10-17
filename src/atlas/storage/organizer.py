"""
Directory structure manager for Atlas v4.

Organizes content files in PRD-specified directory structure:
vault/inbox/{type}/{year}/{month}/filename.md

Handles directory creation, path organization, and vault structure validation.
"""

import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List
import logging

from .writer import MarkdownWriter


class VaultOrganizer:
    """
    Manages Atlas vault directory structure.

    Implements PRD directory organization:
    - vault/
      - inbox/
        - newsletters/{year}/{month}/
        - podcasts/{year}/{month}/
        - articles/{year}/{month}/
        - youtube/{year}/{month}/
        - emails/{year}/{month}/
      - logs/
      - failures/
      - config/
    """

    def __init__(self, vault_root: str):
        """
        Initialize organizer with vault root.

        Args:
            vault_root: Root directory of the vault
        """
        self.vault_root = Path(vault_root)
        self.inbox_dir = self.vault_root / "inbox"
        self.logs_dir = self.vault_root / "logs"
        self.failures_dir = self.vault_root / "failures"
        self.config_dir = self.vault_root / "config"
        self.logger = logging.getLogger(f"atlas.storage.{self.__class__.__name__}")

    def ensure_vault_structure(self) -> bool:
        """
        Ensure complete vault directory structure exists.

        Returns:
            True if successful, False otherwise
        """
        try:
            # Create main directories
            self._create_directory(self.vault_root)
            self._create_directory(self.inbox_dir)
            self._create_directory(self.logs_dir)
            self._create_directory(self.failures_dir)
            self._create_directory(self.config_dir)

            # Create content type directories
            content_types = ['newsletters', 'podcasts', 'articles', 'youtube', 'emails']
            for content_type in content_types:
                type_dir = self.inbox_dir / content_type
                self._create_directory(type_dir)

            # Create date directories for current year/month
            self._create_current_date_directories()

            self.logger.info(f"Vault structure ensured at: {self.vault_root}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to create vault structure: {str(e)}")
            return False

    def _create_directory(self, directory: Path) -> None:
        """Create directory if it doesn't exist."""
        if not directory.exists():
            directory.mkdir(parents=True, exist_ok=True)
            self.logger.debug(f"Created directory: {directory.relative_to(self.vault_root)}")

    def _create_current_date_directories(self) -> None:
        """Create date directories for current year/month."""
        now = datetime.now()
        year = str(now.year)
        month = f"{now.month:02d}"

        for content_type in ['newsletters', 'podcasts', 'articles', 'youtube', 'emails']:
            year_dir = self.inbox_dir / content_type / year
            month_dir = year_dir / month
            self._create_directory(year_dir)
            self._create_directory(month_dir)

    def get_content_dir(self, content_type: str, date: Optional[datetime] = None) -> Path:
        """
        Get directory path for content type and date.

        Args:
            content_type: Type of content (newsletter, podcast, etc.)
            date: Publication date (uses current if None)

        Returns:
            Directory path for the content
        """
        if date is None:
            date = datetime.now()

        year = str(date.year)
        month = f"{date.month:02d}"

        return self.inbox_dir / content_type / year / month

    def get_file_path(
        self,
        content_type: str,
        date: datetime,
        filename: str,
        check_collision: bool = True
    ) -> Path:
        """
        Get full file path for content item.

        Args:
            content_type: Type of content
            date: Publication date
            filename: Base filename (without extension)
            check_collision: Whether to check for existing files

        Returns:
            Full file path
        """
        content_dir = self.get_content_dir(content_type, date)

        # Ensure directory exists
        self._create_directory(content_dir)

        # Check for collision if requested
        if check_collision:
            filename = self._resolve_collision(content_dir, filename)

        return content_dir / f"{filename}.md"

    def _resolve_collision(self, directory: Path, filename: str) -> str:
        """
        Resolve filename collision by adding numeric suffix.

        Args:
            directory: Directory containing the file
            filename: Base filename

        Returns:
            Resolved filename with suffix if needed
        """
        base_path = directory / f"{filename}.md"
        counter = 2

        while base_path.exists():
            new_filename = f"{filename}-{counter}"
            base_path = directory / f"{new_filename}.md"
            counter += 1

            # Safety check to prevent infinite loop
            if counter > 1000:
                raise RuntimeError(f"Too many filename collisions for {filename}")

        # Return final filename (without extension as caller adds it)
        if counter > 2:
            return f"{filename}-{counter-1}"
        else:
            return filename

    def get_logs_dir(self) -> Path:
        """Get logs directory path."""
        return self.logs_dir

    def get_failures_dir(self) -> Path:
        """Get failures directory path."""
        return self.failures_dir

    def get_config_dir(self) -> Path:
        """Get config directory path."""
        return self.config_dir

    def organize_file(self, source_file: Path, content_type: str, date: datetime) -> Optional[Path]:
        """
        Move or copy a file to the correct vault location.

        Args:
            source_file: Source file path
            content_type: Type of content
            date: Publication date
            move: Whether to move (True) or copy (False)

        Returns:
            New file path or None if failed
        """
        try:
            # Generate target path
            filename = source_file.stem
            target_path = self.get_file_path(content_type, date, filename)

            # Ensure target directory exists
            self._create_directory(target_path.parent)

            # Copy file
            if source_file != target_path:
                import shutil
                shutil.copy2(source_file, target_path)

            self.logger.info(
                f"Organized file to vault",
                source=str(source_file),
                target=str(target_path.relative_to(self.vault_root))
            )

            return target_path

        except Exception as e:
            self.logger.error(f"Failed to organize file {source_file}: {str(e)}")
            return None

    def cleanup_empty_directories(self) -> List[str]:
        """
        Remove empty directories in the vault.

        Returns:
            List of removed directory paths
        """
        removed_dirs = []

        try:
            # Start from the deepest level and work up
            for root, dirs, files in os.walk(self.inbox_dir, topdown=False):
                # Skip if directory has files or subdirectories
                if files or dirs:
                    continue

                try:
                    root_path = Path(root)
                    root_path.rmdir()
                    removed_dirs.append(str(root_path.relative_to(self.vault_root)))
                    self.logger.debug(f"Removed empty directory: {root_path.name}")
                except OSError:
                    # Directory not empty or permission denied
                    pass

        except Exception as e:
            self.logger.error(f"Failed to cleanup empty directories: {str(e)}")

        return removed_dirs

    def get_vault_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the vault.

        Returns:
            Dictionary with vault statistics
        """
        stats = {
            'total_files': 0,
            'content_types': {},
            'disk_usage': 0,
            'oldest_file': None,
            'newest_file': None
        }

        try:
            import os

            if not self.vault_root.exists():
                return stats

            # Count files by type
            for content_type in ['newsletters', 'podcasts', 'articles', 'youtube', 'emails']:
                type_dir = self.inbox_dir / content_type
                if type_dir.exists():
                    count = sum(1 for f in type_dir.rglob("*.md") if f.is_file())
                    stats['content_types'][content_type] = count
                    stats['total_files'] += count

            # Get disk usage
            stats['disk_usage'] = sum(
                f.stat().st_size
                for f in self.vault_root.rglob("**/*")
                if f.is_file()
            )

            # Find oldest and newest files
            files = [
                f for f in self.vault_root.rglob("**/*.md")
                if f.is_file()
            ]

            if files:
                file_times = [(f, f.stat().st_mtime) for f in files]
                file_times.sort(key=lambda x: x[1])

                oldest_file = file_times[0][0]
                newest_file = file_times[-1][0]

                stats['oldest_file'] = {
                    'path': str(oldest_file.relative_to(self.vault_root)),
                    'date': datetime.fromtimestamp(oldest_file.stat().st_mtime).isoformat()
                }
                stats['newest_file'] = {
                    'path': str(newest_file.relative_to(self.vault_root)),
                    'date': datetime.fromtimestamp(newest_file.stat().st_mtime).isoformat()
                }

        except Exception as e:
            self.logger.error(f"Failed to get vault stats: {str(e)}")

        return stats

    def validate_vault_structure(self) -> List[str]:
        """
        Validate vault structure against PRD requirements.

        Returns:
            List of validation errors (empty if valid)
        """
        errors = []

        # Check main directories exist
        required_dirs = [
            self.vault_root,
            self.inbox_dir,
            self.logs_dir,
            self.failures_dir,
            self.config_dir
        ]

        for directory in required_dirs:
            if not directory.exists():
                errors.append(f"Missing required directory: {directory.name}")

        # Check content type directories
        content_types = ['newsletters', 'podcasts', 'articles', 'youtube', 'emails']
        for content_type in content_types:
            type_dir = self.inbox_dir / content_type
            if not type_dir.exists():
                errors.append(f"Missing content type directory: {content_type}")

        return errors