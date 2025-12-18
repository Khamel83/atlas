#!/bin/bash

# Atlas v4 Deployment Script
# Sets up production environment and services

set -euo pipefail

# Configuration
ATLAS_HOME="/opt/atlas"
ATLAS_USER="atlas"
ATLAS_GROUP="atlas"
SERVICE_FILES="atlas-ingest.service atlas-bot.service atlas-monitor.service"
PYTHON_VERSION="3.11"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

warn() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING: $1${NC}"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR: $1${NC}"
    exit 1
}

info() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')] INFO: $1${NC}"
}

# Check if running as root
check_root() {
    if [[ $EUID -ne 0 ]]; then
        error "This script must be run as root (use sudo)"
    fi
}

# Check prerequisites
check_prerequisites() {
    log "Checking prerequisites..."

    # Check if Python 3.11+ is available
    if ! command -v python${PYTHON_VERSION} &> /dev/null; then
        error "Python ${PYTHON_VERSION} is required but not installed"
    fi

    # Check if systemd is available
    if ! command -v systemctl &> /dev/null; then
        error "systemd is required but not available"
    fi

    # Check if git is available
    if ! command -v git &> /dev/null; then
        error "git is required but not installed"
    fi

    log "Prerequisites check passed"
}

# Create Atlas user
create_user() {
    log "Creating Atlas user..."

    if ! id "$ATLAS_USER" &>/dev/null; then
        useradd --system --home-dir "$ATLAS_HOME" --shell /bin/bash "$ATLAS_USER"
        log "Created user: $ATLAS_USER"
    else
        info "User $ATLAS_USER already exists"
    fi

    # Create group if not exists
    if ! getent group "$ATLAS_GROUP" &>/dev/null; then
        groupadd "$ATLAS_GROUP"
        log "Created group: $ATLAS_GROUP"
    fi

    # Add user to group
    usermod -a -G "$ATLAS_GROUP" "$ATLAS_USER"
}

# Create directory structure
create_directories() {
    log "Creating directory structure..."

    # Main directories
    mkdir -p "$ATLAS_HOME"/{src,config,data,logs,vault,monitoring,scripts}

    # Data subdirectories
    mkdir -p "$ATLAS_HOME"/data/{queue,registry,cache}

    # Log subdirectories
    mkdir -p "$ATLAS_HOME"/logs/{ingest,bot,monitor}

    # Config directories
    mkdir -p "$ATLAS_HOME"/config/{bot,ingest,monitor}

    # Monitoring directories
    mkdir -p "$ATLAS_HOME"/monitoring/{metrics,alerts,backups}

    # Set ownership
    chown -R "$ATLAS_USER:$ATLAS_GROUP" "$ATLAS_HOME"
    chmod 755 "$ATLAS_HOME"

    log "Directory structure created"
}

# Setup Python virtual environment
setup_venv() {
    log "Setting up Python virtual environment..."

    cd "$ATLAS_HOME"

    # Create virtual environment
    if [[ ! -d "venv" ]]; then
        python${PYTHON_VERSION} -m venv venv
        log "Created virtual environment"
    else
        info "Virtual environment already exists"
    fi

    # Upgrade pip
    ./venv/bin/pip install --upgrade pip

    log "Virtual environment setup complete"
}

# Install Atlas code
install_code() {
    log "Installing Atlas code..."

    # Get current directory (where this script is located)
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    SOURCE_DIR="$(dirname "$SCRIPT_DIR")"

    # Copy source code
    cp -r "$SOURCE_DIR/src" "$ATLAS_HOME/"
    cp -r "$SOURCE_DIR/scripts" "$ATLAS_HOME/"
    cp -r "$SOURCE_DIR/requirements.txt" "$ATLAS_HOME/"

    # Install dependencies
    cd "$ATLAS_HOME"
    ./venv/bin/pip install -r requirements.txt

    # Set permissions
    chown -R "$ATLAS_USER:$ATLAS_GROUP" "$ATLAS_HOME/src"
    chown -R "$ATLAS_USER:$ATLAS_GROUP" "$ATLAS_HOME/scripts"

    log "Code installation complete"
}

# Install systemd services
install_services() {
    log "Installing systemd services..."

    # Copy service files
    for service in $SERVICE_FILES; do
        cp "$SOURCE_DIR/systemd/$service" "/etc/systemd/system/"
        log "Installed service: $service"
    done

    # Reload systemd
    systemctl daemon-reload

    log "Systemd services installed"
}

