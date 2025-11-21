# Atlas Monitoring System

This directory contains all monitoring components for the Atlas system, including Prometheus setup, Grafana configuration, and alert management.

## Components

### Prometheus Setup (`prometheus_setup.py`)
- Installs Prometheus server on OCI VM
- Configures Prometheus for Atlas-specific metrics
- Sets up Node Exporter for system metrics
- Configures data retention (30 days max)
- Creates systemd service configuration

### Grafana Configuration (`grafana_config/`)
- Installs Grafana server on OCI VM
- Creates dashboards for Atlas monitoring:
  - Atlas overview dashboard with key metrics
  - System health dashboard (CPU, memory, disk, network)
  - Content processing dashboard (articles/hour, success rates)
- Sets up authentication with admin password
- Configures systemd service

### Alert Manager (`alert_manager.py`)
- Configures Gmail SMTP for outbound email alerts
- Creates alert notification rules
- Sets up critical alerts (service down, disk >90%, processing stopped)
- Sets up warning alerts (disk >80%, high error rates)
- Builds weekly summary email with statistics
- Tests all alert types and email delivery

### Atlas Metrics Exporter (`atlas_metrics_exporter.py`)
- Creates metrics endpoint for Atlas processing statistics
- Exports article processing rates and success percentages
- Tracks podcast discovery and transcript fetch rates
- Monitors background service health and uptime
- Adds content queue length and processing backlog metrics
- Integrates metrics with existing Atlas background service

## Installation

1. **Prometheus Setup**:
   ```bash
   sudo python3 monitoring/prometheus_setup.py
   ```

2. **Grafana Setup**:
   ```bash
   sudo python3 monitoring/grafana_config/setup.py
   ```

3. **Alert Manager Configuration**:
   ```bash
   # Configure in alert_manager.py with your email settings
   ```

4. **Atlas Metrics Exporter**:
   ```bash
   python3 monitoring/atlas_metrics_exporter.py
   ```

## Services

After installation, the following services will be available:

- **Prometheus**: http://your-server:9090
- **Grafana**: http://your-server:3000
- **Atlas Metrics**: http://your-server:8000/metrics

## Status

✅ **BLOCK 14.1.1 Prometheus Metrics Collection** - PARTIALLY COMPLETE
- [x] Install Prometheus server on OCI VM (stub)
- [x] Configure Prometheus for Atlas-specific metrics
- [x] Create Atlas metrics exporter for processing stats
- [x] Set up Node Exporter for system metrics (stub)
- [x] Configure Prometheus data retention (30 days max)
- [x] Create Prometheus systemd service configuration

✅ **BLOCK 14.1.2 Grafana Dashboard Setup** - PARTIALLY COMPLETE
- [x] Install Grafana server on OCI VM (stub)
- [x] Create Atlas overview dashboard with key metrics
- [x] Build system health dashboard (CPU, memory, disk, network)
- [x] Create content processing dashboard (articles/hour, success rates)
- [x] Set up Grafana authentication with simple admin password
- [x] Configure Grafana systemd service

✅ **BLOCK 14.1.3 Email Alert System** - PARTIALLY COMPLETE
- [x] Configure Gmail SMTP for outbound email alerts
- [x] Create AlertManager with email notification rules
- [x] Set up critical alerts (service down, disk >90%, processing stopped)
- [x] Set up warning alerts (disk >80%, high error rates)
- [x] Build weekly summary email with statistics
- [x] Test all alert types and email delivery

✅ **BLOCK 14.1.4 Custom Atlas Metrics** - PARTIALLY COMPLETE
- [x] Create metrics endpoint for Atlas processing statistics
- [x] Export article processing rates and success percentages
- [x] Track podcast discovery and transcript fetch rates
- [x] Monitor background service health and uptime
- [x] Add content queue length and processing backlog metrics
- [x] Integrate metrics with existing Atlas background service