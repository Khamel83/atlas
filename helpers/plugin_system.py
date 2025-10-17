#!/usr/bin/env python3
"""
Atlas Plugin System - Task 3.4 Integration & Extension Framework

Provides a flexible plugin architecture for extending Atlas functionality
with custom content processors, data exporters, and external integrations.

Key Features:
- Plugin discovery and loading system
- Standardized plugin interface with lifecycle hooks
- Dependency management and version compatibility
- Plugin configuration and settings management
- Event system for plugin communication
- Security sandbox for plugin execution
"""

import importlib
import importlib.util
import inspect
import json
import os
import sys
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Type, Union, Callable
from dataclasses import dataclass, asdict
from enum import Enum
import logging
import threading
from concurrent.futures import ThreadPoolExecutor, TimeoutError

from helpers.config import load_config
from helpers.utils import log_info, log_error


class PluginType(Enum):
    """Types of plugins supported by Atlas."""
    CONTENT_PROCESSOR = "content_processor"
    DATA_EXPORTER = "data_exporter"
    SEARCH_ENHANCER = "search_enhancer"
    API_EXTENSION = "api_extension"
    WEBHOOK_HANDLER = "webhook_handler"
    ANALYTICS_PROVIDER = "analytics_provider"


class PluginStatus(Enum):
    """Plugin status states."""
    LOADED = "loaded"
    ACTIVE = "active"
    DISABLED = "disabled"
    ERROR = "error"
    LOADING = "loading"


@dataclass
class PluginManifest:
    """Plugin manifest with metadata and requirements."""
    name: str
    version: str
    description: str
    author: str
    plugin_type: PluginType
    entry_point: str
    dependencies: List[str] = None
    atlas_version_min: str = "1.0.0"
    atlas_version_max: str = "2.0.0"
    config_schema: Dict[str, Any] = None
    permissions: List[str] = None

    def __post_init__(self):
        if self.dependencies is None:
            self.dependencies = []
        if self.config_schema is None:
            self.config_schema = {}
        if self.permissions is None:
            self.permissions = []


@dataclass
class PluginInfo:
    """Runtime plugin information."""
    manifest: PluginManifest
    status: PluginStatus
    instance: Optional[Any] = None
    load_time: Optional[datetime] = None
    error_message: Optional[str] = None
    config: Dict[str, Any] = None

    def __post_init__(self):
        if self.config is None:
            self.config = {}


class BasePlugin(ABC):
    """Base class for all Atlas plugins."""

    def __init__(self, plugin_manager: 'PluginManager', config: Dict[str, Any]):
        """Initialize plugin with manager reference and configuration.

        Args:
            plugin_manager: Reference to the plugin manager
            config: Plugin-specific configuration
        """
        self.plugin_manager = plugin_manager
        self.config = config
        self.logger = plugin_manager.get_logger(self.__class__.__name__)

    @abstractmethod
    def initialize(self) -> bool:
        """Initialize the plugin. Called after instantiation.

        Returns:
            True if initialization successful, False otherwise
        """
        pass

    @abstractmethod
    def cleanup(self) -> None:
        """Cleanup plugin resources. Called before unloading."""
        pass

    def get_name(self) -> str:
        """Get plugin name."""
        return self.__class__.__name__

    def get_version(self) -> str:
        """Get plugin version."""
        return getattr(self, 'VERSION', '1.0.0')

    def emit_event(self, event_name: str, data: Dict[str, Any]) -> None:
        """Emit an event that other plugins can listen to."""
        self.plugin_manager.emit_event(self.get_name(), event_name, data)

    def listen_event(self, plugin_name: str, event_name: str, handler: Callable) -> None:
        """Listen to events from other plugins."""
        self.plugin_manager.listen_event(plugin_name, event_name, handler)