# Create configuration files
create_configs() {
    log "Creating configuration files..."

    # Environment file
    cat > "$ATLAS_HOME/.env" << 'EOF'
# Atlas Environment Configuration
# Copy this file and update with your values

# Basic settings
ATLAS_CONFIG=/opt/atlas/config/production.yaml
ATLAS_LOG_LEVEL=INFO
ATLAS_VAULT=/opt/atlas/vault

# Gmail integration
GMAIL_CREDENTIALS_FILE=/opt/atlas/config/gmail-credentials.json
GMAIL_TOKEN_FILE=/opt/atlas/config/gmail-token.json

# Telegram bot
ATLAS_BOT_TOKEN=YOUR_BOT_TOKEN_HERE
ATLAS_BOT_ALLOWED_USERS=YOUR_USER_ID_HERE
ATLAS_BOT_ADMIN_CHAT=YOUR_ADMIN_CHAT_ID

# Database
ATLAS_DB_PATH=/opt/atlas/data/atlas.db

# Monitoring
ATLAS_MONITORING_ENABLED=true
ATLAS_METRICS_PATH=/opt/atlas/monitoring/metrics
EOF

    # Production config
    cat > "$ATLAS_HOME/config/production.yaml" << 'EOF'
# Atlas Production Configuration

vault:
  root: "/opt/atlas/vault"

ingestion:
  max_concurrent: 3
  rate_limit: 60  # requests per minute
  timeout: 30
  retry_attempts: 3
  retry_delay: 5  # seconds

database:
  type: "sqlite"
  path: "/opt/atlas/data/atlas.db"

logging:
  level: "INFO"
  format: "json"
  file: "/opt/atlas/logs/atlas.log"
  max_size: "100MB"
  backup_count: 5

monitoring:
  enabled: true
  metrics_path: "/opt/atlas/monitoring/metrics"
  health_check_interval: 60

rss:
  user_agent: "Atlas/4.0 (Knowledge Management Bot)"
  timeout: 30
  max_feeds: 1000

gmail:
  scopes:
    - "https://www.googleapis.com/auth/gmail.readonly"
    - "https://www.googleapis.com/auth/gmail.modify"
  batch_size: 50
  polling_interval: 300

youtube:
  api_key: "YOUR_YOUTUBE_API_KEY"
  timeout: 30
  max_concurrent: 2
EOF

    # Bot config template
    cat > "$ATLAS_HOME/config/bot.yaml" << 'EOF'
# Atlas Telegram Bot Configuration

name: "atlas-bot"
token: "${ATLAS_BOT_TOKEN}"
webhooks: false
webhook_port: 8443

allowed_users: []
allowed_chats: []

log_level: "INFO"
log_file: "/opt/atlas/logs/bot/bot.log"

vault_root: "/opt/atlas/vault"
max_inline_results: 10
rate_limit: 30

admin_chat_id: "${ATLAS_BOT_ADMIN_CHAT}"
monitoring_enabled: true
EOF

    # Set permissions
    chown -R "$ATLAS_USER:$ATLAS_GROUP" "$ATLAS_HOME/config"
    chmod 600 "$ATLAS_HOME/.env"

    log "Configuration files created"
}

# Setup log rotation
setup_logrotate() {
    log "Setting up log rotation..."

    cat > "/etc/logrotate.d/atlas" << EOF
$ATLAS_HOME/logs/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 0644 $ATLAS_USER $ATLAS_GROUP
    postrotate
        systemctl reload atlas-ingest atlas-bot atlas-monitor || true
    endscript
}

