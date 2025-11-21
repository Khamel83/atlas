# Atlas Production Reliability Documentation

## Overview

Atlas has been transformed into a production-grade reliable ingest engine with comprehensive monitoring, configuration management, and operational tooling. This document covers all reliability features and operational procedures.

## System Architecture

### Core Components

1. **Atlas API** (`api.py`) - Main FastAPI service with health monitoring
2. **Atlas Core** (`core/`) - Core processing engine with reliability features
3. **Atlas Services** (`services/`) - Background processing services
4. **Operational Tools** (`tools/`) - Management and monitoring tools
5. **Configuration System** (`config/`, `helpers/`) - Centralized config and secrets

### Service Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Atlas API     │    │ Atlas Services  │    │   Monitoring    │
│   (FastAPI)     │    │  (Workers)      │    │    Agent        │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
         ┌───────────────────────┼───────────────────────┐
         │                       │                       │
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│ Configuration  │    │   Database      │    │   Alerting     │
│    Manager     │    │   (SQLite)      │    │   System       │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## systemd Services

### Service Files

- `atlas-api.service` - Main API service
- `atlas-core.service` - Core processing engine
- `atlas-services.service` - Background services
- `atlas-monitoring.service` - Monitoring agent

### Service Management

```bash
# Start all services
sudo systemctl start atlas-api atlas-core atlas-services atlas-monitoring

# Enable services on boot
sudo systemctl enable atlas-api atlas-core atlas-services atlas-monitoring

# Check service status
sudo systemctl status atlas*

# View logs
journalctl -u atlas-api -f
```

## Configuration Management

### Environment-Specific Configuration

Configuration is organized by environment:

- `config/development.env` - Development settings
- `config/staging.env` - Staging/production-like settings
- `config/production.env` - Production optimized settings

### Key Configuration Categories

1. **API Configuration**
   - Host, port, CORS settings
   - Rate limiting and timeouts
   - Security headers

2. **Database Configuration**
   - SQLite with WAL mode
   - Connection pooling
   - Backup settings

3. **Monitoring Configuration**
   - Metrics collection intervals
   - Alert thresholds
   - Notification channels

4. **Resource Limits**
   - Memory limits
   - CPU limits
   - File descriptors

### Secrets Management

Secrets are encrypted using Fernet encryption:

- `config/development.secrets` - Development secrets
- `config/staging.secrets` - Staging secrets
- `config/production.secrets` - Production secrets

## Operational Tooling

### Atlas Operations CLI (`tools/atlas_ops.py`)

Comprehensive operations management tool:

```bash
# Service management
python tools/atlas_ops.py service start api
python tools/atlas_ops.py service status --all
python tools/atlas_ops.py service restart core

# Backup and restore
python tools/atlas_ops.py backup create
python tools/atlas_ops.py backup restore /backups/atlas_backup_20250917.tar.gz

# Monitoring
python tools/atlas_ops.py monitoring status
python tools/atlas_ops.py monitoring metrics --format json

# Maintenance
python tools/atlas_ops.py maintenance mode --enable
python tools/atlas_ops.py system check --health
```

### Deployment Manager (`tools/deployment_manager.py`)

Version control and deployment management:

```bash
# List available versions
python tools/deployment_manager.py version list

# Deploy new version
python tools/deployment_manager.py deploy --version v2.1.0 --environment staging --strategy rolling

# Rollback deployment
python tools/deployment_manager.py rollback --environment staging --target-version v2.0.0

# Blue-green deployment
python tools/deployment_manager.py deploy --version v2.1.0 --environment production --strategy blue-green
```

### Monitoring Agent (`tools/monitoring_agent.py`)

Real-time monitoring and alerting:

```bash
# Start monitoring daemon
python tools/monitoring_agent.py --daemon --config config/monitoring.yaml

# Check system health
python tools/monitoring_agent.py --check-health

# Test alert notifications
python tools/monitoring_agent.py --test-alerts
```

## Monitoring and Observability

### Metrics Collection

The system collects comprehensive metrics:

1. **System Metrics**
   - CPU usage, memory usage, disk space, network I/O
   - Process count, file descriptors, load average

2. **Application Metrics**
   - API response times, error rates, request counts
   - Database operations, queue lengths, processing times

3. **Business Metrics**
   - Items processed, success rates, backlog size
   - Processing throughput, latency percentiles

### Health Checks

Automated health checks monitor:

- **API Health**: Endpoint responsiveness and error rates
- **Database Health**: Connection status and query performance
- **Service Health**: Background service status and processing rates
- **Disk Health**: Available space and I/O performance
- **Memory Health**: Usage levels and swap activity

