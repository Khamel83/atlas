# Atlas Operations Guide

## Quick Start

### First-Time Setup

1. **Install Services**
   ```bash
   # Copy service files
   sudo cp *.service /etc/systemd/system/
   sudo systemctl daemon-reload

   # Create directories
   sudo mkdir -p /opt/atlas/{config,logs,backups,data}
   sudo chown -R atlas:atlas /opt/atlas
   ```

2. **Configure Environment**
   ```bash
   # Set environment
   export ATLAS_ENVIRONMENT=production

   # Test configuration
   python tools/config_cli.py validate --all
   ```

3. **Start Services**
   ```bash
   sudo systemctl start atlas-api atlas-core atlas-services atlas-monitoring
   sudo systemctl enable atlas-api atlas-core atlas-services atlas-monitoring
   ```

### Common Operations

```bash
# Check system status
python tools/atlas_ops.py system status

# View monitoring metrics
python tools/atlas_ops.py monitoring metrics

# Create backup
python tools/atlas_ops.py backup create

# Check service health
python tools/atlas_ops.py service status --all
```

## Service Management

### Atlas Operations CLI

The `atlas_ops.py` tool provides comprehensive service management:

```bash
# Service control
python tools/atlas_ops.py service start api
python tools/atlas_ops.py service stop core
python tools/atlas_ops.py service restart services
python tools/atlas_ops.py service status --all

# Service information
python tools/atlas_ops.py service info api
python tools/atlas_ops.py service logs api --lines 50
```

### Systemd Commands

Direct systemd management:

```bash
# Service management
sudo systemctl start atlas-api
sudo systemctl stop atlas-core
sudo systemctl restart atlas-services
sudo systemctl status atlas-monitoring

# Service configuration
sudo systemctl enable atlas-api
sudo systemctl disable atlas-core
sudo systemctl daemon-reload

# Log viewing
journalctl -u atlas-api -f
journalctl -u atlas-core --since "1 hour ago"
journalctl -u atlas-services -n 100
```

## Configuration Management

### Configuration CLI

Use `config_cli.py` for configuration management:

```bash
# View configuration
python tools/config_cli.py show api.host
python tools/config_cli.py show --all --format json

# Set configuration
python tools/config_cli.py set api.host 0.0.0.0
python tools/config_cli.py set monitoring.enabled true

# Environment management
python tools/config_cli.py env production
python tools/config_cli.py env development

# Validation
python tools/config_cli.py validate --all
python tools/config_cli.py validate api
```

### Secrets Management

```bash
# Set secrets
python tools/config_cli.py secret set database.password
python tools/config_cli.py secret set api.secret_key

# View secrets (masked)
python tools/config_cli.py secret list

# Generate encryption key
python tools/config_cli.py secret generate-key
```

## Monitoring and Alerting

### Real-time Monitoring

```bash
# Start monitoring agent
python tools/monitoring_agent.py --daemon --config config/monitoring.yaml

# Check system health
python tools/monitoring_agent.py --check-health

# View current metrics
python tools/atlas_ops.py monitoring metrics --format json

# View specific metrics
python tools/atlas_ops.py monitoring metrics --filter cpu
python tools/atlas_ops.py monitoring metrics --filter memory
```

### Alert Management

```bash
# Test alert notifications
python tools/monitoring_agent.py --test-alerts

# Check alert history
python tools/atlas_ops.py monitoring alerts --history

# Configure alert thresholds
python tools/config_cli.py set alerts.cpu_usage.warning 70
python tools/config_cli.py set alerts.memory_usage.critical 90
```

### Performance Analysis

```bash
# Analyze system performance
python tools/atlas_ops.py monitoring analyze --performance

# Check for bottlenecks
python tools/atlas_ops.py monitoring analyze --bottlenecks

# Resource usage report
python tools/atlas_ops.py monitoring report --resources
```

## Deployment Management

### Version Control

```bash
# List available versions
python tools/deployment_manager.py version list

# Show version details
python tools/deployment_manager.py version show v2.1.0

# Check current version
python tools/deployment_manager.py version current
```

### Deployment Operations

```bash
# Rolling deployment
python tools/deployment_manager.py deploy --version v2.1.0 --environment production --strategy rolling

# Blue-green deployment
python tools/deployment_manager.py deploy --version v2.1.0 --environment production --strategy blue-green

# Monitor deployment
python tools/deployment_manager.py deployment status --environment production
```

