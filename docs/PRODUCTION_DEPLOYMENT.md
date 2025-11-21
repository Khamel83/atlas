# Atlas Production Deployment Guide

**Version:** 1.0
**Date:** August 24, 2025
**Target:** Production-ready deployment of Atlas content processing system

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Infrastructure Requirements](#infrastructure-requirements)
3. [Deployment Options](#deployment-options)
4. [Step-by-Step Deployment](#step-by-step-deployment)
5. [Configuration Management](#configuration-management)
6. [Security Hardening](#security-hardening)
7. [Monitoring & Alerting](#monitoring--alerting)
8. [Backup & Recovery](#backup--recovery)
9. [Performance Tuning](#performance-tuning)
10. [Troubleshooting](#troubleshooting)

## Prerequisites

### System Requirements

**Minimum Production Requirements:**
- **OS:** Ubuntu 20.04 LTS / CentOS 8 / RHEL 8
- **CPU:** 4 cores (8+ recommended)
- **RAM:** 16GB (32GB+ recommended for large datasets)
- **Storage:** 500GB SSD (1TB+ recommended)
- **Network:** Stable internet connection with firewall access

**Recommended Production Specifications:**
- **CPU:** 8+ cores with high clock speed
- **RAM:** 32GB+ for handling large content collections
- **Storage:** NVMe SSD with 2TB+ capacity
- **Network:** Redundant network connections

### Software Dependencies

**Required Software:**
```bash
# System packages
sudo apt update && sudo apt install -y \
    python3.9 python3.9-venv python3-pip \
    postgresql postgresql-contrib \
    nginx redis-server supervisor \
    git curl wget unzip \
    build-essential libffi-dev libssl-dev \
    libpq-dev python3-dev

# Optional but recommended
sudo apt install -y \
    htop iotop netstat-nat \
    logrotate fail2ban ufw \
    certbot python3-certbot-nginx
```

## Infrastructure Requirements

### Database Configuration

**PostgreSQL Setup (Recommended for Production):**
```bash
# Install and configure PostgreSQL
sudo postgresql-setup --initdb
sudo systemctl start postgresql
sudo systemctl enable postgresql

# Create Atlas database and user
sudo -u postgres psql << EOF
CREATE DATABASE atlas_production;
CREATE USER atlas_user WITH ENCRYPTED PASSWORD 'secure_password_here';
GRANT ALL PRIVILEGES ON DATABASE atlas_production TO atlas_user;
ALTER USER atlas_user CREATEDB;
\q
EOF
```

**Database Performance Tuning:**
```bash
# Edit /etc/postgresql/13/main/postgresql.conf
shared_buffers = 4GB              # 25% of RAM
effective_cache_size = 12GB       # 75% of RAM
work_mem = 256MB
maintenance_work_mem = 1GB
max_connections = 200
```

### Redis Configuration

**Redis Setup for Caching:**
```bash
# Configure Redis for production
sudo vim /etc/redis/redis.conf

# Key settings:
maxmemory 2gb
maxmemory-policy allkeys-lru
save 900 1
save 300 10
save 60 10000
```

### Reverse Proxy (Nginx)

**Nginx Configuration:**
```nginx
# /etc/nginx/sites-available/atlas
server {
    listen 80;
    server_name your-domain.com;

    # Redirect HTTP to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name your-domain.com;

    # SSL Configuration
    ssl_certificate /path/to/ssl/cert.pem;
    ssl_certificate_key /path/to/ssl/private.key;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512;

    # Security headers
    add_header X-Content-Type-Options nosniff;
    add_header X-Frame-Options DENY;
    add_header X-XSS-Protection "1; mode=block";
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains";

    # Rate limiting
    limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
    limit_req zone=api burst=20 nodelay;

    # Atlas API
    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 300s;

        # Buffer settings
        proxy_buffering on;
        proxy_buffer_size 4k;
        proxy_buffers 8 4k;
    }

    # Dashboard
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Static files (if any)
    location /static/ {
        alias /opt/atlas/static/;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
}
```

## Deployment Options

### Option 1: Docker Deployment (Recommended)

**Docker Compose Configuration:**
```yaml
# docker-compose.prod.yml
version: '3.8'

services:
  atlas-app:
    build:
      context: .
      dockerfile: Dockerfile.prod
    restart: unless-stopped
    depends_on:
      - postgres
      - redis
    environment:
      - DATABASE_URL=postgresql://atlas_user:${DB_PASSWORD}@postgres:5432/atlas_production
      - REDIS_URL=redis://redis:6379/0
      - ENVIRONMENT=production
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
      - ./backups:/app/backups
    ports:
      - "8000:8000"
    healthcheck:
      test: ["CMD", "curl", "-f", "https://atlas.khamel.com/api/v1/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    deploy:
      resources:
        limits:
          memory: 8G
        reservations:
          memory: 4G

  postgres:
    image: postgres:13-alpine
    restart: unless-stopped
    environment:
      POSTGRES_DB: atlas_production
      POSTGRES_USER: atlas_user
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./backups:/backups
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U atlas_user -d atlas_production"]
      interval: 30s
      timeout: 5s
      retries: 3

  redis:
    image: redis:6-alpine
    restart: unless-stopped
    command: redis-server --appendonly yes
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 30s
      timeout: 5s
      retries: 3

  nginx:
    image: nginx:alpine
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/ssl/private
      - /var/log/nginx:/var/log/nginx
    depends_on:
      - atlas-app

volumes:
  postgres_data:
  redis_data:
```

**Production Dockerfile:**
```dockerfile
# Dockerfile.prod
FROM python:3.9-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    postgresql-client \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create app user
RUN useradd --create-home --shell /bin/bash atlas
WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt requirements.prod.txt ./
RUN pip install --no-cache-dir -r requirements.prod.txt

# Copy application code
COPY --chown=atlas:atlas . .

# Create necessary directories
RUN mkdir -p /app/data /app/logs /app/backups && \
    chown -R atlas:atlas /app

# Switch to app user
USER atlas

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f https://atlas.khamel.com/api/v1/health || exit 1

# Start application
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
```

### Option 2: Systemd Service Deployment

**Atlas Service Configuration:**
```ini
# /etc/systemd/system/atlas.service
[Unit]
Description=Atlas Content Processing System
After=network.target postgresql.service redis.service
Requires=postgresql.service redis.service

[Service]
Type=notify
User=atlas
Group=atlas
WorkingDirectory=/opt/atlas
Environment=PATH=/opt/atlas/venv/bin
Environment=PYTHONPATH=/opt/atlas
ExecStart=/opt/atlas/venv/bin/uvicorn api.main:app --host 0.0.0.0 --port 8000 --workers 4
ExecReload=/bin/kill -HUP $MAINPID
KillMode=mixed
TimeoutStopSec=5
PrivateTmp=true
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**Background Service Configuration:**
```ini
# /etc/systemd/system/atlas-background.service
[Unit]
Description=Atlas Background Processing Service
After=network.target atlas.service
Requires=atlas.service

[Service]
Type=simple
User=atlas
Group=atlas
WorkingDirectory=/opt/atlas
Environment=PATH=/opt/atlas/venv/bin
Environment=PYTHONPATH=/opt/atlas
ExecStart=/opt/atlas/venv/bin/python atlas_background_service.py
Restart=on-failure
RestartSec=30

[Install]
WantedBy=multi-user.target
```

## Step-by-Step Deployment

### 1. System Preparation

```bash
# Create atlas user
sudo useradd -m -s /bin/bash atlas
sudo usermod -aG sudo atlas

# Create application directory
sudo mkdir -p /opt/atlas
sudo chown atlas:atlas /opt/atlas

# Switch to atlas user
sudo -u atlas -i
```

### 2. Application Deployment

```bash
# Clone repository
cd /opt/atlas
git clone https://github.com/your-org/atlas.git .

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.prod.txt

# Create necessary directories
mkdir -p data logs backups config
```

### 3. Configuration Setup

```bash
# Copy production configuration
cp env.template .env.production

# Edit production configuration
vim .env.production
```

**Production Environment Variables:**
```bash
# Database Configuration
DATABASE_URL=postgresql://atlas_user:secure_password@localhost:5432/atlas_production
REDIS_URL=redis://localhost:6379/0

# Application Settings
ENVIRONMENT=production
DEBUG=false
SECRET_KEY=your-super-secret-key-here
ALLOWED_HOSTS=your-domain.com

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
API_WORKERS=4

# Processing Configuration
MAX_CONCURRENT_DOWNLOADS=8
PROCESSING_TIMEOUT=600
RETRY_ATTEMPTS=3

# Security Settings
SECURE_SSL_REDIRECT=true
SESSION_COOKIE_SECURE=true
CSRF_COOKIE_SECURE=true
```

### 4. Database Initialization

```bash
# Run database migrations
python manage.py migrate

# Create search indices
python scripts/populate_enhanced_search.py

# Verify database setup
python -c "from helpers.simple_database import SimpleDatabase; db = SimpleDatabase(); print('Database OK')"
```

### 5. SSL Certificate Setup

```bash
# Install Certbot SSL certificate
sudo certbot --nginx -d your-domain.com

# Test SSL configuration
sudo nginx -t
sudo systemctl reload nginx
```

### 6. Service Installation

```bash
# Copy service files
sudo cp deployment/atlas.service /etc/systemd/system/
sudo cp deployment/atlas-background.service /etc/systemd/system/

# Reload systemd and enable services
sudo systemctl daemon-reload
sudo systemctl enable atlas atlas-background
sudo systemctl start atlas atlas-background

# Verify services are running
sudo systemctl status atlas atlas-background
```

### 7. Monitoring Setup

```bash
# Install monitoring tools
pip install prometheus-client grafana-api

# Start monitoring services
python scripts/setup_monitoring.py

# Configure log rotation
sudo cp deployment/atlas-logrotate /etc/logrotate.d/atlas
```

## Configuration Management

### Environment-Specific Configuration

**Development:**
```bash
cp .env.development .env
```

**Staging:**
```bash
cp .env.staging .env
```

**Production:**
```bash
cp .env.production .env
```

### Configuration Validation

```bash
# Validate configuration before deployment
python scripts/validate_config.py --env production

# Test database connectivity
python scripts/test_database_connection.py

# Verify all dependencies
python scripts/validate_dependencies.py
```

## Security Hardening

### Firewall Configuration

```bash
# Configure UFW firewall
sudo ufw enable
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow ssh
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw allow from 10.0.0.0/8 to any port 5432  # Database access
```

### Security Updates

```bash
# Automatic security updates
sudo apt install unattended-upgrades
sudo dpkg-reconfigure unattended-upgrades

# Configure automatic security updates
echo 'Unattended-Upgrade::Automatic-Reboot "true";' | sudo tee -a /etc/apt/apt.conf.d/50unattended-upgrades
```

### Application Security

```bash
# Set secure file permissions
chmod 600 .env.production
chmod -R 750 /opt/atlas
chown -R atlas:atlas /opt/atlas

# Configure fail2ban
sudo cp deployment/atlas-fail2ban.conf /etc/fail2ban/jail.d/
sudo systemctl restart fail2ban
```

## Monitoring & Alerting

### Health Checks

```bash
# API health check
curl -f https://atlas.khamel.com/api/v1/health

# Database health check
python scripts/health_check.py --database

# Full system check
python scripts/health_check.py --all
```

### Log Monitoring

```bash
# Real-time log monitoring
tail -f /opt/atlas/logs/atlas.log

# Log analysis
python scripts/analyze_logs.py --date today
```

### Alerting Setup

```bash
# Configure email alerts
python scripts/setup_alerts.py --email admin@yourcompany.com

# Configure Slack integration
python scripts/setup_alerts.py --slack webhook-url
```

## Backup & Recovery

### Automated Backup

```bash
# Database backup
python scripts/backup_database.py --output /opt/atlas/backups/

# Full system backup
python scripts/backup_system.py --include-data

# Test restore procedure
python scripts/test_restore.py --backup latest
```

### Backup Schedule

```bash
# Add to crontab
0 2 * * * /opt/atlas/venv/bin/python /opt/atlas/scripts/backup_database.py
0 3 * * 0 /opt/atlas/venv/bin/python /opt/atlas/scripts/backup_system.py
```

## Performance Tuning

### Database Optimization

```sql
-- Create indices for better performance
CREATE INDEX CONCURRENTLY idx_content_created_at ON content(created_at);
CREATE INDEX CONCURRENTLY idx_content_type ON content(content_type);
CREATE INDEX CONCURRENTLY idx_search_content ON search_index USING gin(content);
```

### Application Optimization

```bash
# Configure gunicorn for production
pip install gunicorn
gunicorn api.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

### System Optimization

```bash
# Optimize system limits
echo "atlas soft nofile 65536" | sudo tee -a /etc/security/limits.conf
echo "atlas hard nofile 65536" | sudo tee -a /etc/security/limits.conf

# Optimize kernel parameters
echo "net.core.somaxconn = 65536" | sudo tee -a /etc/sysctl.conf
sysctl -p
```

## Troubleshooting

### Common Issues

**Service Won't Start:**
```bash
# Check service logs
journalctl -u atlas -f

# Check application logs
tail -f /opt/atlas/logs/atlas.log

# Verify configuration
python scripts/validate_config.py
```

**Database Connection Issues:**
```bash
# Test database connectivity
python scripts/test_database_connection.py

# Check PostgreSQL status
sudo systemctl status postgresql
```

**Performance Issues:**
```bash
# Monitor resource usage
htop
iotop

# Check database performance
python scripts/analyze_performance.py
```

### Emergency Procedures

**Service Restart:**
```bash
sudo systemctl restart atlas atlas-background nginx
```

**Emergency Rollback:**
```bash
# Stop services
sudo systemctl stop atlas atlas-background

# Restore from backup
python scripts/restore_from_backup.py --backup latest

# Start services
sudo systemctl start atlas atlas-background
```

## Deployment Checklist

### Pre-Deployment

- [ ] System requirements verified
- [ ] Dependencies installed
- [ ] Database configured
- [ ] SSL certificates installed
- [ ] Firewall configured
- [ ] Monitoring setup
- [ ] Backup system tested

### Deployment

- [ ] Application deployed
- [ ] Configuration validated
- [ ] Database migrated
- [ ] Services started
- [ ] Health checks passing
- [ ] SSL working
- [ ] Performance tested

### Post-Deployment

- [ ] Monitoring alerts configured
- [ ] Backup schedule active
- [ ] Log rotation configured
- [ ] Performance baseline established
- [ ] Documentation updated
- [ ] Team notified

---

## Support and Maintenance

For ongoing support and maintenance:

1. **Monitor logs daily**: Check `/opt/atlas/logs/` for errors
2. **Review performance weekly**: Run performance analysis scripts
3. **Update monthly**: Apply security updates and patches
4. **Backup verification**: Test backup restoration monthly
5. **Capacity planning**: Monitor disk usage and scaling needs

**Emergency Contact:** Your DevOps team or Atlas maintainers

**Status Page:** https://status.your-domain.com (if configured)

---

*Atlas Production Deployment Guide v1.0 - Last updated: August 24, 2025*