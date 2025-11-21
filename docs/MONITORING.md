# Atlas Monitoring Guide

This guide covers monitoring, observability, and alerting for Atlas systems in production environments.

## Table of Contents

- [Monitoring Overview](#monitoring-overview)
- [System Architecture](#system-architecture)
- [Metrics Collection](#metrics-collection)
- [Logging](#logging)
- [Alerting](#alerting)
- [Dashboard Configuration](#dashboard-configuration)
- [Performance Monitoring](#performance-monitoring)
- [Troubleshooting](#troubleshooting)
- [Best Practices](#best-practices)

## Monitoring Overview

Atlas provides comprehensive monitoring capabilities through multiple integrated components:

- **Real-time monitoring dashboard** for visual system overview
- **Structured logging** for detailed analysis
- **Metrics collection** for performance tracking
- **Alerting system** for proactive issue detection
- **Health checks** for service availability

### Monitoring Components

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  Monitoring     │    │  Observability  │    │  Alerting       │
│  Dashboard      │────│  Service        │────│  System         │
│  (Web UI)       │    │  (Metrics/Logs) │    │  (Notifications)│
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
         ┌───────────────────────┼───────────────────────┐
         │                       │                       │
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  System         │    │  Application    │    │  Business       │
│  Metrics        │    │  Metrics        │    │  Metrics        │
│  (CPU/Memory)   │    │  (API/Database) │    │  (Processing)   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## System Architecture

### Monitoring Services

1. **Atlas Monitor** (`monitoring_dashboard_service.py`)
   - Web-based dashboard
   - Real-time metrics display
   - WebSocket-based updates
   - Service health visualization

2. **Atlas Observability** (`standalone_observability.py`)
   - Metrics collection and aggregation
   - Structured logging
   - Alert evaluation
   - External metrics export

### Data Flow

```
Applications → Logs → Observability → Metrics → Dashboard → Alerts
      ↓           ↓          ↓          ↓          ↓
   Metrics → Collection → Storage → Analysis → Notifications
```

### Integration Points

- **System Metrics**: CPU, memory, disk, network via `psutil`
- **Application Metrics**: Custom metrics from Atlas services
- **Database Metrics**: SQLite performance metrics
- **External Metrics**: API response times and error rates
- **Business Metrics**: Processing rates and success metrics

## Metrics Collection

### System Metrics

#### CPU Metrics

```python
# CPU usage monitoring
import psutil

cpu_percent = psutil.cpu_percent(interval=1)
cpu_count = psutil.cpu_count()
cpu_freq = psutil.cpu_freq()
load_avg = psutil.getloadavg()
```

#### Memory Metrics

```python
# Memory usage monitoring
memory = psutil.virtual_memory()
swap = psutil.swap_memory()

metrics = {
    'memory_total': memory.total,
    'memory_used': memory.used,
    'memory_percent': memory.percent,
    'swap_total': swap.total,
    'swap_used': swap.used,
    'swap_percent': swap.percent
}
```

#### Disk Metrics

```python
# Disk usage monitoring
disk = psutil.disk_usage('/')
disk_io = psutil.disk_io_counters()

metrics = {
    'disk_total': disk.total,
    'disk_used': disk.used,
    'disk_percent': disk.percent,
    'disk_read_bytes': disk_io.read_bytes,
    'disk_write_bytes': disk_io.write_bytes
}
```

#### Network Metrics

```python
# Network metrics
network = psutil.net_io_counters()

metrics = {
    'network_bytes_sent': network.bytes_sent,
    'network_bytes_recv': network.bytes_recv,
    'network_packets_sent': network.packets_sent,
    'network_packets_recv': network.packets_recv
}
```

### Application Metrics

#### API Metrics

```python
# API performance metrics
from fastapi import Request
import time

@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time

    # Record metrics
    metrics = {
        'api_requests_total': 1,
        'api_request_duration_seconds': process_time,
        'api_response_size': len(response.body)
    }

    return response
```

#### Database Metrics

```python
# Database performance metrics
import sqlite3
import time

def execute_query(query: str, params: tuple = None):
    start_time = time.time()
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()

    try:
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)

        result = cursor.fetchall()
        duration = time.time() - start_time

        # Record metrics
        metrics = {
            'db_queries_total': 1,
            'db_query_duration_seconds': duration,
            'db_rows_returned': len(result)
        }

        return result
    finally:
        conn.close()
```

#### Business Metrics

```python
# Business logic metrics
def process_article(article_id: int):
    start_time = time.time()

    try:
        # Processing logic
        result = process_content(article_id)

        # Record success metrics
        metrics = {
            'articles_processed_total': 1,
            'articles_processed_success': 1,
            'article_processing_duration_seconds': time.time() - start_time
        }

        return result
    except Exception as e:
        # Record failure metrics
        metrics = {
            'articles_processed_total': 1,
            'articles_processed_failed': 1,
            'article_processing_errors': 1
        }
        raise e
```

### Custom Metrics

#### Defining Custom Metrics

```python
# Custom metrics registration
from prometheus_client import Counter, Histogram, Gauge

# Define metrics
ARTICLES_PROCESSED = Counter('articles_processed_total', 'Total articles processed')
PROCESSING_DURATION = Histogram('article_processing_duration_seconds', 'Article processing duration')
ACTIVE_WORKERS = Gauge('active_workers', 'Number of active workers')

# Use metrics in code
def process_article_with_metrics(article_id: int):
    with PROCESSING_DURATION.time():
        result = process_article(article_id)
        ARTICLES_PROCESSED.inc()
        return result

def update_worker_count(count: int):
    ACTIVE_WORKERS.set(count)
```

#### Metrics Aggregation

```python
# Metrics aggregation and storage
class MetricsAggregator:
    def __init__(self):
        self.metrics = {}
        self.aggregation_window = 60  # seconds

    def record_metric(self, name: str, value: float, tags: dict = None):
        timestamp = time.time()

        if name not in self.metrics:
            self.metrics[name] = []

        self.metrics[name].append({
            'timestamp': timestamp,
            'value': value,
            'tags': tags or {}
        })

        # Clean old data
        self.cleanup_old_metrics()

    def get_aggregated_metrics(self, name: str, aggregation: str = 'avg'):
        if name not in self.metrics:
            return None

        # Filter metrics within aggregation window
        now = time.time()
        recent_metrics = [
            m for m in self.metrics[name]
            if now - m['timestamp'] <= self.aggregation_window
        ]

        if not recent_metrics:
            return None

        values = [m['value'] for m in recent_metrics]

        if aggregation == 'avg':
            return sum(values) / len(values)
        elif aggregation == 'max':
            return max(values)
        elif aggregation == 'min':
            return min(values)
        elif aggregation == 'sum':
            return sum(values)
        elif aggregation == 'count':
            return len(values)

    def cleanup_old_metrics(self):
        now = time.time()
        cutoff = now - self.aggregation_window

        for name in self.metrics:
            self.metrics[name] = [
                m for m in self.metrics[name]
                if m['timestamp'] > cutoff
            ]
```

## Logging

### Structured Logging

#### Log Format

Atlas uses structured JSON logging for better analysis:

```python
import logging
import json
from datetime import datetime

class StructuredLogger:
    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
        handler = logging.StreamHandler()
        formatter = logging.Formatter('%(message)s')
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)

    def log(self, level: str, message: str, **kwargs):
        log_entry = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'level': level.upper(),
            'message': message,
            'logger': self.logger.name,
            **kwargs
        }

        log_method = getattr(self.logger, level.lower())
        log_method(json.dumps(log_entry))

    def info(self, message: str, **kwargs):
        self.log('INFO', message, **kwargs)

    def warning(self, message: str, **kwargs):
        self.log('WARNING', message, **kwargs)

    def error(self, message: str, **kwargs):
        self.log('ERROR', message, **kwargs)

    def debug(self, message: str, **kwargs):
        self.log('DEBUG', message, **kwargs)
```

#### Log Examples

```python
logger = StructuredLogger('atlas.api')

# Info log with context
logger.info(
    "API request processed",
    method="GET",
    path="/health",
    status_code=200,
    duration=0.023,
    user_agent="curl/7.68.0"
)

# Error log with error details
logger.error(
    "Database connection failed",
    error="ConnectionTimeoutError",
    database="atlas.db",
    retry_count=3,
    stack_trace="..."
)

# Debug log with performance data
logger.debug(
    "Article processing completed",
    article_id=12345,
    processing_time=1.45,
    word_count=2500,
    extraction_method="beautifulsoup"
)
```

### Log Configuration

#### Configuration Settings

```python
# Logging configuration
LOGGING_CONFIG = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'json': {
            '()': 'pythonjsonlogger.jsonlogger.JsonFormatter'
        }
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'json',
            'stream': 'ext://sys.stdout'
        },
        'file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'formatter': 'json',
            'filename': 'logs/atlas.log',
            'maxBytes': 10485760,  # 10MB
            'backupCount': 5
        }
    },
    'loggers': {
        'atlas': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False
        }
    }
}
```

#### Environment-based Configuration

```python
import os
import logging.config

def setup_logging(environment: str = 'development'):
    if environment == 'production':
        log_level = 'INFO'
        log_file = 'logs/atlas.log'
    elif environment == 'staging':
        log_level = 'DEBUG'
        log_file = 'logs/atlas-staging.log'
    else:
        log_level = 'DEBUG'
        log_file = 'logs/atlas-dev.log'

    LOGGING_CONFIG['loggers']['atlas']['level'] = log_level
    LOGGING_CONFIG['handlers']['file']['filename'] = log_file

    logging.config.dictConfig(LOGGING_CONFIG)
```

### Log Analysis

#### Querying Logs

```bash
# View recent logs
journalctl -u atlas-api -f

# Filter by log level
journalctl -u atlas-api | grep -i error

# Filter by time range
journalctl -u atlas-api --since "1 hour ago" --until "now"

# Extract specific fields
journalctl -u atlas-api -o json | jq -r '.MESSAGE' | jq '.message'

# Filter by specific attributes
journalctl -u atlas-api -o json | jq -r '.MESSAGE' | jq 'select(.level == "ERROR")'
```

#### Log Aggregation

```python
# Log aggregation for analysis
class LogAggregator:
    def __init__(self):
        self.logs = []
        self.aggregation_window = 300  # 5 minutes

    def add_log(self, log_entry: dict):
        self.logs.append(log_entry)
        self.cleanup_old_logs()

    def get_error_count(self, service: str = None) -> int:
        error_logs = [
            log for log in self.logs
            if log.get('level') == 'ERROR'
            and (service is None or log.get('service') == service)
        ]
        return len(error_logs)

    def get_error_rate(self, service: str = None) -> float:
        total_logs = len([
            log for log in self.logs
            if service is None or log.get('service') == service
        ])

        if total_logs == 0:
            return 0.0

        error_count = self.get_error_count(service)
        return (error_count / total_logs) * 100

    def cleanup_old_logs(self):
        now = time.time()
        cutoff = now - self.aggregation_window

        self.logs = [
            log for log in self.logs
            if log.get('timestamp', 0) > cutoff
        ]
```

## Alerting

### Alert Configuration

#### Alert Rules

```python
# Alert rules configuration
ALERT_RULES = {
    'high_cpu_usage': {
        'condition': 'cpu_percent > 80',
        'duration': '5m',
        'severity': 'warning',
        'message': 'High CPU usage detected: {cpu_percent}%'
    },
    'high_memory_usage': {
        'condition': 'memory_percent > 85',
        'duration': '5m',
        'severity': 'warning',
        'message': 'High memory usage detected: {memory_percent}%'
    },
    'database_connection_error': {
        'condition': 'db_connection_failed == true',
        'duration': '1m',
        'severity': 'critical',
        'message': 'Database connection failed'
    },
    'api_error_rate': {
        'condition': 'api_error_rate > 5',
        'duration': '5m',
        'severity': 'warning',
        'message': 'High API error rate: {api_error_rate}%'
    }
}
```

#### Alert Evaluation

```python
# Alert evaluation engine
class AlertEvaluator:
    def __init__(self, rules: dict):
        self.rules = rules
        self.alert_states = {}
        self.last_evaluation = {}

    def evaluate_alerts(self, metrics: dict) -> list:
        alerts = []
        current_time = time.time()

        for rule_name, rule in self.rules.items():
            # Check if condition is met
            condition_met = self._evaluate_condition(rule['condition'], metrics)

            if condition_met:
                # Initialize or update alert state
                if rule_name not in self.alert_states:
                    self.alert_states[rule_name] = {
                        'start_time': current_time,
                        'last_notified': None
                    }

                # Check if duration threshold is met
                duration = current_time - self.alert_states[rule_name]['start_time']
                duration_threshold = self._parse_duration(rule['duration'])

                if duration >= duration_threshold:
                    # Check if we should send notification
                    if self._should_notify(rule_name, rule):
                        alert = {
                            'rule_name': rule_name,
                            'severity': rule['severity'],
                            'message': self._format_message(rule['message'], metrics),
                            'timestamp': current_time,
                            'duration': duration
                        }
                        alerts.append(alert)

                        # Update notification time
                        self.alert_states[rule_name]['last_notified'] = current_time
            else:
                # Reset alert state if condition is no longer met
                if rule_name in self.alert_states:
                    del self.alert_states[rule_name]

        return alerts

    def _evaluate_condition(self, condition: str, metrics: dict) -> bool:
        # Simple condition evaluation (can be enhanced with proper expression parsing)
        try:
            # Replace metric references
            eval_condition = condition
            for key, value in metrics.items():
                eval_condition = eval_condition.replace(key, str(value))

            # Evaluate condition
            return eval(eval_condition)
        except:
            return False

    def _parse_duration(self, duration_str: str) -> float:
        # Parse duration strings like "5m", "1h", "30s"
        if duration_str.endswith('m'):
            return int(duration_str[:-1]) * 60
        elif duration_str.endswith('h'):
            return int(duration_str[:-1]) * 3600
        elif duration_str.endswith('s'):
            return int(duration_str[:-1])
        else:
            return int(duration_str)

    def _should_notify(self, rule_name: str, rule: dict) -> bool:
        # Implement notification logic (e.g., cooldown periods)
        state = self.alert_states[rule_name]

        # Send initial notification
        if state['last_notified'] is None:
            return True

        # Implement cooldown period (e.g., 1 hour between notifications)
        cooldown_period = 3600  # 1 hour
        if time.time() - state['last_notified'] > cooldown_period:
            return True

        return False

    def _format_message(self, message_template: str, metrics: dict) -> str:
        # Format message with metric values
        try:
            return message_template.format(**metrics)
        except:
            return message_template
```

### Notification Channels

#### Email Notifications

```python
# Email notification system
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

class EmailNotifier:
    def __init__(self, smtp_host: str, smtp_port: int, username: str, password: str):
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.username = username
        self.password = password

    def send_alert(self, alert: dict, recipients: list):
        # Create message
        msg = MIMEMultipart()
        msg['From'] = self.username
        msg['To'] = ', '.join(recipients)
        msg['Subject'] = f"Atlas Alert: {alert['rule_name']} [{alert['severity'].upper()}]"

        # Create HTML body
        html_body = f"""
        <html>
        <body>
            <h2>Atlas Alert: {alert['rule_name']}</h2>
            <p><strong>Severity:</strong> {alert['severity'].upper()}</p>
            <p><strong>Time:</strong> {alert['timestamp']}</p>
            <p><strong>Duration:</strong> {alert['duration']:.1f} seconds</p>
            <p><strong>Message:</strong> {alert['message']}</p>

            <hr>
            <p><em>This alert was generated by the Atlas monitoring system.</em></p>
        </body>
        </html>
        """

        msg.attach(MIMEText(html_body, 'html'))

        # Send email
        try:
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.username, self.password)
                server.send_message(msg)

            return True
        except Exception as e:
            print(f"Failed to send email alert: {e}")
            return False
```

#### Webhook Notifications

```python
# Webhook notification system
import requests
import json

class WebhookNotifier:
    def __init__(self, webhook_url: str, headers: dict = None):
        self.webhook_url = webhook_url
        self.headers = headers or {'Content-Type': 'application/json'}

    def send_alert(self, alert: dict):
        payload = {
            'alert': alert,
            'source': 'atlas',
            'timestamp': alert['timestamp']
        }

        try:
            response = requests.post(
                self.webhook_url,
                json=payload,
                headers=self.headers,
                timeout=30
            )

            return response.status_code == 200
        except Exception as e:
            print(f"Failed to send webhook alert: {e}")
            return False
```

#### Slack Notifications

```python
# Slack notification system
class SlackNotifier:
    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url

    def send_alert(self, alert: dict):
        # Color based on severity
        colors = {
            'critical': 'danger',
            'warning': 'warning',
            'info': 'good'
        }

        color = colors.get(alert['severity'], 'warning')

        payload = {
            'attachments': [
                {
                    'color': color,
                    'title': f"Atlas Alert: {alert['rule_name']}",
                    'text': alert['message'],
                    'fields': [
                        {
                            'title': 'Severity',
                            'value': alert['severity'].upper(),
                            'short': True
                        },
                        {
                            'title': 'Duration',
                            'value': f"{alert['duration']:.1f}s",
                            'short': True
                        },
                        {
                            'title': 'Time',
                            'value': alert['timestamp'],
                            'short': False
                        }
                    ]
                }
            ]
        }

        try:
            response = requests.post(
                self.webhook_url,
                json=payload,
                timeout=30
            )

            return response.status_code == 200
        except Exception as e:
            print(f"Failed to send Slack alert: {e}")
            return False
```

### Alert Management

#### Alert Suppression

```python
# Alert suppression system
class AlertSuppressor:
    def __init__(self):
        self.suppressed_rules = set()
        self.suppression_times = {}

    def suppress_alert(self, rule_name: str, duration: int = 3600):
        """Suppress alerts for a specific rule"""
        self.suppressed_rules.add(rule_name)
        self.suppression_times[rule_name] = time.time() + duration

    def unsuppress_alert(self, rule_name: str):
        """Remove alert suppression"""
        self.suppressed_rules.discard(rule_name)
        if rule_name in self.suppression_times:
            del self.suppression_times[rule_name]

    def is_suppressed(self, rule_name: str) -> bool:
        """Check if an alert is suppressed"""
        if rule_name not in self.suppressed_rules:
            return False

        # Check if suppression has expired
        if time.time() > self.suppression_times[rule_name]:
            self.unsuppress_alert(rule_name)
            return False

        return True

    def get_suppressed_alerts(self) -> list:
        """Get list of currently suppressed alerts"""
        return list(self.suppressed_rules)
```

#### Alert History

```python
# Alert history tracking
class AlertHistory:
    def __init__(self, max_history: int = 1000):
        self.max_history = max_history
        self.alerts = []

    def add_alert(self, alert: dict):
        """Add alert to history"""
        self.alerts.append(alert)

        # Maintain history size
        if len(self.alerts) > self.max_history:
            self.alerts = self.alerts[-self.max_history:]

    def get_alert_history(self, rule_name: str = None, limit: int = 100) -> list:
        """Get alert history"""
        if rule_name:
            filtered_alerts = [
                alert for alert in self.alerts
                if alert.get('rule_name') == rule_name
            ]
        else:
            filtered_alerts = self.alerts

        return filtered_alerts[-limit:]

    def get_alert_stats(self, rule_name: str = None) -> dict:
        """Get alert statistics"""
        alerts = self.get_alert_history(rule_name)

        if not alerts:
            return {
                'total_alerts': 0,
                'by_severity': {},
                'by_rule': {}
            }

        stats = {
            'total_alerts': len(alerts),
            'by_severity': {},
            'by_rule': {}
        }

        for alert in alerts:
            # Count by severity
            severity = alert.get('severity', 'unknown')
            stats['by_severity'][severity] = stats['by_severity'].get(severity, 0) + 1

            # Count by rule
            rule = alert.get('rule_name', 'unknown')
            stats['by_rule'][rule] = stats['by_rule'].get(rule, 0) + 1

        return stats
```

## Dashboard Configuration

### Dashboard Setup

#### Main Dashboard

```python
# Main dashboard configuration
DASHBOARD_CONFIG = {
    'title': 'Atlas Monitoring Dashboard',
    'refresh_interval': 30,  # seconds
    'panels': [
        {
            'title': 'System Overview',
            'type': 'overview',
            'metrics': ['cpu_percent', 'memory_percent', 'disk_percent'],
            'layout': {'x': 0, 'y': 0, 'w': 12, 'h': 4}
        },
        {
            'title': 'API Performance',
            'type': 'timeseries',
            'metrics': ['api_requests_total', 'api_response_time_avg'],
            'layout': {'x': 0, 'y': 4, 'w': 6, 'h': 6}
        },
        {
            'title': 'Database Performance',
            'type': 'timeseries',
            'metrics': ['db_queries_total', 'db_query_time_avg'],
            'layout': {'x': 6, 'y': 4, 'w': 6, 'h': 6}
        },
        {
            'title': 'Business Metrics',
            'type': 'timeseries',
            'metrics': ['articles_processed_total', 'processing_success_rate'],
            'layout': {'x': 0, 'y': 10, 'w': 12, 'h': 6}
        }
    ]
}
```

#### Custom Panels

```python
# Custom panel configuration
class CustomPanel:
    def __init__(self, title: str, panel_type: str, metrics: list):
        self.title = title
        self.panel_type = panel_type
        self.metrics = metrics
        self.data = []

    def update_data(self, metrics_data: dict):
        """Update panel data"""
        self.data = []

        for metric in self.metrics:
            if metric in metrics_data:
                self.data.append({
                    'metric': metric,
                    'value': metrics_data[metric],
                    'timestamp': time.time()
                })

    def render(self) -> str:
        """Render panel as HTML"""
        if self.panel_type == 'gauge':
            return self._render_gauge()
        elif self.panel_type == 'timeseries':
            return self._render_timeseries()
        elif self.panel_type == 'counter':
            return self._render_counter()
        else:
            return self._render_default()

    def _render_gauge(self) -> str:
        """Render gauge panel"""
        if not self.data:
            return '<div>No data available</div>'

        value = self.data[-1]['value']
        percentage = min(max(value, 0), 100)

        color = 'green' if percentage < 60 else 'orange' if percentage < 80 else 'red'

        return f"""
        <div class="gauge-panel">
            <h3>{self.title}</h3>
            <div class="gauge">
                <div class="gauge-fill" style="width: {percentage}%; background-color: {color};"></div>
            </div>
            <div class="gauge-value">{percentage:.1f}%</div>
        </div>
        """

    def _render_timeseries(self) -> str:
        """Render timeseries panel"""
        if not self.data:
            return '<div>No data available</div>'

        # This would typically use a charting library like Chart.js
        return f"""
        <div class="timeseries-panel">
            <h3>{self.title}</h3>
            <canvas id="chart-{self.title}" width="400" height="200"></canvas>
            <script>
                // Chart.js implementation would go here
            </script>
        </div>
        """
```

### Real-time Updates

#### WebSocket Integration

```python
# WebSocket server for real-time updates
from fastapi import WebSocket
from typing import List
import asyncio
import json

class WebSocketManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except:
                # Connection might be closed
                pass

# Usage in FastAPI app
websocket_manager = WebSocketManager()

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket_manager.connect(websocket)
    try:
        while True:
            # Keep connection alive
            await asyncio.sleep(1)
    except:
        websocket_manager.disconnect(websocket)

# Broadcast metrics updates
async def broadcast_metrics(metrics: dict):
    message = json.dumps({
        'type': 'metrics_update',
        'data': metrics,
        'timestamp': time.time()
    })
    await websocket_manager.broadcast(message)
```

#### Dashboard JavaScript

```javascript
// Dashboard client-side JavaScript
class AtlasDashboard {
    constructor() {
        this.ws = null;
        this.metrics = {};
        this.charts = {};
        this.init();
    }

    init() {
        this.connectWebSocket();
        this.setupEventListeners();
        this.startMetricsRefresh();
    }

    connectWebSocket() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws`;

        this.ws = new WebSocket(wsUrl);

        this.ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            this.handleWebSocketMessage(data);
        };

        this.ws.onclose = () => {
            setTimeout(() => this.connectWebSocket(), 5000);
        };
    }

    handleWebSocketMessage(data) {
        if (data.type === 'metrics_update') {
            this.updateMetrics(data.data);
        }
    }

    updateMetrics(metrics) {
        this.metrics = { ...this.metrics, ...metrics };
        this.updateDashboard();
    }

    updateDashboard() {
        // Update system overview
        this.updateSystemOverview();

        // Update charts
        this.updateCharts();

        // Update status indicators
        this.updateStatusIndicators();
    }

    updateSystemOverview() {
        const cpu = this.metrics.cpu_percent || 0;
        const memory = this.metrics.memory_percent || 0;
        const disk = this.metrics.disk_percent || 0;

        document.getElementById('cpu-gauge').style.width = `${cpu}%`;
        document.getElementById('memory-gauge').style.width = `${memory}%`;
        document.getElementById('disk-gauge').style.width = `${disk}%`;

        document.getElementById('cpu-value').textContent = `${cpu.toFixed(1)}%`;
        document.getElementById('memory-value').textContent = `${memory.toFixed(1)}%`;
        document.getElementById('disk-value').textContent = `${disk.toFixed(1)}%`;
    }

    updateCharts() {
        // Update timeseries charts
        Object.keys(this.charts).forEach(chartId => {
            const chart = this.charts[chartId];
            const metricName = chart.dataset.metric;

            if (this.metrics[metricName] !== undefined) {
                this.addDataPoint(chart, this.metrics[metricName]);
            }
        });
    }

    addDataPoint(chart, value) {
        const now = new Date();

        if (chart.data.labels.length > 50) {
            chart.data.labels.shift();
            chart.data.datasets[0].data.shift();
        }

        chart.data.labels.push(now.toLocaleTimeString());
        chart.data.datasets[0].data.push(value);
        chart.update();
    }

    startMetricsRefresh() {
        // Fallback metrics refresh in case WebSocket fails
        setInterval(() => {
            if (this.ws.readyState !== WebSocket.OPEN) {
                this.fetchMetrics();
            }
        }, 30000); // 30 seconds
    }

    async fetchMetrics() {
        try {
            const response = await fetch('/api/metrics');
            const metrics = await response.json();
            this.updateMetrics(metrics);
        } catch (error) {
            console.error('Failed to fetch metrics:', error);
        }
    }
}

// Initialize dashboard when page loads
document.addEventListener('DOMContentLoaded', () => {
    window.dashboard = new AtlasDashboard();
});
```

## Performance Monitoring

### Response Time Monitoring

#### API Response Times

```python
# API response time monitoring
from fastapi import Request, Response
import time
import statistics

class ResponseTimeMonitor:
    def __init__(self, max_samples: int = 1000):
        self.response_times = {}
        self.max_samples = max_samples

    def record_response_time(self, endpoint: str, response_time: float):
        if endpoint not in self.response_times:
            self.response_times[endpoint] = []

        self.response_times[endpoint].append(response_time)

        # Maintain sample size
        if len(self.response_times[endpoint]) > self.max_samples:
            self.response_times[endpoint] = self.response_times[endpoint][-self.max_samples:]

    def get_response_time_stats(self, endpoint: str = None) -> dict:
        if endpoint:
            times = self.response_times.get(endpoint, [])
        else:
            times = []
            for endpoint_times in self.response_times.values():
                times.extend(endpoint_times)

        if not times:
            return {
                'count': 0,
                'avg': 0,
                'min': 0,
                'max': 0,
                'p95': 0,
                'p99': 0
            }

        return {
            'count': len(times),
            'avg': statistics.mean(times),
            'min': min(times),
            'max': max(times),
            'p95': statistics.quantiles(times, n=20)[18],  # 95th percentile
            'p99': statistics.quantiles(times, n=100)[98]  # 99th percentile
        }

# Usage in FastAPI middleware
response_time_monitor = ResponseTimeMonitor()

@app.middleware("http")
async def monitor_response_time(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    response_time = time.time() - start_time

    # Record response time
    endpoint = request.url.path
    response_time_monitor.record_response_time(endpoint, response_time)

    return response
```

#### Database Query Monitoring

```python
# Database query monitoring
import sqlite3
import time
from contextlib import contextmanager

class QueryMonitor:
    def __init__(self, max_samples: int = 1000):
        self.query_times = {}
        self.max_samples = max_samples

    def record_query_time(self, query_type: str, execution_time: float):
        if query_type not in self.query_times:
            self.query_times[query_type] = []

        self.query_times[query_type].append(execution_time)

        # Maintain sample size
        if len(self.query_times[query_type]) > self.max_samples:
            self.query_times[query_type] = self.query_times[query_type][-self.max_samples:]

    def get_query_stats(self, query_type: str = None) -> dict:
        if query_type:
            times = self.query_times.get(query_type, [])
        else:
            times = []
            for query_times in self.query_times.values():
                times.extend(query_times)

        if not times:
            return {
                'count': 0,
                'avg': 0,
                'min': 0,
                'max': 0,
                'p95': 0
            }

        return {
            'count': len(times),
            'avg': statistics.mean(times),
            'min': min(times),
            'max': max(times),
            'p95': statistics.quantiles(times, n=20)[18]
        }

# Context manager for query monitoring
query_monitor = QueryMonitor()

@contextmanager
def monitor_query(query_type: str):
    start_time = time.time()
    try:
        yield
    finally:
        execution_time = time.time() - start_time
        query_monitor.record_query_time(query_type, execution_time)

# Usage in database operations
def execute_query(query: str, params: tuple = None):
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()

    try:
        with monitor_query('select'):
            cursor.execute(query, params)
        return cursor.fetchall()
    finally:
        conn.close()
```

### Resource Usage Monitoring

#### Memory Usage Tracking

```python
# Memory usage monitoring
import psutil
import gc
import objgraph

class MemoryMonitor:
    def __init__(self):
        self.process = psutil.Process()
        self.baseline_memory = None

    def get_memory_usage(self) -> dict:
        memory_info = self.process.memory_info()
        memory_percent = self.process.memory_percent()

        return {
            'rss': memory_info.rss,  # Resident Set Size
            'vms': memory_info.vms,  # Virtual Memory Size
            'percent': memory_percent,
            'available': psutil.virtual_memory().available
        }

    def get_memory_objects(self) -> dict:
        """Get information about Python objects in memory"""
        return {
            'objects_total': len(gc.get_objects()),
            'garbage_collected': gc.collect(),
            'object_types': objgraph.typestats()
        }

    def get_memory_growth(self) -> dict:
        """Calculate memory growth since baseline"""
        current_memory = self.get_memory_usage()

        if self.baseline_memory is None:
            self.baseline_memory = current_memory
            return {'growth': 0, 'growth_percent': 0}

        growth = current_memory['rss'] - self.baseline_memory['rss']
        growth_percent = (growth / self.baseline_memory['rss']) * 100

        return {
            'growth': growth,
            'growth_percent': growth_percent,
            'baseline': self.baseline_memory['rss'],
            'current': current_memory['rss']
        }

# Usage
memory_monitor = MemoryMonitor()

@app.get("/api/memory")
async def get_memory_usage():
    return {
        'memory_usage': memory_monitor.get_memory_usage(),
        'memory_objects': memory_monitor.get_memory_objects(),
        'memory_growth': memory_monitor.get_memory_growth()
    }
```

#### CPU Usage Monitoring

```python
# CPU usage monitoring
class CPUMonitor:
    def __init__(self):
        self.process = psutil.Process()
        self.cpu_history = []
        self.max_history = 60  # Keep 1 minute of history

    def get_cpu_usage(self) -> dict:
        cpu_percent = self.process.cpu_percent(interval=1)
        cpu_count = psutil.cpu_count()
        load_avg = psutil.getloadavg()

        # Add to history
        self.cpu_history.append({
            'timestamp': time.time(),
            'cpu_percent': cpu_percent
        })

        # Maintain history size
        if len(self.cpu_history) > self.max_history:
            self.cpu_history = self.cpu_history[-self.max_history:]

        return {
            'cpu_percent': cpu_percent,
            'cpu_count': cpu_count,
            'load_avg_1min': load_avg[0],
            'load_avg_5min': load_avg[1],
            'load_avg_15min': load_avg[2],
            'per_cpu': self.process.cpu_percent(interval=1, percpu=True)
        }

    def get_cpu_trend(self) -> dict:
        """Calculate CPU usage trend"""
        if len(self.cpu_history) < 2:
            return {'trend': 'stable', 'change': 0}

        recent = self.cpu_history[-5:]  # Last 5 measurements
        older = self.cpu_history[-10:-5]  # Previous 5 measurements

        if not older:
            return {'trend': 'stable', 'change': 0}

        recent_avg = sum(point['cpu_percent'] for point in recent) / len(recent)
        older_avg = sum(point['cpu_percent'] for point in older) / len(older)

        change = recent_avg - older_avg

        if change > 5:
            trend = 'increasing'
        elif change < -5:
            trend = 'decreasing'
        else:
            trend = 'stable'

        return {
            'trend': trend,
            'change': change,
            'recent_avg': recent_avg,
            'older_avg': older_avg
        }

# Usage
cpu_monitor = CPUMonitor()

@app.get("/api/cpu")
async def get_cpu_usage():
    return {
        'cpu_usage': cpu_monitor.get_cpu_usage(),
        'cpu_trend': cpu_monitor.get_cpu_trend()
    }
```

## Troubleshooting

### Common Monitoring Issues

#### Dashboard Not Loading

**Symptoms**: Monitoring dashboard shows loading spinner or error messages

**Causes**:
- WebSocket connection failed
- JavaScript errors
- Metrics endpoint not responding

**Solutions**:
```bash
# Check service status
sudo systemctl status atlas-monitor

# Check WebSocket connection
curl -I http://localhost:7445/ws

# Check metrics endpoint
curl http://localhost:7445/api/metrics

# Check browser console for JavaScript errors
```

#### Missing Metrics

**Symptoms**: Some metrics show as zero or null values

**Causes**:
- Metrics collection disabled
- Incorrect metric names
- Permission issues

**Solutions**:
```bash
# Check metrics configuration
python3 tools/config_cli.py show METRICS_EXPORT_ENABLED

# Enable metrics if needed
python3 tools/config_cli.py set METRICS_EXPORT_ENABLED true

# Check metric names in code
grep -r "metric_name" src/
```

#### Alert Not Working

**Symptoms**: Alerts not being sent or received

**Causes**:
- Alert rules misconfigured
- Notification channel issues
- Alert evaluation not running

**Solutions**:
```bash
# Check alert configuration
python3 tools/config_cli.py show ALERTING_ENABLED

# Test notification channels
python3 tools/monitoring_agent.py test-alert

# Check alert evaluation logs
sudo journalctl -u atlas-observability -f | grep alert
```

### Debug Commands

#### Check Service Health

```bash
# Check all monitoring services
sudo systemctl status atlas-monitor atlas-observability

# Check service logs
sudo journalctl -u atlas-monitor -n 50
sudo journalctl -u atlas-observability -n 50

# Check network connectivity
netstat -tlnp | grep -E ':744[4-6]'

# Check port availability
curl -v http://localhost:7445/health
curl -v http://localhost:7446/health
```

#### Check Metrics Collection

```bash
# Check metrics endpoint
curl http://localhost:7445/api/metrics | jq .

# Check system metrics
python3 tools/monitoring_agent.py metrics

# Check alert evaluation
python3 tools/monitoring_agent.py alerts

# Check dashboard data
curl http://localhost:7445/api/dashboard
```

#### Check Database Performance

```bash
# Check database performance
python3 tools/atlas_ops.py check-database

# Check database size
ls -lh /home/atlas/atlas/data/prod/atlas.db

# Check database connections
python3 -c "
import sqlite3
conn = sqlite3.connect('/home/atlas/atlas/data/prod/atlas.db')
cursor = conn.cursor()
cursor.execute('PRAGMA database_list;')
print(cursor.fetchall())
conn.close()
"
```

### Performance Issues

#### High CPU Usage

```bash
# Check CPU usage
top -p $(pgrep -f atlas-monitor)
top -p $(pgrep -f atlas-observability)

# Check CPU by thread
ps -T -p $(pgrep -f atlas-monitor)

# Check CPU limits
sudo systemctl show atlas-monitor | grep CPUQuota

# Adjust CPU limits
sudo systemctl edit atlas-monitor
```

#### High Memory Usage

```bash
# Check memory usage
free -h
ps aux | grep -E 'atlas-monitor|atlas-observability'

# Check memory limits
sudo systemctl show atlas-monitor | grep MemoryLimit

# Check memory leaks
python3 tools/monitoring_agent.py memory-profile

# Restart services if needed
sudo systemctl restart atlas-monitor atlas-observability
```

#### Slow Dashboard Loading

```bash
# Check dashboard performance
curl -w "@curl-format.txt" -o /dev/null -s http://localhost:7445/

# Check WebSocket performance
time curl -N http://localhost:7445/ws

# Check database queries
sudo journalctl -u atlas-observability -f | grep "slow query"

# Optimize database queries
python3 tools/atlas_ops.py optimize-database
```

## Best Practices

### Monitoring Configuration

#### Key Metrics to Monitor

1. **System Metrics**
   - CPU usage (alert if > 80% for 5 minutes)
   - Memory usage (alert if > 85% for 5 minutes)
   - Disk usage (alert if > 90%)
   - Network latency (alert if > 100ms)

2. **Application Metrics**
   - API response time (alert if > 2 seconds)
   - Error rate (alert if > 5%)
   - Database query time (alert if > 1 second)
   - Queue size (alert if > 100 items)

3. **Business Metrics**
   - Articles processed per hour
   - Processing success rate
   - External API success rate
   - User activity metrics

#### Alert Configuration Best Practices

1. **Set appropriate thresholds**
   - Warning level: 80% of capacity
   - Critical level: 90% of capacity
   - Use duration to avoid false positives

2. **Configure notification channels**
   - Email for critical alerts
   - Slack for warning alerts
   - Webhook for integration with other systems

3. **Implement alert suppression**
   - Suppress alerts during maintenance
   - Use cooldown periods to avoid spam
   - Group related alerts

### Performance Optimization

#### Dashboard Optimization

1. **Reduce data transfer**
   - Use WebSocket for real-time updates
   - Aggregate data on the server
   - Limit historical data retention

2. **Optimize charts**
   - Use appropriate chart types
   - Limit data points to 50-100
   - Implement lazy loading

3. **Cache static assets**
   - Use browser caching
   - Implement CDN for static content
   - Optimize images and JavaScript

#### Metrics Collection Optimization

1. **Optimize collection intervals**
   - System metrics: 5-15 seconds
   - Application metrics: 30-60 seconds
   - Business metrics: 1-5 minutes

2. **Reduce metric cardinality**
   - Use consistent metric names
   - Limit tag values
   - Avoid high-cardinality dimensions

3. **Implement sampling**
   - Sample high-frequency metrics
   - Use aggregation for historical data
   - Implement rollups for long-term storage

### Security Considerations

#### Dashboard Security

1. **Authentication and Authorization**
   - Implement user authentication
   - Role-based access control
   - Session management

2. **Network Security**
   - Use HTTPS for dashboard access
   - Implement rate limiting
   - Validate input parameters

3. **Data Protection**
   - Encrypt sensitive metrics
   - Implement access logging
   - Regular security audits

#### Metrics Security

1. **Access Control**
   - Restrict metrics endpoint access
   - Implement API key authentication
   - Use IP whitelisting

2. **Data Privacy**
   - Anonymize user-related metrics
   - Avoid logging sensitive data
   - Implement data retention policies

3. **Audit Logging**
   - Log all access to monitoring data
   - Implement alert for suspicious access
   - Regular access reviews

---

*This guide is part of the Atlas documentation. For additional information, see other files in the `docs/` directory.*