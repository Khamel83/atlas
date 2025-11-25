"""
Main CLI entry point for Atlas v4.

Provides unified command-line interface for all Atlas operations.
"""

import argparse
import sys
import logging
from pathlib import Path
from typing import List, Optional

from ..config import load_config
from ..logging import setup_logging
from ..storage import StorageManager
from .commands import (
    IngestCommand,
    QueryCommand,
    StatusCommand,
    ConfigCommand,
    CleanupCommand,
    APICommand
)


def create_cli_parser() -> argparse.ArgumentParser:
    """
    Create main CLI argument parser.

    Returns:
        Configured ArgumentParser
    """
    parser = argparse.ArgumentParser(
        prog="atlas",
        description="Atlas v4 - Personal Knowledge Automation System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  atlas ingest --source gmail --config ~/.atlas/gmail.yaml
  atlas ingest --source rss --config ~/.atlas/feeds.yaml
  atlas query --type articles --query "python programming"
  atlas status --detailed
  atlas cleanup --old-days 30
  atlas config --validate --file ~/.atlas/config.yaml
  atlas api --host 0.0.0.0 --port 8787
        """
    )

    # Global options
    parser.add_argument(
        "--config",
        type=str,
        help="Path to Atlas configuration file"
    )
    parser.add_argument(
        "--vault",
        type=str,
        help="Path to Atlas vault directory"
    )
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Logging level (default: INFO)"
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress non-error output"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )
    parser.add_argument(
        "--version",
        action="version",
        version="Atlas v4.0.0"
    )

    # Subcommands
    subparsers = parser.add_subparsers(
        title="Commands",
        description="Available commands",
        dest="command",
        help="Command to execute"
    )

    # Ingest command
    ingest_parser = subparsers.add_parser(
        "ingest",
        help="Ingest content from various sources"
    )
    IngestCommand.configure_parser(ingest_parser)

    # Query command
    query_parser = subparsers.add_parser(
        "query",
        help="Query and search stored content"
    )
    QueryCommand.configure_parser(query_parser)

    # Status command
    status_parser = subparsers.add_parser(
        "status",
        help="Show system status and statistics"
    )
    StatusCommand.configure_parser(status_parser)

    # Config command
    config_parser = subparsers.add_parser(
        "config",
        help="Manage configuration"
    )
    ConfigCommand.configure_parser(config_parser)

    # Cleanup command
    cleanup_parser = subparsers.add_parser(
        "cleanup",
        help="Clean up old data and optimize storage"
    )
    CleanupCommand.configure_parser(cleanup_parser)

    # API command
    api_parser = subparsers.add_parser(
        "api",
        help="Start Atlas REST API server"
    )
    APICommand.configure_parser(api_parser)

    return parser


def setup_global_logging(args: argparse.Namespace) -> None:
    """
    Setup global logging based on CLI arguments.

    Args:
        args: Parsed command-line arguments
    """
    log_level = args.log_level
    if args.verbose:
        log_level = "DEBUG"
    elif args.quiet:
        log_level = "ERROR"

    setup_logging(
        level=log_level,
        enable_console=not args.quiet
    )


def load_global_config(args: argparse.Namespace) -> dict:
    """
    Load global configuration.

    Args:
        args: Parsed command-line arguments

    Returns:
        Loaded configuration
    """
    try:
        config = load_config(args.config)

        # Override with CLI arguments
        if args.vault:
            config['vault']['root'] = args.vault

        return config

    except Exception as e:
        print(f"Error loading configuration: {e}", file=sys.stderr)
        sys.exit(1)


def get_vault_root(args: argparse.Namespace, config: dict) -> Path:
    """
    Get vault root directory from args or config.

    Args:
        args: Parsed command-line arguments
        config: Loaded configuration

    Returns:
        Vault root directory
    """
    vault_root = None

    # Try CLI argument first
    if args.vault:
        vault_root = Path(args.vault)
    # Then try config
    elif config and 'vault' in config and 'root' in config['vault']:
        vault_root = Path(config['vault']['root'])
    # Finally try environment variable
    else:
        import os
        env_vault = os.getenv("ATLAS_VAULT")
        if env_vault:
            vault_root = Path(env_vault)

    if not vault_root:
        print("Error: Vault directory not specified. Use --vault or set in config.", file=sys.stderr)
        sys.exit(1)

    return vault_root.resolve()


def create_storage_manager(vault_root: Path) -> StorageManager:
    """
    Create storage manager instance.

    Args:
        vault_root: Vault root directory

    Returns:
        StorageManager instance
    """
    try:
        storage = StorageManager(str(vault_root))

        # Initialize vault structure if needed
        if not storage.initialize_vault():
            print("Warning: Failed to initialize vault structure", file=sys.stderr)

        return storage

    except Exception as e:
        print(f"Error creating storage manager: {e}", file=sys.stderr)
        sys.exit(1)


def main(argv: Optional[List[str]] = None) -> int:
    """
    Main CLI entry point.

    Args:
        argv: Command-line arguments (uses sys.argv if None)

    Returns:
        Exit code
    """
    try:
        # Parse arguments
        parser = create_cli_parser()
        args = parser.parse_args(argv)

        # Setup logging
        setup_global_logging(args)

        # Load configuration
        config = load_global_config(args)

        # Get vault root
        vault_root = get_vault_root(args, config)

        # Create storage manager
        storage = create_storage_manager(vault_root)

        # Initialize command context
        context = {
            'config': config,
            'vault_root': vault_root,
            'storage': storage,
            'args': args
        }

        # Execute command
        if not args.command:
            parser.print_help()
            return 1

        # Get command class and execute
        command_classes = {
            'ingest': IngestCommand,
            'query': QueryCommand,
            'status': StatusCommand,
            'config': ConfigCommand,
            'cleanup': CleanupCommand,
            'api': APICommand
        }

        command_class = command_classes.get(args.command)
        if not command_class:
            print(f"Unknown command: {args.command}", file=sys.stderr)
            return 1

        # Create and execute command
        command = command_class()
        result = command.execute(args, context)

        return result

    except KeyboardInterrupt:
        print("\nOperation cancelled by user", file=sys.stderr)
        return 130
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        if logging.getLogger().level <= logging.DEBUG:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())