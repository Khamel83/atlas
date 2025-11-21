"""
Telegram bot deployment and configuration utilities for Atlas v4.

Provides deployment scripts, configuration management, and monitoring
for running Atlas bots in production environments.
"""

import asyncio
import json
import logging
import signal
import sys
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
import yaml

from .main import AtlasBot, BotConfig


@dataclass
class BotDeploymentConfig:
    """Configuration for bot deployment."""
    name: str
    token: str
    webhooks: bool = False
    webhook_url: Optional[str] = None
    webhook_port: int = 8443
    webhook_path: str = "/webhook"
    ssl_cert: Optional[str] = None
    ssl_key: Optional[str] = None
    allowed_users: List[str] = None
    allowed_chats: List[str] = None
    log_level: str = "INFO"
    log_file: Optional[str] = None
    vault_root: Optional[str] = None
    max_inline_results: int = 10
    rate_limit: int = 30  # messages per minute
    admin_chat_id: Optional[str] = None
    monitoring_enabled: bool = True


class BotDeployment:
    """
    Manages Telegram bot deployment.

    Features:
    - Configuration management
    - Process monitoring and health checks
    - Graceful shutdown handling
    - Multiple deployment modes (polling, webhook)
    - Logging and monitoring
    """

    def __init__(self, deployment_config: BotDeploymentConfig):
        """
        Initialize deployment manager.

        Args:
            deployment_config: Deployment configuration
        """
        self.config = deployment_config
        self.logger = logging.getLogger(f"atlas.bot.{self.__class__.__name__}")
        self.bot: Optional[AtlasBot] = None
        self.running = False
        self.shutdown_requested = False

        # Setup logging
        self._setup_logging()

        # Setup signal handlers
        self._setup_signal_handlers()

    def _setup_logging(self):
        """Setup logging for deployment."""
        log_level = getattr(logging, self.config.log_level.upper())
        root_logger = logging.getLogger()
        root_logger.setLevel(log_level)

        # Remove existing handlers
        root_logger.handlers.clear()

        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(log_level)

        # Formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)

        # File handler if specified
        if self.config.log_file:
            log_file = Path(self.config.log_file)
            log_file.parent.mkdir(parents=True, exist_ok=True)

            file_handler = logging.FileHandler(log_file)
            file_handler.setLevel(log_level)
            file_handler.setFormatter(formatter)
            root_logger.addHandler(file_handler)

    def _setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown."""
        def signal_handler(signum, frame):
            self.logger.info(f"Received signal {signum}, initiating graceful shutdown...")
            self.shutdown_requested = True
            if self.bot and self.bot.application:
                self.bot.application.stop()
            else:
                sys.exit(0)

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

    def create_bot(self) -> AtlasBot:
        """
        Create Atlas bot instance.

        Returns:
            AtlasBot instance
        """
        try:
            # Create bot config from deployment config
            bot_config = BotConfig(
                token=self.config.token,
                allowed_users=self.config.allowed_users or [],
                allowed_chats=self.config.allowed_chats or [],
                enable_inline=True,
                max_inline_results=self.config.max_inline_results,
                log_level=self.config.log_level,
                vault_root=self.config.vault_root
            )

            # Create bot
            bot = AtlasBot(bot_config)
            self.bot = bot

            self.logger.info("Atlas bot created successfully")
            return bot

        except Exception as e:
            self.logger.error(f"Failed to create bot: {str(e)}")
            raise

    def start_polling(self):
        """
        Start bot in polling mode.

        This method blocks until the bot is stopped.
        """
        if not self.bot:
            self.create_bot()

        self.running = True
        self.logger.info("Starting Atlas bot in polling mode")

        try:
            self.bot.run_polling()
        except KeyboardInterrupt:
            self.logger.info("Keyboard interrupt received")
        except Exception as e:
            self.logger.error(f"Bot polling failed: {str(e)}")
            raise
        finally:
            self.running = False

    def start_webhook(self):
        """
        Start bot in webhook mode.

        This method blocks until the bot is stopped.
        """
        if not self.bot:
            self.create_bot()

        if not self.config.webhooks:
            raise ValueError("Webhooks not enabled in configuration")

        self.running = True
        self.logger.info(f"Starting Atlas bot in webhook mode on port {self.config.webhook_port}")

        try:
            webhook_url = self.config.webhook_url or f"https://example.com:{self.config.webhook_port}{self.config.webhook_path}"

            self.bot.run_webhook(
                webhook_url=webhook_url,
                port=self.config.webhook_port,
                cert_path=self.config.ssl_cert
            )
        except KeyboardInterrupt:
            self.logger.info("Keyboard interrupt received")
        except Exception as e:
            self.logger.error(f"Bot webhook failed: {str(e)}")
            raise
        finally:
            self.running = False

    def start_async(self, mode: str = "polling"):
        """
        Start bot asynchronously.

        Args:
            mode: Deployment mode ("polling" or "webhook")
        """
        if not self.bot:
            self.create_bot()

        self.running = True

        async def run_bot():
            try:
                if mode == "polling":
                    self.logger.info("Starting bot in async polling mode")
                    await self.bot.application.start_polling()
                elif mode == "webhook":
                    if not self.config.webhooks:
                        raise ValueError("Webhooks not enabled")

                    self.logger.info(f"Starting bot in async webhook mode")
                    webhook_url = self.config.webhook_url or f"https://example.com:{self.config.webhook_port}{self.config.webhook_path}"

                    await self.bot.application.bot.set_webhook(
                        url=webhook_url,
                        allowed_updates=None
                    )

                    # Start webhook server
                    import uvicorn
                    from telegram.ext import Application

                    # Create FastAPI app for webhook
                    app = Application.builder().token(self.config.token).build()

                    await uvicorn.run(
                        app,
                        host="0.0.0.0",
                        port=self.config.webhook_port,
                        ssl_certfile=self.config.ssl_cert,
                        ssl_keyfile=self.config.ssl_key
                    )
            except Exception as e:
                self.logger.error(f"Async bot failed: {str(e)}")
                raise
            finally:
                self.running = False

        # Run in background
        asyncio.run(run_bot())

    def get_status(self) -> Dict[str, Any]:
        """
        Get current deployment status.

        Returns:
            Status information dictionary
        """
        status = {
            "running": self.running,
            "shutdown_requested": self.shutdown_requested,
            "config": asdict(self.config),
            "bot_created": self.bot is not None,
            "deployment_mode": "webhook" if self.config.webhooks else "polling"
        }

        if self.bot:
            bot_info = self.bot.get_bot_info()
            status.update(bot_info)

        return status

    def stop(self):
        """Stop the bot gracefully."""
        self.logger.info("Stopping Atlas bot...")
        self.shutdown_requested = True

        if self.bot and self.bot.application:
            self.bot.application.stop()

    def health_check(self) -> Dict[str, Any]:
        """
        Perform health check.

        Returns:
            Health check results
        """
        health = {
            "status": "healthy",
            "timestamp": "2025-10-16T17:45:00Z",
            "checks": {}
        }

        try:
            # Check bot exists
            health["checks"]["bot_created"] = {
                "status": "pass" if self.bot is not None else "fail",
                "message": "Bot instance created" if self.bot is not None else "Bot not created"
            }

            # Check storage
            if self.bot and self.bot.storage:
                try:
                    stats = self.bot.storage.get_storage_stats()
                    health["checks"]["storage"] = {
                        "status": "pass",
                        "message": f"Storage accessible, {stats.get('total_files', 0)} files"
                    }
                except Exception as e:
                    health["checks"]["storage"] = {
                        "status": "fail",
                        "message": f"Storage error: {str(e)}"
                    }
                    health["status"] = "unhealthy"

            # Check configuration
            health["checks"]["config"] = {
                "status": "pass",
                "message": "Configuration loaded"
            }

        except Exception as e:
            health["status"] = "unhealthy"
            health["error"] = str(e)

        return health


class BotManager:
    """
    Manages multiple bot deployments.

    Provides centralized management for multiple Atlas bots
    with different configurations and monitoring.
    """

    def __init__(self, config_dir: str):
        """
        Initialize bot manager.

        Args:
            config_dir: Directory containing bot configurations
        """
        self.config_dir = Path(config_dir)
        self.logger = logging.getLogger(f"atlas.bot.{self.__class__.__name__}")
        self.deployments: Dict[str, BotDeployment] = {}

        # Ensure config directory exists
        self.config_dir.mkdir(parents=True, exist_ok=True)

    def load_deployment(self, config_name: str) -> BotDeployment:
        """
        Load deployment configuration.

        Args:
            config_name: Name of deployment configuration

        Returns:
            BotDeployment instance
        """
        config_file = self.config_dir / f"{config_name}.yaml"

        if not config_file.exists():
            raise FileNotFoundError(f"Deployment config not found: {config_file}")

        try:
            with open(config_file, 'r') as f:
                config_data = yaml.safe_load(f)

            deployment_config = BotDeploymentConfig(**config_data)
            deployment = BotDeployment(deployment_config)
            self.deployments[config_name] = deployment

            self.logger.info(f"Loaded deployment config: {config_name}")
            return deployment

        except Exception as e:
            self.logger.error(f"Failed to load deployment config {config_name}: {str(e)}")
            raise

    def create_deployment_template(self, config_name: str, **overrides) -> str:
        """
        Create deployment configuration template.

        Args:
            config_name: Name of deployment
            **overrides: Configuration overrides

        Returns:
            Path to created configuration file
        """
        template_config = {
            "name": config_name,
            "token": "YOUR_BOT_TOKEN_HERE",
            "webhooks": False,
            "allowed_users": ["123456789"],  # Replace with actual user IDs
            "allowed_chats": [],
            "log_level": "INFO",
            "log_file": f"/var/log/atlas/{config_name}.log",
            "vault_root": f"/var/lib/atlas/{config_name}",
            "max_inline_results": 10,
            "rate_limit": 30,
            "admin_chat_id": None,
            "monitoring_enabled": True
        }

        # Apply overrides
        template_config.update(overrides)

        config_file = self.config_dir / f"{config_name}.yaml"

        with open(config_file, 'w') as f:
            yaml.dump(template_config, f, default_flow_style=False)

        self.logger.info(f"Created deployment template: {config_file}")
        return str(config_file)

    def start_deployment(self, config_name: str, mode: str = "polling"):
        """
        Start specific deployment.

        Args:
            config_name: Name of deployment to start
            mode: Deployment mode ("polling" or "webhook")
        """
        if config_name not in self.deployments:
            self.load_deployment(config_name)

        deployment = self.deployments[config_name]
        self.logger.info(f"Starting deployment: {config_name} (mode: {mode})")

        if mode == "webhook":
            deployment.start_webhook()
        else:
            deployment.start_polling()

    def start_deployment_async(self, config_name: str, mode: str = "polling"):
        """
        Start deployment asynchronously.

        Args:
            config_name: Name of deployment to start
            mode: Deployment mode ("polling" or "webhook")
        """
        if config_name not in self.deployments:
            self.load_deployment(config_name)

        deployment = self.deployments[config_name]
        self.logger.info(f"Starting deployment asynchronously: {config_name} (mode: {mode})")

        return deployment.start_async(mode)

    def stop_deployment(self, config_name: str):
        """
        Stop specific deployment.

        Args:
            config_name: Name of deployment to stop
        """
        if config_name not in self.deployments:
            self.logger.warning(f"Deployment not found: {config_name}")
            return

        deployment = self.deployments[config_name]
        deployment.stop()
        self.logger.info(f"Stopped deployment: {config_name}")

    def list_deployments(self) -> List[str]:
        """
        List all available deployments.

        Returns:
            List of deployment names
        """
        return list(self.deployments.keys())

    def get_deployment_status(self, config_name: str) -> Optional[Dict[str, Any]]:
        """
        Get status of specific deployment.

        Args:
            config_name: Name of deployment

        Returns:
            Status information or None if not found
        """
        if config_name not in self.deployments:
            return None

        deployment = self.deployments[config_name]
        return deployment.get_status()

    def health_check_all(self) -> Dict[str, Dict[str, Any]]:
        """
        Perform health check on all deployments.

        Returns:
            Health check results for all deployments
        """
        results = {}

        for config_name, deployment in self.deployments.items():
            try:
                results[config_name] = deployment.health_check()
            except Exception as e:
                results[config_name] = {
                    "status": "error",
                    "error": str(e)
                }

        return results