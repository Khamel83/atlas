"""
Atlas Monitoring Dashboard Service
Real-time monitoring dashboard with WebSocket support and advanced visualization.
"""

import asyncio
import json
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import logging
from pathlib import Path
import os
from dataclasses import dataclass

from fastapi import WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi import APIRouter, Depends, Request, Response
from fastapi.staticfiles import StaticFiles

# Import with fallbacks for missing modules
try:
    from helpers.metrics_collector import get_metrics_collector, get_health_summary
    METRICS_AVAILABLE = True
except ImportError:
    METRICS_AVAILABLE = False

try:
    from helpers.logging_config import get_logger
    LOGGING_AVAILABLE = True
except ImportError:
    import logging
    LOGGING_AVAILABLE = False

try:
    from helpers.queue_manager import get_queue_status
    QUEUE_AVAILABLE = True
except ImportError:
    QUEUE_AVAILABLE = False

try:
    from helpers.alerting_service import get_alerting_service
    ALERTING_AVAILABLE = True
except ImportError:
    ALERTING_AVAILABLE = False

# Fallback logger
if LOGGING_AVAILABLE:
    logger = get_logger("monitoring")
else:
    logger = logging.getLogger("monitoring")
    logger.setLevel(logging.INFO)


router = APIRouter(prefix="/monitoring", tags=["monitoring"])

# Connected WebSocket clients
connected_clients = set()


@dataclass
class DashboardClient:
    """Connected dashboard client with metadata."""
    websocket: WebSocket
    client_id: str
    connected_at: float
    last_active: float
    user_agent: str = ""
    ip_address: str = ""

class ConnectionManager:
    """Manages WebSocket connections for real-time updates."""

    def __init__(self):
        self.active_connections: Dict[str, DashboardClient] = {}
        self.connection_stats = {
            "total_connections": 0,
            "active_connections": 0,
            "messages_broadcast": 0
        }

    async def connect(self, websocket: WebSocket) -> str:
        """Accept a new WebSocket connection and return client ID."""
        await websocket.accept()

        client_id = f"client_{int(time.time() * 1000)}_{len(self.active_connections)}"

        # Get client information
        client = DashboardClient(
            websocket=websocket,
            client_id=client_id,
            connected_at=time.time(),
            last_active=time.time(),
            user_agent=websocket.headers.get("user-agent", ""),
            ip_address=websocket.client.host if websocket.client else "unknown"
        )

        self.active_connections[client_id] = client
        self.connection_stats["total_connections"] += 1
        self.connection_stats["active_connections"] = len(self.active_connections)

        logger.info(f"Client connected: {client_id} from {client.ip_address}")
        return client_id

    def disconnect(self, client_id: str):
        """Remove a WebSocket connection."""
        if client_id in self.active_connections:
            del self.active_connections[client_id]
            self.connection_stats["active_connections"] = len(self.active_connections)
            logger.info(f"Client disconnected: {client_id}")

    async def send_personal_message(self, message: str, client_id: str):
        """Send a message to a specific client."""
        if client_id in self.active_connections:
            try:
                client = self.active_connections[client_id]
                await client.websocket.send_text(message)
                client.last_active = time.time()
                return True
            except Exception as e:
                logger.warning(f"Failed to send message to {client_id}: {e}")
                self.disconnect(client_id)
        return False

    async def broadcast(self, message: str, filter_callback=None):
        """Broadcast a message to all connected clients."""
        disconnected = []
        messages_sent = 0

        for client_id, client in self.active_connections.items():
            try:
                # Apply filter if provided
                if filter_callback and not filter_callback(client):
                    continue

                await client.websocket.send_text(message)
                client.last_active = time.time()
                messages_sent += 1
            except Exception as e:
                logger.warning(f"Failed to broadcast to {client_id}: {e}")
                disconnected.append(client_id)

        # Clean up disconnected clients
        for client_id in disconnected:
            self.disconnect(client_id)

        self.connection_stats["messages_broadcast"] += messages_sent
        return messages_sent

    def get_connection_stats(self) -> Dict[str, Any]:
        """Get detailed connection statistics."""
        current_time = time.time()
        active_connections = len(self.active_connections)

        # Calculate session durations
        session_durations = []
        for client in self.active_connections.values():
            duration = current_time - client.connected_at
            session_durations.append(duration)

        avg_session_duration = sum(session_durations) / len(session_durations) if session_durations else 0

        return {
            **self.connection_stats,
            "current_connections": active_connections,
            "average_session_duration": avg_session_duration,
            "unique_ips": len(set(client.ip_address for client in self.active_connections.values()))
        }

    def cleanup_idle_connections(self, max_idle_time: float = 300):
        """Clean up idle connections."""
        current_time = time.time()
        idle_clients = [
            client_id for client_id, client in self.active_connections.items()
            if current_time - client.last_active > max_idle_time
        ]

        for client_id in idle_clients:
            self.disconnect(client_id)

        return len(idle_clients)


