"""
Main Telegram bot implementation for Atlas v4.

Provides a complete Telegram bot interface for interacting with Atlas
through conversational commands and inline querying.
"""

import asyncio
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

try:
    from telegram import Update, InlineQuery, InlineQueryResultArticle, InputTextMessageContent
    from telegram.ext import Application, CommandHandler, MessageHandler, filters, InlineQueryHandler
    from telegram.constants import ParseMode
except ImportError:
    raise ImportError("python-telegram-bot is required for Telegram bot functionality")

from ..storage import StorageManager
from ..config import load_config
from ..logging import setup_logging
from .handlers import (
    IngestHandler,
    QueryHandler,
    StatusHandler,
    ConfigHandler,
    HelpHandler
)


@dataclass
class BotConfig:
    """Configuration for Telegram bot."""
    token: str
    allowed_users: List[str]
    allowed_chats: List[str]
    enable_inline: bool = True
    max_inline_results: int = 10
    log_level: str = "INFO"
    vault_root: Optional[str] = None


class AtlasBot:
    """
    Main Atlas Telegram bot.

    Features:
    - Command-based interface for all Atlas operations
    - Inline search functionality
    - User authentication and authorization
    - Rich formatting and keyboard interactions
    - Real-time status updates
    """

    def __init__(self, config: BotConfig):
        """
        Initialize Atlas bot.

        Args:
            config: Bot configuration
        """
        self.config = config
        self.logger = logging.getLogger(f"atlas.bot.{self.__class__.__name__}")

        # Setup logging
        setup_logging(level=config.log_level, enable_console=True)

        # Initialize storage
        if config.vault_root:
            self.storage = StorageManager(config.vault_root)
            self.storage.initialize_vault()
        else:
            # Load vault from config
            self._load_storage_from_config()

        # Initialize command handlers
        self.handlers = {
            'ingest': IngestHandler(self.storage),
            'query': QueryHandler(self.storage),
            'status': StatusHandler(self.storage),
            'config': ConfigHandler(self.storage),
            'help': HelpHandler()
        }

        # Initialize Telegram application
        self.application = None

    def _load_storage_from_config(self):
        """Load storage from configuration file."""
        try:
            # Try to load Atlas config
            config_data = load_config()
            vault_root = config_data.get('vault', {}).get('root', './vault')
            self.storage = StorageManager(vault_root)
            self.storage.initialize_vault()
        except Exception as e:
            self.logger.error(f"Failed to load storage from config: {str(e)}")
            raise

    def create_application(self) -> Application:
        """
        Create and configure Telegram application.

        Returns:
            Configured Application instance
        """
        application = Application.builder().token(self.config.token).build()

        # Add command handlers
        application.add_handler(CommandHandler("start", self._handle_start))
        application.add_handler(CommandHandler("help", self._handle_help))
        application.add_handler(CommandHandler("ingest", self._handle_ingest))
        application.add_handler(CommandHandler("search", self._handle_search))
        application.add_handler(CommandHandler("status", self._handle_status))
        application.add_handler(CommandHandler("config", self._handle_config))
        application.add_handler(CommandHandler("recent", self._handle_recent))

        # Add inline query handler if enabled
        if self.config.enable_inline:
            application.add_handler(InlineQueryHandler(self._handle_inline_query))

        # Add message handler for text commands
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self._handle_message))

        # Add error handler
        application.add_error_handler(self._handle_error)

        self.application = application
        return application

    async def _handle_start(self, update: Update, context):
        """Handle /start command."""
        user = update.effective_user
        welcome_message = (
            f"👋 Hello {user.first_name}!\n\n"
            "🚀 Welcome to Atlas v4 - Personal Knowledge Automation System\n\n"
            "I can help you:\n"
            "• 📥 Ingest content from Gmail, RSS, and YouTube\n"
            "• 🔍 Search and query your knowledge base\n"
            "• 📊 Check system status and statistics\n"
            "• ⚙️ Manage configuration\n\n"
            "Type /help to see all available commands,\n"
            "or start typing to search your content!"
        )

        keyboard = [
            ["/ingest - Add content", "/search - Find content"],
            ["/status - System status", "/recent - Recent items"],
            ["/help - All commands"]
        ]

        await update.message.reply_text(
            welcome_message,
            reply_markup={
                'keyboard': keyboard,
                'resize_keyboard': True,
                'one_time_keyboard': False
            }
        )

    async def _handle_help(self, update: Update, context):
        """Handle /help command."""
        help_text = (
            "🔧 *Atlas v4 Commands*\n\n"
            "*Content Ingestion*\n"
            "• `/ingest gmail` - Ingest Gmail messages\n"
            "• `/ingest rss` - Ingest RSS feeds\n"
            "• `/ingest youtube` - Ingest YouTube videos\n\n"
            "*Content Search*\n"
            "• `/search <query>` - Search content\n"
            "• `/recent [type]` - Show recent items\n"
            "• Inline: Type in any chat to search\n\n"
            "*System Management*\n"
            "• `/status` - Show system status\n"
            "• `/config` - Manage configuration\n"
            "• `/help` - Show this help\n\n"
            "*Examples*\n"
            "• `/search python programming`\n"
            "• `/recent articles`\n"
            "• `/ingest gmail --config gmail.yaml`\n"
            "• Inline: `@atlas_bot machine learning`\n"
        )

        await update.message.reply_text(
            help_text,
            parse_mode=ParseMode.MARKDOWN
        )

    async def _handle_ingest(self, update: Update, context):
        """Handle /ingest command."""
        if not self._is_authorized(update):
            await self._send_unauthorized_message(update)
            return

        await self.handlers['ingest'].handle_ingest(update, context)

    async def _handle_search(self, update: Update, context):
        """Handle /search command."""
        if not self._is_authorized(update):
            await self._send_unauthorized_message(update)
            return

        await self.handlers['query'].handle_search(update, context)

    async def _handle_status(self, update: Update, context):
        """Handle /status command."""
        if not self._is_authorized(update):
            await self._send_unauthorized_message(update)
            return

        await self.handlers['status'].handle_status(update, context)

    async def _handle_config(self, update: Update, context):
        """Handle /config command."""
        if not self._is_authorized(update):
            await self._send_unauthorized_message(update)
            return

        await self.handlers['config'].handle_config(update, context)

    async def _handle_recent(self, update: Update, context):
        """Handle /recent command."""
        if not self._is_authorized(update):
            await self._send_unauthorized_message(update)
            return

        await self.handlers['query'].handle_recent(update, context)

    async def _handle_message(self, update: Update, context):
        """Handle text messages (inline search)."""
        if not self._is_authorized(update):
            return

        query = update.message.text.strip()
        if len(query) < 2:  # Ignore very short messages
            return

        await self.handlers['query'].handle_inline_search(update, context, query)

    async def _handle_inline_query(self, update: Update, context):
        """Handle inline queries."""
        if not self._is_authorized(update):
            return

        query = update.inline_query.query.strip()
        if len(query) < 2:
            return

        await self.handlers['query'].handle_inline_query(update, context, query)

    async def _handle_error(self, update: Update, context, error):
        """Handle errors in the bot."""
        self.logger.error(f"Bot error: {str(error)}", exc_info=True)

        try:
            if update.message:
                await update.message.reply_text(
                    "❌ Sorry, an error occurred. Please try again later."
                )
        except Exception:
            pass  # Can't reply if the error happened during sending

    def _is_authorized(self, update: Update) -> bool:
        """Check if user is authorized to use the bot."""
        if not update.effective_user:
            return False

        user_id = str(update.effective_user.id)
        chat_id = str(update.effective_chat.id) if update.effective_chat else None

        # Check if user is allowed
        if user_id in self.config.allowed_users:
            return True

        # Check if chat is allowed
        if chat_id and chat_id in self.config.allowed_chats:
            return True

        # If no restrictions, allow all users (development mode)
        if not self.config.allowed_users and not self.config.allowed_chats:
            return True

        return False

    async def _send_unauthorized_message(self, update: Update):
        """Send unauthorized message."""
        message = "🚫 You are not authorized to use this bot."

        if update.message:
            await update.message.reply_text(message)
        elif update.inline_query:
            # For inline queries, we can't reply directly
            pass

    async def send_message_to_user(self, user_id: str, message: str, parse_mode: str = None):
        """
        Send message to specific user.

        Args:
            user_id: Telegram user ID
            message: Message to send
            parse_mode: Parse mode (HTML or Markdown)
        """
        try:
            await self.application.bot.send_message(
                chat_id=user_id,
                text=message,
                parse_mode=parse_mode
            )
        except Exception as e:
            self.logger.error(f"Failed to send message to user {user_id}: {str(e)}")

    async def send_admin_notification(self, message: str, include_keyboard: bool = False):
        """
        Send notification to all allowed users.

        Args:
            message: Message to send
            include_keyboard: Whether to include inline keyboard
        """
        for user_id in self.config.allowed_users:
            try:
                await self.send_message_to_user(user_id, message)
            except Exception as e:
                self.logger.error(f"Failed to send notification to {user_id}: {str(e)}")

    def run_polling(self):
        """Run the bot in polling mode."""
        self.logger.info("Starting Atlas bot in polling mode")

        # Create application if not already created
        if not self.application:
            self.create_application()

        # Start polling
        self.application.run_polling(
            allowed_updates=Update.ALL_TYPES,
            drop_pending_updates=True
        )

    def run_webhook(self, webhook_url: str, port: int = 8443, cert_path: str = None):
        """
        Run the bot in webhook mode.

        Args:
            webhook_url: Webhook URL
            port: Port to listen on
            cert_path: SSL certificate path (for HTTPS)
        """
        self.logger.info(f"Starting Atlas bot in webhook mode on port {port}")

        # Create application if not already created
        if not self.application:
            self.create_application()

        # Configure webhook
        self.application.bot.set_webhook(
            url=webhook_url,
            allowed_updates=Update.ALL_TYPES,
            drop_pending_updates=True
        )

        # Start webhook server
        import ssl

        ssl_context = None
        if cert_path:
            ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
            ssl_context.load_cert_chain(cert_path)

        self.application.run_webhook(
            listen="0.0.0.0",
            port=port,
            ssl_context=ssl_context
        )

    def get_bot_info(self) -> Dict[str, Any]:
        """
        Get bot information and status.

        Returns:
            Bot information dictionary
        """
        return {
            "status": "running",
            "users_allowed": len(self.config.allowed_users),
            "chats_allowed": len(self.config.allowed_chats),
            "inline_enabled": self.config.enable_inline,
            "max_inline_results": self.config.max_inline_results,
            "handlers": list(self.handlers.keys())
        }


