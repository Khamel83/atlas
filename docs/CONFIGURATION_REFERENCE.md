# Atlas Configuration Reference

## Overview

This document provides a comprehensive reference for all Atlas configuration options, including environment-specific settings, secrets management, and best practices.

## Configuration Structure

### Directory Structure

```
config/
├── development.env          # Development environment configuration
├── staging.env             # Staging environment configuration
├── production.env          # Production environment configuration
├── development.secrets     # Development secrets (encrypted)
├── staging.secrets        # Staging secrets (encrypted)
├── production.secrets     # Production secrets (encrypted)
├── monitoring.yaml         # Monitoring and alerting configuration
├── alerting.yaml          # Alert rules and thresholds
├── schemas.yaml           # Configuration schemas
├── observability.yaml     # Observability and metrics configuration
├── ingestion_reliability.yaml  # Ingestion reliability settings
└── database.yaml          # Database configuration
```

## Environment Configuration

### Development Environment (`development.env`)

```bash
# Environment
ATLAS_ENVIRONMENT=development

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
API_WORKERS=4
API_DEBUG=true
API_CORS_ORIGINS=["http://localhost:3000", "http://localhost:8080"]
API_RATE_LIMIT=100
API_TIMEOUT=30

# Database Configuration
DATABASE_PATH=development/atlas.db
DATABASE_WAL_MODE=true
DATABASE_TIMEOUT=30
DATABASE_POOL_SIZE=5
DATABASE_BACKUP_ENABLED=true
DATABASE_BACKUP_INTERVAL=3600

# Monitoring Configuration
MONITORING_ENABLED=true
MONITORING_INTERVAL=60
MONITORING_PORT=8001
METRICS_ENABLED=true
METRICS_PORT=8002

# Reliability Configuration
RELIABILITY_ENABLED=true
RELIABILITY_CIRCUIT_BREAKER_ENABLED=true
RELIABILITY_DEAD_LETTER_QUEUE_ENABLED=true
RELIABILITY_RATE_LIMITING_ENABLED=true
RELIABILITY_PREDICTIVE_SCALING_ENABLED=true

# Resource Limits
MAX_MEMORY_MB=512
MAX_CPU_PERCENT=70
MAX_DISK_USAGE_PERCENT=80
MAX_FILE_DESCRIPTORS=1024

# Logging Configuration
LOG_LEVEL=DEBUG
LOG_FORMAT=json
LOG_FILE=logs/atlas.log
LOG_ROTATION=daily
LOG_RETENTION=7

# Background Services
SERVICES_ENABLED=true
SERVICES_WORKERS=2
SERVICES_QUEUE_SIZE=100
SERVICES_RETRY_COUNT=3
SERVICES_RETRY_DELAY=5

# Security Configuration
SECURITY_ENABLED=true
SECURITY_SECRET_KEY=development-secret-key
SECURITY_CORS_ENABLED=true
SECURITY_RATE_LIMITING_ENABLED=true
SECURITY_HEADERS_ENABLED=true
```

### Staging Environment (`staging.env`)

```bash
# Environment
ATLAS_ENVIRONMENT=staging

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
API_WORKERS=8
API_DEBUG=false
API_CORS_ORIGINS=["https://staging.atlas.com"]
API_RATE_LIMIT=200
API_TIMEOUT=30

# Database Configuration
DATABASE_PATH=staging/atlas.db
DATABASE_WAL_MODE=true
DATABASE_TIMEOUT=30
DATABASE_POOL_SIZE=10
DATABASE_BACKUP_ENABLED=true
DATABASE_BACKUP_INTERVAL=1800

# Monitoring Configuration
MONITORING_ENABLED=true
MONITORING_INTERVAL=30
MONITORING_PORT=8001
METRICS_ENABLED=true
METRICS_PORT=8002

# Reliability Configuration
RELIABILITY_ENABLED=true
RELIABILITY_CIRCUIT_BREAKER_ENABLED=true
RELIABILITY_DEAD_LETTER_QUEUE_ENABLED=true
RELIABILITY_RATE_LIMITING_ENABLED=true
RELIABILITY_PREDICTIVE_SCALING_ENABLED=true

# Resource Limits
MAX_MEMORY_MB=1024
MAX_CPU_PERCENT=75
MAX_DISK_USAGE_PERCENT=85
MAX_FILE_DESCRIPTORS=2048

# Logging Configuration
LOG_LEVEL=INFO
LOG_FORMAT=json
LOG_FILE=logs/atlas.log
LOG_ROTATION=daily
LOG_RETENTION=14

# Background Services
SERVICES_ENABLED=true
SERVICES_WORKERS=4
SERVICES_QUEUE_SIZE=200
SERVICES_RETRY_COUNT=3
SERVICES_RETRY_DELAY=10

# Security Configuration
SECURITY_ENABLED=true
SECURITY_SECRET_KEY=staging-secret-key-change-in-production
SECURITY_CORS_ENABLED=true
SECURITY_RATE_LIMITING_ENABLED=true
SECURITY_HEADERS_ENABLED=true
```

