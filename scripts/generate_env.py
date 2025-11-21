#!/usr/bin/env python3
"""
Automated .env file generation script for Atlas.

This script creates a working .env file from the template with intelligent defaults
and user prompts for required values, reducing configuration errors and improving
the setup experience for new users.

Usage:
    python scripts/generate_env.py [--force] [--interactive] [--quiet]

Options:
    --force: Overwrite existing .env file without prompting
    --interactive: Prompt for all values, even optional ones
    --quiet: Minimal output, use all defaults for optional values
"""

import argparse
import getpass
import os
import re
import shutil
import sys
from pathlib import Path
from typing import Any, Dict, Optional, Tuple


class EnvGenerator:
    """Automated .env file generator with intelligent defaults and validation."""

    def __init__(self, project_root: Path = None):
        self.project_root = project_root or Path(__file__).parent.parent
        self.template_path = self.project_root / ".env.example"
        self.env_path = self.project_root / ".env"
        self.backup_path = self.project_root / ".env.backup"

        # Configuration schema with defaults, validation, and prompts
        self.config_schema = {
            "DATA_DIRECTORY": {
                "default": "output",
                "required": False,
                "description": "Directory for storing processed content",
                "validation": self._validate_directory_path,
                "prompt": "Data directory path",
            },
            "OPENROUTER_API_KEY": {
                "default": "",
                "required": False,
                "description": "OpenRouter API key for AI features (leave empty to disable)",
                "validation": self._validate_api_key,
                "prompt": "OpenRouter API key (optional, press Enter to skip)",
                "sensitive": True,
            },
            "TRANSCRIBE_ENABLED": {
                "default": "false",
                "required": False,
                "description": "Enable audio transcription features",
                "validation": self._validate_boolean,
                "prompt": "Enable transcription? (y/n)",
                "transform": self._transform_boolean,
            },
            "INSTAPAPER_API_KEY": {
                "default": "",
                "required": False,
                "description": "Instapaper API key (optional)",
                "validation": self._validate_api_key,
                "prompt": "Instapaper API key (optional)",
                "sensitive": True,
            },
            "INSTAPAPER_API_SECRET": {
                "default": "",
                "required": False,
                "description": "Instapaper API secret (optional)",
                "validation": self._validate_api_key,
                "prompt": "Instapaper API secret (optional)",
                "sensitive": True,
            },
            "INSTAPAPER_USERNAME": {
                "default": "",
                "required": False,
                "description": "Instapaper username (optional)",
                "validation": self._validate_optional_string,
                "prompt": "Instapaper username (optional)",
            },
            "INSTAPAPER_PASSWORD": {
                "default": "",
                "required": False,
                "description": "Instapaper password (optional)",
                "validation": self._validate_optional_string,
                "prompt": "Instapaper password (optional)",
                "sensitive": True,
            },
            "INSTAPAPER_CONSUMER_KEY": {
                "default": "",
                "required": False,
                "description": "Instapaper consumer key (optional)",
                "validation": self._validate_api_key,
                "prompt": "Instapaper consumer key (optional)",
                "sensitive": True,
            },
            "INSTAPAPER_CONSUMER_SECRET": {
                "default": "",
                "required": False,
                "description": "Instapaper consumer secret (optional)",
                "validation": self._validate_api_key,
                "prompt": "Instapaper consumer secret (optional)",
                "sensitive": True,
            },
        }

    def generate_env_file(
        self, force: bool = False, interactive: bool = False, quiet: bool = False
    ) -> bool:
        """
        Generate .env file from template with user input and validation.

        Args:
            force: Overwrite existing .env without prompting
            interactive: Prompt for all values including optional ones
            quiet: Use defaults without prompting

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Check if .env already exists
            if self.env_path.exists() and not force:
                if quiet:
                    print(f"✓ .env file already exists at {self.env_path}")
                    return True

                response = input(
                    f".env file already exists at {self.env_path}. Overwrite? (y/n): "
                )
                if response.lower() != "y":
                    print("Operation cancelled.")
                    return False

            # Backup existing .env file
            if self.env_path.exists():
                self._backup_existing_env()
                if not quiet:
                    print(f"✓ Backed up existing .env to {self.backup_path}")

            # Validate template exists
            if not self.template_path.exists():
                raise FileNotFoundError(
                    f"Template file not found: {self.template_path}"
                )

            # Load existing values if available
            existing_values = (
                self._load_existing_env() if self.env_path.exists() else {}
            )

            # Collect configuration values
            config_values = {}

            if not quiet:
                print("\n🔧 Generating .env file from template...")
                print(f"Template: {self.template_path}")
                print(f"Target: {self.env_path}")

                if interactive:
                    print(
                        "\nInteractive mode: You'll be prompted for all configuration values."
                    )
                else:
                    print("Using intelligent defaults. Press Ctrl+C to abort.")
                print()

            # Process each configuration item
            for key, schema in self.config_schema.items():
                try:
                    value = self._get_config_value(
                        key, schema, existing_values.get(key), interactive, quiet
                    )
                    config_values[key] = value
                except KeyboardInterrupt:
                    print("\n\nOperation cancelled by user.")
                    return False
                except Exception as e:
                    print(f"Error processing {key}: {e}")
                    return False

            # Generate .env file
            self._write_env_file(config_values)

            # Validate generated file
            validation_result = self._validate_generated_env()

            if not quiet:
                print("\n✅ Successfully generated .env file!")
                print(f"📍 Location: {self.env_path}")
                print(
                    f"🔍 Validation: {'✓ Passed' if validation_result else '⚠ Issues detected'}"
                )

                # Show next steps
                self._show_next_steps()

            return validation_result

        except Exception as e:
            print(f"❌ Error generating .env file: {e}")
            return False

    def _get_config_value(
        self,
        key: str,
        schema: Dict[str, Any],
        existing_value: Optional[str],
        interactive: bool,
        quiet: bool,
    ) -> str:
        """Get configuration value through user input or defaults."""

        # Use existing value if available and not in interactive mode
        if existing_value is not None and not interactive:
            if not quiet:
                print(f"  {key}: Using existing value")
            return existing_value

        # Use default if in quiet mode
        if quiet:
            return schema["default"]

        # Prompt user for value
        if interactive or schema.get("required", False):
            return self._prompt_for_value(key, schema, existing_value)
        else:
            # For optional values, ask if user wants to customize
            if existing_value:
                use_existing = input(
                    f"  {key} (current: {existing_value}): Keep existing? (y/n, default=y): "
                )
                if use_existing.lower() not in ["n", "no"]:
                    return existing_value

            customize = input(f"  {key}: Customize? (y/n, default=n): ")
            if customize.lower() in ["y", "yes"]:
                return self._prompt_for_value(key, schema, existing_value)
            else:
                return schema["default"]

    def _prompt_for_value(
        self, key: str, schema: Dict[str, Any], existing_value: Optional[str]
    ) -> str:
        """Prompt user for a configuration value with validation."""

        prompt = schema.get("prompt", key)
        default = existing_value or schema["default"]
        description = schema.get("description", "")
        choices = schema.get("choices", [])
        sensitive = schema.get("sensitive", False)

        print(f"\n  {key}:")
        if description:
            print(f"    {description}")
        if choices:
            print(f"    Choices: {', '.join(choices)}")
        if default:
            print(f"    Default: {default}")
        print()

        while True:
            try:
                if sensitive:
                    value = getpass.getpass(f"    {prompt}: ") or default
                else:
                    value = input(f"    {prompt}: ") or default

                # Transform value if needed
                if "transform" in schema:
                    value = schema["transform"](value)

                # Validate value
                if "validation" in schema:
                    is_valid, error_msg = schema["validation"](value)
                    if not is_valid:
                        print(f"    ❌ {error_msg}")
                        continue

                return value

            except KeyboardInterrupt:
                raise
            except Exception as e:
                print(f"    ❌ Error: {e}")
                continue

    def _backup_existing_env(self):
        """Create backup of existing .env file."""
        if self.env_path.exists():
            shutil.copy2(self.env_path, self.backup_path)

    def _load_existing_env(self) -> Dict[str, str]:
        """Load existing .env file values."""
        env_values = {}
        try:
            with open(self.env_path, "r") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        key, value = line.split("=", 1)
                        env_values[key.strip()] = value.strip()
        except Exception:
            pass
        return env_values

    def _write_env_file(self, config_values: Dict[str, str]):
        """Write configuration values to .env file."""

        # Read template
        with open(self.template_path, "r") as f:
            template_content = f.read()

        # Replace values in template
        env_content = template_content
        for key, value in config_values.items():
            # Replace the key=value pattern
            pattern = rf"^{re.escape(key)}=.*$"
            replacement = f"{key}={value}"
            env_content = re.sub(pattern, replacement, env_content, flags=re.MULTILINE)

        # Write .env file
        with open(self.env_path, "w") as f:
            f.write(env_content)

        # Set secure permissions
        os.chmod(self.env_path, 0o600)

    def _validate_generated_env(self) -> bool:
        """Validate the generated .env file."""
        try:
            # Add project root to path for imports
            import sys

            sys.path.insert(0, str(self.project_root))

            # Test that the file can be loaded
            from helpers.config import load_config

            config = load_config()

            # Basic validation checks
            issues = []

            # Check required directories exist or can be created
            data_dir = config.get("data_directory", "output")
            if data_dir and not Path(data_dir).exists():
                try:
                    Path(data_dir).mkdir(parents=True, exist_ok=True)
                except Exception as e:
                    issues.append(f"Cannot create data directory '{data_dir}': {e}")

            # Check API key format if provided
            api_key = config.get("OPENROUTER_API_KEY")
            if api_key and not api_key.startswith(("sk-", "test-")):
                issues.append("OpenRouter API key format may be invalid")

            # Check model format
            model = config.get("llm_model")
            if model and "/" not in model:
                issues.append(
                    "Model name should typically contain provider/model format"
                )

            if issues:
                print("\n⚠ Validation issues detected:")
                for issue in issues:
                    print(f"  - {issue}")
                return False

            return True

        except Exception as e:
            print(f"❌ Validation error: {e}")
            return False

    def _show_next_steps(self):
        """Show next steps after .env generation."""
        print("\n📋 Next Steps:")
        print(f"  1. Review your .env file: {self.env_path}")
        print(
            "  2. Test configuration: python -c \"from helpers.config import load_config; print('✓ Config loads successfully')\""
        )
        print("  3. Create output directories: python scripts/setup_directories.py")
        print("  4. Run Atlas: python run.py")
        print("\n💡 Tips:")
        print("  - Keep your .env file secure (it's in .gitignore)")
        print("  - Use 'python scripts/generate_env.py --interactive' to reconfigure")
        print(f"  - Backup is available at: {self.backup_path}")

    # Validation methods
    def _validate_directory_path(self, value: str) -> Tuple[bool, str]:
        """Validate directory path."""
        if not value:
            return True, ""

        try:
            path = Path(value)
            # Check if parent directory exists or can be created
            if not path.parent.exists():
                path.parent.mkdir(parents=True, exist_ok=True)
            return True, ""
        except Exception as e:
            return False, f"Invalid directory path: {e}"

    def _validate_file_path(self, value: str) -> Tuple[bool, str]:
        """Validate file path."""
        if not value:
            return True, ""

        path = Path(value)
        if not path.exists():
            return False, f"File not found: {value}"

        if not os.access(path, os.X_OK):
            return False, f"File not executable: {value}"

        return True, ""

    def _validate_boolean(self, value: str) -> Tuple[bool, str]:
        """Validate boolean value."""
        if value.lower() in ["true", "false", "yes", "no", "y", "n", "1", "0"]:
            return True, ""
        return False, "Must be true/false, yes/no, y/n, or 1/0"

    def _validate_api_key(self, value: str) -> Tuple[bool, str]:
        """Validate API key format."""
        if not value:
            return True, ""  # Optional

        if len(value) < 10:
            return False, "API key seems too short"

        # Basic format validation for common providers
        if not any(value.startswith(prefix) for prefix in ["sk-", "test-", "api_"]):
            return (
                False,
                "API key format may be invalid (should start with sk-, test-, or api_)",
            )

        return True, ""

    def _validate_optional_string(self, value: str) -> Tuple[bool, str]:
        """Validate optional string value."""
        # Any string is valid for optional fields
        return True, ""

    # Transform methods
    def _transform_boolean(self, value: str) -> str:
        """Transform user input to standard boolean string."""
        if value.lower() in ["true", "yes", "y", "1"]:
            return "true"
        else:
            return "false"


def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(
        description="Generate .env file for Atlas from template",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python scripts/generate_env.py                    # Interactive with defaults
    python scripts/generate_env.py --force            # Overwrite existing
    python scripts/generate_env.py --interactive      # Prompt for all values
    python scripts/generate_env.py --quiet            # Silent with defaults
        """,
    )

    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing .env file without prompting",
    )

    parser.add_argument(
        "--interactive",
        action="store_true",
        help="Prompt for all values, including optional ones",
    )

    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Minimal output, use defaults for optional values",
    )

    args = parser.parse_args()

    if args.quiet and args.interactive:
        print("Error: --quiet and --interactive cannot be used together")
        sys.exit(1)

    # Initialize generator
    generator = EnvGenerator()

    # Generate .env file
    success = generator.generate_env_file(
        force=args.force, interactive=args.interactive, quiet=args.quiet
    )

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
