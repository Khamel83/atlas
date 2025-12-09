"""
Telegram Notifications - Send alerts for failures.

Uses Telegram Bot API to send notifications.
Requires TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in environment.
"""

import os
import logging
from typing import Optional
from datetime import datetime

import requests

logger = logging.getLogger(__name__)


class TelegramNotifier:
    """Send notifications via Telegram."""

    def __init__(
        self,
        bot_token: Optional[str] = None,
        chat_id: Optional[str] = None,
    ):
        self.bot_token = bot_token or os.getenv("TELEGRAM_BOT_TOKEN")
        self.chat_id = chat_id or os.getenv("TELEGRAM_CHAT_ID")
        self.enabled = bool(self.bot_token and self.chat_id)

        if not self.enabled:
            logger.warning("Telegram notifications disabled - missing credentials")

    def send_message(self, message: str, parse_mode: str = "Markdown") -> bool:
        """
        Send a message via Telegram.

        Args:
            message: Message text
            parse_mode: "Markdown" or "HTML"

        Returns:
            True if sent successfully
        """
        if not self.enabled:
            logger.debug("Telegram disabled, not sending message")
            return False

        try:
            url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
            data = {
                "chat_id": self.chat_id,
                "text": message,
                "parse_mode": parse_mode,
            }
            response = requests.post(url, json=data, timeout=10)
            response.raise_for_status()
            logger.debug(f"Telegram message sent: {message[:50]}...")
            return True
        except Exception as e:
            logger.error(f"Failed to send Telegram message: {e}")
            return False

    def notify_error(
        self,
        component: str,
        error: str,
        details: Optional[str] = None,
    ) -> bool:
        """Send an error notification."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        message = f"""🚨 *Atlas Error*

*Component:* `{component}`
*Time:* {timestamp}

*Error:*
```
{error[:500]}
```
"""
        if details:
            message += f"\n*Details:*\n{details[:300]}"

        return self.send_message(message)

    def notify_success(
        self,
        component: str,
        summary: str,
        stats: Optional[dict] = None,
    ) -> bool:
        """Send a success notification (optional, for important completions)."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        message = f"""✅ *Atlas Success*

*Component:* `{component}`
*Time:* {timestamp}

*Summary:* {summary}
"""
        if stats:
            stats_text = "\n".join([f"- {k}: {v}" for k, v in stats.items()])
            message += f"\n*Stats:*\n{stats_text}"

        return self.send_message(message)

    def notify_warning(
        self,
        component: str,
        warning: str,
    ) -> bool:
        """Send a warning notification."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        message = f"""⚠️ *Atlas Warning*

*Component:* `{component}`
*Time:* {timestamp}

*Warning:* {warning}
"""
        return self.send_message(message)


# Singleton instance for easy access
_notifier: Optional[TelegramNotifier] = None


def get_notifier() -> TelegramNotifier:
    """Get the global notifier instance."""
    global _notifier
    if _notifier is None:
        _notifier = TelegramNotifier()
    return _notifier


def notify_error(component: str, error: str, details: Optional[str] = None) -> bool:
    """Convenience function to send error notification."""
    return get_notifier().notify_error(component, error, details)


def notify_success(component: str, summary: str, stats: Optional[dict] = None) -> bool:
    """Convenience function to send success notification."""
    return get_notifier().notify_success(component, summary, stats)


def notify_warning(component: str, warning: str) -> bool:
    """Convenience function to send warning notification."""
    return get_notifier().notify_warning(component, warning)