### Production Environment (`production.env`)

```bash
# Environment
ATLAS_ENVIRONMENT=production

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
API_WORKERS=16
API_DEBUG=false
API_CORS_ORIGINS=["https://atlas.com"]
API_RATE_LIMIT=500
API_TIMEOUT=60

# Database Configuration
DATABASE_PATH=production/atlas.db
DATABASE_WAL_MODE=true
DATABASE_TIMEOUT=60
DATABASE_POOL_SIZE=20
DATABASE_BACKUP_ENABLED=true
DATABASE_BACKUP_INTERVAL=900

# Monitoring Configuration
MONITORING_ENABLED=true
MONITORING_INTERVAL=15
MONITORING_PORT=8001
METRICS_ENABLED=true
METRICS_PORT=8002

# Reliability Configuration
RELIABILITY_ENABLED=true
RELIABILITY_CIRCUIT_BREAKER_ENABLED=true
RELIABILITY_DEAD_LETTER_QUEUE_ENABLED=true
RELIABILITY_RATE_LIMITING_ENABLED=true
RELIABILITY_PREDICTIVE_SCALING_ENABLED=true

# Resource Limits
MAX_MEMORY_MB=2048
MAX_CPU_PERCENT=80
MAX_DISK_USAGE_PERCENT=90
MAX_FILE_DESCRIPTORS=4096

# Logging Configuration
LOG_LEVEL=WARNING
LOG_FORMAT=json
LOG_FILE=logs/atlas.log
LOG_ROTATION=daily
LOG_RETENTION=30

# Background Services
SERVICES_ENABLED=true
SERVICES_WORKERS=8
SERVICES_QUEUE_SIZE=500
SERVICES_RETRY_COUNT=5
SERVICES_RETRY_DELAY=30

# Security Configuration
SECURITY_ENABLED=true
SECURITY_SECRET_KEY=production-secret-key-change-immediately
SECURITY_CORS_ENABLED=true
SECURITY_RATE_LIMITING_ENABLED=true
SECURITY_HEADERS_ENABLED=true
```

## Secrets Configuration

### Secrets Format

Secrets are stored in encrypted files using Fernet encryption. Each secret file contains key-value pairs:

```bash
# Database Secrets
DATABASE_PASSWORD=encrypted_database_password
DATABASE_USERNAME=encrypted_database_username
DATABASE_HOST=encrypted_database_host
DATABASE_PORT=encrypted_database_port

# API Secrets
API_SECRET_KEY=encrypted_api_secret_key
API_JWT_SECRET=encrypted_jwt_secret
API_ENCRYPTION_KEY=encrypted_encryption_key

# External Service Secrets
GOOGLE_API_KEY=encrypted_google_api_key
YOUTUBE_API_KEY=encrypted_youtube_api_key
OPENAI_API_KEY=encrypted_openai_api_key

# Notification Secrets
SMTP_USERNAME=encrypted_smtp_username
SMTP_PASSWORD=encrypted_smtp_password
SLACK_WEBHOOK_URL=encrypted_slack_webhook_url
WEBHOOK_SECRET=encrypted_webhook_secret

# Monitoring Secrets
MONITORING_AUTH_TOKEN=encrypted_monitoring_auth_token
METRICS_API_KEY=encrypted_metrics_api_key

# Security Secrets
SSL_CERTIFICATE=encrypted_ssl_certificate
SSL_PRIVATE_KEY=encrypted_ssl_private_key
ADMIN_PASSWORD=encrypted_admin_password
```