$ATLAS_HOME/logs/*/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 0644 $ATLAS_USER $ATLAS_GROUP
    postrotate
        systemctl reload atlas-ingest atlas-bot atlas-monitor || true
    endscript
}
EOF

    log "Log rotation configured"
}

# Enable services
enable_services() {
    log "Enabling systemd services..."

    for service in $SERVICE_FILES; do
        systemctl enable "$service"
        log "Enabled service: $service"
    done
}

# Create monitoring script
create_monitor_script() {
    log "Creating monitoring script..."

    cat > "$ATLAS_HOME/scripts/monitor.py" << 'EOF'
#!/usr/bin/env python3
"""
Atlas System Monitoring Script

Monitors Atlas services and provides health checks.
"""

import argparse
import asyncio
import json
import logging
import signal
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
import subprocess

# Add src to Python path
script_dir = Path(__file__).parent
src_dir = script_dir.parent / "src"
sys.path.insert(0, str(src_dir))

from atlas.logging import setup_logging


class AtlasMonitor:
    """Atlas system monitor."""

    def __init__(self, config_path: str = None):
        self.logger = logging.getLogger(f"atlas.{self.__class__.__name__}")
        self.running = False
        self.config_path = config_path

    def setup_logging(self, level: str = "INFO"):
        """Setup monitoring logging."""
        setup_logging(level=level, enable_console=True)

    def check_service_status(self, service_name: str) -> dict:
        """Check systemd service status."""
        try:
            result = subprocess.run(
                ["systemctl", "is-active", service_name],
                capture_output=True,
                text=True,
                timeout=5
            )

            return {
                "name": service_name,
                "status": result.stdout.strip(),
                "active": result.returncode == 0,
                "timestamp": datetime.utcnow().isoformat()
            }
        except Exception as e:
            return {
                "name": service_name,
                "status": "error",
                "error": str(e),
                "active": False,
                "timestamp": datetime.utcnow().isoformat()
            }

    def check_disk_space(self, path: str = "/opt/atlas") -> dict:
        """Check disk space usage."""
        try:
            stat = Path(path).statvfs(path)
            total = stat.f_frsize * stat.f_blocks
            free = stat.f_frsize * stat.f_bavail
            used = total - free
            usage_percent = (used / total) * 100

            return {
                "path": path,
                "total_gb": round(total / (1024**3), 2),
                "free_gb": round(free / (1024**3), 2),
                "used_gb": round(used / (1024**3), 2),
                "usage_percent": round(usage_percent, 2),
                "timestamp": datetime.utcnow().isoformat()
            }
        except Exception as e:
            return {
                "path": path,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }

    def check_database_health(self, db_path: str = "/opt/atlas/data/atlas.db") -> dict:
        """Check database health."""
        try:
            if not Path(db_path).exists():
                return {
                    "path": db_path,
                    "status": "missing",
                    "timestamp": datetime.utcnow().isoformat()
                }

            # Basic connectivity check
            import sqlite3
            conn = sqlite3.connect(db_path, timeout=5)
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'")
            table_count = cursor.fetchone()[0]
            conn.close()

            return {
                "path": db_path,
                "status": "healthy",
                "table_count": table_count,
                "timestamp": datetime.utcnow().isoformat()
            }
        except Exception as e:
            return {
                "path": db_path,
                "status": "error",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }

    def collect_metrics(self) -> dict:
        """Collect all system metrics."""
        metrics = {
            "timestamp": datetime.utcnow().isoformat(),
            "services": {},
            "system": {},
            "database": {}
        }

        # Check services
        services = ["atlas-ingest", "atlas-bot", "atlas-monitor"]
        for service in services:
            metrics["services"][service] = self.check_service_status(service)

        # Check disk space
        metrics["system"]["disk"] = self.check_disk_space()

        # Check database
        metrics["database"] = self.check_database_health()

        return metrics

    def save_metrics(self, metrics: dict, output_path: str = "/opt/atlas/monitoring/metrics"):
        """Save metrics to file."""
        try:
            output_dir = Path(output_path)
            output_dir.mkdir(parents=True, exist_ok=True)

            # Use timestamp for filename
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            filename = f"metrics_{timestamp}.json"
            output_file = output_dir / filename

            with open(output_file, 'w') as f:
                json.dump(metrics, f, indent=2)

            # Keep only last 100 files
            files = sorted(output_dir.glob("metrics_*.json"))
            for old_file in files[:-100]:
                old_file.unlink()

        except Exception as e:
            self.logger.error(f"Failed to save metrics: {e}")

    def run_health_check(self) -> dict:
        """Run comprehensive health check."""
        metrics = self.collect_metrics()

        # Determine overall health
        services_healthy = all(
            service.get("active", False)
            for service in metrics["services"].values()
        )

        disk_ok = metrics["system"]["disk"].get("usage_percent", 100) < 90
        db_healthy = metrics["database"].get("status") == "healthy"

        overall_healthy = services_healthy and disk_ok and db_healthy

        return {
            "overall_status": "healthy" if overall_healthy else "unhealthy",
            "services_healthy": services_healthy,
            "disk_ok": disk_ok,
            "database_healthy": db_healthy,
            "metrics": metrics,
            "timestamp": datetime.utcnow().isoformat()
        }

    async def run_daemon(self, interval: int = 60):
        """Run monitoring daemon."""
        self.running = True
        self.logger.info(f"Starting Atlas monitoring daemon (interval: {interval}s)")

        while self.running:
            try:
                # Collect and save metrics
                metrics = self.collect_metrics()
                self.save_metrics(metrics)

                # Run health check
                health = self.run_health_check()

                if health["overall_status"] != "healthy":
                    self.logger.warning(f"System health check failed: {health}")

                # Sleep for interval
                await asyncio.sleep(interval)

            except Exception as e:
                self.logger.error(f"Monitoring error: {e}")
                await asyncio.sleep(min(interval, 60))

    def stop(self):
        """Stop monitoring daemon."""
        self.running = False


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Atlas System Monitor",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument(
        "--daemon",
        action="store_true",
        help="Run as daemon"
    )

    parser.add_argument(
        "--interval",
        type=int,
        default=60,
        help="Monitoring interval in seconds (default: 60)"
    )

    parser.add_argument(
        "--config",
        help="Configuration file path"
    )

    parser.add_argument(
        "--health-check",
        action="store_true",
        help="Run one-time health check"
    )

    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Log level (default: INFO)"
    )

    args = parser.parse_args()

    # Create monitor
    monitor = AtlasMonitor(args.config)
    monitor.setup_logging(args.log_level)

    # Setup signal handlers
    def signal_handler(signum, frame):
        monitor.logger.info(f"Received signal {signum}, stopping...")
        monitor.stop()

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        if args.health_check:
            # Run one-time health check
            health = monitor.run_health_check()
            print(json.dumps(health, indent=2))
            sys.exit(0 if health["overall_status"] == "healthy" else 1)

        elif args.daemon:
            # Run daemon
            await monitor.run_daemon(args.interval)

        else:
            # Default: show current status
            metrics = monitor.collect_metrics()
            print(json.dumps(metrics, indent=2))

    except KeyboardInterrupt:
        monitor.logger.info("Stopped by user")
    except Exception as e:
        monitor.logger.error(f"Monitor failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
EOF

    chmod +x "$ATLAS_HOME/scripts/monitor.py"
    chown "$ATLAS_USER:$ATLAS_GROUP" "$ATLAS_HOME/scripts/monitor.py"

    log "Monitoring script created"
}

# Print deployment summary
print_summary() {
    log "Deployment completed successfully!"
    echo
    info "Atlas v4 has been deployed to: $ATLAS_HOME"
    echo
    warn "Next steps:"
    echo "1. Update $ATLAS_HOME/.env with your configuration values"
    echo "2. Set up Gmail credentials in $ATLAS_HOME/config/"
    echo "3. Configure Telegram bot token in $ATLAS_HOME/.env"
    echo "4. Start services: systemctl start atlas-ingest atlas-bot atlas-monitor"
    echo "5. Check status: systemctl status atlas-ingest atlas-bot atlas-monitor"
    echo
    info "Service commands:"
    echo "  Start:   systemctl start atlas-ingest"
    echo "  Stop:    systemctl stop atlas-ingest"
    echo "  Restart: systemctl restart atlas-ingest"
    echo "  Status:  systemctl status atlas-ingest"
    echo "  Logs:    journalctl -u atlas-ingest -f"
    echo
    info "Configuration files:"
    echo "  Main:    $ATLAS_HOME/config/production.yaml"
    echo "  Bot:     $ATLAS_HOME/config/bot.yaml"
    echo "  Env:     $ATLAS_HOME/.env"
    echo
    info "Monitoring:"
    echo "  Health check: $ATLAS_HOME/scripts/monitor.py --health-check"
    echo "  Metrics:      $ATLAS_HOME/monitoring/metrics/"
}

# Main deployment function
main() {
    log "Starting Atlas v4 deployment..."

    check_root
    check_prerequisites
    create_user
    create_directories
    setup_venv
    install_code
    install_services
    create_configs
    setup_logrotate
    enable_services
    create_monitor_script

    print_summary
}

# Run main function
main "$@"