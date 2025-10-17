#!/usr/bin/env python3
"""
Grafana Configuration for Atlas Monitoring System

This script automates the installation and configuration of Grafana
on an OCI VM for visualizing Atlas system and application metrics.

Features:
- Grafana server installation
- Pre-configured dashboards for Atlas monitoring
- Systemd service configuration
- Admin user setup with basic authentication
"""

import os
import subprocess
import sys
import json
from helpers.bulletproof_process_manager import create_managed_process


def run_command(cmd, description=""):
    """Run a shell command with error handling"""
    try:
        print(f"Executing: {description}")
        process = create_managed_process(
            cmd, description, shell=True, capture_output=True, text=True
        )
        stdout, stderr = process.communicate()
        if process.returncode != 0:
            raise subprocess.CalledProcessError(process.returncode, process.args, output=stdout, stderr=stderr)
        print(f"Success: {description}")
        return stdout
    except subprocess.CalledProcessError as e:
        print(f"Error executing: {description}")
        print(f"Error: {e.stderr}")
        sys.exit(1)
    except Exception as e:
        print(f"Error executing: {description}")
        print(f"Error: {e}")
        sys.exit(1)


def install_grafana():
    """Install Grafana server"""
    print("Installing Grafana...")

    # Add Grafana repository
    run_command(
        "wget -q -O - https://packages.grafana.com/gpg.key | sudo apt-key add -",
        "Adding Grafana GPG key",
    )
    run_command(
        'sudo add-apt-repository "deb https://packages.grafana.com/oss/deb stable main"',
        "Adding Grafana repository",
    )

    # Install Grafana
    run_command("sudo apt-get update", "Updating package list")
    run_command("sudo apt-get install -y grafana", "Installing Grafana")

    print("Grafana installed successfully")


def configure_grafana():
    """Configure Grafana for Atlas monitoring"""
    print("Configuring Grafana...")

    # Create grafana.ini configuration
    grafana_ini = """
[server]
http_addr = 0.0.0.0
http_port = 3000
domain = localhost
enforce_domain = false
root_url = %(protocol)s://%(domain)s:%(http_port)s/
router_logging = false
static_root_path = public
enable_gzip = true
cert_file =
key_file =

[database]
type = sqlite3
host = 127.0.0.1:3306
name = grafana
user = root
password =
url =
ssl_mode = disable

[session]
provider = file
provider_config = sessions
cookie_name = grafana_sess
cookie_secure = false
session_life_time = 86400

[analytics]
reporting_enabled = false
check_for_updates = true

[security]
admin_user = admin
admin_password = admin
secret_key = SW2YcwTIb9zpOOhoPsMm
login_remember_days = 7
cookie_username = grafana_user
cookie_remember_name = grafana_remember
disable_gravatar = false
data_source_proxy_whitelist =

[snapshots]
external_enabled = true
external_snapshot_url = https://snapshots.raintank.io
external_snapshot_name = Publish to snapshot.raintank.io

[users]
allow_sign_up = false
allow_org_create = false
auto_assign_org = true
auto_assign_org_role = Viewer
verify_email_enabled = false
login_hint = email or username
default_theme = dark

[auth]
disable_login_form = false
disable_signout_menu = false

[auth.anonymous]
enabled = false

[auth.basic]
enabled = true

[auth.proxy]
enabled = false

[log]
mode = console file
level = info

[log.console]
level = info
format = console

[log.file]
level = info
format = text
log_rotate = true
max_lines = 1000000
max_size_shift = 28
daily_rotate = true
max_days = 7

[paths]
data = /var/lib/grafana
logs = /var/log/grafana
plugins = /var/lib/grafana/plugins
provisioning = /etc/grafana/provisioning
"""

    with open("/tmp/grafana.ini", "w") as f:
        f.write(grafana_ini)

    run_command(
        "sudo cp /tmp/grafana.ini /etc/grafana/grafana.ini",
        "Copying Grafana configuration",
    )
    run_command(
        "sudo chown grafana:grafana /etc/grafana/grafana.ini",
        "Setting config ownership",
    )
    run_command("sudo chmod 600 /etc/grafana/grafana.ini", "Setting config permissions")

    print("Grafana configured successfully")


