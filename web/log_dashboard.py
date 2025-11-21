#!/usr/bin/env python3
"""
Atlas Log Dashboard
Web interface for viewing and analyzing Atlas system logs with real-time updates and filtering.
"""

import os
import sys
import json
import sqlite3
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from helpers.logging_config import get_logger
from helpers.database_config import get_database_connection

@dataclass
class LogEntry:
    """Structured log entry for display."""
    timestamp: str
    level: str
    component: str
    message: str
    details: Optional[Dict[str, Any]] = None
    performance_metrics: Optional[Dict[str, Any]] = None

class LogDashboard:
    """Log viewing and analysis dashboard."""

    def __init__(self):
        self.logger = get_logger("log_dashboard")

        # Use same log directory logic as logging_config
        try:
            self.log_dir = Path("/var/log/atlas")
            self.log_dir.mkdir(exist_ok=True, parents=True)
        except PermissionError:
            self.log_dir = Path("logs") / "atlas"
            self.log_dir.mkdir(exist_ok=True, parents=True)

        self.log_db_path = self.log_dir / "log_index.db"
        self.setup_log_database()

    def setup_log_database(self):
        """Setup SQLite database for log indexing."""
        try:
            self.log_dir.mkdir(exist_ok=True, parents=True)

            conn = sqlite3.connect(self.log_db_path)
            cursor = conn.cursor()

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS log_entries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    level TEXT NOT NULL,
                    component TEXT NOT NULL,
                    message TEXT NOT NULL,
                    details TEXT,
                    performance_metrics TEXT,
                    log_file TEXT NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Create indexes separately
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON log_entries(timestamp)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_level ON log_entries(level)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_component ON log_entries(component)")

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS error_patterns (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    pattern TEXT NOT NULL,
                    count INTEGER DEFAULT 1,
                    first_seen DATETIME DEFAULT CURRENT_TIMESTAMP,
                    last_seen DATETIME DEFAULT CURRENT_TIMESTAMP,
                    severity TEXT DEFAULT 'medium'
                )
            """)

            conn.commit()
            conn.close()

        except Exception as e:
            self.logger.error(f"Failed to setup log database: {e}")

    def index_log_files(self):
        """Index JSON log files into database for fast searching."""
        try:
            conn = sqlite3.connect(self.log_db_path)
            cursor = conn.cursor()

            # Get last indexed timestamp
            cursor.execute("SELECT MAX(timestamp) FROM log_entries")
            last_indexed = cursor.fetchone()[0]

            indexed_count = 0

            for log_file in self.log_dir.glob("*.json.log"):
                with open(log_file, 'r') as f:
                    for line_num, line in enumerate(f, 1):
                        try:
                            log_data = json.loads(line.strip())

                            # Skip if already indexed
                            if last_indexed and log_data.get('timestamp', '') <= last_indexed:
                                continue

                            cursor.execute("""
                                INSERT INTO log_entries
                                (timestamp, level, component, message, details, performance_metrics, log_file)
                                VALUES (?, ?, ?, ?, ?, ?, ?)
                            """, (
                                log_data.get('timestamp', ''),
                                log_data.get('level', 'INFO'),
                                log_data.get('component', 'unknown'),
                                log_data.get('message', ''),
                                json.dumps(log_data.get('details')) if log_data.get('details') else None,
                                json.dumps(log_data.get('performance_metrics')) if log_data.get('performance_metrics') else None,
                                str(log_file)
                            ))
                            indexed_count += 1

                        except json.JSONDecodeError:
                            # Skip invalid JSON lines
                            continue
                        except Exception as e:
                            self.logger.error(f"Error indexing line {line_num} in {log_file}: {e}")

            conn.commit()
            conn.close()

            if indexed_count > 0:
                self.logger.info(f"Indexed {indexed_count} new log entries")

        except Exception as e:
            self.logger.error(f"Failed to index log files: {e}")

    def get_recent_logs(self, limit: int = 100, level_filter: str = None,
                       component_filter: str = None, hours_back: int = 24) -> List[LogEntry]:
        """Get recent log entries with optional filtering."""
        try:
            conn = sqlite3.connect(self.log_db_path)
            cursor = conn.cursor()

            # Build query with filters
            query = """
                SELECT timestamp, level, component, message, details, performance_metrics
                FROM log_entries
                WHERE timestamp >= datetime('now', '-{} hours')
            """.format(hours_back)

            params = []

            if level_filter:
                query += " AND level = ?"
                params.append(level_filter)

            if component_filter:
                query += " AND component = ?"
                params.append(component_filter)

            query += " ORDER BY timestamp DESC LIMIT ?"
            params.append(limit)

            cursor.execute(query, params)
            results = cursor.fetchall()

            logs = []
            for row in results:
                timestamp, level, component, message, details_json, metrics_json = row

                details = None
                if details_json:
                    try:
                        details = json.loads(details_json)
                    except json.JSONDecodeError:
                        pass

                performance_metrics = None
                if metrics_json:
                    try:
                        performance_metrics = json.loads(metrics_json)
                    except json.JSONDecodeError:
                        pass

                logs.append(LogEntry(
                    timestamp=timestamp,
                    level=level,
                    component=component,
                    message=message,
                    details=details,
                    performance_metrics=performance_metrics
                ))

            conn.close()
            return logs

        except Exception as e:
            self.logger.error(f"Failed to get recent logs: {e}")
            return []

    def get_error_summary(self, hours_back: int = 24) -> Dict[str, Any]:
        """Get error summary statistics."""
        try:
            conn = sqlite3.connect(self.log_db_path)
            cursor = conn.cursor()

            # Error counts by level
            cursor.execute("""
                SELECT level, COUNT(*) as count
                FROM log_entries
                WHERE timestamp >= datetime('now', '-{} hours')
                AND level IN ('ERROR', 'CRITICAL', 'WARNING')
                GROUP BY level
            """.format(hours_back))

            error_counts = {row[0]: row[1] for row in cursor.fetchall()}

            # Top error messages
            cursor.execute("""
                SELECT message, COUNT(*) as count
                FROM log_entries
                WHERE timestamp >= datetime('now', '-{} hours')
                AND level IN ('ERROR', 'CRITICAL')
                GROUP BY message
                ORDER BY count DESC
                LIMIT 10
            """.format(hours_back))

            top_errors = [{"message": row[0], "count": row[1]} for row in cursor.fetchall()]

            # Component error breakdown
            cursor.execute("""
                SELECT component, level, COUNT(*) as count
                FROM log_entries
                WHERE timestamp >= datetime('now', '-{} hours')
                AND level IN ('ERROR', 'CRITICAL', 'WARNING')
                GROUP BY component, level
                ORDER BY component, level
            """.format(hours_back))

            component_errors = {}
            for row in cursor.fetchall():
                component, level, count = row
                if component not in component_errors:
                    component_errors[component] = {}
                component_errors[component][level] = count

            conn.close()

            return {
                "error_counts": error_counts,
                "top_errors": top_errors,
                "component_errors": component_errors,
                "total_errors": sum(error_counts.values())
            }

        except Exception as e:
            self.logger.error(f"Failed to get error summary: {e}")
            return {"error_counts": {}, "top_errors": [], "component_errors": {}, "total_errors": 0}

    def search_logs(self, search_term: str, limit: int = 100,
                   hours_back: int = 24) -> List[LogEntry]:
        """Search logs for specific terms."""
        try:
            conn = sqlite3.connect(self.log_db_path)
            cursor = conn.cursor()

            cursor.execute("""
                SELECT timestamp, level, component, message, details, performance_metrics
                FROM log_entries
                WHERE timestamp >= datetime('now', '-{} hours')
                AND (message LIKE ? OR component LIKE ?)
                ORDER BY timestamp DESC
                LIMIT ?
            """.format(hours_back), (f"%{search_term}%", f"%{search_term}%", limit))

            results = cursor.fetchall()

            logs = []
            for row in results:
                timestamp, level, component, message, details_json, metrics_json = row

                details = None
                if details_json:
                    try:
                        details = json.loads(details_json)
                    except json.JSONDecodeError:
                        pass

                performance_metrics = None
                if metrics_json:
                    try:
                        performance_metrics = json.loads(metrics_json)
                    except json.JSONDecodeError:
                        pass

                logs.append(LogEntry(
                    timestamp=timestamp,
                    level=level,
                    component=component,
                    message=message,
                    details=details,
                    performance_metrics=performance_metrics
                ))

            conn.close()
            return logs

        except Exception as e:
            self.logger.error(f"Failed to search logs: {e}")
            return []

    def get_performance_timeline(self, hours_back: int = 24) -> Dict[str, List]:
        """Get performance metrics over time."""
        try:
            conn = sqlite3.connect(self.log_db_path)
            cursor = conn.cursor()

            cursor.execute("""
                SELECT timestamp, performance_metrics
                FROM log_entries
                WHERE timestamp >= datetime('now', '-{} hours')
                AND performance_metrics IS NOT NULL
                ORDER BY timestamp
            """.format(hours_back))

            timeline = {
                "timestamps": [],
                "memory_usage": [],
                "cpu_usage": [],
                "queue_pending": []
            }

            for row in cursor.fetchall():
                timestamp, metrics_json = row

                try:
                    metrics = json.loads(metrics_json)
                    timeline["timestamps"].append(timestamp)
                    timeline["memory_usage"].append(metrics.get("memory_usage_mb", 0))
                    timeline["cpu_usage"].append(metrics.get("cpu_usage_percent", 0))
                    timeline["queue_pending"].append(metrics.get("queue_pending", 0))
                except json.JSONDecodeError:
                    continue

            conn.close()
            return timeline

        except Exception as e:
            self.logger.error(f"Failed to get performance timeline: {e}")
            return {"timestamps": [], "memory_usage": [], "cpu_usage": [], "queue_pending": []}

    def generate_html_dashboard(self) -> str:
        """Generate HTML dashboard for log viewing."""
        # Update log index first
        self.index_log_files()

        recent_logs = self.get_recent_logs(limit=50)
        error_summary = self.get_error_summary()
        performance_timeline = self.get_performance_timeline()

        html_template = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Atlas Log Dashboard</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
        }}
        .dashboard-header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 20px;
        }}
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        .stat-card {{
            background: white;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        .stat-number {{
            font-size: 2em;
            font-weight: bold;
            color: #333;
        }}
        .stat-label {{
            color: #666;
            font-size: 0.9em;
        }}
        .error {{ color: #e74c3c; }}
        .warning {{ color: #f39c12; }}
        .critical {{ color: #c0392b; }}
        .info {{ color: #3498db; }}
        .debug {{ color: #95a5a6; }}
        .log-container {{
            background: white;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            overflow: hidden;
        }}
        .log-header {{
            background: #34495e;
            color: white;
            padding: 15px 20px;
            font-weight: bold;
        }}
        .log-entry {{
            padding: 12px 20px;
            border-bottom: 1px solid #eee;
            font-family: 'Courier New', monospace;
            font-size: 0.9em;
        }}
        .log-entry:hover {{
            background-color: #f8f9fa;
        }}
        .log-timestamp {{
            color: #666;
            margin-right: 10px;
        }}
        .log-component {{
            background: #ecf0f1;
            padding: 2px 6px;
            border-radius: 3px;
            font-size: 0.8em;
            margin-right: 10px;
        }}
        .chart-container {{
            background: white;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            margin-bottom: 20px;
        }}
        .filters {{
            background: white;
            padding: 15px 20px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            margin-bottom: 20px;
        }}
        .filter-group {{
            display: inline-block;
            margin-right: 20px;
        }}
        .filter-group label {{
            display: block;
            margin-bottom: 5px;
            font-weight: bold;
        }}
        .filter-group select, .filter-group input {{
            padding: 8px;
            border: 1px solid #ddd;
            border-radius: 5px;
        }}
        .refresh-btn {{
            background: #3498db;
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 5px;
            cursor: pointer;
        }}
        .refresh-btn:hover {{
            background: #2980b9;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="dashboard-header">
            <h1>🔍 Atlas Log Dashboard</h1>
            <p>Real-time system monitoring and log analysis</p>
            <p><small>Last updated: {current_time}</small></p>
        </div>

        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-number error">{total_errors}</div>
                <div class="stat-label">Total Errors (24h)</div>
            </div>
            <div class="stat-card">
                <div class="stat-number warning">{warning_count}</div>
                <div class="stat-label">Warnings (24h)</div>
            </div>
            <div class="stat-card">
                <div class="stat-number info">{log_entries_count}</div>
                <div class="stat-label">Recent Log Entries</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{active_components}</div>
                <div class="stat-label">Active Components</div>
            </div>
        </div>

        <div class="chart-container">
            <h3>Performance Timeline (24h)</h3>
            <canvas id="performanceChart" width="400" height="100"></canvas>
        </div>

        <div class="filters">
            <div class="filter-group">
                <label for="levelFilter">Log Level:</label>
                <select id="levelFilter">
                    <option value="">All Levels</option>
                    <option value="CRITICAL">Critical</option>
                    <option value="ERROR">Error</option>
                    <option value="WARNING">Warning</option>
                    <option value="INFO">Info</option>
                    <option value="DEBUG">Debug</option>
                </select>
            </div>
            <div class="filter-group">
                <label for="componentFilter">Component:</label>
                <select id="componentFilter">
                    <option value="">All Components</option>
                    {component_options}
                </select>
            </div>
            <div class="filter-group">
                <label for="searchFilter">Search:</label>
                <input type="text" id="searchFilter" placeholder="Search logs...">
            </div>
            <button class="refresh-btn" onclick="location.reload()">🔄 Refresh</button>
        </div>

        <div class="log-container">
            <div class="log-header">Recent Log Entries</div>
            {log_entries_html}
        </div>
    </div>

    <script>
        // Performance Chart
        const ctx = document.getElementById('performanceChart').getContext('2d');
        new Chart(ctx, {{
            type: 'line',
            data: {{
                labels: {chart_labels},
                datasets: [{{
                    label: 'Memory Usage (MB)',
                    data: {memory_data},
                    borderColor: 'rgb(255, 99, 132)',
                    backgroundColor: 'rgba(255, 99, 132, 0.2)',
                    yAxisID: 'y'
                }}, {{
                    label: 'CPU Usage (%)',
                    data: {cpu_data},
                    borderColor: 'rgb(54, 162, 235)',
                    backgroundColor: 'rgba(54, 162, 235, 0.2)',
                    yAxisID: 'y1'
                }}, {{
                    label: 'Queue Pending',
                    data: {queue_data},
                    borderColor: 'rgb(255, 205, 86)',
                    backgroundColor: 'rgba(255, 205, 86, 0.2)',
                    yAxisID: 'y2'
                }}]
            }},
            options: {{
                responsive: true,
                scales: {{
                    y: {{
                        type: 'linear',
                        display: true,
                        position: 'left',
                        title: {{ display: true, text: 'Memory (MB)' }}
                    }},
                    y1: {{
                        type: 'linear',
                        display: true,
                        position: 'right',
                        title: {{ display: true, text: 'CPU (%)' }},
                        grid: {{ drawOnChartArea: false }}
                    }},
                    y2: {{
                        type: 'linear',
                        display: false,
                        position: 'right'
                    }}
                }}
            }}
        }});

        // Auto-refresh every 30 seconds
        setTimeout(() => location.reload(), 30000);
    </script>
</body>
</html>
        """

        # Generate log entries HTML
        log_entries_html = ""
        for log in recent_logs:
            level_class = log.level.lower()
            timestamp_short = log.timestamp.split('T')[1].split('.')[0] if 'T' in log.timestamp else log.timestamp

            log_entries_html += f"""
            <div class="log-entry">
                <span class="log-timestamp">{timestamp_short}</span>
                <span class="log-component">{log.component}</span>
                <span class="{level_class}">[{log.level}]</span>
                {log.message}
            </div>
            """

        # Generate component options
        components = set(log.component for log in recent_logs)
        component_options = "".join(f'<option value="{comp}">{comp}</option>' for comp in sorted(components))

        # Prepare chart data
        chart_labels = json.dumps([ts.split('T')[1].split('.')[0] for ts in performance_timeline["timestamps"][-20:]])
        memory_data = json.dumps(performance_timeline["memory_usage"][-20:])
        cpu_data = json.dumps(performance_timeline["cpu_usage"][-20:])
        queue_data = json.dumps(performance_timeline["queue_pending"][-20:])

        return html_template.format(
            current_time=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            total_errors=error_summary["total_errors"],
            warning_count=error_summary["error_counts"].get("WARNING", 0),
            log_entries_count=len(recent_logs),
            active_components=len(components),
            component_options=component_options,
            log_entries_html=log_entries_html,
            chart_labels=chart_labels,
            memory_data=memory_data,
            cpu_data=cpu_data,
            queue_data=queue_data
        )