## Monitoring Configuration (`monitoring.yaml`)

```yaml
# General Settings
monitoring:
  enabled: true
  interval: 30
  port: 8001
  health_check_interval: 60

  # Metrics Collection
  metrics:
    enabled: true
    port: 8002
    export_interval: 60
    retention_days: 30

  # System Metrics
  system:
    cpu_usage: true
    memory_usage: true
    disk_usage: true
    network_io: true
    disk_io: true
    load_average: true
    process_count: true
    file_descriptors: true

  # Application Metrics
  application:
    api_response_time: true
    api_error_rate: true
    api_request_count: true
    database_query_time: true
    database_connection_count: true
    queue_length: true
    processing_time: true
    success_rate: true
    backlog_size: true
    throughput: true

  # Health Checks
  health_checks:
    api_health: true
    database_health: true
    service_health: true
    disk_health: true
    memory_health: true
    network_health: true

  # Storage
  storage:
    metrics_file: data/metrics.json
    health_file: data/health.json
    alerts_file: data/alerts.json
    max_file_size_mb: 100
    compression_enabled: true
```

## Alerting Configuration (`alerting.yaml`)

```yaml
# Alert Rules
alerts:
  # CPU Usage Alerts
  cpu_usage:
    warning: 70
    critical: 85
    cooldown: 300  # 5 minutes
    enabled: true

  # Memory Usage Alerts
  memory_usage:
    warning: 80
    critical: 90
    cooldown: 300
    enabled: true

  # Disk Usage Alerts
  disk_usage:
    warning: 85
    critical: 95
    cooldown: 600  # 10 minutes
    enabled: true

  # API Error Rate Alerts
  api_error_rate:
    warning: 5     # 5%
    critical: 10   # 10%
    cooldown: 180  # 3 minutes
    enabled: true

  # Database Performance Alerts
  database_response_time:
    warning: 1000  # 1 second
    critical: 5000 # 5 seconds
    cooldown: 300
    enabled: true

  # Service Health Alerts
  service_health:
    warning: 2     # 2 failed services
    critical: 1    # 1 failed service
    cooldown: 180
    enabled: true

  # Queue Length Alerts
  queue_length:
    warning: 100
    critical: 500
    cooldown: 300
    enabled: true

  # Backlog Size Alerts
  backlog_size:
    warning: 1000
    critical: 5000
    cooldown: 600
    enabled: true

# Notification Channels
notifications:
  # Email Notifications
  email:
    enabled: true
    smtp_server: smtp.gmail.com
    smtp_port: 587
    username: your-email@gmail.com
    password: your-app-password
    use_tls: true
    from_address: atlas@yourcompany.com
    to_addresses:
      - admin@yourcompany.com
      - ops@yourcompany.com
    subject_prefix: "[Atlas Alert]"

  # Webhook Notifications
  webhook:
    enabled: true
    url: https://hooks.slack.com/services/YOUR/WEBHOOK/URL
    headers:
      Content-Type: application/json
      User-Agent: Atlas-Monitoring/1.0
    timeout: 30
    retry_count: 3

  # Slack Notifications
  slack:
    enabled: true
    webhook_url: https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK
    channel: "#alerts"
    username: Atlas-Monitoring
    icon_emoji: ":warning:"

  # Log Notifications
  log:
    enabled: true
    file: logs/alerts.log
    level: WARNING
    format: json
    rotation: daily
    retention: 30

# Alert Templates
templates:
  warning_subject: "Atlas Warning: {alert_name}"
  critical_subject: "Atlas CRITICAL: {alert_name}"
  warning_message: |
    Atlas Warning: {alert_name}
    Current Value: {current_value}
    Threshold: {threshold}
    Time: {timestamp}
    Host: {hostname}

  critical_message: |
    Atlas CRITICAL: {alert_name}
    Current Value: {current_value}
    Threshold: {threshold}
    Time: {timestamp}
    Host: {hostname}

    This requires immediate attention!
```