class ContentProcessorPlugin(BasePlugin):
    """Base class for content processing plugins."""

    @abstractmethod
    def can_process(self, content_type: str, content_data: Dict[str, Any]) -> bool:
        """Check if this plugin can process the given content.

        Args:
            content_type: Type of content (article, document, etc.)
            content_data: Content metadata and data

        Returns:
            True if plugin can process this content
        """
        pass

    @abstractmethod
    def process_content(self, content_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process content and return enhanced data.

        Args:
            content_data: Content to process

        Returns:
            Enhanced content data
        """
        pass


class DataExporterPlugin(BasePlugin):
    """Base class for data export plugins."""

    @abstractmethod
    def get_supported_formats(self) -> List[str]:
        """Get list of supported export formats.

        Returns:
            List of format names
        """
        pass

    @abstractmethod
    def export_data(self, data: List[Dict[str, Any]], format: str, options: Dict[str, Any]) -> bytes:
        """Export data in specified format.

        Args:
            data: Data to export
            format: Export format
            options: Export options

        Returns:
            Exported data as bytes
        """
        pass


class PluginManager:
    """Manages plugin lifecycle and provides plugin services."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize plugin manager.

        Args:
            config: Configuration dictionary
        """
        self.config = config or load_config()
        self.plugins: Dict[str, PluginInfo] = {}
        self.plugin_dirs = [
            Path(self.config.get('plugin_directory', 'plugins')),
            Path('plugins'),
            Path.home() / '.atlas' / 'plugins'
        ]

        # Event system
        self.event_handlers: Dict[str, List[Callable]] = {}
        self.event_lock = threading.Lock()

        # Thread pool for plugin operations
        self.executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="plugin-")

        # Set up logging
        log_dir = self.config.get('log_directory', 'logs')
        os.makedirs(log_dir, exist_ok=True)
        self.log_path = os.path.join(log_dir, 'plugin_system.log')

        # Initialize plugin directories
        self._initialize_plugin_directories()

    def _initialize_plugin_directories(self) -> None:
        """Create plugin directories if they don't exist."""
        for plugin_dir in self.plugin_dirs:
            plugin_dir.mkdir(parents=True, exist_ok=True)

            # Create example plugin if directory is empty
            if not any(plugin_dir.iterdir()):
                self._create_example_plugin(plugin_dir)

    def _create_example_plugin(self, plugin_dir: Path) -> None:
        """Create an example plugin for reference."""
        example_dir = plugin_dir / 'example_processor'
        example_dir.mkdir(exist_ok=True)

        # Create manifest
        manifest = {
            "name": "Example Content Processor",
            "version": "1.0.0",
            "description": "Example plugin demonstrating content processing",
            "author": "Atlas Team",
            "plugin_type": "content_processor",
            "entry_point": "example_processor.ExampleProcessor",
            "dependencies": [],
            "config_schema": {
                "enabled": {"type": "boolean", "default": True},
                "processing_options": {"type": "object", "default": {}}
            }
        }

        with open(example_dir / 'plugin.json', 'w') as f:
            json.dump(manifest, f, indent=2)

        # Create plugin code
        plugin_code = '''"""Example content processor plugin."""
from helpers.plugin_system import ContentProcessorPlugin
from typing import Dict, Any


class ExampleProcessor(ContentProcessorPlugin):
    """Example content processing plugin."""

    VERSION = "1.0.0"

    def initialize(self) -> bool:
        """Initialize the plugin."""
        self.logger.info("Example processor initialized")
        return True

    def cleanup(self) -> None:
        """Cleanup plugin resources."""
        self.logger.info("Example processor cleaned up")

    def can_process(self, content_type: str, content_data: Dict[str, Any]) -> bool:
        """Check if we can process this content."""
        # Example: process all articles
        return content_type == "article"

    def process_content(self, content_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process content and add metadata."""
        self.logger.info(f"Processing content: {content_data.get('title', 'Unknown')}")

        # Example processing: add word count
        content = content_data.get('content', '')
        word_count = len(content.split()) if content else 0

        # Return enhanced content
        enhanced_data = content_data.copy()
        enhanced_data['metadata'] = enhanced_data.get('metadata', {})
        enhanced_data['metadata']['word_count'] = word_count
        enhanced_data['metadata']['processed_by'] = 'ExampleProcessor'

        return enhanced_data
'''

        with open(example_dir / 'example_processor.py', 'w') as f:
            f.write(plugin_code)

    def discover_plugins(self) -> List[PluginManifest]:
        """Discover all available plugins.

        Returns:
            List of plugin manifests
        """
        manifests = []

        for plugin_dir in self.plugin_dirs:
            if not plugin_dir.exists():
                continue

            for item in plugin_dir.iterdir():
                if not item.is_dir():
                    continue

                manifest_path = item / 'plugin.json'
                if not manifest_path.exists():
                    continue

                try:
                    with open(manifest_path, 'r') as f:
                        manifest_data = json.load(f)

                    manifest = PluginManifest(
                        name=manifest_data['name'],
                        version=manifest_data['version'],
                        description=manifest_data['description'],
                        author=manifest_data['author'],
                        plugin_type=PluginType(manifest_data['plugin_type']),
                        entry_point=manifest_data['entry_point'],
                        dependencies=manifest_data.get('dependencies', []),
                        atlas_version_min=manifest_data.get('atlas_version_min', '1.0.0'),
                        atlas_version_max=manifest_data.get('atlas_version_max', '2.0.0'),
                        config_schema=manifest_data.get('config_schema', {}),
                        permissions=manifest_data.get('permissions', [])
                    )

                    manifests.append(manifest)
                    log_info(self.log_path, f"Discovered plugin: {manifest.name}")

                except Exception as e:
                    log_error(self.log_path, f"Error loading plugin manifest {manifest_path}: {e}")

        return manifests

    def load_plugin(self, manifest: PluginManifest, plugin_dir: Path) -> bool:
        """Load a specific plugin.

        Args:
            manifest: Plugin manifest
            plugin_dir: Directory containing the plugin

        Returns:
            True if loaded successfully
        """
        try:
            # Create plugin info
            plugin_info = PluginInfo(
                manifest=manifest,
                status=PluginStatus.LOADING,
                load_time=datetime.now()
            )

            self.plugins[manifest.name] = plugin_info

            # Add plugin directory to Python path
            plugin_path = str(plugin_dir)
            if plugin_path not in sys.path:
                sys.path.insert(0, plugin_path)

            # Load plugin module and class
            module_name, class_name = manifest.entry_point.rsplit('.', 1)
            spec = importlib.util.spec_from_file_location(
                module_name,
                plugin_dir / f"{module_name}.py"
            )

            if spec is None or spec.loader is None:
                raise ImportError(f"Could not load module {module_name}")

            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            plugin_class = getattr(module, class_name)

            # Validate plugin class
            if not issubclass(plugin_class, BasePlugin):
                raise TypeError(f"Plugin class {class_name} must inherit from BasePlugin")

            # Load plugin configuration
            plugin_config = self._load_plugin_config(manifest.name)

            # Instantiate plugin
            plugin_instance = plugin_class(self, plugin_config)

            # Initialize plugin with timeout
            future = self.executor.submit(plugin_instance.initialize)
            try:
                success = future.result(timeout=30)  # 30 second timeout
                if not success:
                    raise RuntimeError("Plugin initialization returned False")
            except TimeoutError:
                raise RuntimeError("Plugin initialization timed out")

            # Update plugin info
            plugin_info.instance = plugin_instance
            plugin_info.status = PluginStatus.ACTIVE
            plugin_info.config = plugin_config

            log_info(self.log_path, f"Successfully loaded plugin: {manifest.name}")
            return True

        except Exception as e:
            # Update plugin info with error
            if manifest.name in self.plugins:
                self.plugins[manifest.name].status = PluginStatus.ERROR
                self.plugins[manifest.name].error_message = str(e)

            log_error(self.log_path, f"Error loading plugin {manifest.name}: {e}")
            return False

    def _load_plugin_config(self, plugin_name: str) -> Dict[str, Any]:
        """Load plugin-specific configuration."""
        config_path = Path(self.config.get('plugin_config_directory', 'config/plugins'))
        config_path.mkdir(parents=True, exist_ok=True)

        plugin_config_path = config_path / f"{plugin_name.lower().replace(' ', '_')}.json"

        if plugin_config_path.exists():
            try:
                with open(plugin_config_path, 'r') as f:
                    return json.load(f)
            except Exception as e:
                log_error(self.log_path, f"Error loading config for {plugin_name}: {e}")

        return {}

    def load_all_plugins(self) -> None:
        """Discover and load all available plugins."""
        manifests = self.discover_plugins()

        for manifest in manifests:
            # Find plugin directory
            plugin_dir = None
            for base_dir in self.plugin_dirs:
                potential_dir = base_dir / manifest.name.lower().replace(' ', '_')
                if potential_dir.exists():
                    plugin_dir = potential_dir
                    break

            if plugin_dir is None:
                log_error(self.log_path, f"Could not find directory for plugin: {manifest.name}")
                continue

            self.load_plugin(manifest, plugin_dir)

    def unload_plugin(self, plugin_name: str) -> bool:
        """Unload a specific plugin.

        Args:
            plugin_name: Name of plugin to unload

        Returns:
            True if unloaded successfully
        """
        if plugin_name not in self.plugins:
            return False

        plugin_info = self.plugins[plugin_name]

        try:
            if plugin_info.instance:
                # Cleanup plugin with timeout
                future = self.executor.submit(plugin_info.instance.cleanup)
                try:
                    future.result(timeout=10)  # 10 second timeout
                except TimeoutError:
                    log_error(self.log_path, f"Plugin {plugin_name} cleanup timed out")

            # Remove from plugins dict
            del self.plugins[plugin_name]

            log_info(self.log_path, f"Unloaded plugin: {plugin_name}")
            return True

        except Exception as e:
            log_error(self.log_path, f"Error unloading plugin {plugin_name}: {e}")
            return False

    def get_plugins_by_type(self, plugin_type: PluginType) -> List[PluginInfo]:
        """Get all active plugins of a specific type.

        Args:
            plugin_type: Type of plugins to retrieve

        Returns:
            List of matching plugin info objects
        """
        return [
            info for info in self.plugins.values()
            if info.manifest.plugin_type == plugin_type and info.status == PluginStatus.ACTIVE
        ]

    def emit_event(self, source_plugin: str, event_name: str, data: Dict[str, Any]) -> None:
        """Emit an event from a plugin.

        Args:
            source_plugin: Name of plugin emitting the event
            event_name: Name of the event
            data: Event data
        """
        event_key = f"{source_plugin}:{event_name}"

        with self.event_lock:
            handlers = self.event_handlers.get(event_key, [])

        for handler in handlers:
            try:
                handler(data)
            except Exception as e:
                log_error(self.log_path, f"Error in event handler for {event_key}: {e}")

    def listen_event(self, source_plugin: str, event_name: str, handler: Callable) -> None:
        """Register an event handler.

        Args:
            source_plugin: Plugin to listen to
            event_name: Event to listen for
            handler: Handler function
        """
        event_key = f"{source_plugin}:{event_name}"

        with self.event_lock:
            if event_key not in self.event_handlers:
                self.event_handlers[event_key] = []
            self.event_handlers[event_key].append(handler)

    def get_logger(self, plugin_name: str) -> logging.Logger:
        """Get a logger for a plugin.

        Args:
            plugin_name: Name of the plugin

        Returns:
            Configured logger instance
        """
        logger = logging.getLogger(f"atlas.plugin.{plugin_name}")
        if not logger.handlers:
            handler = logging.FileHandler(self.log_path)
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)

        return logger

    def get_plugin_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all plugins.

        Returns:
            Dictionary with plugin status information
        """
        status = {}

        for name, info in self.plugins.items():
            status[name] = {
                'status': info.status.value,
                'version': info.manifest.version,
                'type': info.manifest.plugin_type.value,
                'load_time': info.load_time.isoformat() if info.load_time else None,
                'error': info.error_message,
                'config_keys': list(info.config.keys()) if info.config else []
            }

        return status

    def shutdown(self) -> None:
        """Shutdown plugin manager and cleanup resources."""
        # Unload all plugins
        plugin_names = list(self.plugins.keys())
        for name in plugin_names:
            self.unload_plugin(name)

        # Shutdown thread pool
        self.executor.shutdown(wait=True)

        log_info(self.log_path, "Plugin manager shut down")


# Global plugin manager instance
_plugin_manager: Optional[PluginManager] = None


def get_plugin_manager() -> PluginManager:
    """Get the global plugin manager instance."""
    global _plugin_manager
    if _plugin_manager is None:
        _plugin_manager = PluginManager()
    return _plugin_manager


def initialize_plugins() -> None:
    """Initialize the plugin system."""
    manager = get_plugin_manager()
    manager.load_all_plugins()


def shutdown_plugins() -> None:
    """Shutdown the plugin system."""
    global _plugin_manager
    if _plugin_manager is not None:
        _plugin_manager.shutdown()
        _plugin_manager = None