### Rollback Operations

```bash
# List previous versions
python tools/deployment_manager.py version list --previous

# Rollback to specific version
python tools/deployment_manager.py rollback --environment production --target-version v2.0.0

# Quick rollback (to previous version)
python tools/deployment_manager.py rollback --environment production --quick
```

## Backup and Recovery

### Backup Operations

```bash
# Create backup
python tools/atlas_ops.py backup create

# Create full backup
python tools/atlas_ops.py backup create --full

# List backups
python tools/atlas_ops.py backup list

# Schedule backups
python tools/atlas_ops.py backup schedule --daily --retain 7
python tools/atlas_ops.py backup schedule --weekly --retain 4
```

### Recovery Operations

```bash
# Restore from backup
python tools/atlas_ops.py backup restore /backups/atlas_backup_20250917.tar.gz

# Restore database only
python tools/atlas_ops.py backup restore --database /backups/db_backup_20250917.sql

# Verify backup integrity
python tools/atlas_ops.py backup verify /backups/atlas_backup_20250917.tar.gz
```

## Database Operations

### Database Maintenance

```bash
# Optimize database
python tools/atlas_ops.py database optimize

# Vacuum database
python tools/atlas_ops.py database vacuum

# Check database health
python tools/atlas_ops.py system check --database

# Database statistics
python tools/atlas_ops.py database stats
```

### Database Administration

```bash
# Create database backup
python tools/atlas_ops.py database backup

# Restore database
python tools/atlas_ops.py database restore /backups/db_backup.sql

# Run database migrations
python tools/atlas_ops.py database migrate
```

## System Maintenance

### Health Checks

```bash
# Comprehensive health check
python tools/atlas_ops.py system check --health

# Specific component checks
python tools/atlas_ops.py system check --api
python tools/atlas_ops.py system check --database
python tools/atlas_ops.py system check --services

# Automated healing
python tools/atlas_ops.py system heal
```

### Maintenance Mode

```bash
# Enable maintenance mode
python tools/atlas_ops.py maintenance mode --enable --reason "System maintenance"

# Disable maintenance mode
python tools/atlas_ops.py maintenance mode --disable

# Check maintenance status
python tools/atlas_ops.py maintenance status
```

### System Updates

```bash
# Check for updates
python tools/atlas_ops.py system update --check

# Apply updates
python tools/atlas_ops.py system update --apply

# Post-update verification
python tools/atlas_ops.py system check --health
```

## Troubleshooting

### Common Issues

#### Service Not Starting

```bash
# Check service logs
journalctl -u atlas-api -n 50

# Check configuration
python tools/config_cli.py validate --all

# Check permissions
ls -la /opt/atlas/

# Check resource availability
python tools/atlas_ops.py system check --resources
```

#### High Memory Usage

```bash
# Check memory metrics
python tools/atlas_ops.py monitoring metrics --filter memory

# Check memory leaks
python tools/atlas_ops.py monitoring analyze --memory

# Restart services
python tools/atlas_ops.py service restart all

# Clear caches
python tools/atlas_ops.py maintenance clear-cache
```

#### Database Performance Issues

```bash
# Check database health
python tools/atlas_ops.py system check --database

# Check slow queries
python tools/atlas_ops.py database slow-queries

# Optimize database
python tools/atlas_ops.py database optimize

# Check connections
python tools/atlas_ops.py database connections
```

#### API Performance Issues

```bash
# Check API metrics
python tools/atlas_ops.py monitoring metrics --filter api

# Check error rates
python tools/atlas_ops.py monitoring metrics --filter errors

# Check response times
python tools/atlas_ops.py monitoring metrics --filter response-time

# Restart API service
python tools/atlas_ops.py service restart api
```

### Log Analysis

```bash
# View recent logs
journalctl -u atlas-api --since "1 hour ago"

# Filter by error level
journalctl -u atlas-api -p err

# Export logs
journalctl -u atlas-api --since yesterday > atlas_api_logs_$(date +%Y%m%d).log

# Analyze logs
python tools/atlas_ops.py logs analyze --service api --since 1h
```

### Performance Diagnostics

