#!/usr/bin/env python3
"""
Bulletproof Watchdog Service
Monitors Atlas services and ensures they stay healthy
"""
import time
import psutil
import logging
import threading
from pathlib import Path
from helpers.bulletproof_process_manager import get_manager

class AtlasWatchdog:
    def __init__(self, check_interval=30):
        self.check_interval = check_interval
        self.running = False
        self.services_to_monitor = [
            'atlas_background_service.py',
            'atlas_service_manager.py'
        ]

    def start(self):
        """Start the watchdog"""
        if self.running:
            return

        self.running = True
        thread = threading.Thread(target=self._monitor_loop, daemon=True)
        thread.start()
        logging.info("🐕 Atlas watchdog started")

    def _monitor_loop(self):
        """Main monitoring loop"""
        while self.running:
            try:
                self._check_services()
                self._check_resources()
                time.sleep(self.check_interval)
            except Exception as e:
                logging.error(f"Watchdog error: {e}")

    def _check_services(self):
        """Check if required services are running"""
        manager = get_manager()
        status = manager.get_status()

        if status['total_processes'] == 0:
            logging.warning("🚨 No processes running, may need to restart services")

        # Check for failed circuit breakers
        for name, cb_status in status['circuit_breakers'].items():
            if cb_status['state'] == 'OPEN':
                logging.error(f"🔴 Circuit breaker OPENED for {name}")

    def _check_resources(self):
        """Check system resources"""
        # Memory check
        memory = psutil.virtual_memory()
        if memory.percent > 95:
            logging.error(f"🚨 Critical memory usage: {memory.percent}%")

        # Disk check
        disk = psutil.disk_usage('/')
        free_gb = disk.free / (1024**3)
        if free_gb < 1.0:
            logging.error(f"🚨 Critical disk space: {free_gb:.1f}GB")

if __name__ == "__main__":
    watchdog = AtlasWatchdog()
    watchdog.start()

    try:
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        watchdog.running = False
