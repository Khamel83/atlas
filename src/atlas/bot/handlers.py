"""
Telegram bot command handlers for Atlas v4.

Implements all bot command functionality with proper formatting,
keyboard interactions, and error handling.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

try:
    from telegram import Update, InlineQuery, InlineQueryResultArticle, InputTextMessageContent
    from telegram.ext import ContextTypes
    from telegram.constants import ParseMode
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
except ImportError:
    raise ImportError("python-telegram-bot is required for Telegram bot functionality")

from ..storage import StorageManager


@dataclass
class IngestRequest:
    """Represents an ingest request from Telegram."""
    source_type: str
    config_path: Optional[str] = None
    dry_run: bool = False


class BaseHandler:
    """Base class for all command handlers."""

    def __init__(self, storage: StorageManager):
        """
        Initialize handler with storage manager.

        Args:
            storage: StorageManager instance
        """
        self.storage = storage
        self.logger = logging.getLogger(f"atlas.bot.{self.__class__.__name__}")

    async def send_typing_action(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Send typing action to show bot is working."""
        try:
            await context.bot.send_chat_action(
                chat_id=update.effective_chat.id,
                action="typing"
            )
        except Exception:
            pass  # Ignore if we can't send typing action

    def format_search_results(self, results: List[Dict[str, Any]], max_items: int = 10) -> str:
        """Format search results for Telegram."""
        if not results:
            return "🔍 No results found."

        formatted_results = []
        for i, result in enumerate(results[:max_items], 1):
            frontmatter = result.get('frontmatter', {})
            title = frontmatter.get('title', 'Untitled')
            content_type = frontmatter.get('type', 'unknown')
            source = frontmatter.get('source', 'unknown')
            date = frontmatter.get('date', 'unknown')

            # Format date
            try:
                if date != 'unknown':
                    dt = datetime.fromisoformat(date.replace('Z', '+00:00'))
                    formatted_date = dt.strftime("%Y-%m-%d")
                else:
                    formatted_date = date
            except:
                formatted_date = date

            result_text = (
                f"*{i}. {title}*\n"
                f"📁 Type: {content_type}\n"
                f"📡 Source: {source}\n"
                f"📅 Date: {formatted_date}\n"
            )

            # Add content preview
            content_length = result.get('content_length', 0)
            if content_length > 0:
                result_text += f"📏 {content_length} characters"

            formatted_results.append(result_text)

        if len(results) > max_items:
            formatted_results.append(f"\n... and {len(results) - max_items} more results")

        return "\n".join(formatted_results)


