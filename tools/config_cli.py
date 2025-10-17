#!/usr/bin/env python3
"""
Atlas Configuration CLI Tool

Command-line interface for managing Atlas configuration and secrets.
Provides commands for viewing, editing, validating, and managing configuration.
"""

import argparse
import sys
import json
import yaml
import os
from pathlib import Path
from typing import Dict, Any, List, Optional

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from helpers.configuration_manager import ConfigurationManager, Environment
from helpers.secret_manager import SecretManager


class ConfigCLI:
    """Command-line interface for configuration management."""

    def __init__(self):
        self.config_manager = None
        self.secret_manager = None

    def init_managers(self, environment: str, config_dir: str = "config", secrets_dir: str = "config"):
        """Initialize configuration and secret managers."""
        env = Environment(environment.lower())
        self.config_manager = ConfigurationManager(
            environment=env,
            config_dir=config_dir,
            secrets_dir=secrets_dir
        )
        self.secret_manager = SecretManager(
            secrets_dir=secrets_dir,
            environment=environment
        )

    def cmd_show(self, args):
        """Show configuration value."""
        value = self.config_manager.get(args.key, args.default, args.required)
        if value is not None:
            if args.format == 'json':
                print(json.dumps(value, indent=2))
            else:
                print(value)

    def cmd_set(self, args):
        """Set configuration value."""
        # Parse value based on type
        if args.type == 'int':
            value = int(args.value)
        elif args.type == 'float':
            value = float(args.value)
        elif args.type == 'bool':
            value = args.value.lower() in ['true', 'yes', '1', 'on']
        elif args.type == 'json':
            value = json.loads(args.value)
        else:
            value = args.value

        self.config_manager.set(args.key, value)
        print(f"Configuration '{args.key}' set to '{value}'")

    def cmd_list(self, args):
        """List configuration values."""
        config = self.config_manager.get_all()

        if args.pattern:
            # Filter by pattern
            import re
            pattern = re.compile(args.pattern, re.IGNORECASE)
            config = {k: v for k, v in config.items() if pattern.search(k)}

        if args.format == 'json':
            print(json.dumps(config, indent=2))
        elif args.format == 'yaml':
            print(yaml.dump(config, default_flow_style=False))
        else:
            # Format as key=value pairs
            for key, value in sorted(config.items()):
                print(f"{key}={value}")

    def cmd_validate(self, args):
        """Validate configuration."""
        errors = self.config_manager.validate_configuration()

        if errors:
            print("Configuration validation failed:")
            for error in errors:
                print(f"  ❌ {error}")
            if args.fix:
                print("\nAttempting to fix common issues...")
                self._fix_common_issues()
                errors = self.config_manager.validate_configuration()
                if errors:
                    print("Remaining issues:")
                    for error in errors:
                        print(f"  ❌ {error}")
                else:
                    print("✅ All issues fixed!")
            sys.exit(1)
        else:
            print("✅ Configuration is valid")

    def _fix_common_issues(self):
        """Fix common configuration issues."""
        # Set required defaults
        required_configs = {
            'ATLAS_DATABASE_PATH': 'data/atlas.db',
            'ATLAS_LOG_LEVEL': 'INFO',
            'API_HOST': 'localhost',
            'API_PORT': 7444
        }

        for key, default in required_configs.items():
            try:
                self.config_manager.get(key, required=True)
            except ValueError:
                self.config_manager.set(key, default)

    def cmd_env(self, args):
        """Show or set environment."""
        if args.set_env:
            # Switch to different environment
            self.init_managers(args.set_env)
            print(f"Switched to {args.set_env} environment")
        else:
            # Show current environment
            print(f"Current environment: {self.config_manager.environment.value}")

    def cmd_export(self, args):
        """Export configuration."""
        output = self.config_manager.export_config(
            output_file=args.output,
            format=args.format,
            include_sensitive=args.include_sensitive
        )
        print(f"Configuration exported to {args.output}")

    def cmd_reload(self, args):
        """Reload configuration from files."""
        self.config_manager.reload_configuration()
        print("Configuration reloaded successfully")

    def cmd_schema(self, args):
        """Show configuration schema."""
        if args.key:
            # Show schema for specific key
            schema = self.config_manager.get_schema(args.key)
            if schema:
                print(json.dumps(schema, indent=2))
            else:
                print(f"No schema found for '{args.key}'")
        else:
            # Show all schemas
            schemas = self.config_manager.get_all_schemas()
            if args.format == 'json':
                print(json.dumps(schemas, indent=2))
            elif args.format == 'yaml':
                print(yaml.dump(schemas, default_flow_style=False))
            else:
                # Show as formatted text
                for key, schema in sorted(schemas.items()):
                    print(f"{key}:")
                    for field, value in schema.items():
                        print(f"  {field}: {value}")
                    print()

    def cmd_secret(self, args):
        """Secret management commands."""
        if args.secret_command == 'get':
            value = self.secret_manager.get_secret(args.key, args.default, args.required)
            if value is not None:
                print(value)

        elif args.secret_command == 'set':
            self.secret_manager.set_secret(args.key, args.value, not args.no_encrypt)
            print(f"Secret '{args.key}' set successfully")

        elif args.secret_command == 'list':
            for key in self.secret_manager.list_secrets():
                print(key)

        elif args.secret_command == 'encrypt':
            encrypted = self.secret_manager.encrypt_value(args.value)
            print(encrypted)

        elif args.secret_command == 'decrypt':
            decrypted = self.secret_manager.decrypt_value(args.value)
            print(decrypted)

        elif args.secret_command == 'save':
            self.secret_manager.save_secrets(args.output)
            print("Secrets saved successfully")

        elif args.secret_command == 'audit':
            audit = self.secret_manager.audit_secrets()
            print(json.dumps(audit, indent=2))

        elif args.secret_command == 'export':
            exported = self.secret_manager.export_secrets(args.format)
            print(exported)

    def cmd_diff(self, args):
        """Compare configuration between environments."""
        # Load both environments
        env1_manager = ConfigurationManager(
            environment=Environment(args.env1),
            config_dir=args.config_dir,
            secrets_dir=args.secrets_dir
        )
        env2_manager = ConfigurationManager(
            environment=Environment(args.env2),
            config_dir=args.config_dir,
            secrets_dir=args.secrets_dir
        )

        config1 = env1_manager.get_all()
        config2 = env2_manager.get_all()

        # Find differences
        all_keys = set(config1.keys()) | set(config2.keys())
        differences = {}

        for key in sorted(all_keys):
            val1 = config1.get(key)
            val2 = config2.get(key)

            if val1 != val2:
                differences[key] = {
                    args.env1: val1,
                    args.env2: val2
                }

        if differences:
            print(f"Differences between {args.env1} and {args.env2}:")
            if args.format == 'json':
                print(json.dumps(differences, indent=2))
            else:
                for key, diff in differences.items():
                    print(f"{key}:")
                    print(f"  {args.env1}: {diff[args.env1]}")
                    print(f"  {args.env2}: {diff[args.env2]}")
                    print()
        else:
            print("No differences found")

    def cmd_backup(self, args):
        """Backup configuration."""
        backup_file = args.output or f"config_backup_{self.config_manager.environment.value}.json"
        self.config_manager.backup_configuration(backup_file)
        print(f"Configuration backed up to {backup_file}")

    def cmd_restore(self, args):
        """Restore configuration from backup."""
        self.config_manager.restore_configuration(args.backup_file)
        print(f"Configuration restored from {args.backup_file}")