manager = ConnectionManager()


@router.get("/", response_class=HTMLResponse)
async def get_monitoring_dashboard():
    """Get the enhanced monitoring dashboard."""
    return get_enhanced_dashboard_html()


class MonitoringService:
    """Background service for collecting and broadcasting metrics."""

    def __init__(self):
        self.is_running = False
        self.update_task = None
        self.cleanup_task = None
        self.update_interval = 5  # seconds
        self.cleanup_interval = 60  # seconds

    async def start(self):
        """Start the monitoring service."""
        if self.is_running:
            return

        self.is_running = True
        self.update_task = asyncio.create_task(self._update_loop())
        self.cleanup_task = asyncio.create_task(self._cleanup_loop())

        logger.info("Monitoring service started")

    async def stop(self):
        """Stop the monitoring service."""
        self.is_running = False

        if self.update_task:
            self.update_task.cancel()
            try:
                await self.update_task
            except asyncio.CancelledError:
                pass

        if self.cleanup_task:
            self.cleanup_task.cancel()
            try:
                await self.cleanup_task
            except asyncio.CancelledError:
                pass

        logger.info("Monitoring service stopped")

    async def _update_loop(self):
        """Main update loop for broadcasting metrics."""
        while self.is_running:
            try:
                data = get_realtime_metrics()
                messages_sent = await manager.broadcast(json.dumps(data))

                if messages_sent > 0:
                    logger.debug(f"Broadcasted metrics to {messages_sent} clients")

                await asyncio.sleep(self.update_interval)
            except Exception as e:
                logger.error(f"Error in update loop: {e}")
                await asyncio.sleep(5)

    async def _cleanup_loop(self):
        """Cleanup idle connections."""
        while self.is_running:
            try:
                cleaned = manager.cleanup_idle_connections()
                if cleaned > 0:
                    logger.info(f"Cleaned up {cleaned} idle connections")
                await asyncio.sleep(self.cleanup_interval)
            except Exception as e:
                logger.error(f"Error in cleanup loop: {e}")
                await asyncio.sleep(30)

# Global monitoring service
monitoring_service = MonitoringService()

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """Enhanced WebSocket endpoint for real-time updates."""
    client_id = await manager.connect(websocket)

    try:
        # Send initial data
        initial_data = get_realtime_metrics()
        await manager.send_personal_message(json.dumps(initial_data), client_id)

        # Keep connection alive and handle client messages
        while True:
            try:
                # Wait for client messages (heartbeat, subscription changes, etc.)
                message = await websocket.receive_text()
                data = json.loads(message)

                # Handle client commands
                if data.get("type") == "ping":
                    pong_response = {"type": "pong", "timestamp": time.time()}
                    await manager.send_personal_message(json.dumps(pong_response), client_id)

                elif data.get("type") == "subscribe":
                    # Handle subscription to specific metrics (future enhancement)
                    logger.debug(f"Client {client_id} subscription request: {data}")

                elif data.get("type") == "get_history":
                    # Send historical data (future enhancement)
                    history_data = get_historical_metrics(data.get("metric"), data.get("period", "1h"))
                    await manager.send_personal_message(json.dumps(history_data), client_id)

            except WebSocketDisconnect:
                break
            except Exception as e:
                logger.warning(f"Error handling client {client_id} message: {e}")
                break

    except WebSocketDisconnect:
        pass
    finally:
        manager.disconnect(client_id)


