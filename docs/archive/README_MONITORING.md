# Atlas Monitoring Dashboard

## Overview
The Atlas Monitoring Dashboard provides real-time monitoring and visualization of the Atlas podcast transcript management system.

## Features

### 🚀 Real-time Monitoring
- **WebSocket Support**: Live updates without page refresh
- **System Metrics**: CPU, memory, disk usage monitoring
- **Queue Status**: Real-time transcript processing queue status
- **Health Monitoring**: System health and service availability

### 📊 Dashboard Components
- **Key Metrics Cards**: Queue pending, transcription rate, memory usage, uptime
- **Alerts System**: Active alerts with severity levels (critical, warning)
- **Performance Charts**: Visual representation of system performance over time
- **Connection Management**: WebSocket connection statistics

### 🔧 API Endpoints
- `GET /monitoring/` - Main dashboard interface
- `GET /monitoring/metrics` - Current system metrics
- `GET /monitoring/alerts` - Active alerts
- `GET /monitoring/alerts/history` - Alert history
- `GET /monitoring/system` - Detailed system metrics
- `GET /monitoring/logs` - Recent log entries
- `GET /monitoring/prometheus` - Prometheus-formatted metrics
- `GET /monitoring/health` - Comprehensive health check
- `GET /monitoring/connections` - WebSocket connection stats
- `WebSocket /monitoring/ws` - Real-time updates

## Usage

### Starting the Service
```bash
# Start the monitoring service
./start_monitoring.sh start

# Check status
./start_monitoring.sh status

# Stop the service
./start_monitoring.sh stop

# Restart the service
./start_monitoring.sh restart
```

### Accessing the Dashboard
- **Main Dashboard**: http://localhost:7445/monitoring/
- **Health Check**: http://localhost:7445/health
- **API Documentation**: FastAPI auto-docs available at /docs

### Real-time Features
- **Auto-refresh**: Dashboard updates every 5 seconds via WebSocket
- **Live Metrics**: System metrics updated in real-time
- **Alert Notifications**: Immediate alert notifications
- **Connection Status**: WebSocket connection indicator

## Architecture

### Service Components
1. **Monitoring Service**: FastAPI-based web service
2. **WebSocket Manager**: Handles real-time client connections
3. **Metrics Collector**: Gathers system and application metrics
4. **Alert System**: Monitors and triggers alerts based on thresholds
5. **Health Checker**: Comprehensive system health monitoring

### Integration Points
- **Atlas Manager**: Main podcast processing system
- **Database**: SQLite database for metrics storage
- **System Metrics**: psutil for system monitoring
- **Logging**: Integrated with Atlas logging system

## Configuration

### Service Settings
- **Port**: 7445 (configurable in monitoring_service.py)
- **Host**: 0.0.0.0 (listens on all interfaces)
- **Update Interval**: 5 seconds for real-time updates
- **WebSocket Timeout**: 300 seconds (5 minutes)

### Metrics Collected
- **System Metrics**: CPU, memory, disk, network usage
- **Queue Metrics**: Pending tasks, failed tasks, processing rate
- **Database Metrics**: Connection count, query performance
- **Service Metrics**: Uptime, error rates, request counts

## Monitoring Data

### Example Metrics Response
```json
{
  "metrics": {
    "atlas_queue_pending_total": {"value": 5100},
    "atlas_transcription_rate": {"value": 2.5},
    "atlas_memory_usage_bytes": {"value": 1073741824},
    "atlas_system_uptime_seconds": {"value": 86400}
  },
  "health": {
    "status": "healthy",
    "alerts": []
  },
  "queue": {
    "pending": 5100,
    "failed": 111
  }
}
```

### System Metrics
```json
{
  "memory": {
    "total": 8589934592,
    "used": 2348810240,
    "percent": 27.3
  },
  "cpu": {
    "percent": 15.2,
    "count": 4
  },
  "disk": {
    "total": 107374182400,
    "used": 100000000000,
    "percent": 93.1
  }
}
```

## Troubleshooting

### Common Issues
1. **Service won't start**: Check port 7445 is available
2. **WebSocket connection fails**: Verify firewall settings
3. **Metrics not updating**: Check Atlas Manager is running
4. **High memory usage**: Restart monitoring service

### Logs
- **Service Logs**: `logs/monitoring_service.log`
- **Output Logs**: `logs/monitoring_output.log`
- **Access Logs**: Available through /monitoring/logs endpoint

### Health Check
```bash
curl http://localhost:7445/health
```

## Security Considerations

### Current Configuration
- **CORS**: Open for development (restrict in production)
- **Authentication**: None (add for production deployment)
- **Rate Limiting**: Not implemented (add for production)

### Production Recommendations
1. **Authentication**: Implement API key or OAuth
2. **HTTPS**: Enable SSL/TLS
3. **Rate Limiting**: Implement request throttling
4. **CORS**: Restrict to specific domains
5. **Firewall**: Restrict access to monitoring endpoints

## Future Enhancements

### Planned Features
- **Historical Data**: Time-series database integration
- **Custom Alerts**: User-defined alert thresholds
- **Export Functionality**: CSV/PDF report generation
- **User Management**: Role-based access control
- **Mobile Support**: Responsive design improvements
- **Notification System**: Email/Slack integration

### Integration Opportunities
- **Prometheus Integration**: Native Prometheus metrics
- **Grafana Dashboards**: Pre-built Grafana templates
- **ELK Stack**: Centralized log management
- **Kubernetes**: Container orchestration support

---

**Status**: ✅ Implemented and running
**Version**: 1.0.0
**Last Updated**: 2025-09-28