## Database Configuration (`database.yaml`)

```yaml
# SQLite Configuration
sqlite:
  path: production/atlas.db
  journal_mode: WAL
  synchronous: NORMAL
  cache_size: 10000
  timeout: 60
  foreign_keys: true
  auto_vacuum: FULL

  # Connection Pool
  pool:
    max_connections: 20
    min_connections: 5
    max_idle_time: 300
    connection_timeout: 30
    retry_attempts: 3
    retry_delay: 5

  # Performance
  performance:
    wal_autocheckpoint: 1000
    mmap_size: 268435456  # 256MB
    page_size: 4096
    temp_store: MEMORY

  # Backup
  backup:
    enabled: true
    interval: 900  # 15 minutes
    retention: 48  # 48 hours
    compression: true
    verify: true
    path: backups/database/

  # Maintenance
  maintenance:
    auto_vacuum: true
    auto_analyze: true
    optimize_interval: 86400  # 24 hours
    integrity_check_interval: 604800  # 7 days
```

## Ingestion Reliability Configuration (`ingestion_reliability.yaml`)

```yaml
# Rate Limiting
rate_limiting:
  enabled: true
  algorithm: token_bucket
  bucket_size: 1000
  refill_rate: 100
  initial_tokens: 500

  # Adaptive Rate Limiting
  adaptive:
    enabled: true
    adjustment_factor: 0.8
    recovery_factor: 1.2
    adjustment_interval: 300  # 5 minutes

# Circuit Breaker
circuit_breaker:
  enabled: true
  failure_threshold: 5
  recovery_threshold: 3
  timeout: 60
  cooldown: 180  # 3 minutes

  # Circuit States
  states:
    closed:
      max_failures: 5
      timeout: 60

    open:
      timeout: 180
      half_open_attempts: 3

    half_open:
      max_requests: 10
      success_threshold: 8

# Dead Letter Queue
dead_letter_queue:
  enabled: true
  max_size: 10000
  retry_attempts: 5
  retry_delay:
    initial: 60
    multiplier: 2
    maximum: 3600  # 1 hour

  # Processing
  processing:
    batch_size: 100
    processing_interval: 300  # 5 minutes
    max_processing_time: 1800  # 30 minutes

# Predictive Scaling
predictive_scaling:
  enabled: true
  lookback_period: 86400  # 24 hours
  prediction_interval: 3600  # 1 hour

  # Scaling Factors
  scaling:
    cpu_factor: 1.2
    memory_factor: 1.1
    queue_factor: 1.3
    backlog_factor: 1.4

  # Thresholds
  thresholds:
    scale_up: 0.7
    scale_down: 0.3
    max_scale_up: 2.0
    max_scale_down: 0.5

# Quality Control
quality_control:
  enabled: true
  validation_rules:
    required_fields: true
    data_format: true
    content_length: true
    url_validation: true

  # Sampling
  sampling:
    enabled: true
    sample_rate: 0.1  # 10%
    max_samples: 1000

  # Anomaly Detection
  anomaly_detection:
    enabled: true
    sensitivity: 0.8
    window_size: 100
    threshold: 2.0
```

## Observability Configuration (`observability.yaml`)