### Alerting System

Multi-channel alerting with configurable thresholds:

1. **Email Notifications**
   - Critical alerts via email
   - Configurable recipients and severity levels

2. **Webhook Notifications**
   - Integration with external systems
   - Custom payload formatting

3. **Slack Integration**
   - Real-time alerts in Slack channels
   - Interactive messages with actions

## Reliability Features

### Ingestion Reliability

1. **Adaptive Rate Limiting**
   - Dynamic adjustment based on system load
   - Token bucket algorithm for smooth throttling

2. **Circuit Breakers**
   - Automatic failure detection and isolation
   - Gradual recovery with health checks

3. **Dead Letter Queues**
   - Failed message isolation and retry logic
   - Exponential backoff for retries

4. **Predictive Scaling**
   - Historical pattern analysis
   - Resource allocation based on predicted load

### Database Reliability

1. **SQLite with WAL Mode**
   - Concurrent read access during writes
   - Crash recovery and consistency

2. **Connection Pooling**
   - Efficient connection management
   - Timeout and retry logic

3. **Automated Backups**
   - Scheduled backups with retention policies
   - Backup integrity verification

4. **Performance Monitoring**
   - Query execution times
   - Index usage analysis

## Deployment Procedures

### Initial Setup

1. **Environment Preparation**
   ```bash
   # Create directories
   sudo mkdir -p /opt/atlas/{config,logs,backups,data}
   sudo chown -R atlas:atlas /opt/atlas

   # Install dependencies
   pip install -r requirements.txt
   pip install -r requirements-dev.txt
   ```

2. **Configuration Setup**
   ```bash
   # Copy configuration files
   cp config/*.env /opt/atlas/config/
   cp config/*.secrets /opt/atlas/config/

   # Set environment
   export ATLAS_ENVIRONMENT=production
   ```

3. **Service Installation**
   ```bash
   # Copy service files
   sudo cp *.service /etc/systemd/system/

   # Reload systemd
   sudo systemctl daemon-reload

   # Enable and start services
   sudo systemctl enable atlas-api atlas-core atlas-services atlas-monitoring
   sudo systemctl start atlas-api atlas-core atlas-services atlas-monitoring
   ```

### Deployment Process

1. **Pre-deployment Checks**
   ```bash
   # Run health checks
   python tools/atlas_ops.py system check --health

   # Create backup
   python tools/atlas_ops.py backup create
   ```

2. **Deployment**
   ```bash
   # Deploy new version
   python tools/deployment_manager.py deploy --version v2.1.0 --environment production --strategy rolling

   # Monitor deployment
   python tools/deployment_manager.py deployment status --environment production
   ```

3. **Post-deployment Verification**
   ```bash
   # Verify service health
   python tools/atlas_ops.py service status --all

   # Check metrics
   python tools/atlas_ops.py monitoring metrics --format json
   ```

### Rollback Procedure

```bash
# Initiate rollback
python tools/deployment_manager.py rollback --environment production --target-version v2.0.0

# Monitor rollback progress
python tools/deployment_manager.py deployment status --environment production

# Verify system stability
python tools/atlas_ops.py system check --health
```

## Monitoring and Alerting Configuration

### Alert Thresholds

Configure thresholds in `config/alerting.yaml`:

```yaml
alerts:
  cpu_usage:
    warning: 70
    critical: 85
    cooldown: 300  # 5 minutes

  memory_usage:
    warning: 80
    critical: 90
    cooldown: 300

  disk_usage:
    warning: 85
    critical: 95
    cooldown: 600  # 10 minutes

  api_error_rate:
    warning: 5     # 5%
    critical: 10   # 10%
    cooldown: 180  # 3 minutes
```

### Notification Channels

Configure channels in `config/monitoring.yaml`:

```yaml
notifications:
  email:
    enabled: true
    smtp_server: smtp.gmail.com
    smtp_port: 587
    username: your-email@gmail.com
    password: your-app-password

  webhook:
    enabled: true
    url: https://hooks.slack.com/services/YOUR/WEBHOOK/URL
    headers:
      Content-Type: application/json

  slack:
    enabled: true
    webhook_url: https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK
    channel: "#alerts"
```

## Troubleshooting

### Common Issues

1. **Service Not Starting**
   ```bash
   # Check service logs
   journalctl -u atlas-api -n 50

   # Check configuration
   python tools/config_cli.py validate --all

   # Verify permissions
   ls -la /opt/atlas/
   ```

