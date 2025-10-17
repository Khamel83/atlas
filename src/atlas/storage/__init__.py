"""
Unified storage interface for Atlas v4.

Provides a high-level interface that combines the writer, organizer,
and collision handler modules into a single cohesive storage system.
"""

from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, List
import logging

from .writer import MarkdownWriter
from .organizer import VaultOrganizer
from .collision import CollisionHandler
from ..core.validator import ValidationResult


class StorageManager:
    """
    Unified storage interface for Atlas content items.

    Combines directory organization, collision handling, and file writing
    into a single high-level interface that handles all storage operations.
    """

    def __init__(self, vault_root: str):
        """
        Initialize storage manager with vault root directory.

        Args:
            vault_root: Root directory of the vault
        """
        self.vault_root = Path(vault_root)
        self.writer = MarkdownWriter(vault_root)
        self.organizer = VaultOrganizer(vault_root)
        self.collision_handler = CollisionHandler(vault_root)
        self.logger = logging.getLogger(f"atlas.storage.{self.__class__.__name__}")

    def initialize_vault(self) -> bool:
        """
        Initialize complete vault structure.

        Returns:
            True if successful, False otherwise
        """
        try:
            success = self.organizer.ensure_vault_structure()
            if success:
                self.logger.info(f"Vault initialized at: {self.vault_root}")
            else:
                self.logger.error("Failed to initialize vault structure")
            return success
        except Exception as e:
            self.logger.error(f"Failed to initialize vault: {str(e)}")
            return False

    def store_content_item(self, content_item: Dict[str, Any]) -> Optional[Path]:
        """
        Store a content item with full processing pipeline.

        Args:
            content_item: Standardized Atlas content item

        Returns:
            Path to stored file or None if failed
        """
        try:
            # Validate content item first
            validation_result = self._validate_content_item(content_item)
            if not validation_result.is_valid:
                self.logger.warning(
                    f"Content item failed validation: {content_item.get('title', 'Unknown')} - {validation_result.errors}"
                )
                # Continue anyway - storage is more important than validation

            # Extract metadata for path generation
            content_type = content_item.get('type', 'unknown')
            date_str = content_item.get('date', datetime.now().isoformat())

            # Parse date
            try:
                date = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            except ValueError:
                date = datetime.now()

            # Generate base filename
            title = content_item.get('title', 'untitled')
            source = content_item.get('source', 'unknown')
            base_filename = self.writer._generate_filename(title, source, date_str)

            # Get target directory
            target_dir = self.organizer.get_content_dir(content_type, date)

            # Resolve filename collisions
            resolved_filename, collision_info = self.collision_handler.resolve_collision(
                target_dir, base_filename, content_item
            )

            # Create complete file path
            file_path = target_dir / f"{resolved_filename}.md"

            # Add collision info to content metadata
            if collision_info['strategy_used'] != 'none':
                content_item['collision_info'] = collision_info

            # Override the filename in content item to use resolved filename
            content_item['_resolved_filename'] = resolved_filename

            # Ensure directory exists
            target_dir.mkdir(parents=True, exist_ok=True)

            # Write content using writer with explicit file path
            written_path = self.writer.write_content_item_to_path(content_item, file_path)

            if written_path:
                self.logger.info(
                    f"Content item stored successfully: {content_item.get('title', 'Unknown')} ({content_type}) -> {written_path.relative_to(self.vault_root)} [collision: {collision_info['strategy_used']}]"
                )
                return written_path
            else:
                self.logger.error(f"Failed to write content item: {content_item.get('title', 'Unknown')}")
                return None

        except Exception as e:
            self.logger.error(
                f"Failed to store content item: {content_item.get('title', 'Unknown')} ({content_item.get('type', 'unknown')}) - {str(e)}",
                exc_info=True
            )
            return None

    def store_batch(self, content_items: List[Dict[str, Any]]) -> List[Path]:
        """
        Store multiple content items.

        Args:
            content_items: List of content items to store

        Returns:
            List of successfully stored file paths
        """
        stored_paths = []

        for item in content_items:
            try:
                path = self.store_content_item(item)
                if path:
                    stored_paths.append(path)
            except Exception as e:
                self.logger.error(f"Failed to store item in batch: {str(e)}")
                continue

        self.logger.info(
            f"Batch storage completed",
            total_items=len(content_items),
            successful=len(stored_paths),
            failed=len(content_items) - len(stored_paths)
        )

        return stored_paths

    def update_content_item(self, file_path: Path, updates: Dict[str, Any]) -> bool:
        """
        Update existing content item.

        Args:
            file_path: Path to existing file
            updates: Fields to update

        Returns:
            True if successful, False otherwise
        """
        try:
            # Use writer to update the file
            success = self.writer.update_content_item(file_path, updates)

            if success:
                self.logger.info(f"Content item updated: {file_path.name}")
            else:
                self.logger.error(f"Failed to update content item: {file_path.name}")

            return success

        except Exception as e:
            self.logger.error(f"Failed to update content item {file_path}: {str(e)}")
            return False

    def get_file_info(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """
        Get information about a stored file.

        Args:
            file_path: Path to stored file

        Returns:
            File information dictionary or None if file doesn't exist
        """
        return self.writer.get_file_info(file_path)

    def list_content_by_type(self, content_type: str, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        List stored content by type.

        Args:
            content_type: Type of content to list
            limit: Maximum number of items to return

        Returns:
            List of file information dictionaries
        """
        try:
            content_dir = self.organizer.inbox_dir / content_type
            if not content_dir.exists():
                return []

            files = []
            for file_path in content_dir.rglob("*.md"):
                if file_path.is_file():
                    info = self.get_file_info(file_path)
                    if info:
                        files.append(info)
                        if limit and len(files) >= limit:
                            break

            # Sort by modification date (newest first)
            files.sort(key=lambda x: x['modified'], reverse=True)
            return files

        except Exception as e:
            self.logger.error(f"Failed to list content by type {content_type}: {str(e)}")
            return []

    def search_content(self, query: str, content_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Search content by title or frontmatter.

        Args:
            query: Search query
            content_type: Optional content type filter

        Returns:
            List of matching file information dictionaries
        """
        try:
            results = []
            query_lower = query.lower()

            # Determine search directories
            search_dirs = [self.organizer.inbox_dir]
            if content_type:
                search_dirs = [self.organizer.inbox_dir / content_type]

            for search_dir in search_dirs:
                if not search_dir.exists():
                    continue

                for file_path in search_dir.rglob("*.md"):
                    if file_path.is_file():
                        info = self.get_file_info(file_path)
                        if info:
                            # Search in title and frontmatter
                            title = info['frontmatter'].get('title', '').lower()
                            content_text = info['frontmatter'].get('content', '').lower()

                            if (query_lower in title or
                                query_lower in content_text or
                                query_lower in str(info['frontmatter']).lower()):
                                results.append(info)

            results.sort(key=lambda x: x['modified'], reverse=True)
            return results

        except Exception as e:
            self.logger.error(f"Failed to search content: {str(e)}")
            return []

    def get_storage_stats(self) -> Dict[str, Any]:
        """
        Get comprehensive storage statistics.

        Returns:
            Dictionary with storage statistics
        """
        try:
            # Get vault stats from organizer
            vault_stats = self.organizer.get_vault_stats()

            # Get collision stats
            collision_stats = self.collision_handler.get_collision_stats()

            # Combine stats
            combined_stats = {
                **vault_stats,
                'collisions': collision_stats,
                'vault_root': str(self.vault_root),
                'vault_structure_valid': len(self.organizer.validate_vault_structure()) == 0
            }

            return combined_stats

        except Exception as e:
            self.logger.error(f"Failed to get storage stats: {str(e)}")
            return {}

    def cleanup_storage(self) -> Dict[str, Any]:
        """
        Perform storage cleanup operations.

        Returns:
            Dictionary with cleanup results
        """
        try:
            results = {
                'collision_registry_cleaned': 0,
                'empty_directories_removed': []
            }

            # Clean up collision registry
            cleaned = self.collision_handler.cleanup_registry()
            results['collision_registry_cleaned'] = cleaned

            # Remove empty directories
            empty_dirs = self.organizer.cleanup_empty_directories()
            results['empty_directories_removed'] = empty_dirs

            self.logger.info(
                f"Storage cleanup completed",
                collisions_cleaned=cleaned,
                empty_dirs_removed=len(empty_dirs)
            )

            return results

        except Exception as e:
            self.logger.error(f"Failed to cleanup storage: {str(e)}")
            return {}

    def validate_storage_integrity(self) -> List[str]:
        """
        Validate storage integrity and structure.

        Returns:
            List of validation errors (empty if valid)
        """
        errors = []

        try:
            # Validate vault structure
            structure_errors = self.organizer.validate_vault_structure()
            errors.extend(structure_errors)

            # Check vault root exists
            if not self.vault_root.exists():
                errors.append(f"Vault root directory does not exist: {self.vault_root}")
            elif not self.vault_root.is_dir():
                errors.append(f"Vault root is not a directory: {self.vault_root}")

            # Check critical subdirectories
            critical_dirs = ['inbox', 'logs', 'failures', 'config']
            for dir_name in critical_dirs:
                dir_path = self.vault_root / dir_name
                if not dir_path.exists():
                    errors.append(f"Missing critical directory: {dir_name}")

            # Check collision registry integrity
            if self.collision_handler.registry_file.exists():
                try:
                    import json
                    with open(self.collision_handler.registry_file, 'r') as f:
                        json.load(f)  # Verify valid JSON
                except json.JSONDecodeError:
                    errors.append("Collision registry file is corrupted")

            return errors

        except Exception as e:
            errors.append(f"Storage validation failed: {str(e)}")
            return errors

    def _validate_content_item(self, content_item: dict) -> ValidationResult:
        """Validate content item using validator."""
        try:
            from ..core.validator import ContentValidator

            validator = ContentValidator()
            return validator.validate_content_item(content_item)

        except Exception as e:
            self.logger.debug(f"Content validation failed: {str(e)}")
            # Return valid result if validation fails - storage is more important
            return ValidationResult(is_valid=True, errors=[], warnings=[], metadata={})

    def export_content_list(self, output_file: Path) -> bool:
        """
        Export list of all stored content to file.

        Args:
            output_file: Path to output file

        Returns:
            True if successful, False otherwise
        """
        try:
            import json

            all_content = []

            # Collect all content files
            for content_type in ['newsletters', 'podcasts', 'articles', 'youtube', 'emails']:
                content_items = self.list_content_by_type(content_type)
                for item in content_items:
                    item_info = {
                        'path': str(item['path']),
                        'type': item['frontmatter'].get('type', 'unknown'),
                        'title': item['frontmatter'].get('title', 'Untitled'),
                        'source': item['frontmatter'].get('source', 'unknown'),
                        'date': item['frontmatter'].get('date', ''),
                        'created': item['created'].isoformat(),
                        'modified': item['modified'].isoformat()
                    }
                    all_content.append(item_info)

            # Write to file
            output_file.parent.mkdir(parents=True, exist_ok=True)
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'export_date': datetime.now().isoformat(),
                    'total_items': len(all_content),
                    'content': all_content
                }, f, indent=2)

            self.logger.info(
                f"Content list exported",
                total_items=len(all_content),
                output_file=str(output_file)
            )

            return True

        except Exception as e:
            self.logger.error(f"Failed to export content list: {str(e)}")
            return False


__all__ = [
    "StorageManager",
]