def create_parser():
    """Create argument parser."""
    parser = argparse.ArgumentParser(
        description='Atlas Configuration Management CLI',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Get configuration value
  atlas-config get API_PORT

  # Set configuration value
  atlas-config set API_PORT 8080

  # List all configuration
  atlas-config list

  # Validate configuration
  atlas-config validate

  # Show current environment
  atlas-config env

  # Get secret
  atlas-config secret get OPENROUTER_API_KEY

  # Set secret
  atlas-config secret set OPENROUTER_API_KEY your_api_key

  # Compare environments
  atlas-config diff development production
        """
    )

    parser.add_argument('--env', default='development', help='Environment (development, staging, production)')
    parser.add_argument('--config-dir', default='config', help='Configuration directory')
    parser.add_argument('--secrets-dir', default='config', help='Secrets directory')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')

    subparsers = parser.add_subparsers(dest='command', help='Command')

    # Show configuration
    show_parser = subparsers.add_parser('show', help='Show configuration value')
    show_parser.add_argument('key', help='Configuration key')
    show_parser.add_argument('--default', help='Default value')
    show_parser.add_argument('--required', action='store_true', help='Required configuration')
    show_parser.add_argument('--format', choices=['text', 'json'], default='text', help='Output format')

    # Set configuration
    set_parser = subparsers.add_parser('set', help='Set configuration value')
    set_parser.add_argument('key', help='Configuration key')
    set_parser.add_argument('value', help='Configuration value')
    set_parser.add_argument('--type', choices=['str', 'int', 'float', 'bool', 'json'], default='str', help='Value type')

    # List configuration
    list_parser = subparsers.add_parser('list', help='List configuration values')
    list_parser.add_argument('--pattern', help='Filter by pattern')
    list_parser.add_argument('--format', choices=['text', 'json', 'yaml'], default='text', help='Output format')

    # Validate configuration
    validate_parser = subparsers.add_parser('validate', help='Validate configuration')
    validate_parser.add_argument('--fix', action='store_true', help='Attempt to fix common issues')

    # Environment
    env_parser = subparsers.add_parser('env', help='Show or set environment')
    env_parser.add_argument('--set-env', help='Set environment')

    # Export configuration
    export_parser = subparsers.add_parser('export', help='Export configuration')
    export_parser.add_argument('--output', help='Output file')
    export_parser.add_argument('--format', choices=['env', 'json', 'yaml'], default='env', help='Export format')
    export_parser.add_argument('--include-sensitive', action='store_true', help='Include sensitive values')

    # Reload configuration
    subparsers.add_parser('reload', help='Reload configuration from files')

    # Schema
    schema_parser = subparsers.add_parser('schema', help='Show configuration schema')
    schema_parser.add_argument('key', nargs='?', help='Configuration key')
    schema_parser.add_argument('--format', choices=['text', 'json', 'yaml'], default='text', help='Output format')

    # Secret management
    secret_parser = subparsers.add_parser('secret', help='Secret management')
    secret_subparsers = secret_parser.add_subparsers(dest='secret_command', help='Secret command')

    # Secret get
    secret_get = secret_subparsers.add_parser('get', help='Get secret')
    secret_get.add_argument('key', help='Secret key')
    secret_get.add_argument('--default', help='Default value')
    secret_get.add_argument('--required', action='store_true', help='Required secret')

    # Secret set
    secret_set = secret_subparsers.add_parser('set', help='Set secret')
    secret_set.add_argument('key', help='Secret key')
    secret_set.add_argument('value', help='Secret value')
    secret_set.add_argument('--no-encrypt', action='store_true', help='Don\'t encrypt')

    # Secret list
    secret_subparsers.add_parser('list', help='List secrets')

    # Secret encrypt
    secret_encrypt = secret_subparsers.add_parser('encrypt', help='Encrypt value')
    secret_encrypt.add_argument('value', help='Value to encrypt')

    # Secret decrypt
    secret_decrypt = secret_subparsers.add_parser('decrypt', help='Decrypt value')
    secret_decrypt.add_argument('value', help='Value to decrypt')

    # Secret save
    secret_save = secret_subparsers.add_parser('save', help='Save secrets')
    secret_save.add_argument('--output', help='Output file')

    # Secret audit
    secret_subparsers.add_parser('audit', help='Audit secrets')

    # Secret export
    secret_export = secret_subparsers.add_parser('export', help='Export secrets')
    secret_export.add_argument('--format', choices=['env', 'json', 'yaml'], default='env', help='Export format')

    # Diff environments
    diff_parser = subparsers.add_parser('diff', help='Compare environments')
    diff_parser.add_argument('env1', help='First environment')
    diff_parser.add_argument('env2', help='Second environment')
    diff_parser.add_argument('--format', choices=['text', 'json'], default='text', help='Output format')

    # Backup
    backup_parser = subparsers.add_parser('backup', help='Backup configuration')
    backup_parser.add_argument('--output', help='Output file')

    # Restore
    restore_parser = subparsers.add_parser('restore', help='Restore configuration')
    restore_parser.add_argument('backup_file', help='Backup file to restore from')

    return parser


def main():
    """Main CLI entry point."""
    parser = create_parser()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    # Initialize CLI
    cli = ConfigCLI()
    cli.init_managers(args.env, args.config_dir, args.secrets_dir)

    # Execute command
    try:
        if args.command == 'show':
            cli.cmd_show(args)
        elif args.command == 'set':
            cli.cmd_set(args)
        elif args.command == 'list':
            cli.cmd_list(args)
        elif args.command == 'validate':
            cli.cmd_validate(args)
        elif args.command == 'env':
            cli.cmd_env(args)
        elif args.command == 'export':
            cli.cmd_export(args)
        elif args.command == 'reload':
            cli.cmd_reload(args)
        elif args.command == 'schema':
            cli.cmd_schema(args)
        elif args.command == 'secret':
            cli.cmd_secret(args)
        elif args.command == 'diff':
            cli.cmd_diff(args)
        elif args.command == 'backup':
            cli.cmd_backup(args)
        elif args.command == 'restore':
            cli.cmd_restore(args)
        else:
            parser.print_help()
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()