```yaml
# Metrics Export
metrics:
  enabled: true
  port: 8002
  path: /metrics

  # Prometheus
  prometheus:
    enabled: true
    path: /metrics
    format: prometheus
    namespace: atlas

  # Export Formats
  export:
    json: true
    prometheus: true
    influx: false

  # Retention
  retention:
    metrics_days: 30
    aggregates_days: 90

# Tracing
tracing:
  enabled: true
  service_name: atlas
  sample_rate: 0.1

  # Exporters
  exporters:
    jaeger:
      enabled: false
      endpoint: http://localhost:14268/api/traces

    zipkin:
      enabled: false
      endpoint: http://localhost:9411/api/v2/spans

# Logging
logging:
  level: INFO
  format: json
  output: console

  # Structured Logging
  structured:
    enabled: true
    fields:
      timestamp: true
      level: true
      service: true
      trace_id: true
      span_id: true

  # Log Rotation
  rotation:
    enabled: true
    max_size_mb: 100
    max_files: 10
    compression: true

# Health Checks
health:
  enabled: true
  endpoint: /health

  # Checks
  checks:
    database:
      enabled: true
      timeout: 5

    redis:
      enabled: false
      timeout: 3

    external_services:
      enabled: true
      timeout: 10

  # Liveness/Readiness
    liveness:
      path: /health/live
      interval: 30

    readiness:
      path: /health/ready
      interval: 30
```

## Configuration Management

### Environment Variables

Atlas can be configured via environment variables, which take precedence over configuration files:

```bash
# Environment
export ATLAS_ENVIRONMENT=production

# API Configuration
export API_HOST=0.0.0.0
export API_PORT=8000
export API_DEBUG=false

# Database Configuration
export DATABASE_PATH=/opt/atlas/data/production.db
export DATABASE_WAL_MODE=true

# Monitoring Configuration
export MONITORING_ENABLED=true
export MONITORING_INTERVAL=30

# Resource Limits
export MAX_MEMORY_MB=2048
export MAX_CPU_PERCENT=80
```

### Configuration Validation

Atlas validates configuration on startup:

```bash
# Validate all configuration
python tools/config_cli.py validate --all

# Validate specific configuration
python tools/config_cli.py validate api
python tools/config_cli.py validate database
python tools/config_cli.py validate monitoring

# Check for deprecated options
python tools/config_cli.py validate --check-deprecated
```

### Configuration Migration

```bash
# Migrate configuration to new format
python tools/config_cli.py migrate --from-old --to-new

# Backup current configuration
python tools/config_cli.py backup --config

# Restore configuration from backup
python tools/config_cli.py restore --config /path/to/backup.tar.gz
```

## Best Practices

### Security

1. **Secrets Management**
   - Always use encrypted secrets files
   - Rotate encryption keys regularly
   - Limit access to secret files
   - Use environment variables for secrets in CI/CD

2. **Configuration Security**
   - Restrict file permissions on configuration files
   - Use least privilege principles
   - Audit configuration changes
   - Validate all configuration inputs

3. **Network Security**
   - Use TLS/SSL for all external connections
   - Restrict access to monitoring ports
   - Use VPN or private networks for internal communication

### Performance

1. **Resource Optimization**
   - Monitor resource usage regularly
   - Adjust worker counts based on load
   - Use appropriate connection pool sizes
   - Enable compression for large data transfers

2. **Database Performance**
   - Use WAL mode for concurrent access
   - Optimize connection pooling
   - Regular maintenance and vacuuming
   - Monitor query performance

### Reliability

1. **High Availability**
   - Implement proper service dependencies
   - Use health checks and automatic recovery
   - Configure appropriate retry policies
   - Implement circuit breakers for external services

2. **Monitoring and Alerting**
   - Configure comprehensive monitoring
   - Set appropriate alert thresholds
   - Use multiple notification channels
   - Regular testing of alerting system

3. **Backup and Recovery**
   - Regular automated backups
   - Test backup restoration procedures
   - Implement disaster recovery plans
   - Document recovery procedures

### Maintenance

1. **Regular Updates**
   - Keep dependencies up to date
   - Monitor for security patches
   - Test updates in staging environment
   - Schedule maintenance windows

2. **Log Management**
   - Implement log rotation
   - Use structured logging
   - Archive old logs
   - Monitor log anomalies

3. **Performance Tuning**
   - Regular performance reviews
   - Monitor trends and patterns
   - Optimize based on usage patterns
   - Capacity planning for growth

---

**Version**: 2.1.0
**Last Updated**: 2025-09-17
**Maintainer**: Atlas Development Team