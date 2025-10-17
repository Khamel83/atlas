#!/usr/bin/env python3
"""
Atlas Metrics Exporter for Prometheus

This script creates a Prometheus metrics exporter for Atlas application metrics.
It exposes key performance indicators and system health metrics for monitoring.

Features:
- Exports Atlas processing statistics
- Exposes system health metrics
- Integrates with existing Atlas background service
- Provides metrics in Prometheus format
"""

import json
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import sqlite3
import os
import subprocess
from datetime import datetime, timedelta
from helpers.bulletproof_process_manager import create_managed_process


class AtlasMetricsExporter(BaseHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        # Initialize database connection
        self.db_path = (
            "/home/ubuntu/dev/atlas/atlas.db"  # Default path, can be configured
        )
        super().__init__(*args, **kwargs)

    def do_GET(self):
        """Handle GET requests for metrics endpoint"""
        if self.path == "/metrics":
            self.send_metrics()
        elif self.path == "/health":
            self.send_health_check()
        else:
            self.send_404()

    def send_metrics(self):
        """Send Prometheus formatted metrics"""
        try:
            # Collect metrics
            metrics = self.collect_metrics()

            # Format metrics
            response = self.format_metrics(metrics)

            # Send response
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.end_headers()
            self.wfile.write(response.encode("utf-8"))

        except Exception as e:
            print(f"Error collecting metrics: {str(e)}")
            self.send_error(500, f"Error collecting metrics: {str(e)}")

    def send_health_check(self):
        """Send health check response"""
        try:
            health_status = self.check_health()

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()

            response = json.dumps(
                {
                    "status": "healthy" if health_status else "unhealthy",
                    "timestamp": datetime.now().isoformat(),
                    "checks": {
                        "database": self.check_database(),
                        "disk_space": self.check_disk_space(),
                        "background_service": self.check_background_service(),
                    },
                }
            )

            self.wfile.write(response.encode("utf-8"))

        except Exception as e:
            print(f"Error checking health: {str(e)}")
            self.send_error(500, f"Error checking health: {str(e)}")

    def send_404(self):
        """Send 404 Not Found response"""
        self.send_response(404)
        self.end_headers()
        self.wfile.write(b"Endpoint not found. Available endpoints: /metrics, /health")

    def collect_metrics(self):
        """Collect all Atlas metrics"""
        metrics = {}

        # Collect article processing metrics
        article_metrics = self.get_article_metrics()
        metrics.update(article_metrics)

        # Collect podcast metrics
        podcast_metrics = self.get_podcast_metrics()
        metrics.update(podcast_metrics)

        # Collect YouTube metrics
        youtube_metrics = self.get_youtube_metrics()
        metrics.update(youtube_metrics)

        # Collect system metrics
        system_metrics = self.get_system_metrics()
        metrics.update(system_metrics)

        # Collect queue metrics
        queue_metrics = self.get_queue_metrics()
        metrics.update(queue_metrics)

        return metrics

    def get_article_metrics(self):
        """Get article processing metrics from database"""
        metrics = {}

        try:
            if os.path.exists(self.db_path):
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()

                # Get total articles processed
                cursor.execute(
                    "SELECT COUNT(*) FROM articles WHERE status = 'processed'"
                )
                total_processed = cursor.fetchone()[0] or 0

                cursor.execute("SELECT COUNT(*) FROM articles WHERE status = 'failed'")
                total_failed = cursor.fetchone()[0] or 0

                # Get recent articles (last 24 hours)
                since = datetime.now() - timedelta(hours=24)
                cursor.execute(
                    "SELECT COUNT(*) FROM articles WHERE status = 'processed' AND processed_at > ?",
                    (since.isoformat(),),
                )
                recent_processed = cursor.fetchone()[0] or 0

                cursor.execute(
                    "SELECT COUNT(*) FROM articles WHERE status = 'failed' AND processed_at > ?",
                    (since.isoformat(),),
                )
                recent_failed = cursor.fetchone()[0] or 0

                conn.close()

                metrics["atlas_articles_processed_total"] = {
                    "type": "counter",
                    "help": "Total number of articles processed",
                    "values": [
                        {"labels": {"status": "success"}, "value": total_processed},
                        {"labels": {"status": "failed"}, "value": total_failed},
                    ],
                }

                metrics["atlas_articles_processed_24h"] = {
                    "type": "gauge",
                    "help": "Articles processed in the last 24 hours",
                    "values": [
                        {"labels": {"status": "success"}, "value": recent_processed},
                        {"labels": {"status": "failed"}, "value": recent_failed},
                    ],
                }
            else:
                # Initialize with zero values if database doesn't exist
                metrics["atlas_articles_processed_total"] = {
                    "type": "counter",
                    "help": "Total number of articles processed",
                    "values": [
                        {"labels": {"status": "success"}, "value": 0},
                        {"labels": {"status": "failed"}, "value": 0},
                    ],
                }

                metrics["atlas_articles_processed_24h"] = {
                    "type": "gauge",
                    "help": "Articles processed in the last 24 hours",
                    "values": [
                        {"labels": {"status": "success"}, "value": 0},
                        {"labels": {"status": "failed"}, "value": 0},
                    ],
                }

        except Exception as e:
            print(f"Error getting article metrics: {str(e)}")
            # Return zero values on error
            metrics["atlas_articles_processed_total"] = {
                "type": "counter",
                "help": "Total number of articles processed",
                "values": [
                    {"labels": {"status": "success"}, "value": 0},
                    {"labels": {"status": "failed"}, "value": 0},
                ],
            }

        return metrics

    def get_podcast_metrics(self):
        """Get podcast processing metrics"""
        metrics = {}

        try:
            if os.path.exists(self.db_path):
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()

                # Get total podcasts processed
                cursor.execute(
                    "SELECT COUNT(*) FROM podcasts WHERE status = 'downloaded'"
                )
                total_downloaded = cursor.fetchone()[0] or 0

                cursor.execute("SELECT COUNT(*) FROM podcasts WHERE status = 'failed'")
                total_failed = cursor.fetchone()[0] or 0

                conn.close()

                metrics["atlas_podcasts_downloaded_total"] = {
                    "type": "counter",
                    "help": "Total number of podcasts downloaded",
                    "values": [
                        {"labels": {"status": "success"}, "value": total_downloaded},
                        {"labels": {"status": "failed"}, "value": total_failed},
                    ],
                }
            else:
                metrics["atlas_podcasts_downloaded_total"] = {
                    "type": "counter",
                    "help": "Total number of podcasts downloaded",
                    "values": [
                        {"labels": {"status": "success"}, "value": 0},
                        {"labels": {"status": "failed"}, "value": 0},
                    ],
                }

        except Exception as e:
            print(f"Error getting podcast metrics: {str(e)}")
            metrics["atlas_podcasts_downloaded_total"] = {
                "type": "counter",
                "help": "Total number of podcasts downloaded",
                "values": [
                    {"labels": {"status": "success"}, "value": 0},
                    {"labels": {"status": "failed"}, "value": 0},
                ],
            }

        return metrics

    def get_youtube_metrics(self):
        """Get YouTube processing metrics"""
        metrics = {}

        try:
            if os.path.exists(self.db_path):
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()

                # Get total YouTube videos processed
                cursor.execute(
                    "SELECT COUNT(*) FROM youtube_videos WHERE status = 'processed'"
                )
                total_processed = cursor.fetchone()[0] or 0

                cursor.execute(
                    "SELECT COUNT(*) FROM youtube_videos WHERE status = 'failed'"
                )
                total_failed = cursor.fetchone()[0] or 0

                conn.close()

                metrics["atlas_youtube_videos_processed_total"] = {
                    "type": "counter",
                    "help": "Total number of YouTube videos processed",
                    "values": [
                        {"labels": {"status": "success"}, "value": total_processed},
                        {"labels": {"status": "failed"}, "value": total_failed},
                    ],
                }
            else:
                metrics["atlas_youtube_videos_processed_total"] = {
                    "type": "counter",
                    "help": "Total number of YouTube videos processed",
                    "values": [
                        {"labels": {"status": "success"}, "value": 0},
                        {"labels": {"status": "failed"}, "value": 0},
                    ],
                }

        except Exception as e:
            print(f"Error getting YouTube metrics: {str(e)}")
            metrics["atlas_youtube_videos_processed_total"] = {
                "type": "counter",
                "help": "Total number of YouTube videos processed",
                "values": [
                    {"labels": {"status": "success"}, "value": 0},
                    {"labels": {"status": "failed"}, "value": 0},
                ],
            }

        return metrics

    def get_system_metrics(self):
        """Get system health metrics"""
        metrics = {}

        try:
            # Get disk usage
            process = create_managed_process(["df", "/"], "get_disk_usage")
            stdout, stderr = process.communicate()
            df_result_stdout = stdout.decode('utf-8')
            if process.returncode == 0:
                lines = df_result_stdout.strip().split("\n")
                if len(lines) > 1:
                    usage_info = lines[1].split()
                    disk_usage_percent = int(usage_info[4].rstrip("%"))

                    metrics["atlas_system_disk_usage_percent"] = {
                        "type": "gauge",
                        "help": "System disk usage percentage",
                        "values": [{"labels": {}, "value": disk_usage_percent}],
                    }

            # Get memory usage
            process = create_managed_process(["free"], "get_memory_usage")
            stdout, stderr = process.communicate()
            free_result_stdout = stdout.decode('utf-8')
            if process.returncode == 0:
                lines = free_result_stdout.strip().split("\n")
                if len(lines) > 1:
                    # Parse memory line (line 2)
                    mem_info = lines[1].split()
                    if len(mem_info) >= 7:
                        total_mem = int(mem_info[1])
                        avail_mem = int(mem_info[6])
                        mem_usage_percent = int(
                            ((total_mem - avail_mem) / total_mem) * 100
                        )

                        metrics["atlas_system_memory_usage_percent"] = {
                            "type": "gauge",
                            "help": "System memory usage percentage",
                            "values": [{"labels": {}, "value": mem_usage_percent}],
                        }

            # System health status (1=healthy, 0=unhealthy)
            health_status = 1 if self.check_health() else 0
            metrics["atlas_system_health_status"] = {
                "type": "gauge",
                "help": "System health status (1=healthy, 0=unhealthy)",
                "values": [{"labels": {}, "value": health_status}],
            }

        except Exception as e:
            print(f"Error getting system metrics: {str(e)}")

        return metrics

    def get_queue_metrics(self):
        """Get content processing queue metrics"""
        metrics = {}

        try:
            # For now, we'll simulate queue metrics
            # In a real implementation, this would query the actual queue

            # Simulate queue length
            queue_length = 0

            if os.path.exists(self.db_path):
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()

                # Count articles that are pending processing
                cursor.execute("SELECT COUNT(*) FROM articles WHERE status = 'pending'")
                queue_length = cursor.fetchone()[0] or 0

                conn.close()

            metrics["atlas_processing_queue_length"] = {
                "type": "gauge",
                "help": "Current length of processing queue",
                "values": [{"labels": {}, "value": queue_length}],
            }

        except Exception as e:
            print(f"Error getting queue metrics: {str(e)}")
            metrics["atlas_processing_queue_length"] = {
                "type": "gauge",
                "help": "Current length of processing queue",
                "values": [{"labels": {}, "value": 0}],
            }

        return metrics

    def format_metrics(self, metrics):
        """Format metrics in Prometheus exposition format"""
        output = []

        for name, metric in metrics.items():
            # Add help text
            output.append(f"# HELP {name} {metric['help']}")

            # Add type
            output.append(f"# TYPE {name} {metric['type']}")

            # Add values
            for value_entry in metric["values"]:
                labels = value_entry.get("labels", {})
                value = value_entry["value"]

                # Format labels
                if labels:
                    label_str = ",".join([f'{k}="{v}"' for k, v in labels.items()])
                    output.append(f"{name}{{{label_str}}} {value}")
                else:
                    output.append(f"{name} {value}")

            output.append("")  # Empty line between metrics

        return "\n".join(output)

    def check_health(self):
        """Perform overall health check"""
        checks = [
            self.check_database(),
            self.check_disk_space(),
            self.check_background_service(),
        ]

        return all(checks)

    def check_database(self):
        """Check if database is accessible"""
        try:
            if os.path.exists(self.db_path):
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                cursor.execute("SELECT 1")
                conn.close()
                return True
            return False
        except:
            return False

    def check_disk_space(self):
        """Check if disk space is sufficient"""
        try:
            process = create_managed_process(["df", "/"], "check_disk_space")
            stdout, stderr = process.communicate()
            df_result_stdout = stdout.decode('utf-8')
            if process.returncode == 0:
                lines = df_result_stdout.strip().split("\n")
                if len(lines) > 1:
                    usage_info = lines[1].split()
                    usage_percent = int(usage_info[4].rstrip("%"))
                    return usage_percent < 95  # Healthy if less than 95% usage
            return False
        except:
            return False

    def check_background_service(self):
        """Check if Atlas background service is running"""
        try:
            # Check if the background service process is running
            process = create_managed_process(
                ["pgrep", "-f", "atlas_background"], "check_background_service"
            )
            stdout, stderr = process.communicate()
            return process.returncode == 0
        except:
            return False


def run_metrics_server(port=8000):
    """Run the metrics server"""
    server_address = ("localhost", port)
    httpd = HTTPServer(server_address, AtlasMetricsExporter)
    print(f"Atlas metrics exporter running on http://localhost:{port}/metrics")
    print(f"Health check endpoint: http://localhost:{port}/health")
    httpd.serve_forever()


if __name__ == "__main__":
    run_metrics_server()
