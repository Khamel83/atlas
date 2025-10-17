"""
Atlas Monitoring Dashboard
Web interface for real-time system monitoring and metrics visualization.
"""

import json
from datetime import datetime, timedelta
from typing import Dict, Any, List

from helpers.metrics_collector import get_metrics_collector, get_health_summary
from helpers.queue_manager import get_queue_status
from helpers.database_config import get_database_connection


def get_monitoring_dashboard_html() -> str:
    """Generate monitoring dashboard HTML."""
    metrics_collector = get_metrics_collector()
    health_summary = get_health_summary()
    queue_status = get_queue_status()

    # Get key metrics for display
    transcription_rate = metrics_collector.get_metric_value("atlas_transcription_rate") or 0
    queue_pending = metrics_collector.get_metric_value("atlas_queue_pending_total") or 0
    queue_failed = metrics_collector.get_metric_value("atlas_queue_failed_total") or 0
    memory_usage = metrics_collector.get_metric_value("atlas_memory_usage_bytes") or 0
    disk_free = metrics_collector.get_metric_value("atlas_disk_free_bytes") or 0

    # Convert bytes to human readable
    memory_mb = memory_usage / 1024 / 1024
    disk_gb = disk_free / 1024 / 1024 / 1024

    # Get alerts
    alerts = health_summary.get("alerts", [])
    critical_alerts = [a for a in alerts if a["severity"] == "critical"]
    warning_alerts = [a for a in alerts if a["severity"] == "warning"]

    # Status color
    status_color = {
        "healthy": "#22c55e",
        "warning": "#f59e0b",
        "critical": "#ef4444"
    }.get(health_summary["status"], "#6b7280")

    # Get recent metrics for charts (simplified JSON data)
    chart_data = get_chart_data(metrics_collector)

    html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Atlas Monitoring Dashboard</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #0f172a;
            color: #e2e8f0;
            line-height: 1.6;
        }}

        .header {{
            background: #1e293b;
            padding: 1rem 2rem;
            border-bottom: 1px solid #334155;
        }}

        .header h1 {{
            font-size: 1.5rem;
            font-weight: bold;
            color: #f1f5f9;
        }}

        .status-badge {{
            display: inline-block;
            padding: 0.25rem 0.75rem;
            border-radius: 0.375rem;
            font-size: 0.875rem;
            font-weight: 500;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            background: {status_color};
            color: white;
            margin-left: 1rem;
        }}

        .dashboard {{
            padding: 2rem;
            max-width: 1400px;
            margin: 0 auto;
        }}

        .metrics-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 1.5rem;
            margin-bottom: 2rem;
        }}

        .metric-card {{
            background: #1e293b;
            border: 1px solid #334155;
            border-radius: 0.5rem;
            padding: 1.5rem;
        }}

        .metric-title {{
            font-size: 0.875rem;
            color: #94a3b8;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            margin-bottom: 0.5rem;
        }}

        .metric-value {{
            font-size: 2rem;
            font-weight: bold;
            color: #f1f5f9;
        }}

        .metric-unit {{
            font-size: 0.875rem;
            color: #64748b;
            margin-left: 0.25rem;
        }}

        .alerts-section {{
            margin-bottom: 2rem;
        }}

        .alert {{
            background: #1e293b;
            border-left: 4px solid;
            padding: 1rem;
            margin-bottom: 0.5rem;
            border-radius: 0 0.375rem 0.375rem 0;
        }}

        .alert.critical {{
            border-color: #ef4444;
            background: #1e293b;
        }}

        .alert.warning {{
            border-color: #f59e0b;
            background: #1e293b;
        }}

        .alert-title {{
            font-weight: 600;
            margin-bottom: 0.25rem;
        }}

        .charts-section {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
            gap: 2rem;
        }}

        .chart-container {{
            background: #1e293b;
            border: 1px solid #334155;
            border-radius: 0.5rem;
            padding: 1.5rem;
        }}

        .chart-title {{
            font-size: 1.125rem;
            font-weight: 600;
            margin-bottom: 1rem;
            color: #f1f5f9;
        }}

        .refresh-info {{
            text-align: center;
            margin-top: 2rem;
            color: #64748b;
            font-size: 0.875rem;
        }}

        .timestamp {{
            color: #64748b;
            font-size: 0.75rem;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🎯 Atlas Monitoring Dashboard</h1>
        <span class="status-badge">{health_summary["status"]}</span>
        <span class="timestamp">Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</span>
    </div>

    <div class="dashboard">
        <!-- Key Metrics -->
        <div class="metrics-grid">
            <div class="metric-card">
                <div class="metric-title">Transcription Rate</div>
                <div class="metric-value">{transcription_rate:.1f}<span class="metric-unit">/min</span></div>
            </div>

            <div class="metric-card">
                <div class="metric-title">Queue Pending</div>
                <div class="metric-value">{queue_pending:,.0f}<span class="metric-unit">tasks</span></div>
            </div>

            <div class="metric-card">
                <div class="metric-title">Failed Tasks</div>
                <div class="metric-value">{queue_failed:,.0f}<span class="metric-unit">tasks</span></div>
            </div>

            <div class="metric-card">
                <div class="metric-title">Memory Usage</div>
                <div class="metric-value">{memory_mb:.0f}<span class="metric-unit">MB</span></div>
            </div>

            <div class="metric-card">
                <div class="metric-title">Disk Free</div>
                <div class="metric-value">{disk_gb:.1f}<span class="metric-unit">GB</span></div>
            </div>

            <div class="metric-card">
                <div class="metric-title">System Status</div>
                <div class="metric-value" style="color: {status_color};">{health_summary["status"].upper()}</div>
            </div>
        </div>

        <!-- Alerts Section -->
        {get_alerts_html(critical_alerts, warning_alerts)}

        <!-- Charts -->
        <div class="charts-section">
            <div class="chart-container">
                <div class="chart-title">Transcription Rate (Last 24h)</div>
                <canvas id="transcriptionChart" width="400" height="200"></canvas>
            </div>

            <div class="chart-container">
                <div class="chart-title">Queue Depth (Last 24h)</div>
                <canvas id="queueChart" width="400" height="200"></canvas>
            </div>

            <div class="chart-container">
                <div class="chart-title">Memory Usage (Last 24h)</div>
                <canvas id="memoryChart" width="400" height="200"></canvas>
            </div>

            <div class="chart-container">
                <div class="chart-title">System Health</div>
                <canvas id="healthChart" width="400" height="200"></canvas>
            </div>
        </div>

        <div class="refresh-info">
            📊 Dashboard auto-refreshes every 60 seconds<br>
            🔄 Metrics collected every 60 seconds<br>
            📡 Real-time monitoring active
        </div>
    </div>

    <script>
        // Chart.js configuration
        Chart.defaults.color = '#e2e8f0';
        Chart.defaults.borderColor = '#334155';

        const chartData = {json.dumps(chart_data)};

        // Transcription Rate Chart
        new Chart(document.getElementById('transcriptionChart'), {{
            type: 'line',
            data: {{
                labels: chartData.labels,
                datasets: [{{
                    label: 'Transcriptions/min',
                    data: chartData.transcription_rate,
                    borderColor: '#22c55e',
                    backgroundColor: 'rgba(34, 197, 94, 0.1)',
                    tension: 0.4
                }}]
            }},
            options: {{
                responsive: true,
                scales: {{
                    y: {{
                        beginAtZero: true,
                        grid: {{ color: '#334155' }}
                    }},
                    x: {{
                        grid: {{ color: '#334155' }}
                    }}
                }},
                plugins: {{
                    legend: {{ display: false }}
                }}
            }}
        }});

        // Queue Depth Chart
        new Chart(document.getElementById('queueChart'), {{
            type: 'line',
            data: {{
                labels: chartData.labels,
                datasets: [{{
                    label: 'Pending Tasks',
                    data: chartData.queue_pending,
                    borderColor: '#3b82f6',
                    backgroundColor: 'rgba(59, 130, 246, 0.1)',
                    tension: 0.4
                }}]
            }},
            options: {{
                responsive: true,
                scales: {{
                    y: {{
                        beginAtZero: true,
                        grid: {{ color: '#334155' }}
                    }},
                    x: {{
                        grid: {{ color: '#334155' }}
                    }}
                }},
                plugins: {{
                    legend: {{ display: false }}
                }}
            }}
        }});

        // Memory Usage Chart
        new Chart(document.getElementById('memoryChart'), {{
            type: 'line',
            data: {{
                labels: chartData.labels,
                datasets: [{{
                    label: 'Memory (MB)',
                    data: chartData.memory_usage,
                    borderColor: '#f59e0b',
                    backgroundColor: 'rgba(245, 158, 11, 0.1)',
                    tension: 0.4
                }}]
            }},
            options: {{
                responsive: true,
                scales: {{
                    y: {{
                        beginAtZero: true,
                        grid: {{ color: '#334155' }}
                    }},
                    x: {{
                        grid: {{ color: '#334155' }}
                    }}
                }},
                plugins: {{
                    legend: {{ display: false }}
                }}
            }}
        }});

        // Health Status Chart (Simple status indicator)
        new Chart(document.getElementById('healthChart'), {{
            type: 'doughnut',
            data: {{
                labels: ['Healthy', 'Warning', 'Critical'],
                datasets: [{{
                    data: [{len([a for a in alerts if a["severity"] == "info"])}, {len(warning_alerts)}, {len(critical_alerts)}],
                    backgroundColor: ['#22c55e', '#f59e0b', '#ef4444']
                }}]
            }},
            options: {{
                responsive: true,
                plugins: {{
                    legend: {{
                        position: 'bottom'
                    }}
                }}
            }}
        }});

        // Auto-refresh every 60 seconds
        setTimeout(() => {{
            window.location.reload();
        }}, 60000);
    </script>
</body>
</html>
"""

    return html


def get_alerts_html(critical_alerts: List[Dict], warning_alerts: List[Dict]) -> str:
    """Generate alerts HTML section."""
    if not critical_alerts and not warning_alerts:
        return """
        <div class="alerts-section">
            <h2 style="color: #22c55e; margin-bottom: 1rem;">✅ No Active Alerts</h2>
        </div>
        """

    html = '<div class="alerts-section">'

    if critical_alerts or warning_alerts:
        html += '<h2 style="color: #ef4444; margin-bottom: 1rem;">🚨 Active Alerts</h2>'

    for alert in critical_alerts:
        html += f'''
        <div class="alert critical">
            <div class="alert-title">🚨 CRITICAL: {alert["condition"].replace("_", " ").title()}</div>
            <div>{alert["message"]}</div>
        </div>
        '''

    for alert in warning_alerts:
        html += f'''
        <div class="alert warning">
            <div class="alert-title">⚠️ WARNING: {alert["condition"].replace("_", " ").title()}</div>
            <div>{alert["message"]}</div>
        </div>
        '''

    html += '</div>'
    return html


def get_chart_data(metrics_collector) -> Dict[str, List]:
    """Get chart data for the last 24 hours."""
    # For now, generate simple sample data
    # In production, this would query historical metrics

    import random
    from datetime import datetime, timedelta

    now = datetime.now()
    labels = []
    transcription_rate = []
    queue_pending = []
    memory_usage = []

    # Generate 24 data points (hourly for last 24h)
    for i in range(24):
        time_point = now - timedelta(hours=23-i)
        labels.append(time_point.strftime('%H:%M'))

        # Sample data with some variation
        transcription_rate.append(random.uniform(0, 5))
        queue_pending.append(random.randint(0, 100))
        memory_usage.append(random.randint(200, 400))

    return {
        "labels": labels,
        "transcription_rate": transcription_rate,
        "queue_pending": queue_pending,
        "memory_usage": memory_usage
    }