def create_dashboards():
    """Create pre-configured dashboards for Atlas monitoring"""
    print("Creating Grafana dashboards...")

    # Create provisioning directory structure
    run_command(
        "sudo mkdir -p /etc/grafana/provisioning/datasources",
        "Creating datasources directory",
    )
    run_command(
        "sudo mkdir -p /etc/grafana/provisioning/dashboards",
        "Creating dashboards directory",
    )

    # Create datasource configuration
    datasource_config = """
apiVersion: 1

datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    url: http://localhost:9090
    isDefault: true
    editable: true
"""

    with open("/tmp/prometheus_datasource.yml", "w") as f:
        f.write(datasource_config)

    run_command(
        "sudo cp /tmp/prometheus_datasource.yml /etc/grafana/provisioning/datasources/prometheus.yml",
        "Installing datasource configuration",
    )

    # Create dashboard configuration
    dashboard_config = """
apiVersion: 1

providers:
  - name: 'Atlas Dashboards'
    orgId: 1
    folder: ''
    type: file
    disableDeletion: false
    editable: true
    options:
      path: /var/lib/grafana/dashboards
"""

    with open("/tmp/dashboard_provider.yml", "w") as f:
        f.write(dashboard_config)

    run_command(
        "sudo cp /tmp/dashboard_provider.yml /etc/grafana/provisioning/dashboards/atlas.yml",
        "Installing dashboard provider",
    )

    # Create dashboards directory
    run_command(
        "sudo mkdir -p /var/lib/grafana/dashboards", "Creating dashboards directory"
    )
    run_command(
        "sudo chown -R grafana:grafana /var/lib/grafana/dashboards",
        "Setting dashboard directory ownership",
    )

    # Create Atlas overview dashboard
    atlas_overview = {
        "dashboard": {
            "id": None,
            "title": "Atlas Overview",
            "timezone": "browser",
            "schemaVersion": 16,
            "version": 0,
            "refresh": "10s",
            "rows": [
                {
                    "panels": [
                        {
                            "id": 1,
                            "type": "graph",
                            "title": "Content Processing Rate",
                            "gridPos": {"x": 0, "y": 0, "w": 12, "h": 9},
                            "targets": [
                                {
                                    "expr": "rate(atlas_articles_processed_total[5m])",
                                    "legendFormat": "{{status}}",
                                }
                            ],
                            "yaxes": [
                                {"format": "short", "label": "Articles/second"},
                                {"format": "short"},
                            ],
                        },
                        {
                            "id": 2,
                            "type": "singlestat",
                            "title": "Processing Queue Length",
                            "gridPos": {"x": 12, "y": 0, "w": 12, "h": 9},
                            "targets": [{"expr": "atlas_processing_queue_length"}],
                            "format": "none",
                        },
                    ]
                },
                {
                    "panels": [
                        {
                            "id": 3,
                            "type": "graph",
                            "title": "System Health",
                            "gridPos": {"x": 0, "y": 9, "w": 12, "h": 9},
                            "targets": [
                                {
                                    "expr": "atlas_system_health_status",
                                    "legendFormat": "Health Status",
                                }
                            ],
                            "yaxes": [
                                {"format": "short", "label": "Status (1=Healthy)"},
                                {"format": "short"},
                            ],
                        },
                        {
                            "id": 4,
                            "type": "graph",
                            "title": "Content Type Distribution",
                            "gridPos": {"x": 12, "y": 9, "w": 12, "h": 9},
                            "targets": [
                                {
                                    "expr": "atlas_articles_processed_total",
                                    "legendFormat": "Articles",
                                },
                                {
                                    "expr": "atlas_podcasts_downloaded_total",
                                    "legendFormat": "Podcasts",
                                },
                                {
                                    "expr": "atlas_youtube_videos_processed_total",
                                    "legendFormat": "YouTube Videos",
                                },
                            ],
                            "yaxes": [
                                {"format": "short", "label": "Total Count"},
                                {"format": "short"},
                            ],
                        },
                    ]
                },
            ],
        },
        "overwrite": True,
    }

    with open("/tmp/atlas_overview.json", "w") as f:
        json.dump(atlas_overview, f, indent=2)

    run_command(
        "sudo cp /tmp/atlas_overview.json /var/lib/grafana/dashboards/atlas_overview.json",
        "Installing Atlas overview dashboard",
    )

    # Create system health dashboard
    system_health = {
        "dashboard": {
            "id": None,
            "title": "System Health",
            "timezone": "browser",
            "schemaVersion": 16,
            "version": 0,
            "refresh": "10s",
            "rows": [
                {
                    "panels": [
                        {
                            "id": 1,
                            "type": "graph",
                            "title": "CPU Usage",
                            "gridPos": {"x": 0, "y": 0, "w": 12, "h": 9},
                            "targets": [
                                {
                                    "expr": '100 - (avg by (instance) (irate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)',
                                    "legendFormat": "CPU Usage %",
                                }
                            ],
                            "yaxes": [
                                {"format": "percent", "label": "CPU Usage %"},
                                {"format": "short"},
                            ],
                        },
                        {
                            "id": 2,
                            "type": "graph",
                            "title": "Memory Usage",
                            "gridPos": {"x": 12, "y": 0, "w": 12, "h": 9},
                            "targets": [
                                {
                                    "expr": "(node_memory_MemTotal_bytes - node_memory_MemAvailable_bytes) / node_memory_MemTotal_bytes * 100",
                                    "legendFormat": "Memory Usage %",
                                }
                            ],
                            "yaxes": [
                                {"format": "percent", "label": "Memory Usage %"},
                                {"format": "short"},
                            ],
                        },
                    ]
                },
                {
                    "panels": [
                        {
                            "id": 3,
                            "type": "graph",
                            "title": "Disk Usage",
                            "gridPos": {"x": 0, "y": 9, "w": 12, "h": 9},
                            "targets": [
                                {
                                    "expr": '(node_filesystem_size_bytes{mountpoint="/"} - node_filesystem_free_bytes{mountpoint="/"}) / node_filesystem_size_bytes{mountpoint="/"} * 100',
                                    "legendFormat": "Disk Usage %",
                                }
                            ],
                            "yaxes": [
                                {"format": "percent", "label": "Disk Usage %"},
                                {"format": "short"},
                            ],
                        },
                        {
                            "id": 4,
                            "type": "graph",
                            "title": "Network Traffic",
                            "gridPos": {"x": 12, "y": 9, "w": 12, "h": 9},
                            "targets": [
                                {
                                    "expr": "irate(node_network_receive_bytes_total[5m])",
                                    "legendFormat": "Received - {{device}}",
                                },
                                {
                                    "expr": "irate(node_network_transmit_bytes_total[5m])",
                                    "legendFormat": "Transmitted - {{device}}",
                                },
                            ],
                            "yaxes": [
                                {"format": "Bps", "label": "Bytes/sec"},
                                {"format": "short"},
                            ],
                        },
                    ]
                },
            ],
        },
        "overwrite": True,
    }

    with open("/tmp/system_health.json", "w") as f:
        json.dump(system_health, f, indent=2)

    run_command(
        "sudo cp /tmp/system_health.json /var/lib/grafana/dashboards/system_health.json",
        "Installing system health dashboard",
    )

    print("Grafana dashboards created successfully")


def start_services():
    """Start Grafana service"""
    print("Starting Grafana service...")

    # Enable and start Grafana service
    run_command("sudo systemctl daemon-reload", "Reloading systemd")
    run_command("sudo systemctl enable grafana-server", "Enabling Grafana service")
    run_command("sudo systemctl start grafana-server", "Starting Grafana service")

    # Check service status
    print("\nGrafana Service Status:")
    run_command(
        "sudo systemctl status grafana-server --no-pager -l || true", "Grafana status"
    )

    print("\nGrafana service started successfully")


def main():
    """Main installation and configuration function"""
    print("Starting Grafana setup for Atlas monitoring...")

    # Install Grafana
    install_grafana()

    # Configure Grafana
    configure_grafana()

    # Create dashboards
    create_dashboards()

    # Start services
    start_services()

    print("\nGrafana setup completed successfully!")
    print("Grafana is now running and monitoring:")
    print("- Access the dashboard at http://localhost:3000")
    print("- Default login: admin/admin (please change after first login)")
    print("- Pre-configured dashboards for Atlas and system metrics")
    print("\nServices are configured to auto-start on boot")


if __name__ == "__main__":
    main()
