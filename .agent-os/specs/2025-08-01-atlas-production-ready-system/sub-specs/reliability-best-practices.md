# Reliability & Best Practices Specification

This document outlines technical reliability strategies and basic security best practices aligned with Atlas principles of simplicity, robustness, and personal use.

## Core Reliability Principles

### 1. Fail Fast, Fail Clearly
- **Quick failure detection**: If content ingestion fails, fail within 30 seconds with clear error message
- **Notification system**: Immediate alerts for ingestion failures with actionable information
- **Graceful degradation**: Core capture functionality continues even if secondary features fail
- **Error categorization**: Distinguish between temporary failures (retry) vs permanent failures (skip)

### 2. Capture-First Architecture
- **Primary mission protection**: Content capture pipeline isolated from processing pipeline
- **Minimal dependencies**: Core capture requires only essential packages (requests, BeautifulSoup)
- **Offline resilience**: Queue URLs for processing when external services are unavailable
- **Data durability**: Raw content always saved before any processing attempts

### 3. Self-Healing Systems
- **Automatic retry**: Exponential backoff for temporary failures
- **Circuit breakers**: Skip problematic sources temporarily, resume automatically
- **Health monitoring**: Automated detection and recovery from common failure modes
- **Queue management**: Automatic cleanup of stale queue items

## Technical Reliability Recommendations

### Package Management Strategy
```bash
# Create local package cache for reliability
pip download -r requirements.txt -d packages/
# Install from local cache
pip install --find-links packages/ --no-index -r requirements.txt
```

### Docker Deployment (Raspberry Pi Backup)
```dockerfile
# Multi-stage build for reliability
FROM python:3.9-slim as builder
COPY requirements.txt .
RUN pip wheel --no-cache-dir --no-deps --wheel-dir /wheels -r requirements.txt

FROM python:3.9-slim
COPY --from=builder /wheels /wheels
RUN pip install --no-cache /wheels/*
```

### Content Source Resilience
- **6-layer fallback strategy**: Already implemented, maintain and enhance
- **User-agent rotation**: Reduce blocking probability
- **Rate limiting**: Respect source limitations to avoid bans
- **Archive integration**: Wayback Machine as ultimate fallback

### Database Reliability
- **SQLite with WAL mode**: Concurrent read/write without corruption
- **Automatic backups**: Daily backups with integrity checks
- **Schema migrations**: Forward-compatible database changes
- **Transaction safety**: All critical operations in transactions

## Basic Security Best Practices

### Local-First Security
- **No external exposure**: Services bind to localhost only
- **Tailscale integration**: Secure remote access without port forwarding
- **Environment isolation**: Run in Docker container for containment
- **File permissions**: Restrict access to data directories (700/600)

### API Security (for personal projects)
```python
# Simple API key authentication
API_KEYS = {
    "personal-key-1": {"name": "Main API Key", "permissions": ["read", "write"]},
    "readonly-key": {"name": "Read Only", "permissions": ["read"]}
}

# Rate limiting per key
RATE_LIMITS = {
    "personal-key-1": 1000,  # requests per hour
    "readonly-key": 100
}
```

### Data Protection
- **Sensitive data encryption**: Encrypt API keys and credentials at rest
- **Log sanitization**: Never log credentials or personal data
- **Secure defaults**: Disable debug mode, secure session keys
- **Regular updates**: Automated security patches for critical packages

### Network Security
```yaml
# docker-compose.yml with security
version: '3.8'
services:
  atlas:
    build: .
    networks:
      - internal
    volumes:
      - ./data:/app/data:rw
    environment:
      - ATLAS_ENV=production
    restart: unless-stopped

networks:
  internal:
    driver: bridge
    internal: true  # No external access
```

## Monitoring & Alerting (Simple)

### Health Checks
- **Basic endpoint**: `/health` returns system status
- **Content pipeline**: Monitor ingestion success rate
- **Resource usage**: Alert on disk space, memory usage
- **Service availability**: Ensure all core services responding

### Logging Strategy
```python
# Structured logging for reliability
import structlog

logger = structlog.get_logger()
logger.info("content_captured", url=url, status="success", duration=0.5)
logger.error("content_failed", url=url, error="timeout", retry_count=3)
```

### Simple Alerting
```bash
# Email alerts for critical failures
echo "Atlas ingestion failure: $ERROR" | mail -s "Atlas Alert" your@email.com
```

## Deployment Best Practices

### Raspberry Pi Optimization
- **Resource monitoring**: Alert before running out of disk/memory
- **Temperature monitoring**: Throttle processing during high temps
- **SD card health**: Monitor write cycles, backup frequently
- **Power management**: Graceful shutdown on power issues

### Mac Mini M4 Backup Deployment
- **Docker Compose**: Easy migration from Pi if needed
- **Shared storage**: Network storage accessible from both devices
- **Configuration sync**: Same .env works on both platforms
- **Automated failover**: Simple script to detect Pi failure and start on Mac Mini

## Maintenance Automation

### Daily Tasks
- **Health check**: Verify all services running
- **Backup verification**: Ensure backups completed successfully
- **Queue status**: Check for stuck items in processing queue
- **Disk cleanup**: Remove old logs and temporary files

### Weekly Tasks
- **Database maintenance**: VACUUM, ANALYZE for SQLite
- **Security updates**: Check for critical package updates
- **Performance review**: Identify any degradation trends
- **Backup rotation**: Clean old backups, verify restore capability

### Monthly Tasks
- **Dependency audit**: Check for deprecated packages
- **Configuration review**: Ensure settings still optimal
- **Documentation sync**: Update any changed procedures
- **Disaster recovery test**: Verify backup/restore works

## Implementation Priorities

1. **Core reliability** (Tasks 1-8): Environment, testing, error handling
2. **Security basics** (Tasks 16-20): Monitoring, backup, basic hardening
3. **Deployment automation** (Task 19): Docker, systemd, health checks
4. **Maintenance automation** (Task 18): Automated cleanup and optimization

This approach prioritizes the core capture mission while building in reliability and security best practices that don't add unnecessary complexity.