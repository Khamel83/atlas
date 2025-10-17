# Atlas Maintenance Automation

This directory contains all maintenance automation components for the Atlas system, including system updates, service maintenance, disk management, and service monitoring.

## Components

### System Updates (`system_updates.py`)
- Configures Ubuntu unattended-upgrades for security updates
- Sets up automatic security updates at 4 AM PST
- Configures update notifications via email
- Implements reboot scheduling if required (with service restart)
- Creates update log monitoring and reporting

### Atlas Service Maintenance (`atlas_maintenance.py`)
- Creates Atlas-specific maintenance tasks
- Implements failed article retry automation (daily)
- Sets up database optimization and vacuum tasks
- Creates log rotation and cleanup for Atlas logs
- Adds content deduplication and cleanup tasks
- Configures Atlas service health monitoring and auto-restart

### Disk Space Management (`disk_management.py`)
- Creates disk space monitoring and cleanup automation
- Implements old log file cleanup (keep 30 days)
- Sets up temporary file cleanup
- Creates old backup cleanup (local and OCI)
- Adds disk space alerts (80% and 90% thresholds)
- Configures automatic cleanup when space is low

### Service Health Monitoring (`service_monitor.py`)
- Creates comprehensive service health checks
- Implements automatic service restart for failed services
- Sets up service dependency management
- Creates service status reporting and logging
- Adds email notifications for service failures
- Tests service recovery and restart procedures

## Installation

1. **System Updates Setup**:
   ```bash
   sudo python3 maintenance/system_updates.py
   ```

2. **Atlas Service Maintenance Setup**:
   ```bash
   sudo python3 maintenance/atlas_maintenance.py
   ```

3. **Disk Management Setup**:
   ```bash
   sudo python3 maintenance/disk_management.py
   ```

4. **Service Monitoring Setup**:
   ```bash
   sudo python3 maintenance/service_monitor.py
   ```

## Status

✅ **BLOCK 14.4.1 System Auto-Updates** - PARTIALLY COMPLETE
- [x] Configure Ubuntu unattended-upgrades for security updates
- [x] Set up automatic security updates at 4 AM PST
- [x] Configure update notifications via email
- [x] Implement reboot scheduling if required (with service restart)
- [x] Create update log monitoring and reporting

✅ **BLOCK 14.4.2 Atlas Service Maintenance** - PARTIALLY COMPLETE
- [x] Create Atlas-specific maintenance tasks
- [x] Implement failed article retry automation (daily)
- [x] Set up database optimization and vacuum tasks
- [x] Create log rotation and cleanup for Atlas logs
- [x] Add content deduplication and cleanup tasks
- [x] Configure Atlas service health monitoring and auto-restart

✅ **BLOCK 14.4.3 Disk Space Management** - PARTIALLY COMPLETE
- [x] Create disk space monitoring and cleanup automation
- [x] Implement old log file cleanup (keep 30 days)
- [x] Set up temporary file cleanup
- [x] Create old backup cleanup (local and OCI)
- [x] Add disk space alerts (80% and 90% thresholds)
- [x] Configure automatic cleanup when space is low

✅ **BLOCK 14.4.4 Service Health Monitoring** - PARTIALLY COMPLETE
- [x] Create comprehensive service health checks
- [x] Implement automatic service restart for failed services
- [x] Set up service dependency management
- [x] Create service status reporting and logging
- [x] Add email notifications for service failures
- [x] Test service recovery and restart procedures