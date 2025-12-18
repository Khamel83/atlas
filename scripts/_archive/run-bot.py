#!/usr/bin/env python3
"""
Atlas v4 Telegram Bot Runner

This script starts and manages Atlas Telegram bots with various
configuration options and deployment modes.
"""

import argparse
import asyncio
import signal
import sys
import os
from pathlib import Path

# Add src to Python path
script_dir = Path(__file__).parent
src_dir = script_dir.parent / "src"
sys.path.insert(0, str(src_dir))

from atlas.bot.deployment import BotManager, BotDeploymentConfig


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Atlas v4 Telegram Bot Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run-bot.py --token YOUR_TOKEN --polling
  python run-bot.py --config config.yaml --webhook
  python run-bot.py --create-template production
        """
    )

    # Basic configuration
    parser.add_argument(
        "--token",
        help="Telegram bot token (overrides config file)"
    )
    parser.add_argument(
        "--vault",
        help="Atlas vault directory"
    )
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Logging level (default: INFO)"
    )
    parser.add_argument(
        "--log-file",
        help="Log file path"
    )

    # Deployment mode
    parser.add_argument(
        "--polling",
        action="store_true",
        help="Run in polling mode (default)"
    )
    parser.add_argument(
        "--webhook",
        action="store_true",
        help="Run in webhook mode"
    )
    parser.add_argument(
        "--webhook-url",
        help="Webhook URL (for webhook mode)"
    )
    parser.add_argument(
        "--webhook-port",
        type=int,
        default=8443,
        help="Webhook port (default: 8443)"
    )

    # Authorization
    parser.add_argument(
        "--allowed-users",
        help="Comma-separated list of allowed Telegram user IDs"
    )
    parser.add_argument(
        "--allowed-chats",
        help="Comma-separated list of allowed Telegram chat IDs"
    )

    # Configuration
    parser.add_argument(
        "--config",
        help="Path to deployment configuration file"
    )
    parser.add_argument(
        "--create-template",
        help="Create deployment configuration template"
    )

    # Bot management
    parser.add_argument(
        "--list-configs",
        action="store_true",
        help="List available deployment configurations"
    )
    parser.add_argument(
        "--health-check",
        action="store_true",
        help="Perform health check on all deployments"
    )
    parser.add_argument(
        "--daemon",
        action="store_true",
        help="Run in daemon mode"
    )

    return parser.parse_args()


def load_or_create_config(args):
    """Load configuration from file or create from arguments."""
    if args.config:
        # Load from file
        if not Path(args.config).exists():
            print(f"Error: Configuration file not found: {args.config}")
            sys.exit(1)

        try:
            from atlas.bot.deployment import BotManager
            manager = BotManager(Path(args.config).parent)
            return manager.load_deployment(Path(args.config).stem)
        except Exception as e:
            print(f"Error loading configuration: {e}")
            sys.exit(1)

    # Create config from arguments
    config_dict = {
        "name": "default",
        "token": args.token or os.getenv("ATLAS_BOT_TOKEN"),
        "webhooks": args.webhook,
        "webhook_url": args.webhook_url,
        "webhook_port": args.webhook_port,
        "allowed_users": args.allowed_users.split(",") if args.allowed_users else [],
        "allowed_chats": args.allowed_chats.split(",") if args.allowed_chats else [],
        "log_level": args.log_level,
        "log_file": args.log_file,
        "vault_root": args.vault or os.getenv("ATLAS_VAULT"),
        "max_inline_results": 10,
        "rate_limit": 30,
        "admin_chat_id": os.getenv("ATLAS_BOT_ADMIN_CHAT")
    }

    # Validate required fields
    if not config_dict["token"]:
        print("Error: Bot token is required. Use --token or ATLAS_BOT_TOKEN environment variable.")
        sys.exit(1)

    return BotDeploymentConfig(**config_dict)


def create_template(config_name: str):
    """Create deployment configuration template."""
    template_path = f"config/bot/{config_name}.yaml"
    template_dir = Path(template_path).parent
    template_dir.mkdir(parents=True, exist_ok=True)

    try:
        from atlas.bot.deployment import BotManager
        manager = BotManager("config/bot")
        created_path = manager.create_deployment_template(config_name)

        print(f"✅ Created deployment template: {created_path}")
        print("\nEdit the template file and update:")
        print("  - bot token")
        print("  - allowed users/chats")
        print("  - vault directory")
        print(f"  - Then run: python run-bot.py --config {template_path}")

    except Exception as e:
        print(f"Error creating template: {e}")
        sys.exit(1)


def list_deployments():
    """List available deployment configurations."""
    try:
        from atlas.bot.deployment import BotManager
        manager = BotManager("config/bot")
        deployments = manager.list_deployments()

        if not deployments:
            print("No deployment configurations found.")
            print("Create one with: python run-bot.py --create-template <name>")
            return

        print("Available deployment configurations:")
        for name in deployments:
            print(f"  - {name}")

    except Exception as e:
        print(f"Error listing deployments: {e}")
        sys.exit(1)


def health_check():
    """Perform health check on all deployments."""
    try:
        from atlas.bot.deployment import BotManager
        manager = BotManager("config/bot")
        results = manager.health_check_all()

        if not results:
            print("No deployments found to check.")
            return

        print("Health Check Results:")
        for name, health in results.items():
            status = health.get("status", "unknown")
            message = health.get("message", "No message")
            print(f"  {name}: {status.upper()} - {message}")

    except Exception as e:
        print(f"Error performing health check: {e}")
        sys.exit(1)


def run_bot_deployment(deployment_config, mode: str = "polling"):
    """Run the bot deployment."""
    try:
        from atlas.bot.deployment import BotDeployment
        deployment = BotDeployment(deployment_config)

        print(f"🚀 Starting Atlas bot...")
        print(f"Mode: {mode}")
        print(f"Vault: {deployment_config.vault_root or 'Default'}")
        print(f"Users allowed: {len(deployment_config.allowed_users or [])}")
        print(f"Inline queries: {'Enabled' if deployment_config.max_inline_results > 0 else 'Disabled'}")
        print()

        # Start the bot
        if mode == "webhook":
            deployment.start_webhook()
        else:
            deployment.start_polling()

    except KeyboardInterrupt:
        print("\n👋 Bot stopped by user")
    except Exception as e:
        print(f"❌ Bot failed to start: {e}")
        if "token" in str(e).lower():
            print("💡 Make sure your bot token is correct and has bot:api permissions")
        sys.exit(1)


def main():
    """Main entry point."""
    args = parse_arguments()

    # Handle special commands
    if args.create_template:
        create_template(args.create_template)
        return

    if args.list_configs:
        list_deployments()
        return

    if args.health_check:
        health_check()
        return

    # Load configuration
    try:
        deployment_config = load_or_create_config(args)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

    # Determine deployment mode
    if args.webhook:
        mode = "webhook"
    else:
        mode = "polling"

    # Run bot
    if args.daemon:
        # TODO: Implement daemon mode
        print("Daemon mode not yet implemented")
        sys.exit(1)

    run_bot_deployment(deployment_config, mode)


if __name__ == "__main__":
    main()