2. **High Memory Usage**
   ```bash
   # Check memory metrics
   python tools/atlas_ops.py monitoring metrics --filter memory

   # Restart services
   python tools/atlas_ops.py service restart all

   # Check for memory leaks
   python tools/atlas_ops.py monitoring analyze --memory
   ```

3. **Database Performance Issues**
   ```bash
   # Check database health
   python tools/atlas_ops.py system check --database

   # Optimize database
   python tools/atlas_ops.py database optimize

   # Create backup before maintenance
   python tools/atlas_ops.py backup create
   ```

### Log Analysis

```bash
# View recent logs
journalctl -u atlas-api --since "1 hour ago"

# Filter by error level
journalctl -u atlas-api -p err

# Export logs for analysis
journalctl -u atlas-api --since yesterday > atlas_api_logs_$(date +%Y%m%d).log
```

## Performance Optimization

### Database Optimization

1. **Enable WAL Mode**
   ```bash
   # Execute in database
   PRAGMA journal_mode=WAL;
   PRAGMA synchronous=NORMAL;
   PRAGMA cache_size=10000;
   ```

2. **Regular Maintenance**
   ```bash
   # Run maintenance commands
   python tools/atlas_ops.py database optimize

   # Vacuum and analyze
   python tools/atlas_ops.py database vacuum
   ```

### API Optimization

1. **Caching Strategy**
   - Implement Redis caching for frequent queries
   - Cache API responses where appropriate

2. **Connection Pooling**
   - Configure optimal pool sizes
   - Set appropriate timeouts

3. **Resource Limits**
   - Adjust worker processes based on available resources
   - Configure memory limits per process

## Security Considerations

### Configuration Security

1. **Secrets Management**
   - Use encrypted secrets files
   - Rotate encryption keys regularly
   - Limit access to secret files

2. **Service Security**
   - Run services as non-root user
   - Use security hardening options
   - Restrict network access

### Network Security

1. **Firewall Configuration**
   ```bash
   # Allow only necessary ports
   sudo ufw allow 8000/tcp    # API port
   sudo ufw allow 8001/tcp    # Alternative API port
   sudo ufw enable
   ```

2. **SSL/TLS Configuration**
   - Use HTTPS in production
   - Configure proper certificates
   - Enable HSTS headers

## Backup and Recovery

### Backup Strategy

1. **Automated Backups**
   ```bash
   # Configure automated backups
   python tools/atlas_ops.py backup schedule --daily --retain 7
   python tools/atlas_ops.py backup schedule --weekly --retain 4
   ```

2. **Manual Backup**
   ```bash
   # Create full backup
   python tools/atlas_ops.py backup create --full

   # Create database-only backup
   python tools/atlas_ops.py backup create --database-only
   ```

### Recovery Procedures

1. **Database Recovery**
   ```bash
   # Restore database from backup
   python tools/atlas_ops.py backup restore --database /path/to/backup.sql

   # Verify data integrity
   python tools/atlas_ops.py system check --database
   ```

2. **Full System Recovery**
   ```bash
   # Restore complete system
   python tools/atlas_ops.py backup restore /path/to/full_backup.tar.gz

   # Restart services
   python tools/atlas_ops.py service start all
   ```

## Testing and Validation

### Reliability Testing

```bash
# Run reliability tests
python test_reliability.py

# Load testing
python tools/atlas_ops.py test load --duration 300 --concurrent 50

# Failover testing
python tools/atlas_ops.py test failover
```

### Integration Testing

```bash
# Test all components
python test_system_integration.py

# Test configuration management
python test_configuration_management.py

# Test operational tools
python test_operational_tools.py
```

## Support and Maintenance

### Regular Maintenance Tasks

1. **Daily Tasks**
   - Check system health
   - Review alert logs
   - Verify backup integrity

2. **Weekly Tasks**
   - Review performance metrics
   - Update security patches
   - Test failover procedures

3. **Monthly Tasks**
   - Full system audit
   - Capacity planning
   - Security assessment

### Contact and Support

- **Critical Issues**: Immediate alerting via configured channels
- **Non-Critical Issues**: Email support with 24-hour response
- **Maintenance Windows**: Scheduled maintenance with advance notice

---

## Version History

- **v2.1.0**: Production reliability implementation
  - Comprehensive monitoring and alerting
  - Configuration management system
  - Operational tooling suite
  - Deployment automation

- **v2.0.0**: Core system stabilization
  - SQLite with WAL mode
  - Basic health monitoring
  - Service reliability improvements

---

**Last Updated**: 2025-09-17
**Maintainer**: Atlas Development Team
**Contact**: support@atlas-system.com