def get_log_dashboard() -> LogDashboard:
    """Get singleton LogDashboard instance."""
    if not hasattr(get_log_dashboard, '_instance'):
        get_log_dashboard._instance = LogDashboard()
    return get_log_dashboard._instance

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Atlas Log Dashboard")
    parser.add_argument("--index", action="store_true", help="Index log files")
    parser.add_argument("--generate-html", action="store_true", help="Generate HTML dashboard")
    parser.add_argument("--search", type=str, help="Search logs for term")
    parser.add_argument("--errors", action="store_true", help="Show error summary")

    args = parser.parse_args()

    dashboard = get_log_dashboard()

    if args.index:
        print("Indexing log files...")
        dashboard.index_log_files()
        print("Log indexing completed.")

    elif args.generate_html:
        html_content = dashboard.generate_html_dashboard()
        output_file = Path("logs") / "dashboard.html"
        output_file.parent.mkdir(exist_ok=True)

        with open(output_file, 'w') as f:
            f.write(html_content)

        print(f"HTML dashboard generated: {output_file}")

    elif args.search:
        results = dashboard.search_logs(args.search)
        print(f"Found {len(results)} matching entries:")
        for log in results[:10]:  # Show first 10
            print(f"{log.timestamp} [{log.level}] {log.component}: {log.message}")

    elif args.errors:
        error_summary = dashboard.get_error_summary()
        print("Error Summary (24h):")
        print(f"Total errors: {error_summary['total_errors']}")
        for level, count in error_summary['error_counts'].items():
            print(f"  {level}: {count}")

        if error_summary['top_errors']:
            print("\nTop Error Messages:")
            for error in error_summary['top_errors'][:5]:
                print(f"  {error['count']}x: {error['message'][:80]}...")

    else:
        print("Use --help to see available options")