"""
External interfaces for Atlas v4.

Communication channels:
- Telegram bot interface
- CLI commands (handled in cli.py)
- Python API for agent integration
"""

from .telegram_bot import AtlasTelegramBot

__all__ = [
    "AtlasTelegramBot",
]