@router.get("/metrics")
async def get_dashboard_metrics():
    """Get dashboard metrics data."""
    try:
        metrics_collector = get_metrics_collector() if METRICS_AVAILABLE else None
        health_summary = get_health_summary() if METRICS_AVAILABLE else {"status": "unknown", "alerts": []}
        queue_status = get_queue_status() if QUEUE_AVAILABLE else {"pending": 0, "failed": 0}

        return {
            "metrics": get_all_metrics(metrics_collector) if metrics_collector else {},
            "health": health_summary,
            "queue": queue_status,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Failed to get dashboard metrics: {e}")
        return {"error": str(e)}


@router.get("/alerts")
async def get_dashboard_alerts():
    """Get current alerts for the dashboard."""
    try:
        if ALERTING_AVAILABLE:
            alerting_service = get_alerting_service()
            active_alerts = alerting_service.get_active_alerts()
            alert_status = alerting_service.get_alert_status()
        else:
            active_alerts = []
            alert_status = {"status": "unknown"}

        return {
            "alerts": active_alerts,
            "status": alert_status,
            "count": len(active_alerts),
            "critical_count": len([a for a in active_alerts if a.get("alert", {}).get("severity") == "critical"]),
            "warning_count": len([a for a in active_alerts if a.get("alert", {}).get("severity") == "warning"]),
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Failed to get dashboard alerts: {e}")
        return {"error": str(e)}

@router.get("/alerts/history")
async def get_alerts_history(limit: int = 100, severity: Optional[str] = None):
    """Get alert history with filtering."""
    try:
        alerting_service = get_alerting_service()
        history = alerting_service.get_alert_history(limit=limit)

        # Filter by severity if specified
        if severity:
            history = [alert for alert in history if alert.get("severity") == severity]

        return {
            "history": history,
            "total": len(history),
            "filter": {"severity": severity} if severity else None,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Failed to get alert history: {e}")
        return {"error": str(e)}

@router.get("/system")
async def get_system_metrics():
    """Get comprehensive system metrics."""
    try:
        import psutil

        # Memory metrics
        memory = psutil.virtual_memory()
        swap = psutil.swap_memory()

        # CPU metrics
        cpu_percent = psutil.cpu_percent(interval=1)
        cpu_count = psutil.cpu_count()
        load_avg = psutil.getloadavg()

        # Disk metrics
        disk = psutil.disk_usage('/')
        disk_io = psutil.disk_io_counters()

        # Network metrics
        network = psutil.net_io_counters()

        # Process metrics
        process = psutil.Process()
        process_memory = process.memory_info()
        process_cpu = process.cpu_percent()

        # Database metrics
        db_path = Path("/home/ubuntu/dev/atlas/data/atlas.db")
        db_size = db_path.stat().st_size if db_path.exists() else 0

        return {
            "memory": {
                "total": memory.total,
                "available": memory.available,
                "used": memory.used,
                "free": memory.free,
                "percent": memory.percent,
                "swap_total": swap.total,
                "swap_used": swap.used,
                "swap_percent": swap.percent
            },
            "cpu": {
                "percent": cpu_percent,
                "count": cpu_count,
                "load_avg": load_avg,
                "process_percent": process_cpu
            },
            "disk": {
                "total": disk.total,
                "used": disk.used,
                "free": disk.free,
                "percent": disk.percent,
                "read_bytes": disk_io.read_bytes if disk_io else 0,
                "write_bytes": disk_io.write_bytes if disk_io else 0
            },
            "network": {
                "bytes_sent": network.bytes_sent,
                "bytes_recv": network.bytes_recv,
                "packets_sent": network.packets_sent,
                "packets_recv": network.packets_recv
            },
            "process": {
                "memory_rss": process_memory.rss,
                "memory_vms": process_memory.vms,
                "cpu_percent": process_cpu,
                "num_threads": process.num_threads(),
                "open_files": process.num_fds() if hasattr(process, 'num_fds') else 0
            },
            "database": {
                "size_bytes": db_size,
                "size_mb": db_size / (1024 * 1024)
            },
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Failed to get system metrics: {e}")
        return {"error": str(e)}

@router.get("/logs")
async def get_logs(
    level: Optional[str] = None,
    component: Optional[str] = None,
    limit: int = 100,
    offset: int = 0
):
    """Get recent logs with filtering."""
    try:
        # This would typically read from the actual log files
        # For now, return recent log entries from memory
        log_entries = []

        # Try to read from log files if available
        log_files = []
        log_dir = Path("/var/log/atlas")
        if log_dir.exists():
            log_files = list(log_dir.glob("*.log"))

        # Fallback to local logs directory
        if not log_files:
            local_log_dir = Path("logs/atlas")
            if local_log_dir.exists():
                log_files = list(local_log_dir.glob("*.log"))

        # Read recent log entries
        for log_file in log_files[-10:]:  # Last 10 log files
            try:
                with open(log_file, 'r') as f:
                    lines = f.readlines()
                    for line in lines[-50:]:  # Last 50 lines per file
                        try:
                            log_entry = json.loads(line.strip())
                            log_entries.append(log_entry)
                        except json.JSONDecodeError:
                            # Skip malformed log entries
                            continue
            except Exception as e:
                logger.warning(f"Failed to read log file {log_file}: {e}")
                continue

        # Sort by timestamp
        log_entries.sort(key=lambda x: x.get('timestamp', ''), reverse=True)

        # Apply filters
        if level:
            log_entries = [entry for entry in log_entries if entry.get('level') == level]

        if component:
            log_entries = [entry for entry in log_entries if entry.get('component') == component]

        # Apply pagination
        total = len(log_entries)
        log_entries = log_entries[offset:offset + limit]

        return {
            "logs": log_entries,
            "total": total,
            "offset": offset,
            "limit": limit,
            "filters": {"level": level, "component": component},
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Failed to get logs: {e}")
        return {"error": str(e)}

@router.get("/prometheus")
async def get_prometheus_metrics():
    """Get Prometheus-formatted metrics."""
    try:
        metrics_collector = get_metrics_collector()
        prometheus_output = metrics_collector.get_prometheus_metrics()

        return Response(
            content=prometheus_output,
            media_type="text/plain; version=0.0.4"
        )
    except Exception as e:
        logger.error(f"Failed to get Prometheus metrics: {e}")
        return Response(
            content=f"# Error generating metrics: {e}",
            media_type="text/plain"
        )

@router.get("/health")
async def get_health_check():
    """Get comprehensive health check."""
    try:
        if METRICS_AVAILABLE:
            metrics_collector = get_metrics_collector()
            health_summary = metrics_collector.get_health_summary()
        else:
            health_summary = {"status": "unknown"}

        # Add service-specific health checks
        service_health = {
            "monitoring_service": "healthy" if monitoring_service.is_running else "unhealthy",
            "alerting_service": "healthy" if ALERTING_AVAILABLE else "unavailable",
            "queue_manager": "healthy" if QUEUE_AVAILABLE else "unavailable",
            "metrics_collector": "healthy" if METRICS_AVAILABLE else "unavailable"
        }

        # Determine overall status
        critical_services = [status for status in service_health.values() if status in ["unhealthy", "unavailable"]]
        if health_summary.get("status") == "critical" or critical_services:
            overall_status = "critical"
        elif health_summary.get("status") == "warning":
            overall_status = "warning"
        else:
            overall_status = "healthy"

        return {
            "status": overall_status,
            "system_health": health_summary,
            "service_health": service_health,
            "checks_performed": [
                "service_status",
                "monitoring_service"
            ] + (["queue_depth", "processing_rate", "memory_usage", "disk_usage", "alert_conditions"] if METRICS_AVAILABLE else []),
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Failed to get health check: {e}")
        return {
            "status": "critical",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }

@router.get("/connections")
async def get_connection_stats():
    """Get WebSocket connection statistics."""
    try:
        stats = manager.get_connection_stats()
        return {
            **stats,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Failed to get connection stats: {e}")
        return {"error": str(e)}


def get_all_metrics(metrics_collector) -> Dict[str, Any]:
    """Get all current metrics for dashboard display."""
    metrics_data = {}

    for metric_name, metric in metrics_collector._metrics.items():
        latest_value = metrics_collector.get_metric_value(metric_name)
        if latest_value is not None:
            metrics_data[metric_name] = {
                "value": latest_value,
                "type": metric.metric_type,
                "help": metric.help_text
            }

    return metrics_data


def get_realtime_metrics() -> Dict[str, Any]:
    """Get real-time metrics for WebSocket updates."""
    try:
        metrics_collector = get_metrics_collector() if METRICS_AVAILABLE else None
        health_summary = get_health_summary() if METRICS_AVAILABLE else {"status": "unknown", "alerts": []}
        queue_status = get_queue_status() if QUEUE_AVAILABLE else {"pending": 0, "failed": 0}

        alerts_data = {}
        if ALERTING_AVAILABLE:
            alerting_service = get_alerting_service()
            alerts_data = {
                "active": alerting_service.get_active_alerts(),
                "status": alerting_service.get_alert_status()
            }
        else:
            alerts_data = {"active": [], "status": "unknown"}

        return {
            "type": "metrics_update",
            "data": {
                "metrics": get_all_metrics(metrics_collector) if metrics_collector else {},
                "health": health_summary,
                "queue": queue_status,
                "alerts": alerts_data,
                "timestamp": datetime.utcnow().isoformat()
            }
        }
    except Exception as e:
        logger.error(f"Failed to get realtime metrics: {e}")
        return {"type": "error", "message": str(e)}

def get_historical_metrics(metric_name: str, period: str = "1h") -> Dict[str, Any]:
    """Get historical metrics for a specific time period."""
    # Placeholder implementation - would typically query a time-series database
    return {
        "type": "historical_data",
        "metric": metric_name,
        "period": period,
        "data": [],
        "message": "Historical metrics not yet implemented"
    }

# Service lifecycle functions
async def start_monitoring_service():
    """Start the monitoring service."""
    await monitoring_service.start()

async def stop_monitoring_service():
    """Stop the monitoring service."""
    await monitoring_service.stop()


def get_enhanced_dashboard_html() -> str:
    """Generate enhanced monitoring dashboard HTML with real-time updates."""
    return """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Atlas Monitoring Dashboard</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #0f172a;
            color: #e2e8f0;
            line-height: 1.6;
        }

        .container {
            max-width: 1400px;
            margin: 0 auto;
            padding: 20px;
        }

        .header {
            background: #1e293b;
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .header h1 {
            color: #60a5fa;
            font-size: 2rem;
        }

        .status-indicator {
            display: flex;
            align-items: center;
            gap: 10px;
            font-weight: bold;
        }

        .status-dot {
            width: 12px;
            height: 12px;
            border-radius: 50%;
            animation: pulse 2s infinite;
        }

        .status-healthy { background: #22c55e; }
        .status-warning { background: #f59e0b; }
        .status-critical { background: #ef4444; }

        @keyframes pulse {
            0% { opacity: 1; }
            50% { opacity: 0.5; }
            100% { opacity: 1; }
        }

        .metrics-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }

        .metric-card {
            background: #1e293b;
            border-radius: 10px;
            padding: 20px;
            border: 1px solid #334155;
            transition: all 0.3s ease;
        }

        .metric-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 25px rgba(0,0,0,0.3);
        }

        .metric-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 15px;
        }

        .metric-title {
            color: #94a3b8;
            font-size: 0.9rem;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }

        .metric-value {
            font-size: 2rem;
            font-weight: bold;
            color: #60a5fa;
        }

        .metric-change {
            font-size: 0.8rem;
            color: #22c55e;
        }

        .metric-change.negative {
            color: #ef4444;
        }

        .alerts-section {
            background: #1e293b;
            border-radius: 10px;
            padding: 20px;
            margin-bottom: 20px;
        }

        .alert-item {
            display: flex;
            align-items: center;
            padding: 10px;
            margin: 10px 0;
            border-radius: 5px;
            border-left: 4px solid;
        }

        .alert-critical {
            background: rgba(239, 68, 68, 0.1);
            border-color: #ef4444;
        }

        .alert-warning {
            background: rgba(245, 158, 11, 0.1);
            border-color: #f59e0b;
        }

        .charts-section {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(500px, 1fr));
            gap: 20px;
            margin-top: 20px;
        }

        .chart-container {
            background: #1e293b;
            border-radius: 10px;
            padding: 20px;
            height: 300px;
            position: relative;
        }

        .connection-status {
            position: fixed;
            top: 20px;
            right: 20px;
            background: #1e293b;
            padding: 10px;
            border-radius: 5px;
            font-size: 0.9rem;
            border: 1px solid #334155;
        }

        .connected {
            color: #22c55e;
        }

        .disconnected {
            color: #ef4444;
        }

        .loading {
            opacity: 0.6;
        }

        .refresh-btn {
            background: #3b82f6;
            color: white;
            border: none;
            padding: 8px 16px;
            border-radius: 5px;
            cursor: pointer;
            font-size: 0.9rem;
            transition: background 0.3s ease;
        }

        .refresh-btn:hover {
            background: #2563eb;
        }

        .time-ago {
            font-size: 0.8rem;
            color: #64748b;
            margin-top: 5px;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🚀 Atlas Monitoring Dashboard</h1>
            <div class="status-indicator">
                <div id="status-dot" class="status-dot status-healthy"></div>
                <span id="status-text">Healthy</span>
            </div>
        </div>

        <div class="connection-status" id="connection-status">
            <span id="connection-text">Connecting...</span>
        </div>

        <div class="metrics-grid">
            <div class="metric-card">
                <div class="metric-header">
                    <span class="metric-title">Queue Pending</span>
                    <button class="refresh-btn" onclick="refreshData()">Refresh</button>
                </div>
                <div class="metric-value" id="queue-pending">0</div>
                <div class="time-ago" id="queue-time">Loading...</div>
            </div>

            <div class="metric-card">
                <div class="metric-header">
                    <span class="metric-title">Transcription Rate</span>
                    <span class="metric-title">per minute</span>
                </div>
                <div class="metric-value" id="transcription-rate">0.0</div>
                <div class="time-ago" id="rate-time">Loading...</div>
            </div>

            <div class="metric-card">
                <div class="metric-header">
                    <span class="metric-title">Memory Usage</span>
                    <span class="metric-title">MB</span>
                </div>
                <div class="metric-value" id="memory-usage">0</div>
                <div class="time-ago" id="memory-time">Loading...</div>
            </div>

            <div class="metric-card">
                <div class="metric-header">
                    <span class="metric-title">System Uptime</span>
                    <span class="metric-title">hours</span>
                </div>
                <div class="metric-value" id="uptime">0</div>
                <div class="time-ago" id="uptime-time">Loading...</div>
            </div>

            <div class="metric-card">
                <div class="metric-header">
                    <span class="metric-title">Active Alerts</span>
                    <span id="alert-count" class="metric-value">0</span>
                </div>
                <div class="time-ago" id="alert-time">Loading...</div>
            </div>

            <div class="metric-card">
                <div class="metric-header">
                    <span class="metric-title">Success Rate</span>
                    <span class="metric-title">%</span>
                </div>
                <div class="metric-value" id="success-rate">0</div>
                <div class="time-ago" id="success-time">Loading...</div>
            </div>
        </div>

        <div class="alerts-section">
            <h3>🚨 Active Alerts</h3>
            <div id="alerts-container">
                <p style="color: #64748b; padding: 20px;">No active alerts</p>
            </div>
        </div>

        <div class="charts-section">
            <div class="chart-container">
                <h3>📊 System Performance</h3>
                <canvas id="performance-chart"></canvas>
            </div>
            <div class="chart-container">
                <h3>📈 Queue Status</h3>
                <canvas id="queue-chart"></canvas>
            </div>
        </div>
    </div>

    <script>
        let ws = null;
        let isConnected = false;
        let performanceChart = null;
        let queueChart = null;

        function connectWebSocket() {
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            const wsUrl = `${protocol}//${window.location.host}/monitoring/ws`;

            ws = new WebSocket(wsUrl);

            ws.onopen = function() {
                isConnected = true;
                updateConnectionStatus('Connected', true);
                console.log('WebSocket connected');
            };

            ws.onmessage = function(event) {
                try {
                    const data = JSON.parse(event.data);
                    updateDashboard(data);
                } catch (e) {
                    console.error('Error parsing WebSocket message:', e);
                }
            };

            ws.onclose = function() {
                isConnected = false;
                updateConnectionStatus('Disconnected', false);
                console.log('WebSocket disconnected');
                // Attempt to reconnect after 5 seconds
                setTimeout(connectWebSocket, 5000);
            };

            ws.onerror = function(error) {
                console.error('WebSocket error:', error);
                updateConnectionStatus('Error', false);
            };
        }

        function updateConnectionStatus(text, connected) {
            const statusEl = document.getElementById('connection-status');
            const textEl = document.getElementById('connection-text');
            textEl.textContent = text;
            statusEl.className = connected ? 'connection-status connected' : 'connection-status disconnected';
        }

        function updateDashboard(data) {
            if (data.type !== 'metrics_update') return;

            const metrics = data.data.metrics;
            const health = data.data.health;
            const queue = data.data.queue;

            // Update metrics
            updateMetric('queue-pending', metrics.atlas_queue_pending_total?.value || 0);
            updateMetric('transcription-rate', metrics.atlas_transcription_rate?.value || 0.0);
            updateMetric('memory-usage', Math.round((metrics.atlas_memory_usage_bytes?.value || 0) / 1024 / 1024));
            updateMetric('uptime', Math.round((metrics.atlas_system_uptime_seconds?.value || 0) / 3600));

            // Update alerts
            const alertCount = health.alerts?.length || 0;
            document.getElementById('alert-count').textContent = alertCount;

            // Update status
            updateSystemStatus(health.status);

            // Update alerts display
            updateAlerts(health.alerts || []);

            // Update timestamps
            const timestamp = new Date(data.data.timestamp).toLocaleTimeString();
            document.querySelectorAll('.time-ago').forEach(el => {
                el.textContent = `Last updated: ${timestamp}`;
            });

            // Update charts
            updateCharts(data.data);
        }

        function updateMetric(id, value) {
            const element = document.getElementById(id);
            if (element) {
                element.textContent = typeof value === 'number' ? value.toFixed(1) : value;
            }
        }

        function updateSystemStatus(status) {
            const statusDot = document.getElementById('status-dot');
            const statusText = document.getElementById('status-text');

            statusDot.className = `status-dot status-${status}`;
            statusText.textContent = status.charAt(0).toUpperCase() + status.slice(1);
        }

        function updateAlerts(alerts) {
            const container = document.getElementById('alerts-container');

            if (alerts.length === 0) {
                container.innerHTML = '<p style="color: #64748b; padding: 20px;">No active alerts</p>';
                return;
            }

            container.innerHTML = alerts.map(alert => `
                <div class="alert-item alert-${alert.severity}">
                    <div>
                        <strong>${alert.severity.toUpperCase()}</strong>: ${alert.message}
                        <br>
                        <small>Metric: ${alert.metric} | Value: ${alert.value}</small>
                    </div>
                </div>
            `).join('');
        }

        function updateCharts(data) {
            // Simple chart implementation (in production, use Chart.js or similar)
            console.log('Updating charts with data:', data);
        }

        function refreshData() {
            // Manual refresh
            fetch('/monitoring/metrics')
                .then(response => response.json())
                .then(data => {
                    if (data.error) {
                        console.error('Error fetching metrics:', data.error);
                        return;
                    }
                    updateDashboard({
                        type: 'metrics_update',
                        data: data
                    });
                })
                .catch(error => {
                    console.error('Error refreshing data:', error);
                });
        }

        // Initialize WebSocket connection
        connectWebSocket();

        // Initial data load
        refreshData();

        // Set up periodic refresh as fallback
        setInterval(refreshData, 30000); // Refresh every 30 seconds if WebSocket fails
    </script>
</body>
</html>
    """


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("monitoring_dashboard_service:router", host="0.0.0.0", port=7445, reload=True)