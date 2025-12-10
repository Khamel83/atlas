#!/usr/bin/env python3
"""
OOS Service Manager with SystemD integration and watchdog
"""

import os
import sys
import time
import json
import signal
import logging
import threading
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional
import argparse

# Add lib to path
sys.path.insert(0, str(Path(__file__).parent / 'lib'))
sys.path.insert(0, str(Path(__file__).parent / 'helpers'))

try:
    import systemd.daemon
    SYSTEMD_AVAILABLE = True
except ImportError:
    SYSTEMD_AVAILABLE = False
    print("Warning: systemd module not available, watchdog disabled")

from resource_manager import ResourceManager

class OOSServiceManager:
    """Main service manager with SystemD integration"""

    def __init__(self, config_path: str = "data/oos_config.json"):
        self.config_path = config_path
        self.config = self._load_config()
        self.logger = self._setup_logging()
        self.shutdown_requested = False
        self.watchdog_thread = None
        self.resource_manager = ResourceManager()

        # Service components
        self.services = {}

        self.logger.info("OOS Service Manager initializing...")

    def _load_config(self) -> Dict:
        """Load service configuration"""
        default_config = {
            "service": {
                "name": "oos",
                "description": "Organized Operational Setup",
                "watchdog_interval": 15,  # seconds
                "health_check_interval": 60,
                "max_memory_mb": 2048,
                "max_cpu_percent": 200
            },
            "components": {
                "resource_manager": {
                    "enabled": True,
                    "check_interval": 60
                },
                "health_monitor": {
                    "enabled": True,
                    "check_interval": 30
                },
                "log_manager": {
                    "enabled": True,
                    "rotation_interval": 3600
                }
            },
            "logging": {
                "level": "INFO",
                "file": "data/oos_service.log",
                "max_size_mb": 100,
                "backup_count": 5
            }
        }

        try:
            if Path(self.config_path).exists():
                with open(self.config_path) as f:
                    config = json.load(f)
                # Merge with defaults
                for key, value in default_config.items():
                    if key not in config:
                        config[key] = value
                    elif isinstance(value, dict):
                        for subkey, subvalue in value.items():
                            if subkey not in config[key]:
                                config[key][subkey] = subvalue
                return config
            else:
                self._save_config(default_config)
                return default_config
        except Exception as e:
            print(f"Error loading config: {e}")
            return default_config

    def _save_config(self, config: Dict):
        """Save configuration to file"""
        try:
            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
            with open(self.config_path, 'w') as f:
                json.dump(config, f, indent=2)
        except Exception as e:
            print(f"Error saving config: {e}")

    def _setup_logging(self) -> logging.Logger:
        """Setup logging for service manager"""
        logger = logging.getLogger('oos_service')
        logger.setLevel(getattr(logging, self.config["logging"]["level"]))

        if not logger.handlers:
            # File handler
            log_file = self.config["logging"]["file"]
            os.makedirs(os.path.dirname(log_file), exist_ok=True)

            from logging.handlers import RotatingFileHandler
            file_handler = RotatingFileHandler(
                log_file,
                maxBytes=self.config["logging"]["max_size_mb"] * 1024 * 1024,
                backupCount=self.config["logging"]["backup_count"]
            )

            # Console handler for systemd
            console_handler = logging.StreamHandler(sys.stdout)

            # Formatter
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            file_handler.setFormatter(formatter)
            console_handler.setFormatter(formatter)

            logger.addHandler(file_handler)
            logger.addHandler(console_handler)

        return logger

    def _start_watchdog(self):
        """Start SystemD watchdog thread"""
        if not SYSTEMD_AVAILABLE:
            self.logger.warning("SystemD not available, watchdog disabled")
            return

        def watchdog_worker():
            interval = self.config["service"]["watchdog_interval"]
            self.logger.info(f"Starting watchdog with {interval}s interval")

            while not self.shutdown_requested:
                try:
                    # Perform health check
                    if self._health_check():
                        # Send watchdog ping
                        systemd.daemon.notify("WATCHDOG=1")
                        self.logger.debug("Watchdog heartbeat sent")
                    else:
                        self.logger.error("Health check failed, skipping watchdog ping")

                    time.sleep(interval)

                except Exception as e:
                    self.logger.error(f"Watchdog error: {e}")
                    time.sleep(interval)

        self.watchdog_thread = threading.Thread(target=watchdog_worker, daemon=True)
        self.watchdog_thread.start()

    def _health_check(self) -> bool:
        """Perform comprehensive health check"""
        try:
            # Check resource usage
            metrics = self.resource_manager.collect_metrics()

            # Check memory usage
            max_memory = self.config["service"]["max_memory_mb"]
            if metrics.memory_percent > (max_memory / 2048) * 100:  # Rough conversion
                self.logger.warning(f"High memory usage: {metrics.memory_percent:.1f}%")

            # Check CPU usage
            max_cpu = self.config["service"]["max_cpu_percent"]
            if metrics.cpu_percent > max_cpu:
                self.logger.warning(f"High CPU usage: {metrics.cpu_percent:.1f}%")

            # Check disk space
            if metrics.disk_percent > 95:
                self.logger.error(f"Critical disk usage: {metrics.disk_percent:.1f}%")
                return False

            # Check service components
            for component_name, component_config in self.config["components"].items():
                if component_config.get("enabled", False):
                    if not self._check_component_health(component_name):
                        self.logger.error(f"Component {component_name} health check failed")
                        return False

            return True

        except Exception as e:
            self.logger.error(f"Health check error: {e}")
            return False

    def _check_component_health(self, component_name: str) -> bool:
        """Check health of individual component"""
        try:
            if component_name == "resource_manager":
                return self.resource_manager is not None
            elif component_name == "health_monitor":
                return True  # Basic implementation
            elif component_name == "log_manager":
                return os.path.exists(self.config["logging"]["file"])
            else:
                return True  # Unknown component, assume healthy
        except Exception as e:
            self.logger.error(f"Error checking {component_name} health: {e}")
            return False

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        signal_names = {
            signal.SIGTERM: "SIGTERM",
            signal.SIGINT: "SIGINT",
            signal.SIGHUP: "SIGHUP"
        }

        signal_name = signal_names.get(signum, str(signum))
        self.logger.info(f"Received {signal_name} signal")

        if signum in [signal.SIGTERM, signal.SIGINT]:
            self.shutdown()
        elif signum == signal.SIGHUP:
            self.reload_config()

    def reload_config(self):
        """Reload configuration without restarting"""
        self.logger.info("Reloading configuration...")
        try:
            old_config = self.config.copy()
            self.config = self._load_config()

            # Compare and apply changes
            if old_config != self.config:
                self.logger.info("Configuration updated")
                # Apply configuration changes here
            else:
                self.logger.info("No configuration changes detected")

        except Exception as e:
            self.logger.error(f"Error reloading configuration: {e}")

    def start(self):
        """Start the service"""
        self.logger.info("Starting OOS Service Manager")

        # Setup signal handlers
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGHUP, self._signal_handler)

        try:
            # Notify systemd that we're ready
            if SYSTEMD_AVAILABLE:
                systemd.daemon.notify("READY=1")
                self.logger.info("Notified SystemD that service is ready")

            # Start watchdog
            self._start_watchdog()

            # Start service components
            self._start_components()

            # Main service loop
            self._run_main_loop()

        except Exception as e:
            self.logger.error(f"Service start error: {e}")
            self.shutdown()
            return 1

        return 0

    def _start_components(self):
        """Start service components"""
        for component_name, component_config in self.config["components"].items():
            if component_config.get("enabled", False):
                self.logger.info(f"Starting component: {component_name}")
                try:
                    self._start_component(component_name, component_config)
                except Exception as e:
                    self.logger.error(f"Failed to start component {component_name}: {e}")

    def _start_component(self, name: str, config: Dict):
        """Start individual component"""
        if name == "resource_manager":
            # Resource manager already initialized
            pass
        elif name == "health_monitor":
            self._start_health_monitor(config)
        elif name == "log_manager":
            self._start_log_manager(config)

    def _start_health_monitor(self, config: Dict):
        """Start health monitoring component"""
        def health_monitor_worker():
            interval = config.get("check_interval", 60)

            while not self.shutdown_requested:
                try:
                    # Collect and log health metrics
                    metrics = self.resource_manager.collect_metrics()
                    self.logger.debug(f"Health: CPU={metrics.cpu_percent:.1f}%, "
                                    f"Memory={metrics.memory_percent:.1f}%, "
                                    f"Disk={metrics.disk_percent:.1f}%")

                    # Check for issues
                    memory_check = self.resource_manager.check_memory_pressure()
                    if memory_check["pressure_level"] != "normal":
                        self.logger.warning(f"Memory pressure: {memory_check}")

                    time.sleep(interval)

                except Exception as e:
                    self.logger.error(f"Health monitor error: {e}")
                    time.sleep(interval)

        health_thread = threading.Thread(target=health_monitor_worker, daemon=True)
        health_thread.start()
        self.services["health_monitor"] = health_thread

    def _start_log_manager(self, config: Dict):
        """Start log management component"""
        def log_manager_worker():
            interval = config.get("rotation_interval", 3600)

            while not self.shutdown_requested:
                try:
                    # Perform log rotation and cleanup
                    self.logger.debug("Log manager check")
                    # Add log management logic here

                    time.sleep(interval)

                except Exception as e:
                    self.logger.error(f"Log manager error: {e}")
                    time.sleep(interval)

        log_thread = threading.Thread(target=log_manager_worker, daemon=True)
        log_thread.start()
        self.services["log_manager"] = log_thread

    def _run_main_loop(self):
        """Main service loop"""
        self.logger.info("Entering main service loop")

        while not self.shutdown_requested:
            try:
                # Main service work goes here
                time.sleep(1)

            except KeyboardInterrupt:
                self.logger.info("Keyboard interrupt received")
                break
            except Exception as e:
                self.logger.error(f"Main loop error: {e}")
                time.sleep(5)  # Wait before continuing

    def shutdown(self):
        """Shutdown the service gracefully"""
        if self.shutdown_requested:
            return

        self.logger.info("Shutting down OOS Service Manager")
        self.shutdown_requested = True

        try:
            # Stop service components
            for component_name, component in self.services.items():
                self.logger.info(f"Stopping component: {component_name}")
                if hasattr(component, 'shutdown'):
                    component.shutdown()

            # Wait for watchdog thread
            if self.watchdog_thread and self.watchdog_thread.is_alive():
                self.watchdog_thread.join(timeout=5)

            # Notify systemd
            if SYSTEMD_AVAILABLE:
                systemd.daemon.notify("STOPPING=1")
                self.logger.info("Notified SystemD that service is stopping")

            self.logger.info("Service shutdown complete")

        except Exception as e:
            self.logger.error(f"Error during shutdown: {e}")

    def status(self) -> Dict:
        """Get service status"""
        return {
            'service': self.config["service"]["name"],
            'status': 'running' if not self.shutdown_requested else 'stopping',
            'uptime': time.time(),  # Simplified
            'components': list(self.services.keys()),
            'resource_status': self.resource_manager.get_metrics_summary() if self.resource_manager else None,
            'config_path': self.config_path
        }

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="OOS Service Manager")
    parser.add_argument("--config", default="data/oos_config.json", help="Configuration file path")
    parser.add_argument("--status", action="store_true", help="Show service status")
    parser.add_argument("--test", action="store_true", help="Run in test mode")

    args = parser.parse_args()

    service = OOSServiceManager(args.config)

    if args.status:
        status = service.status()
        print(json.dumps(status, indent=2, default=str))
        return 0
    elif args.test:
        print("Testing service configuration...")
        print(f"Config loaded from: {args.config}")
        print(f"SystemD available: {SYSTEMD_AVAILABLE}")

        # Test health check
        health_ok = service._health_check()
        print(f"Health check: {'✓' if health_ok else '✗'}")

        print("Test completed")
        return 0
    else:
        # Run service
        return service.start()

if __name__ == "__main__":
    sys.exit(main())