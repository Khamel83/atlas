#!/usr/bin/env python3
"""
Atlas Configuration Manager
Supports both JSON and TOML configuration formats with fallback capabilities
"""

import os
import json
from typing import Dict, Any, Optional
from pathlib import Path

# Import TOML support with fallback for older Python versions
try:
    import tomllib  # Python 3.11+
except ImportError:
    try:
        import tomli as tomllib  # pip install tomli
    except ImportError:
        tomllib = None

class AtlasConfig:
    """
    Atlas configuration manager supporting both JSON and TOML formats
    with automatic fallback and migration capabilities
    """

    def __init__(self, config_dir: str = "."):
        self.config_dir = Path(config_dir)
        self.json_config = self.config_dir / "atlas_relayq_config.json"
        self.toml_config = self.config_dir / "atlas_config.toml"

    def _load_toml(self, config_path: Path) -> Optional[Dict[str, Any]]:
        """Load TOML configuration file"""
        if not tomllib:
            raise ImportError("TOML support not available. Install tomli: pip install tomli")

        try:
            with open(config_path, 'rb') as f:
                return tomllib.load(f)
        except FileNotFoundError:
            return None
        except Exception as e:
            raise ValueError(f"Error loading TOML config {config_path}: {e}")

    def _load_json(self, config_path: Path) -> Optional[Dict[str, Any]]:
        """Load JSON configuration file"""
        try:
            with open(config_path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return None
        except Exception as e:
            raise ValueError(f"Error loading JSON config {config_path}: {e}")

    def load_config(self, prefer_toml: bool = True) -> Dict[str, Any]:
        """
        Load configuration with automatic fallback

        Args:
            prefer_toml: If True, try TOML first, then JSON

        Returns:
            Loaded configuration dictionary
        """
        config = None

        if prefer_toml:
            # Try TOML first
            config = self._load_toml(self.toml_config)
            if config is None:
                # Fallback to JSON
                config = self._load_json(self.json_config)
        else:
            # Try JSON first
            config = self._load_json(self.json_config)
            if config is None:
                # Fallback to TOML
                config = self._load_toml(self.toml_config)

        if config is None:
            raise FileNotFoundError(
                f"No configuration found. Tried {self.toml_config} and {self.json_config}"
            )

        return config

    def get_source_format(self) -> str:
        """Determine which configuration format is being used"""
        if self.toml_config.exists():
            return "toml"
        elif self.json_config.exists():
            return "json"
        else:
            return "none"

    def migrate_to_toml(self, backup: bool = True) -> bool:
        """
        Migrate from JSON to TOML configuration

        Args:
            backup: Create backup of original JSON file

        Returns:
            True if migration successful, False otherwise
        """
        if not self.json_config.exists():
            raise FileNotFoundError(f"JSON config {self.json_config} not found")

        if self.toml_config.exists():
            raise FileExistsError(f"TOML config {self.toml_config} already exists")

        try:
            # Load JSON config
            json_config = self._load_json(self.json_config)

            # Create backup if requested
            if backup:
                backup_path = self.config_dir / "config_backup" / f"atlas_relayq_config_backup_{timestamp()}.json"
                backup_path.parent.mkdir(exist_ok=True)
                import shutil
                shutil.copy2(self.json_config, backup_path)
                print(f"📋 JSON config backed up to: {backup_path}")

            # Convert to TOML structure and save
            toml_content = self._convert_json_to_toml(json_config)
            with open(self.toml_config, 'w') as f:
                f.write(toml_content)

            print(f"✅ Successfully migrated to TOML: {self.toml_config}")
            return True

        except Exception as e:
            print(f"❌ Migration failed: {e}")
            return False

    def _convert_json_to_toml(self, json_config: Dict[str, Any]) -> str:
        """Convert JSON config structure to TOML format"""
        toml_lines = []

        # Add header comment
        toml_lines.append("# Atlas Configuration")
        toml_lines.append("# Migrated from JSON configuration")
        toml_lines.append("")

        # Service section
        if "service_name" in json_config:
            toml_lines.append("[service]")
            toml_lines.append(f'name = "{json_config.get("service_name", "Atlas")}"')
            if "version" in json_config:
                toml_lines.append(f'version = "{json_config["version"]}"')
            if "created" in json_config:
                toml_lines.append(f'created = "{json_config["created"]}"')
            toml_lines.append("")

        # Atlas section
        if "atlas" in json_config:
            toml_lines.append("[atlas]")
            atlas_config = json_config["atlas"]
            for key, value in atlas_config.items():
                if isinstance(value, str):
                    toml_lines.append(f'{key} = "{value}"')
                else:
                    toml_lines.append(f'{key} = {value}')
            toml_lines.append("")

        # RelayQ section
        if "relayq" in json_config:
            toml_lines.append("[relayq]")
            relayq_config = json_config["relayq"]
            for key, value in relayq_config.items():
                if isinstance(value, list):
                    toml_lines.append(f'{key} = {self._format_list(value)}')
                elif isinstance(value, str):
                    toml_lines.append(f'{key} = "{value}"')
                else:
                    toml_lines.append(f'{key} = {value}')
            toml_lines.append("")

        # Processing section
        if "processing" in json_config:
            toml_lines.append("[processing]")
            processing_config = json_config["processing"]
            for key, value in processing_config.items():
                if isinstance(value, list):
                    toml_lines.append(f'{key} = {self._format_list(value)}')
                else:
                    toml_lines.append(f'{key} = {value}')
            toml_lines.append("")

        # Endpoints section
        if "endpoints" in json_config:
            toml_lines.append("[endpoints]")
            endpoints_config = json_config["endpoints"]
            for key, value in endpoints_config.items():
                if isinstance(value, str):
                    toml_lines.append(f'{key} = "{value}"')
                else:
                    toml_lines.append(f'{key} = {value}')

        return "\n".join(toml_lines)

    def _format_list(self, lst: list) -> str:
        """Format a list for TOML output"""
        if not lst:
            return "[]"

        formatted_items = []
        for item in lst:
            if isinstance(item, str):
                formatted_items.append(f'"{item}"')
            else:
                formatted_items.append(str(item))

        return f"[{', '.join(formatted_items)}]"

    def validate_config(self, config: Dict[str, Any]) -> bool:
        """Validate configuration structure"""
        required_sections = ["atlas", "relayq", "processing", "endpoints"]

        for section in required_sections:
            if section not in config:
                print(f"❌ Missing required section: {section}")
                return False

        # Validate atlas section
        atlas_config = config["atlas"]
        if "database_path" not in atlas_config:
            print("❌ Missing atlas.database_path")
            return False

        # Validate database path exists
        if not os.path.exists(atlas_config["database_path"]):
            print(f"⚠️  Database file not found: {atlas_config['database_path']}")

        print("✅ Configuration validation passed")
        return True

def timestamp() -> str:
    """Generate timestamp for backup files"""
    from datetime import datetime
    return datetime.now().strftime("%Y%m%d_%H%M%S")

# Example usage
if __name__ == "__main__":
    config = AtlasConfig()

    print("Atlas Configuration Manager")
    print(f"Current format: {config.get_source_format()}")

    try:
        loaded_config = config.load_config()
        print("✅ Configuration loaded successfully")
        config.validate_config(loaded_config)

        # Show some config values
        print(f"\n📊 Atlas Info:")
        if "atlas" in loaded_config:
            atlas = loaded_config["atlas"]
            print(f"   Database: {atlas.get('database_path', 'N/A')}")
            print(f"   Podcasts: {atlas.get('podcasts_count', 'N/A')}")
            print(f"   Episodes: {atlas.get('episodes_count', 'N/A')}")

    except Exception as e:
        print(f"❌ Error: {e}")