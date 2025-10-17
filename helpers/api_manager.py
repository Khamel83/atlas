#!/usr/bin/env python3
"""
Centralized API Manager for Atlas

SINGLE POINT OF CONTROL for all API keys and expensive services.

This replaces the distributed global singleton pattern with a centralized
system that always checks current permissions before using any API.

Principles:
1. No global instances that cache API keys
2. Always check permissions before using APIs
3. Single source of truth for API authorization
4. Immediate revocation capability
"""

import os
import json
import logging
import subprocess
from typing import Dict, List, Optional, Any
from pathlib import Path
from dataclasses import dataclass
from enum import Enum
from functools import wraps
import time

logger = logging.getLogger(__name__)

class APIStatus(Enum):
    ENABLED = "enabled"
    DISABLED = "disabled"
    QUOTA_EXCEEDED = "quota_exceeded"
    UNAUTHORIZED = "unauthorized"

@dataclass
class APIService:
    name: str
    env_keys: List[str]
    cost_level: str  # "free", "low", "high", "premium"
    daily_quota: Optional[int] = None
    auth_file: Optional[str] = None
    requires_1password: bool = False

class APIManager:
    """
    SINGLE POINT OF CONTROL for all API usage

    This class replaces global instances and ensures:
    - API permissions are checked BEFORE every call
    - No caching of API keys or permissions
    - Immediate ability to revoke API access
    - Centralized logging and monitoring
    """

    # Service definitions - SINGLE SOURCE OF TRUTH
    SERVICES = {
        "google_search": APIService(
            name="Google Search API",
            env_keys=["GOOGLE_SEARCH_API_KEY", "GOOGLE_SEARCH_ENGINE_ID"],
            cost_level="high",
            daily_quota=100,
            auth_file="google_search_enabled",
            requires_1password=True
        ),
        "youtube": APIService(
            name="YouTube API",
            env_keys=["YOUTUBE_API_KEY"],
            cost_level="low",
            daily_quota=10000,
            auth_file="youtube_enabled"
        ),
        "openai": APIService(
            name="OpenAI API",
            env_keys=["OPENAI_API_KEY"],
            cost_level="premium",
            auth_file="openai_enabled",
            requires_1password=True
        ),
        "anthropic": APIService(
            name="Anthropic API",
            env_keys=["ANTHROPIC_API_KEY"],
            cost_level="premium",
            auth_file="anthropic_enabled",
            requires_1password=True
        )
    }

    def __init__(self):
        self.config_dir = Path("/home/ubuntu/dev/atlas/config")
        self.config_dir.mkdir(exist_ok=True)

        # Runtime permission cache (short-lived, for performance)
        self._permission_cache = {}
        self._cache_ttl = 60  # 60 seconds

    def _clear_permission_cache(self):
        """Clear the permission cache to force rechecking"""
        self._permission_cache.clear()
        logger.info("🧹 Cleared API permission cache")

    def _load_1password_credentials(self, service: APIService) -> Dict[str, str]:
        """Load credentials from 1Password for a specific service"""
        if not service.requires_1password:
            return {}

        credentials = {}

        try:
            # Check if 1Password CLI is available
            result = subprocess.run(
                ["op", "--version"],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode != 0:
                logger.warning("1Password CLI not found")
                return credentials

            # Get the Atlas API keys item
            result = subprocess.run(
                ["op", "item", "get", "atlas-api-keys", "--format", "json"],
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode == 0:
                item_data = json.loads(result.stdout)

                # Map environment keys to 1Password field IDs
                field_mapping = {
                    "GOOGLE_SEARCH_API_KEY": "google_search_api_key",
                    "GOOGLE_SEARCH_ENGINE_ID": "google_search_engine_id",
                    "YOUTUBE_API_KEY": "youtube_api_key",
                    "OPENAI_API_KEY": "openai_api_key",
                    "ANTHROPIC_API_KEY": "anthropic_api_key"
                }

                # Extract credentials for this service
                for env_key in service.env_keys:
                    field_id = field_mapping.get(env_key)
                    if field_id:
                        for field in item_data.get("fields", []):
                            if field.get("id") == field_id:
                                credentials[env_key] = field.get("value", "")

        except Exception as e:
            logger.error(f"Error loading 1Password credentials for {service.name}: {e}")

        return credentials

    def check_service_permission(self, service_name: str) -> APIStatus:
        """
        Check if a service is authorized to run

        THIS IS THE SINGLE POINT OF TRUTH for API permissions
        """
        # Check cache first
        cache_key = f"{service_name}_{int(time.time() / self._cache_ttl)}"
        if cache_key in self._permission_cache:
            return self._permission_cache[cache_key]

        service = self.SERVICES.get(service_name)
        if not service:
            status = APIStatus.UNAUTHORIZED
            self._permission_cache[cache_key] = status
            return status

        # Load credentials from 1Password if required
        credentials = self._load_1password_credentials(service)

        # Check if API keys are available
        keys_available = False
        for env_key in service.env_keys:
            # Check environment first, then 1Password credentials
            key_value = os.getenv(env_key) or credentials.get(env_key)
            if key_value:
                keys_available = True
                break

        if not keys_available:
            status = APIStatus.DISABLED
            self._permission_cache[cache_key] = status
            logger.debug(f"🚫 {service.name}: No API keys available")
            return status

        # Check authorization file for expensive services
        if service.cost_level in ["high", "premium"]:
            auth_file = self.config_dir / service.auth_file
            if not auth_file.exists():
                status = APIStatus.UNAUTHORIZED
                self._permission_cache[cache_key] = status
                logger.warning(f"🚫 {service.name}: No authorization file {auth_file}")
                return status

        status = APIStatus.ENABLED
        self._permission_cache[cache_key] = status
        logger.info(f"✅ {service.name}: Authorized")
        return status

    def require_service(self, service_name: str):
        """
        Decorator to require API service permission
        Usage:
            @api_manager.require_service("google_search")
            def expensive_search_function(query):
                # This will only run if google_search is authorized
        """
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                # Check permission BEFORE running the function
                status = self.check_service_permission(service_name)

                if status != APIStatus.ENABLED:
                    raise PermissionError(f"Service {service_name} is not authorized (status: {status.value})")

                # Load credentials if needed
                service = self.SERVICES.get(service_name)
                if service:
                    credentials = self._load_1password_credentials(service)
                    # Temporarily set environment variables
                    old_env = {}
                    for env_key in service.env_keys:
                        old_env[env_key] = os.getenv(env_key)
                        if env_key in credentials:
                            os.environ[env_key] = credentials[env_key]
                        elif env_key in os.environ:
                            # Remove if not in 1Password but in environment
                            del os.environ[env_key]

                try:
                    return func(*args, **kwargs)
                finally:
                    # Restore original environment
                    if service:
                        for env_key in service.env_keys:
                            if env_key in old_env:
                                if old_env[env_key] is not None:
                                    os.environ[env_key] = old_env[env_key]
                                else:
                                    if env_key in os.environ:
                                        del os.environ[env_key]
            return wrapper
        return decorator

    def get_service_credentials(self, service_name: str) -> Dict[str, str]:
        """Get credentials for a service (if authorized)"""
        status = self.check_service_permission(service_name)
        if status != APIStatus.ENABLED:
            return {}

        service = self.SERVICES.get(service_name)
        if not service:
            return {}

        credentials = {}

        # Get from environment or 1Password
        one_pass_creds = self._load_1password_credentials(service)

        for env_key in service.env_keys:
            value = os.getenv(env_key) or one_pass_creds.get(env_key)
            if value:
                credentials[env_key] = value

        return credentials

    def enable_service(self, service_name: str, reason: str = ""):
        """Enable a service by creating authorization file"""
        service = self.SERVICES.get(service_name)
        if not service:
            raise ValueError(f"Unknown service: {service_name}")

        if not service.auth_file:
            raise ValueError(f"Service {service_name} cannot be manually enabled")

        auth_file = self.config_dir / service.auth_file
        with open(auth_file, "w") as f:
            f.write(f"Enabled: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Reason: {reason}\n")
            f.write(f"User: {os.getenv('USER', 'unknown')}\n")

        # Clear cache to force recheck
        self._clear_permission_cache()

        logger.info(f"✅ Enabled {service_name}: {reason}")

    def disable_service(self, service_name: str, reason: str = ""):
        """Disable a service by removing authorization file"""
        service = self.SERVICES.get(service_name)
        if not service:
            return

        if service.auth_file:
            auth_file = self.config_dir / service.auth_file
            if auth_file.exists():
                auth_file.unlink()

        # Clear cache to force recheck
        self._clear_permission_cache()

        logger.info(f"🚫 Disabled {service_name}: {reason}")

    def disable_all_expensive_services(self):
        """Disable all expensive services"""
        expensive_services = [name for name, service in self.SERVICES.items()
                             if service.cost_level in ["high", "premium"]]

        for service_name in expensive_services:
            self.disable_service(service_name, "Disabled all expensive services")

        logger.info(f"🚫 Disabled {len(expensive_services)} expensive services")

    def get_service_status(self, service_name: str) -> Dict[str, Any]:
        """Get status information for a service"""
        service = self.SERVICES.get(service_name)
        if not service:
            return {"error": "Unknown service"}

        status = self.check_service_permission(service_name)
        credentials = self.get_service_credentials(service_name)

        return {
            "name": service.name,
            "status": status.value,
            "cost_level": service.cost_level,
            "auth_file": str(self.config_dir / service.auth_file) if service.auth_file else None,
            "credentials_available": len(credentials) > 0,
            "requires_1password": service.requires_1password,
            "permission_cache_size": len(self._permission_cache)
        }

    def list_all_services(self) -> Dict[str, Dict[str, Any]]:
        """List status of all services"""
        return {name: self.get_service_status(name) for name in self.SERVICES.keys()}

# Global instance - SINGLE POINT OF CONTROL
api_manager = APIManager()

def main():
    """CLI interface for API management"""
    import argparse

    parser = argparse.ArgumentParser(description="Atlas API Manager - Single Point of Control")
    parser.add_argument("--list", action="store_true", help="List all services")
    parser.add_argument("--enable", help="Enable a service")
    parser.add_argument("--disable", help="Disable a service")
    parser.add_argument("--reason", help="Reason for enable/disable")
    parser.add_argument("--disable-expensive", action="store_true", help="Disable all expensive services")
    parser.add_argument("--clear-cache", action="store_true", help="Clear permission cache")

    args = parser.parse_args()

    if args.clear_cache:
        api_manager._clear_permission_cache()
        print("✅ Cleared permission cache")
        return

    if args.list:
        services = api_manager.list_all_services()
        print("🔑 Atlas API Services Status")
        print("=" * 50)
        for name, info in services.items():
            status_icon = "✅" if info["status"] == "enabled" else "🚫"
            cost_icon = {"free": "🆓", "low": "💰", "high": "💸", "premium": "💎"}[info["cost_level"]]
            print(f"{status_icon} {name} ({cost_icon})")
            print(f"   Status: {info['status']}")
            print(f"   Credentials: {'✓' if info['credentials_available'] else '✗'}")
            print(f"   1Password: {'✓' if info['requires_1password'] else '✗'}")
            print()

    elif args.enable:
        api_manager.enable_service(args.enable, args.reason or "Manual enable")
        print(f"✅ Enabled {args.enable}")

    elif args.disable:
        api_manager.disable_service(args.disable, args.reason or "Manual disable")
        print(f"🚫 Disabled {args.disable}")

    elif args.disable_expensive:
        api_manager.disable_all_expensive_services()
        print("🚫 Disabled all expensive services")

    else:
        parser.print_help()

if __name__ == "__main__":
    main()