# Convenience function to create and run bot
def create_bot(config_path: Optional[str] = None) -> AtlasBot:
    """
    Create Atlas bot from configuration.

    Args:
        config_path: Path to bot configuration file

    Returns:
        AtlasBot instance
    """
    # Load configuration
    if config_path:
        with open(config_path, 'r') as f:
            import yaml
            config_data = yaml.safe_load(f)
    else:
        # Try environment variables
        import os
        token = os.getenv("ATLAS_BOT_TOKEN")
        if not token:
            raise ValueError("Bot token not provided. Set ATLAS_BOT_TOKEN environment variable or provide config file.")

        allowed_users = os.getenv("ATLAS_BOT_ALLOWED_USERS", "").split(",") if os.getenv("ATLAS_BOT_ALLOWED_USERS") else []
        allowed_chats = os.getenv("ATLAS_BOT_ALLOWED_CHATS", "").split(",") if os.getenv("ATLAS_BOT_ALLOWED_CHATS") else []

        config_data = {
            "token": token,
            "allowed_users": [u for u in allowed_users if u.strip()],
            "allowed_chats": [c for c in allowed_chats if c.strip()],
            "enable_inline": True,
            "max_inline_results": 10,
            "log_level": "INFO"
        }

    # Create bot config
    bot_config = BotConfig(**config_data)

    # Create bot
    return AtlasBot(bot_config)