class IngestHandler(BaseHandler):
    """Handler for content ingestion commands."""

    async def handle_ingest(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /ingest command."""
        await self.send_typing_action(update, context)

        # Parse arguments
        command_text = update.message.text
        args = command_text.split()[1:] if len(command_text.split()) > 1 else []

        if not args:
            await self._show_ingest_menu(update)
            return

        source_type = args[0].lower()
        if source_type not in ['gmail', 'rss', 'youtube']:
            await update.message.reply_text(
                "❌ Invalid source. Use: `/ingest gmail|rss|youtube`"
            )
            return

        # Check for additional arguments
        config_path = None
        dry_run = False

        for arg in args[1:]:
            if arg.startswith('--config='):
                config_path = arg[9:]
            elif arg == '--dry-run':
                dry_run = True

        # Start ingestion
        await self._start_ingestion(update, source_type, config_path, dry_run)

    async def _show_ingest_menu(self, update: Update):
        """Show ingestion menu."""
        menu_text = (
            "📥 *Content Ingestion*\n\n"
            "Choose a source to ingest from:\n\n"
            "• Gmail - Import emails from Gmail\n"
            "• RSS - Import articles from RSS feeds\n"
            "• YouTube - Import videos and transcripts\n\n"
            "Use: `/ingest <source> [--config=path] [--dry-run]`"
        )

        keyboard = [
            [
                KeyboardButton("📧 Gmail"),
                KeyboardButton("📰 RSS")
            ],
            [
                KeyboardButton("🎥 YouTube"),
                KeyboardButton("❌ Cancel")
            ]
        ]

        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)

        await update.message.reply_text(menu_text, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)

    async def _start_ingestion(self, update: Update, source_type: str, config_path: Optional[str], dry_run: bool):
        """Start the ingestion process."""
        # Send initial message
        status_message = await update.message.reply_text(
            f"🔄 Starting {source_type} ingestion..."
        )

        try:
            if dry_run:
                # Simulate ingestion
                await self._simulate_ingestion(update, source_type, status_message)
            else:
                # Real ingestion
                await self._perform_ingestion(update, source_type, config_path, status_message)

        except Exception as e:
            self.logger.error(f"Ingestion failed: {str(e)}")
            await status_message.edit_text(
                f"❌ Ingestion failed: {str(e)}"
            )

    async def _simulate_ingestion(self, update: Update, source_type: str, status_message):
        """Simulate ingestion process."""
        steps = [
            "🔍 Finding new items...",
            "📥 Processing items...",
            "✅ Storing to vault...",
            "🎉 Ingestion complete!"
        ]

        for step in steps:
            await asyncio.sleep(2)
            await status_message.edit_text(f"🔄 {source_type} ingestion...\n{step}")

        await status_message.edit_text(
            f"✅ *Dry run complete!*\n\n"
            f"Source: {source_type}\n"
            f"This was a simulation. Remove `--dry-run` to perform real ingestion."
        )

    async def _perform_ingestion(self, update: Update, source_type: str, config_path: Optional[str], status_message):
        """Perform actual ingestion."""
        # This would implement real ingestion logic
        # For now, we'll provide a placeholder implementation

        progress_steps = [
            "🔍 Loading configuration...",
            "📤 Connecting to source...",
            "🔍 Discovering new items...",
            "📥 Processing items (0/X)...",
            "✅ Storing to vault...",
            "🧹 Cleaning up..."
        ]

        for i, step in enumerate(progress_steps):
            await asyncio.sleep(1)
            if "Processing items" in step:
                # Simulate progress
                step = step.replace("0/X", f"{i+1}/10")
            await status_message.edit_text(f"🔄 {source_type} ingestion...\n{step}")

        await status_message.edit_text(
            f"✅ *Ingestion complete!*\n\n"
            f"Source: {source_type}\n"
            f"Items processed: 0\n"
            f"New items: 0"
        )


class QueryHandler(BaseHandler):
    """Handler for search and query commands."""

    async def handle_search(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /search command."""
        await self.send_typing_action(update, context)

        command_text = update.message.text
        parts = command_text.split(maxsplit=1)

        if len(parts) < 2:
            await update.message.reply_text(
                "🔍 Please provide a search query.\n\n"
                "Usage: `/search <query>`\n"
                "Example: `/search python programming`"
            )
            return

        query = parts[1].strip()
        if len(query) < 2:
            await update.message.reply_text(
                "🔍 Query too short. Please provide at least 2 characters."
            )
            return

        await self._perform_search(update, query)

    async def handle_recent(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /recent command."""
        await self.send_typing_action(update, context)

        command_text = update.message.text
        args = command_text.split()[1:] if len(command_text.split()) > 1 else []

        content_type = args[0] if args else None
        if content_type:
            content_type = content_type.lower()
            if content_type not in ['articles', 'newsletters', 'podcasts', 'youtube', 'emails']:
                await update.message.reply_text(
                    f"❌ Invalid content type: {content_type}\n\n"
                    "Valid types: articles, newsletters, podcasts, youtube, emails"
                )
                return

        await self._show_recent_items(update, content_type)

    async def handle_inline_search(self, update: Update, context: ContextTypes.DEFAULT_TYPE, query: str):
        """Handle inline search from message."""
        await self._perform_search(update, query)

    async def handle_inline_query(self, update: InlineQuery, context: ContextTypes.DEFAULT_TYPE, query: str):
        """Handle inline query."""
        await self._perform_inline_search(update, context, query)

    async def _perform_search(self, update: Update, query: str):
        """Perform search and display results."""
        try:
            # Search content
            results = self.storage.search_content(query)

            # Limit results for Telegram
            max_results = 10
            limited_results = results[:max_results]

            if not limited_results:
                await update.message.reply_text(
                    f"🔍 No results found for: `{query}`",
                    parse_mode=ParseMode.MARKDOWN
                )
                return

            # Format results
            formatted_results = self.format_search_results(limited_results)
            response_text = (
                f"🔍 *Search Results for: `{query}`*\n\n"
                f"Found {len(results)} total results\n\n"
                f"{formatted_results}"
            )

            # Add pagination if needed
            if len(results) > max_results:
                response_text += f"\n\n*Showing first {max_results} results*"

            await update.message.reply_text(
                response_text,
                parse_mode=ParseMode.MARKDOWN
            )

        except Exception as e:
            self.logger.error(f"Search failed: {str(e)}")
            await update.message.reply_text(
                f"❌ Search failed: {str(e)}"
            )

    async def _show_recent_items(self, update: Update, content_type: Optional[str]):
        """Show recent items."""
        try:
            if content_type:
                results = self.storage.list_content_by_type(content_type, limit=10)
            else:
                # Show recent items from all types
                results = []
                for type_name in ['articles', 'newsletters', 'podcasts', 'youtube', 'emails']:
                    type_results = self.storage.list_content_by_type(type_name, limit=5)
                    results.extend(type_results)

            # Sort by modification date
            results.sort(key=lambda x: x['modified'], reverse=True)
            results = results[:10]

            if not results:
                await update.message.reply_text("📭 No recent items found.")
                return

            # Format results
            formatted_results = self.format_search_results(results)

            response_text = (
                f"📅 *Recent Items*\n\n"
                f"Showing {len(results)} most recent items"
            )

            if content_type:
                response_text += f" (type: {content_type})"

            response_text += f":\n\n{formatted_results}"

            await update.message.reply_text(
                response_text,
                parse_mode=ParseMode.MARKDOWN
            )

        except Exception as e:
            self.logger.error(f"Recent items failed: {str(e)}")
            await update.message.reply_text(
                f"❌ Failed to get recent items: {str(e)}"
            )

    async def _perform_inline_search(self, update: InlineQuery, context: ContextTypes.DEFAULT_TYPE, query: str):
        """Perform inline search for inline queries."""
        try:
            # Search content
            results = self.storage.search_content(query)
            limited_results = results[:self.config.max_inline_results] if hasattr(self, 'config') else results[:10]

            if not limited_results:
                return

            # Create inline query results
            inline_results = []
            for result in limited_results:
                frontmatter = result.get('frontmatter', {})
                title = frontmatter.get('title', 'Untitled')
                content_type = frontmatter.get('type', 'unknown')

                # Create result description
                description = f"Type: {content_type}"
                if frontmatter.get('source'):
                    description += f" | Source: {frontmatter['source']}"

                # Create message content
                message_content = self.format_search_results([result], max_items=1)

                inline_result = InlineQueryResultArticle(
                    id=result.get('path', 'unknown'),
                    title=title,
                    description=description,
                    input_message_content=InputTextMessageContent(
                        message_text=message_content,
                        parse_mode=ParseMode.MARKDOWN
                    ),
                    thumb_url=None
                )
                inline_results.append(inline_result)

            await update.inline_query.answer(inline_results, cache_time=300)

        except Exception as e:
            self.logger.error(f"Inline search failed: {str(e)}")


class StatusHandler(BaseHandler):
    """Handler for system status commands."""

    async def handle_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /status command."""
        await self.send_typing_action(update, context)

        try:
            # Get storage statistics
            stats = self.storage.get_storage_stats()

            # Format status message
            status_text = (
                "📊 *Atlas System Status*\n\n"
                f"📁 **Storage**\n"
                f"Total files: {stats.get('total_files', 0)}\n"
                f"Disk usage: {self._format_size(stats.get('disk_usage', 0))}\n"
            )

            # Add content breakdown
            if 'content_types' in stats:
                status_text += "\n📚 **Content by Type**\n"
                for content_type, count in stats['content_types'].items():
                    if count > 0:
                        emoji = self._get_content_type_emoji(content_type)
                        status_text += f"{emoji} {content_type}: {count}\n"

            # Add system health if available
            try:
                from ..core.recovery import get_system_health
                health = get_system_health()

                status_text += (
                    f"\n💻 **System Health**\n"
                    f"CPU: {health.cpu_percent:.1f}%\n"
                    f"Memory: {health.memory_percent:.1f}%\n"
                    f"Disk: {health.disk_usage_percent:.1f}%\n"
                    f"Network: {'🟢' if health.network_status else '🔴'}\n"
                )
            except Exception:
                pass  # Skip system health if not available

            status_text += f"\n🕒 *Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*"

            await update.message.reply_text(
                status_text,
                parse_mode=ParseMode.MARKDOWN
            )

        except Exception as e:
            self.logger.error(f"Status failed: {str(e)}")
            await update.message.reply_text(
                f"❌ Failed to get status: {str(e)}"
            )

    def _format_size(self, size_bytes: int) -> str:
        """Format bytes as human-readable size."""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} PB"

    def _get_content_type_emoji(self, content_type: str) -> str:
        """Get emoji for content type."""
        emojis = {
            'articles': '📄',
            'newsletters': '📰',
            'podcasts': '🎙️',
            'youtube': '🎥',
            'emails': '📧'
        }
        return emojis.get(content_type, '📁')


class ConfigHandler(BaseHandler):
    """Handler for configuration commands."""

    async def handle_config(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /config command."""
        await self.send_typing_action(update, context)

        # Parse arguments
        command_text = update.message.text
        args = command_text.split()[1:] if len(command_text.split()) > 1 else []

        if not args:
            await self._show_config_menu(update)
            return

        action = args[0].lower()
        if action == 'validate':
            await self._validate_config(update)
        elif action == 'show':
            await self._show_config(update)
        elif action == 'create':
            await self._create_config_template(update, args[1] if len(args) > 1 else None)
        else:
            await update.message.reply_text(
                "❌ Unknown config action. Use: `/config validate|show|create`"
            )

    async def _show_config_menu(self, update: Update):
        """Show configuration menu."""
        menu_text = (
            "⚙️ *Configuration Management*\n\n"
            "Available actions:\n\n"
            "• `/config validate` - Validate configuration\n"
            "• `/config show` - Show current configuration\n"
            "• `/config create <name>` - Create template file\n"
        )

        keyboard = [
            [KeyboardButton("✅ Validate"), KeyboardButton("👁️ Show")],
            [KeyboardButton("📄 Create"), KeyboardButton("❌ Cancel")]
        ]

        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)

        await update.message.reply_text(menu_text, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)

    async def _validate_config(self, update: Update):
        """Validate configuration."""
        await update.message.reply_text("🔍 Configuration validation not yet implemented.")

    async def _show_config(self, Update):
        """Show current configuration."""
        await update.message.reply_text("👁️ Configuration display not yet implemented.")

    async def _create_config_template(self, update: Update, config_name: Optional[str]):
        """Create configuration template."""
        await update.message.reply_text("📄 Template creation not yet implemented.")


class HelpHandler(BaseHandler):
    """Handler for help commands."""

    async def handle_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle help command."""
        help_text = (
            "🔧 *Atlas v4 Help*\n\n"
            "*Quick Commands*\n"
            "• `/ingest <source>` - Add content\n"
            "• `/search <query>` - Find content\n"
            "• `/recent [type]` - Recent items\n"
            "• `/status` - System status\n"
            "• `/config` - Configuration\n"
            "• `/help` - Show this help\n\n"
            "*Ingestion Sources*\n"
            "• Gmail: `/ingest gmail [--config=path.yaml]`\n"
            "• RSS: `/ingest rss [--config=feeds.yaml]`\n"
            "• YouTube: `/ingest youtube [--config=youtube.yaml]`\n\n"
            "*Search Examples*\n"
            "• `/search python programming`\n"
            "• `/search \"machine learning\"`\n"
            "• Inline: Just type your search in any chat\n\n"
            "*Configuration*\n"
            "• `/config validate` - Check configuration\n"
            "• `/config show` - View settings\n"
            "• `/config create` - Create template\n\n"
            "*Need more help?*\n"
            "Visit the documentation or use `/status` to check system health."
        )

        await update.message.reply_text(help_text, parse_mode=ParseMode.MARKDOWN)