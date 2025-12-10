#!/usr/bin/env python3
"""
Atlas Service Manager
Monitor and manage Atlas processing service
"""

import os
import sys
import time
import subprocess
import signal
from datetime import datetime
from pathlib import Path

class AtlasServiceManager:
    def __init__(self):
        self.project_dir = Path(__file__).parent
        self.pid_file = self.project_dir / "atlas.pid"
        self.log_file = self.project_dir / "logs" / "atlas_processing.log"

    def is_running(self):
        """Check if Atlas service is running"""
        if not self.pid_file.exists():
            return False

        try:
            with open(self.pid_file, 'r') as f:
                pid = int(f.read().strip())
            # Check if process is still running
            os.kill(pid, 0)
            return True
        except (OSError, ValueError):
            return False

    def start(self):
        """Start Atlas service"""
        if self.is_running():
            print("✅ Atlas is already running")
            return True

        print("🚀 Starting Atlas service...")

        # Load environment
        env_file = self.project_dir / ".env"
        if env_file.exists():
            with open(env_file) as f:
                for line in f:
                    if line.strip() and not line.startswith('#'):
                        key, value = line.strip().split('=', 1)
                        os.environ[key] = value

        if not os.environ.get('GITHUB_TOKEN'):
            print("❌ GITHUB_TOKEN not found in environment")
            return False

        # Start Atlas orchestrator
        try:
            cmd = [sys.executable, str(self.project_dir / "atlas_orchestrator.py")]
            with open(self.log_file, 'a') as log:
                process = subprocess.Popen(
                    cmd,
                    stdout=log,
                    stderr=subprocess.STDOUT,
                    cwd=self.project_dir,
                    env=os.environ
                )

            with open(self.pid_file, 'w') as f:
                f.write(str(process.pid))

            print(f"✅ Atlas started with PID: {process.pid}")
            return True

        except Exception as e:
            print(f"❌ Failed to start Atlas: {e}")
            return False

    def stop(self):
        """Stop Atlas service"""
        if not self.is_running():
            print("ℹ️ Atlas is not running")
            return True

        try:
            with open(self.pid_file, 'r') as f:
                pid = int(f.read().strip())

            os.kill(pid, signal.SIGTERM)

            # Wait for process to stop
            for _ in range(10):
                if not self.is_running():
                    break
                time.sleep(1)

            if self.is_running():
                os.kill(pid, signal.SIGKILL)

            self.pid_file.unlink(missing_ok=True)
            print("✅ Atlas stopped")
            return True

        except Exception as e:
            print(f"❌ Failed to stop Atlas: {e}")
            return False

    def status(self):
        """Check Atlas service status"""
        if self.is_running():
            with open(self.pid_file, 'r') as f:
                pid = int(f.read().strip())
            print(f"✅ Atlas is running (PID: {pid})")
            print(f"📊 Log file: {self.log_file}")
        else:
            print("❌ Atlas is not running")

        # Check recent processing
        try:
            from src.atlas_data_provider import AtlasDataProvider
            provider = AtlasDataProvider()
            stats = provider.get_stats()
            print(f"📊 Episodes pending: {stats.get('pending', 0)}")
            print(f"✅ Episodes completed: {stats.get('completed', 0)}")
        except Exception as e:
            print(f"⚠️ Could not fetch stats: {e}")

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 atlas_service_manager.py [start|stop|restart|status]")
        sys.exit(1)

    manager = AtlasServiceManager()
    command = sys.argv[1].lower()

    if command == "start":
        success = manager.start()
        sys.exit(0 if success else 1)
    elif command == "stop":
        success = manager.stop()
        sys.exit(0 if success else 1)
    elif command == "restart":
        manager.stop()
        time.sleep(2)
        success = manager.start()
        sys.exit(0 if success else 1)
    elif command == "status":
        manager.status()
    else:
        print("Unknown command:", command)
        sys.exit(1)

if __name__ == "__main__":
    main()