```bash
# System performance report
python tools/atlas_ops.py monitoring report --performance

# Resource usage analysis
python tools/atlas_ops.py monitoring analyze --resources

# Bottleneck detection
python tools/atlas_ops.py monitoring analyze --bottlenecks

# Capacity planning
python tools/atlas_ops.py monitoring report --capacity
```

## Testing and Validation

### System Testing

```bash
# Run system tests
python test_system_integration.py

# Load testing
python tools/atlas_ops.py test load --duration 300 --concurrent 50

# Stress testing
python tools/atlas_ops.py test stress --duration 60

# Failover testing
python tools/atlas_ops.py test failover
```

### Configuration Testing

```bash
# Test configuration
python test_configuration_management.py

# Validate configuration
python tools/config_cli.py validate --all

# Test environment switching
python tools/config_cli.py env production
python tools/config_cli.py env development
```

### Reliability Testing

```bash
# Run reliability tests
python test_reliability.py

# Test backup/restore
python tools/atlas_ops.py test backup-restore

# Test deployment rollback
python tools/deployment_manager.py test rollback
```

## Emergency Procedures

### System Failure

```bash
# Emergency stop all services
python tools/atlas_ops.py service stop all --emergency

# Emergency backup
python tools/atlas_ops.py backup create --emergency

# Emergency restore
python tools/atlas_ops.py backup restore --emergency /backups/latest_backup.tar.gz
```

### Data Corruption

```bash
# Verify data integrity
python tools/atlas_ops.py system check --integrity

# Restore from backup
python tools/atlas_ops.py backup restore /backups/last_known_good_backup.tar.gz

# Verify restoration
python tools/atlas_ops.py system check --health
```

### Security Incident

```bash
# Enable maintenance mode
python tools/atlas_ops.py maintenance mode --enable --reason "Security incident"

# Rotate secrets
python tools/config_cli.py secret rotate-all

# Audit system
python tools/atlas_ops.py security audit

# Generate incident report
python tools/atlas_ops.py security incident-report
```

## Best Practices

### Daily Operations

1. **Morning Check**
   ```bash
   python tools/atlas_ops.py system status
   python tools/atlas_ops.py monitoring metrics
   python tools/atlas_ops.py backup check
   ```

2. **Throughout Day**
   ```bash
   # Monitor alerts
   python tools/atlas_ops.py monitoring alerts --active

   # Check performance
   python tools/atlas_ops.py monitoring metrics --filter performance
   ```

3. **End of Day**
   ```bash
   python tools/atlas_ops.py backup create
   python tools/atlas_ops.py monitoring report --daily
   ```

### Weekly Maintenance

1. **Database Maintenance**
   ```bash
   python tools/atlas_ops.py database optimize
   python tools/atlas_ops.py database vacuum
   python tools/atlas_ops.py database stats
   ```

2. **System Review**
   ```bash
   python tools/atlas_ops.py monitoring report --weekly
   python tools/atlas_ops.py system check --health
   python tools/atlas_ops.py backup list
   ```

3. **Security Check**
   ```bash
   python tools/atlas_ops.py security audit
   python tools/config_cli.py secret list
   ```

### Monthly Tasks

1. **Capacity Planning**
   ```bash
   python tools/atlas_ops.py monitoring report --capacity
   python tools/atlas_ops.py monitoring analyze --trends
   ```

2. **Full System Audit**
   ```bash
   python tools/atlas_ops.py system audit
   python tools/atlas_ops.py security audit --full
   ```

3. **Performance Review**
   ```bash
   python tools/atlas_ops.py monitoring report --performance
   python tools/atlas_ops.py monitoring analyze --optimization
   ```

## Contact and Support

### Support Channels

- **Critical Issues**: Use configured alert channels
- **Operational Issues**: Email support@atlas-system.com
- **Documentation**: Check OPERATIONS_GUIDE.md and PRODUCTION_RELIABILITY.md

### Incident Response

1. **Immediate Actions**
   - Assess impact and scope
   - Enable maintenance mode if needed
   - Notify stakeholders

2. **Investigation**
   - Collect logs and metrics
   - Identify root cause
   - Determine resolution path

3. **Resolution**
   - Implement fix
   - Verify system health
   - Document incident

4. **Post-incident**
   - Review incident response
   - Update procedures
   - Implement preventive measures

---

**Version**: 2.1.0
**Last Updated**: 2025-09-17
**Maintainer**: Atlas Development Team