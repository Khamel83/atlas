#!/usr/bin/env python3
"""
Atlas Service Status API

This script provides a simple HTTP API to check service status.
"""

from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import subprocess
from datetime import datetime


class StatusHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/status":
            self.send_status()
        else:
            self.send_404()

    def send_status(self):
        """Send service status as JSON"""
        try:
            # Get service status
            status = self.get_service_status()

            # Send response
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()

            response = json.dumps(
                {"timestamp": datetime.now().isoformat(), "status": status}
            )

            self.wfile.write(response.encode("utf-8"))

        except Exception as e:
            self.send_error(587, f"Error getting status: {str(e)}")

    def send_404(self):
        """Send 404 Not Found response"""
        self.send_response(404)
        self.end_headers()
        self.wfile.write(b"Endpoint not found. Available: /status")

    def get_service_status(self):
        """Get status of all services"""
        services = {
            "atlas": {"type": "systemd"},
            "prometheus": {"type": "systemd"},
            "grafana-server": {"type": "systemd"},
            "nginx": {"type": "systemd"},
        }

        status = {}

        for service_name, service_info in services.items():
            try:
                if service_info["type"] == "systemd":
                    result = subprocess.run(
                        ["systemctl", "is-active", service_name],
                        capture_output=True,
                        text=True,
                    )
                    is_active = result.stdout.strip() == "active"
                else:
                    result = subprocess.run(
                        ["pgrep", "-f", service_name], capture_output=True, text=True
                    )
                    is_active = result.returncode == 0

                status[service_name] = "running" if is_active else "stopped"
            except:
                status[service_name] = "unknown"

        return status


def run_status_api(port=8080):
    """Run the status API server"""
    server_address = ("localhost", port)
    httpd = HTTPServer(server_address, StatusHandler)
    print(f"Service status API running on http://localhost:{port}/status")
    httpd.serve_forever()


if __name__ == "__main__":
    run_status_api()
