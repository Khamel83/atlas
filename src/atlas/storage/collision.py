"""
Filename collision handling for Atlas v4.

Handles filename collisions when multiple content items would otherwise
have the same filename. Implements multiple strategies and maintains a collision registry.
"""

import json
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import logging

from .organizer import VaultOrganizer


class CollisionHandler:
    """
    Handles filename collisions in Atlas storage.

    Provides multiple collision resolution strategies:
    1. Numeric suffix (-2, -3, etc.)
    2. Hash-based suffix
    3. Content-based disambiguation
    4. Timestamp-based suffix
    """

    def __init__(self, vault_root: str, registry_file: Optional[str] = None):
        """
        Initialize collision handler.

        Args:
            vault_root: Root directory of the vault
            registry_file: Path to collision registry file (optional)
        """
        self.vault_root = Path(vault_root)
        self.registry_file = Path(registry_file) if registry_file else Path(vault_root) / ".collision_registry.json"
        self.logger = logging.getLogger(f"atlas.storage.{self.__class__.__name__}")

        # Load existing registry
        self.registry = self._load_registry()

    def _load_registry(self) -> dict:
        """Load collision registry from file."""
        if self.registry_file.exists():
            try:
                with open(self.registry_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                self.logger.warning(f"Failed to load collision registry: {str(e)}")
                return {}

        return {}

    def _save_registry(self) -> None:
        """Save collision registry to file."""
        try:
            # Ensure directory exists
            self.registry_file.parent.mkdir(parents=True, exist_ok=True)

            with open(self.registry_file, 'w', encoding='utf-8') as f:
                json.dump(self.registry, f, indent=2, default=str)
        except Exception as e:
            self.logger.error(f"Failed to save collision registry: {str(e)}")

    def resolve_collision(
        self,
        directory: Path,
        filename: str,
        content_item: Optional[dict] = None
    ) -> tuple:
        """
        Resolve filename collision using multiple strategies.

        Args:
            directory: Target directory
            filename: Base filename
            content_item: Content item for advanced resolution

        Returns:
            Tuple of (resolved_filename, collision_info)
        """
        collision_info = {
            'original_filename': filename,
            'strategy_used': None,
            'collision_count': 0,
            'resolved_filename': filename,
            'registry_entry': None
        }

        try:
            # Strategy 1: Check if this is a known collision
            if filename in self.registry:
                return self._resolve_known_collision(directory, filename, collision_info)

            # Strategy 2: Check for existing file with same name
            file_path = directory / f"{filename}.md"
            if file_path.exists():
                return self._resolve_new_collision(directory, filename, collision_info)

            # No collision - return original
            collision_info['resolved_filename'] = filename
            return filename, collision_info

        except Exception as e:
            self.logger.error(f"Failed to resolve collision for {filename}: {str(e)}")
            # Fallback to original filename
            collision_info['resolved_filename'] = filename
            return filename, collision_info

    def _resolve_known_collision(
        self,
        directory: Path,
        filename: str,
        collision_info: dict
    ) -> tuple:
        """Resolve collision that's been seen before."""
        registry_entry = self.registry[filename]

        collision_info['strategy_used'] = 'registry'
        collision_info['collision_count'] = registry_entry['collision_count']

        # Use the existing resolved filename
        resolved_filename = registry_entry['resolved_filename']
        collision_info['resolved_filename'] = resolved_filename
        collision_info['registry_entry'] = registry_entry

        return resolved_filename, collision_info

    def _resolve_new_collision(
        self,
        directory: Path,
        filename: str,
        collision_info: dict
    ) -> tuple:
        """Resolve new collision using numeric suffix strategy."""
        base_filename = filename
        counter = 2
        max_attempts = 100

        while counter <= max_attempts:
            test_filename = f"{base_filename}-{counter}"
            test_path = directory / f"{test_filename}.md"

            if not test_path.exists():
                # Found available filename
                collision_info['strategy_used'] = 'numeric_suffix'
                collision_info['collision_count'] = counter - 1
                collision_info['resolved_filename'] = test_filename

                # Register this collision
                self._register_collision(base_filename, test_filename, counter - 1)

                return test_filename, collision_info

            counter += 1

        # If we get here, all numeric options are exhausted
        # Fallback to hash-based strategy
        return self._resolve_with_hash(directory, base_filename, collision_info)

    def _resolve_with_hash(
        self,
        directory: Path,
        filename: str,
        collision_info: dict
    ) -> tuple:
        """Resolve collision using hash-based strategy."""
        # Create a unique hash based on current timestamp and random
        hash_input = f"{filename}_{datetime.now().isoformat()}_{hash(filename)}"
        hash_suffix = hashlib.md5(hash_input.encode()).hexdigest()[:8]

        hash_filename = f"{filename}-{hash_suffix}"
        hash_path = directory / f"{hash_filename}.md"

        # Check if even hash-based filename collides (very unlikely)
        if hash_path.exists():
            # Add another random component
            hash_suffix = hashlib.md5(f"{hash_input}_retry_{hash(hash_suffix.encode())}").hexdigest()[:8]
            hash_filename = f"{filename}-{hash_suffix}"

        collision_info['strategy_used'] = 'hash_suffix'
        collision_info['resolved_filename'] = hash_filename

        return hash_filename, collision_info

    def _register_collision(self, original_filename: str, resolved_filename: str, suffix: int) -> None:
        """Register a collision in the registry."""
        try:
            # Update existing entry or create new one
            if original_filename in self.registry:
                # Update existing entry
                self.registry[original_filename]['collision_count'] = suffix
                self.registry[original_filename]['resolved_filename'] = resolved_filename
                self.registry[original_filename]['last_updated'] = datetime.now().isoformat()
            else:
                # Create new entry
                self.registry[original_filename] = {
                    'original_filename': original_filename,
                    'resolved_filename': resolved_filename,
                    'collision_count': suffix,
                    'created_at': datetime.now().isoformat(),
                    'last_updated': datetime.now().isoformat()
                }

            self._save_registry()

        except Exception as e:
            self.logger.error(f"Failed to register collision: {str(e)}")

    def get_collision_info(self, filename: str) -> Optional[dict]:
        """
        Get collision information for a filename.

        Args:
            filename: Base filename

        Returns:
            Collision information or None if no collision
        """
        if filename in self.registry:
            return self.registry[filename]
        return None

    def list_collisions(self, content_type: Optional[str] = None) -> list:
        """
        List all collisions in the registry.

        Args:
            content_type: Filter by content type (optional)

        Returns:
            List of collision information
        """
        collisions = []

        for filename, info in self.registry.items():
            if content_type and content_type not in filename.lower():
                continue

            collisions.append(info)

        return collisions

    def cleanup_registry(self) -> int:
        """
        Clean up the collision registry by removing entries for files that no longer exist.

        Returns:
            Number of entries cleaned up
        """
        cleaned = 0
        to_remove = []

        for filename, info in self.registry.items():
            # Check if resolved file exists
            resolved_path = self.vault_root / "inbox"
            for content_type in ['newsletters', 'podcasts', 'articles', 'youtube', 'emails']:
                type_dir = resolved_path / content_type
                for date_dir in type_dir.iterdir():
                    if date_dir.is_dir():
                        for file_path in date_dir.glob(f"{info['resolved_filename']}.md"):
                            if file_path.exists():
                                break
                    else:
                        # Check if any file matches in this date directory
                        if any(file_path.name == f"{info['resolved_filename']}.md" for file_path in date_dir.glob("*.md")):
                            break

        for filename, info in self.registry.items():
            file_found = False
            resolved_path = self.vault_root / "inbox"
            for content_type in ['newsletters', 'podcasts', 'articles', 'youtube', 'emails']:
                type_dir = resolved_path / content_type
                for date_dir in type_dir.iterdir():
                    if date_dir.is_dir():
                        if (date_dir / f"{info['resolved_filename']}.md").exists():
                            file_found = True
                            break
                    else:
                        # Check all files in this date directory
                        if any(f.name == f"{info['resolved_filename']}.md" for f in date_dir.glob("*.md")):
                            file_found = True
                            break

                if file_found:
                    break

            if not file_found:
                to_remove.append(filename)

        # Remove entries
        for filename in to_remove:
            del self.registry[filename]
            cleaned += 1

        if cleaned > 0:
            self._save_registry()
            self.logger.info(f"Cleaned up {cleaned} collision registry entries")

        return cleaned

    def get_collision_stats(self) -> dict:
        """
        Get statistics about collisions.

        Returns:
            Dictionary with collision statistics
        """
        stats = {
            'total_collisions': len(self.registry),
            'collision_types': {},
            'most_common_collisions': [],
            'oldest_collision': None,
            'newest_collision': None
        }

        if not self.registry:
            return stats

        # Count collision types
        for info in self.registry.values():
            count = info['collision_count']
            strategy = info.get('strategy_used', 'unknown')
            stats['collision_types'][strategy] = stats['collision_types'].get(strategy, 0) + 1

        # Find most common collisions
        sorted_collisions = sorted(
            self.registry.items(),
            key=lambda x: x[1]['collision_count'],
            reverse=True
        )
        stats['most_common_collisions'] = [
            {'filename': filename, 'count': info['collision_count']}
            for filename, info in sorted_collisions[:10]
        ]

        # Find oldest and newest collisions
        date_fields = ['created_at', 'last_updated']
        for field in date_fields:
            if field in info and info[field]:
                pass

        return stats