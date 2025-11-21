"""
Markdown+YAML file writer for Atlas v4.

Handles writing content items as Obsidian-compatible Markdown files
with YAML frontmatter. Manages atomic writes and content formatting.
"""

import os
import re
import yaml
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, Union
import logging

from ..core.validator import ValidationResult


class MarkdownWriter:
    """
    Writes Atlas content items as Markdown+YAML files.

    Features:
    - Atomic writes to prevent corruption
    - YAML frontmatter formatting
    - Obsidian compatibility
    - Content validation
    """

    def __init__(self, vault_root: str):
        """
        Initialize writer with vault root directory.

        Args:
            vault_root: Root directory of the vault
        """
        self.vault_root = Path(vault_root)
        self.logger = logging.getLogger(f"atlas.storage.{self.__class__.__name__}")

    def write_content_item(self, content_item: dict) -> Optional[Path]:
        """
        Write a content item as a Markdown+YAML file.

        Args:
            content_item: Standardized Atlas content item

        Returns:
            Path to written file or None if failed
        """
        try:
            # Validate content item first
            self._validate_content_item(content_item)

            # Generate file path
            file_path = self._generate_file_path(content_item)

            # Ensure directory exists
            file_path.parent.mkdir(parents=True, exist_ok=True)

            # Create YAML frontmatter and markdown content
            markdown_content = self._create_markdown_content(content_item)

            # Write atomically
            self._write_atomically(file_path, markdown_content)

            self.logger.info(
                f"Written content item to file: {file_path.relative_to(self.vault_root)} ({content_item.get('title', 'Unknown')}, {content_item.get('type', 'unknown')})"
            )

            return file_path

        except Exception as e:
            self.logger.error(f"Failed to write content item: {content_item.get('title', 'Unknown')} ({content_item.get('type', 'unknown')}) - {str(e)}")
            return None

    def write_content_item_to_path(self, content_item: dict, file_path: Path) -> Optional[Path]:
        """
        Write a content item to a specific file path.

        Args:
            content_item: Standardized Atlas content item
            file_path: Target file path

        Returns:
            Path to written file or None if failed
        """
        try:
            # Validate content item first
            self._validate_content_item(content_item)

            # Ensure directory exists
            file_path.parent.mkdir(parents=True, exist_ok=True)

            # Create YAML frontmatter and markdown content
            markdown_content = self._create_markdown_content(content_item)

            # Write atomically
            self._write_atomically(file_path, markdown_content)

            self.logger.info(
                f"Written content item to specific path: {file_path.relative_to(self.vault_root)} ({content_item.get('title', 'Unknown')}, {content_item.get('type', 'unknown')})"
            )

            return file_path

        except Exception as e:
            self.logger.error(f"Failed to write content item to path: {content_item.get('title', 'Unknown')} ({content_item.get('type', 'unknown')}) - {str(e)}")
            return None

    def _validate_content_item(self, content_item: Dict[str, Any]) -> None:
        """Validate content item before writing."""
        required_fields = ['id', 'type', 'source', 'title', 'date', 'ingested_at', 'content']

        for field in required_fields:
            if field not in content_item:
                raise ValueError(f"Missing required field: {field}")
            if not content_item[field]:
                raise ValueError(f"Required field is empty: {field}")

        # Validate date format
        date_fields = ['date', 'ingested_at']
        for field in date_fields:
            if field in content_item:
                date_value = content_item[field]
                try:
                    datetime.fromisoformat(date_value.replace('Z', '+00:00'))
                except ValueError:
                    raise ValueError(f"Invalid date format in field '{field}': {date_value}")

    def _generate_file_path(self, content_item: Dict[str, Any]) -> Path:
        """Generate file path for content item."""
        content_type = content_item.get('type', 'unknown')
        source = content_item.get('source', 'unknown')
        date = content_item.get('date', datetime.now().isoformat())
        title = content_item.get('title', 'untitled')

        # Parse date
        try:
            dt = datetime.fromisoformat(date.replace('Z', '+00:00'))
            year = dt.year
            month = f"{dt.month:02d}"
        except ValueError:
            # Fallback to current date
            now = datetime.now()
            year = now.year
            month = f"{now.month:02d}"

        # Generate filename
        filename = self._generate_filename(title, source, date)

        # Build directory path: vault_root/inbox/{type}/{year}/{month}/
        dir_path = (
            self.vault_root /
            "inbox" /
            content_type /
            str(year) /
            month
        )

        return dir_path / f"{filename}.md"

    def _generate_filename(self, title: str, source: str, date: str) -> str:
        """
        Generate filename from title and metadata.

        Format: {source-name}-{date}-{slug}.md (max 100 chars)

        Args:
            title: Content title
            source: Source name
            date: Publication date

        Returns:
            Generated filename
        """
        # Clean source name
        source_clean = self._clean_filename_component(source)

        # Clean date
        try:
            dt = datetime.fromisoformat(date.replace('Z', '+00:00'))
            date_clean = dt.strftime("%Y-%m-%d")
        except ValueError:
            date_clean = "unknown-date"

        # Clean title
        title_slug = self._clean_filename_component(title)

        # Combine components
        max_length = 100
        components = [source_clean, date_clean, title_slug]

        # Build filename and truncate if too long
        filename = "-".join(components)
        if len(filename) > max_length:
            # Truncate to max length, avoiding cutting in middle of word
            filename = filename[:max_length]
            # Find last dash and truncate there
            last_dash = filename.rfind("-")
            if last_dash > 0:
                filename = filename[:last_dash]

        return filename

    def _clean_filename_component(self, text: str) -> str:
        """Clean text component for use in filename."""
        # Remove or replace special characters
        cleaned = re.sub(r'[^\w\s-]', '', text)
        # Replace spaces with dashes
        cleaned = re.sub(r'\s+', '-', cleaned)
        # Remove multiple consecutive dashes
        cleaned = re.sub(r'-+', '-', cleaned)
        # Remove leading/trailing dashes
        cleaned = cleaned.strip('-')
        # Convert to lowercase
        cleaned = cleaned.lower()
        # Remove empty components
        return cleaned or "unknown"

    def _create_markdown_content(self, content_item: Dict[str, Any]) -> str:
        """Create complete markdown content with YAML frontmatter."""
        # Separate metadata from content
        metadata = self._extract_metadata(content_item)
        content = content_item.get('content', '')

        # Create YAML frontmatter
        frontmatter = self._create_yaml_frontmatter(metadata)

        # Combine frontmatter and content
        return f"---\n{frontmatter}---\n\n{content}"

    def _extract_metadata(self, content_item: Dict[str, Any]) -> Dict[str, Any]:
        """Extract metadata for YAML frontmatter."""
        # Define frontmatter fields
        frontmatter_fields = [
            'id', 'type', 'source', 'title', 'date', 'author', 'url',
            'content_hash', 'tags', 'ingested_at'
        ]

        metadata = {}
        for field in frontmatter_fields:
            if field in content_item:
                metadata[field] = content_item[field]

        # Add optional fields if present
        optional_fields = [
            'duration', 'view_count', 'like_count', 'channel',
            'video_id', 'audio_url', 'video_url', 'thumbnail_url',
            'podcast', 'newsletter', 'from_address', 'to_addresses',
            'subject', 'message_id', 'guid', 'guid_hash', 'url_hash'
        ]

        for field in optional_fields:
            if field in content_item:
                metadata[field] = content_item[field]

        # Add validation metadata if available
        if 'validation' in content_item:
            metadata['validation'] = content_item['validation']

        return metadata

    def _create_yaml_frontmatter(self, metadata: Dict[str, Any]) -> str:
        """Create YAML frontmatter string."""
        try:
            # Format special fields
            formatted_metadata = {}
            for key, value in metadata.items():
                if isinstance(value, datetime):
                    formatted_metadata[key] = value.isoformat()
                elif isinstance(value, (list, tuple)):
                    formatted_metadata[key] = list(value)
                elif isinstance(value, dict):
                    formatted_metadata[key] = dict(value)
                else:
                    formatted_metadata[key] = value

            # Dump as YAML
            yaml_content = yaml.dump(
                formatted_metadata,
                default_flow_style=False,
                indent=2,
                sort_keys=False,
                allow_unicode=True
            )

            return yaml_content.strip()

        except Exception as e:
            self.logger.error(f"Failed to create YAML frontmatter: {str(e)}")
            # Fallback to simple format
            return str(metadata)

    def _write_atomically(self, file_path: Path, content: str) -> None:
        """
        Write content to file atomically to prevent corruption.

        Args:
            file_path: Target file path
            content: Content to write
        """
        temp_path = file_path.with_suffix('.tmp')

        try:
            # Write to temporary file
            with open(temp_path, 'w', encoding='utf-8') as f:
                f.write(content)

            # Atomic rename
            temp_path.rename(file_path)

        except Exception as e:
            # Clean up temp file if rename failed
            if temp_path.exists():
                try:
                    temp_path.unlink()
                except Exception:
                    pass
            raise

    def write_batch(self, content_items: list) -> list:
        """
        Write multiple content items.

        Args:
            content_items: List of content items to write

        Returns:
            List of successfully written file paths
        """
        written_files = []

        for item in content_items:
            try:
                file_path = self.write_content_item(item)
                if file_path:
                    written_files.append(file_path)
            except Exception as e:
                self.logger.error(f"Failed to write content item in batch: {str(e)}")
                continue

        return written_files

    def update_content_item(self, file_path: Path, updates: dict) -> bool:
        """
        Update existing content item.

        Args:
            file_path: Path to existing file
            updates: Fields to update

        Returns:
            True if successful, False otherwise
        """
        try:
            # Read existing content
            if not file_path.exists():
                self.logger.error(f"File does not exist: {file_path}")
                return False

            with open(file_path, 'r', encoding='utf-8') as f:
                existing_content = f.read()

            # Parse existing frontmatter and content
            parsed = self._parse_markdown_content(existing_content)
            existing_metadata = parsed['frontmatter']
            body_content = parsed['content']

            # Merge updates
            updated_metadata = {**existing_metadata, **updates}
            updated_metadata['updated_at'] = datetime.now().isoformat()

            # Recreate markdown content
            new_content = self._create_markdown_content({
                'content': body_content,
                **updated_metadata
            })

            # Write atomically
            self._write_atomically(file_path, new_content)

            self.logger.info(f"Updated content item: {file_path.name}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to update content item {file_path}: {str(e)}")
            return False

    def _parse_markdown_content(self, content: str) -> Dict[str, Any]:
        """Parse markdown content to extract frontmatter and body."""
        frontmatter_pattern = r'^---\s*\n(.*?)\n---\s*\n(.*)$'
        match = re.match(frontmatter_pattern, content, re.DOTALL)

        if match:
            frontmatter_text, body_content = match.groups()

            try:
                frontmatter = yaml.safe_load(frontmatter_text)
            except yaml.YAMLError as e:
                self.logger.warning(f"Invalid YAML frontmatter: {str(e)}")
                frontmatter = {}

            return {
                'frontmatter': frontmatter or {},
                'content': body_content.strip()
            }
        else:
            return {
                'frontmatter': {},
                'content': content.strip()
            }

    def get_file_info(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """
        Get information about a content file.

        Args:
            file_path: Path to content file

        Returns:
            File information dictionary or None if file doesn't exist
        """
        if not file_path.exists():
            return None

        try:
            stat = file_path.stat()
            content = self._parse_markdown_content(file_path.read_text(encoding='utf-8'))

            return {
                'path': str(file_path),
                'size': stat.st_size,
                'created': datetime.fromtimestamp(stat.st_ctime),
                'modified': datetime.fromtimestamp(stat.st_mtime),
                'frontmatter': content['frontmatter'],
                'content_length': len(content['content'])
            }

        except Exception as e:
            self.logger.error(f"Failed to get file info for {file_path}: {str(e)}")
            return None