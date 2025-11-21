# Atlas Deployment Guide

This guide covers deployment procedures for Atlas in production environments, including installation, configuration, and ongoing maintenance.

## Table of Contents

- [Deployment Overview](#deployment-overview)
- [System Requirements](#system-requirements)
- [Installation](#installation)
- [Configuration](#configuration)
- [Service Management](#service-management)
- [Deployment Strategies](#deployment-strategies)
- [Monitoring and Maintenance](#monitoring-and-maintenance)
- [Security Considerations](#security-considerations)
- [Troubleshooting](#troubleshooting)
- [Backup and Recovery](#backup-and-recovery)

## Deployment Overview

Atlas is designed to be deployed as a set of interconnected services that work together to provide reliable content ingestion and processing. The deployment process includes:

1. **System preparation** - installing dependencies and configuring the environment
2. **Application deployment** - installing and configuring Atlas services
3. **Service management** - configuring systemd services for automatic startup
4. **Monitoring setup** - configuring monitoring and alerting
5. **Ongoing maintenance** - regular updates and health checks

### Architecture Overview

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Atlas API     │    │ Atlas Scheduler │    │ Atlas Worker    │
│   (FastAPI)     │    │   (Tasks)       │    │ (Processing)    │
│   Port: 7444    │    │                 │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
         ┌───────────────────────┼───────────────────────┐
         │                       │                       │
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│ Atlas Monitor   │    │Atlas Observable │    │   Database      │
│ (Dashboard)     │    │ (Metrics/Logs)  │    │   (SQLite)      │
│ Port: 7445      │    │ Port: 7446      │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## System Requirements

### Minimum Requirements

- **OS**: Ubuntu 20.04+ LTS or equivalent
- **CPU**: 2 cores (4 cores recommended)
- **RAM**: 4GB (8GB recommended)
- **Storage**: 50GB SSD (100GB recommended)
- **Network**: Stable internet connection for external APIs

### Recommended Requirements

- **OS**: Ubuntu 22.04+ LTS
- **CPU**: 4+ cores
- **RAM**: 8GB+ (16GB for high-volume processing)
- **Storage**: 100GB+ SSD with expansion capability
- **Network**: High-speed connection with unlimited data

### Software Dependencies

#### System Packages

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install -y python3 python3-pip python3-venv sqlite3 systemd nginx

# RHEL/CentOS
sudo yum install -y python3 python3-pip sqlite3 systemd nginx
```

#### Python Packages

```bash
# Core requirements
python3 -m pip install --upgrade pip
python3 -m pip install -r requirements.txt
```

### Network Requirements

#### Port Configuration

| Service | Port | Purpose | External Access |
|---------|------|---------|-----------------|
| Atlas API | 7444 | Main API and web interface | Optional (via reverse proxy) |
| Atlas Monitor | 7445 | Monitoring dashboard | Internal only |
| Atlas Observability | 7446 | Metrics and logs | Internal only |

#### Firewall Configuration

```bash
# Allow API port (if direct access needed)
sudo ufw allow 7444/tcp

# Allow monitoring ports (internal access)
sudo ufw allow from 192.168.1.0/24 to any port 7445
sudo ufw allow from 192.168.1.0/24 to any port 7446

# Allow SSH for management
sudo ufw allow ssh

# Enable firewall
sudo ufw enable
```

## Installation

### Step 1: System Preparation

```bash
# Create atlas user
sudo useradd -m -s /bin/bash atlas
sudo usermod -aG sudo atlas

# Switch to atlas user
sudo su - atlas

# Create directories
mkdir -p ~/atlas/{config,data,logs,backups}
mkdir -p ~/atlas/config/secrets
```

### Step 2: Clone Repository

```bash
# Clone the repository
git clone https://github.com/your-org/atlas.git ~/atlas

# Navigate to atlas directory
cd ~/atlas

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Step 3: Configuration

```bash
# Copy configuration files
cp config/development.env config/.env

# Edit configuration
nano config/.env

# Set environment
export ATLAS_ENVIRONMENT=production

# Generate encryption key
python3 tools/config_cli.py generate-key
```

### Step 4: Database Setup

```bash
# Initialize database
python3 core/database.py

# Enable WAL mode for better performance
python3 tools/config_cli.py set DATABASE_WAL_MODE true

# Set database path
python3 tools/config_cli.py set ATLAS_DATABASE_PATH /home/atlas/atlas/data/prod/atlas.db
```

### Step 5: Service Installation

```bash
# Install systemd services
sudo cp systemd/* /etc/systemd/system/

# Update service files with correct paths
sudo sed -i "s|/opt/atlas|/home/atlas/atlas|g" /etc/systemd/system/atlas-*.service

# Reload systemd
sudo systemctl daemon-reload

# Enable services
sudo systemctl enable atlas-api atlas-scheduler atlas-worker atlas-monitor atlas-observability
```

### Step 6: Start Services

```bash
# Start services in dependency order
sudo systemctl start atlas-observability
sudo systemctl start atlas-monitor
sudo systemctl start atlas-api
sudo systemctl start atlas-scheduler
sudo systemctl start atlas-worker

# Check service status
sudo systemctl status atlas-*
```

## Configuration

### Production Configuration

Create a production configuration file:

```bash
# Create production configuration
cat > config/production.env << EOF
# Production environment
ATLAS_ENVIRONMENT=production

# Database
ATLAS_DATABASE_PATH=/home/atlas/atlas/data/prod/atlas.db
DATABASE_WAL_MODE=true
DATABASE_TIMEOUT=30

# API Settings
API_HOST=0.0.0.0
API_PORT=7444
API_DEBUG=false
API_CORS_ORIGINS=https://your-domain.com

# Security
API_TOKEN_REQUIRED=true
JWT_SECRET_KEY=your-jwt-secret-key
SESSION_SECRET=your-session-secret

# Processing
MAX_CONCURRENT_ARTICLES=8
ARTICLE_PROCESSING_TIMEOUT=600

# Monitoring
MONITORING_ENABLED=true
OBSERVABILITY_ENABLED=true
ALERTING_ENABLED=true

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json
EOF
```

### Secret Management

```bash
# Set required secrets
python3 tools/config_cli.py secret set OPENROUTER_API_KEY your-openrouter-key
python3 tools/config_cli.py secret set YOUTUBE_API_KEY your-youtube-key
python3 tools/config_cli.py secret set GOOGLE_SEARCH_API_KEY your-google-key
python3 tools/config_cli.py secret set GOOGLE_SEARCH_CX your-google-cx

# Set email credentials (if needed)
python3 tools/config_cli.py secret set EMAIL_USERNAME your-email@gmail.com
python3 tools/config_cli.py secret set EMAIL_PASSWORD your-app-password
```

### Reverse Proxy Configuration (Optional)

Configure nginx as a reverse proxy:

```nginx
# /etc/nginx/sites-available/atlas
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://localhost:7444;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /monitoring {
        proxy_pass http://localhost:7445;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

```bash
# Enable site
sudo ln -s /etc/nginx/sites-available/atlas /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

## Service Management

### Starting and Stopping Services

```bash
# Start all services
sudo systemctl start atlas-api atlas-scheduler atlas-worker atlas-monitor atlas-observability

# Stop all services
sudo systemctl stop atlas-api atlas-scheduler atlas-worker atlas-monitor atlas-observability

# Restart specific service
sudo systemctl restart atlas-api

# Check service status
sudo systemctl status atlas-api
```

### Service Dependencies

Services should be started in this order:

1. **atlas-observability** - Metrics and logging
2. **atlas-monitor** - Monitoring dashboard
3. **atlas-api** - Main API service
4. **atlas-scheduler** - Task scheduling
5. **atlas-worker** - Background processing

### Health Checks

```bash
# Check API health
curl http://localhost:7444/health

# Check monitoring health
curl http://localhost:7445/health

# Check observability health
curl http://localhost:7446/health

# Check all services
python3 tools/atlas_ops.py health-check
```

## Deployment Strategies

### Blue-Green Deployment

1. **Prepare New Environment**
   ```bash
   # Create new deployment directory
   mkdir -p /home/atlas/atlas-blue

   # Deploy new version
   git clone https://github.com/your-org/atlas.git /home/atlas/atlas-blue
   cd /home/atlas/atlas-blue

   # Install dependencies
   source venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Configure New Environment**
   ```bash
   # Copy configuration
   cp ../atlas/config/.env config/.env

   # Update configuration if needed
   python3 tools/config_cli.py set API_PORT 7447
   ```

3. **Start New Services**
   ```bash
   # Start new services on different ports
   sudo systemctl start atlas-blue-api
   sudo systemctl start atlas-blue-monitor

   # Test new deployment
   curl http://localhost:7447/health
   ```

4. **Switch Traffic**
   ```bash
   # Update nginx configuration
   sudo nano /etc/nginx/sites-available/atlas

   # Change proxy_pass to new port
   # proxy_pass http://localhost:7447;

   # Reload nginx
   sudo systemctl reload nginx
   ```

5. **Cleanup Old Deployment**
   ```bash
   # Stop old services
   sudo systemctl stop atlas-api atlas-monitor

   # Remove old deployment
   sudo rm -rf /home/atlas/atlas
   mv /home/atlas/atlas-blue /home/atlas/atlas
   ```

### Rolling Deployment

1. **Update Application**
   ```bash
   # Pull latest changes
   cd /home/atlas/atlas
   git pull origin main

   # Update dependencies
   source venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Rolling Restart**
   ```bash
   # Restart services one by one
   sudo systemctl restart atlas-worker
   sleep 10
   sudo systemctl restart atlas-scheduler
   sleep 10
   sudo systemctl restart atlas-api
   ```

### Canary Deployment

1. **Deploy to Subset of Servers**
   ```bash
   # Deploy to canary server
   ssh canary-server "cd /home/atlas/atlas && git pull && pip install -r requirements.txt"

   # Restart canary services
   ssh canary-server "sudo systemctl restart atlas-*"

   # Monitor canary performance
   python3 tools/monitoring_agent.py status --server canary-server
   ```

2. **Gradual Rollout**
   ```bash
   # Deploy to 10% of servers
   for server in $(cat servers.txt | head -n 1); do
     ssh $server "cd /home/atlas/atlas && git pull && pip install -r requirements.txt"
     ssh $server "sudo systemctl restart atlas-*"
   done

   # Monitor and gradually deploy to remaining servers
   ```

## Monitoring and Maintenance

### System Monitoring

```bash
# Check system resources
htop
df -h
free -h

# Check service logs
sudo journalctl -u atlas-api -f
sudo journalctl -u atlas-scheduler -f
sudo journalctl -u atlas-worker -f

# Check application logs
tail -f logs/atlas.log
```

### Performance Monitoring

```bash
# Check API performance
curl -w "@curl-format.txt" -o /dev/null -s http://localhost:7444/health

# Monitor database performance
python3 tools/atlas_ops.py check-database

# Check worker queue status
python3 tools/atlas_ops.py queue-status
```

### Log Management

```bash
# Rotate logs
sudo logrotate -f /etc/logrotate.d/atlas

# Archive old logs
find logs/ -name "*.log.*" -mtime +30 -exec gzip {} \;

# Clean up old logs
find logs/ -name "*.log.*.gz" -mtime +90 -delete
```

### Database Maintenance

```bash
# Optimize database
python3 tools/atlas_ops.py optimize-database

# Vacuum database
python3 tools/atlas_ops.py vacuum-database

# Check database integrity
python3 tools/atlas_ops.py check-database

# Create backup
python3 tools/atlas_ops.py backup
```

## Security Considerations

### System Security

```bash
# Update system packages
sudo apt update && sudo apt upgrade -y

# Configure automatic security updates
sudo apt install -y unattended-upgrades
sudo dpkg-reconfigure -plow unattended-upgrades

# Configure firewall
sudo ufw enable
sudo ufw default deny incoming
sudo ufw default allow outgoing
```

### Application Security

```bash
# Set proper file permissions
chmod 600 config/.env
chmod 600 config/secrets/*.secrets
chmod 700 config/secrets/
chmod 755 logs/
chmod 644 logs/*.log

# Configure log rotation
sudo tee /etc/logrotate.d/atlas > /dev/null << EOF
/home/atlas/atlas/logs/*.log {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    notifempty
    create 644 atlas atlas
    postrotate
        systemctl reload atlas-api atlas-scheduler atlas-worker
    endscript
}
EOF
```

### Secret Management

```bash
# Generate strong secrets
openssl rand -hex 32 > /home/atlas/.atlas_encryption_key
chmod 600 /home/atlas/.atlas_encryption_key

# Configure environment variables
echo "export ATLAS_ENCRYPTION_KEY=$(cat /home/atlas/.atlas_encryption_key)" >> /home/atlas/.bashrc

# Regular secret rotation
python3 tools/config_cli.py secret rotate-all
```

### Network Security

```bash
# Configure SSH security
sudo nano /etc/ssh/sshd_config

# Recommended settings:
# Port 22
# PermitRootLogin no
# PasswordAuthentication no
# PubkeyAuthentication yes

# Restart SSH
sudo systemctl restart sshd
```

## Troubleshooting

### Common Issues

#### Service Won't Start

```bash
# Check service status
sudo systemctl status atlas-api

# Check service logs
sudo journalctl -u atlas-api -n 50

# Check configuration
python3 tools/config_cli.py validate

# Check dependencies
python3 -c "import fastapi; import uvicorn; import sqlalchemy"
```

#### Database Connection Issues

```bash
# Check database file
ls -la /home/atlas/atlas/data/prod/atlas.db

# Check database permissions
ls -la /home/atlas/atlas/data/prod/

# Test database connection
python3 -c "
from core.database import get_db
db = next(get_db())
print('Database connection successful')
"
```

#### Memory Issues

```bash
# Check memory usage
free -h
htop

# Check memory limits
sudo systemctl show atlas-api | grep MemoryLimit

# Adjust memory limits
sudo systemctl edit atlas-api

# Add:
# [Service]
# MemoryLimit=4G
```

#### Performance Issues

```bash
# Check CPU usage
top -p $(pgrep -f atlas-api)

# Check database performance
python3 tools/atlas_ops.py check-database

# Check worker queue
python3 tools/atlas_ops.py queue-status

# Check network performance
iperf3 -s
```

### Debug Commands

```bash
# Show service status
sudo systemctl status atlas-*

# Show recent logs
sudo journalctl -u atlas-api --since "1 hour ago"

# Show configuration
python3 tools/config_cli.py show

# Show system metrics
python3 tools/atlas_ops.py metrics

# Test API connectivity
curl -v http://localhost:7444/health
```

### Emergency Procedures

#### Service Failure

```bash
# Restart all services
sudo systemctl restart atlas-*

# Check for port conflicts
sudo netstat -tlnp | grep -E ':744[4-6]'

# Check system resources
df -h
free -h
```

#### Database Corruption

```bash
# Check database integrity
sqlite3 /home/atlas/atlas/data/prod/atlas.db "PRAGMA integrity_check;"

# Restore from backup
python3 tools/atlas_ops.py restore --backup-file /path/to/backup.sql

# Rebuild database if needed
mv /home/atlas/atlas/data/prod/atlas.db /home/atlas/atlas/data/prod/atlas.db.corrupt
python3 core/database.py
```

#### Data Loss

```bash
# Restore from backup
python3 tools/atlas_ops.py restore --backup-file /path/to/backup.sql

# Check backup integrity
sqlite3 /path/to/backup.sql "PRAGMA integrity_check;"

# Verify data consistency
python3 tools/atlas_ops.py check-database
```

## Backup and Recovery

### Automated Backups

```bash
# Create backup script
cat > /home/atlas/atlas/backup.sh << EOF
#!/bin/bash
# Atlas backup script

DATE=\$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/home/atlas/atlas/backups"
DB_PATH="/home/atlas/atlas/data/prod/atlas.db"

# Create backup directory
mkdir -p \$BACKUP_DIR

# Backup database
sqlite3 \$DB_PATH ".backup \$BACKUP_DIR/atlas_\$DATE.db"

# Backup configuration
tar -czf \$BACKUP_DIR/config_\$DATE.tar.gz config/

# Cleanup old backups (keep 30 days)
find \$BACKUP_DIR -name "*.db" -mtime +30 -delete
find \$BACKUP_DIR -name "*.tar.gz" -mtime +30 -delete

echo "Backup completed: \$DATE"
EOF

chmod +x /home/atlas/atlas/backup.sh
```

### Scheduled Backups

```bash
# Create systemd timer
sudo tee /etc/systemd/system/atlas-backup.timer > /dev/null << EOF
[Unit]
Description=Atlas backup timer
Requires=atlas-backup.service

[Timer]
OnCalendar=daily
Persistent=true

[Install]
WantedBy=timers.target
EOF

sudo tee /etc/systemd/system/atlas-backup.service > /dev/null << EOF
[Unit]
Description=Atlas backup service

[Service]
Type=oneshot
User=atlas
Group=atlas
ExecStart=/home/atlas/atlas/backup.sh
EOF

# Enable backup timer
sudo systemctl daemon-reload
sudo systemctl enable atlas-backup.timer
sudo systemctl start atlas-backup.timer
```

### Recovery Procedures

#### Database Recovery

```bash
# Stop services
sudo systemctl stop atlas-api atlas-scheduler atlas-worker

# Restore database
cp /path/to/backup.db /home/atlas/atlas/data/prod/atlas.db

# Start services
sudo systemctl start atlas-api atlas-scheduler atlas-worker

# Verify restoration
curl http://localhost:7444/health
```

#### Configuration Recovery

```bash
# Restore configuration
tar -xzf /path/to/config_backup.tar.gz -C config/

# Reload configuration
python3 tools/config_cli.py reload

# Restart services
sudo systemctl restart atlas-*
```

#### Complete System Recovery

```bash
# Create new server
# Install system dependencies
# Create atlas user
# Clone repository
# Restore database from backup
# Restore configuration from backup
# Start services
# Verify all systems
```

## Performance Tuning

### Database Optimization

```bash
# Enable WAL mode
python3 tools/config_cli.py set DATABASE_WAL_MODE true

# Set appropriate cache size
python3 tools/config_cli.py set DATABASE_CACHE_SIZE 65536

# Optimize journal mode
python3 tools/config_cli.py set DATABASE_JOURNAL_MODE WAL

# Set timeout values
python3 tools/config_cli.py set DATABASE_TIMEOUT 60
python3 tools/config_cli.py set DATABASE_CONNECTION_TIMEOUT 30
```

### Application Optimization

```bash
# Optimize worker count
python3 tools/config_cli.py set MAX_CONCURRENT_ARTICLES $(nproc)

# Set appropriate timeouts
python3 tools/config_cli.py set ARTICLE_PROCESSING_TIMEOUT 600

# Configure retry settings
python3 tools/config_cli.py set CONTENT_PROCESSING_RETRY_COUNT 5
python3 tools/config_cli.py set CONTENT_PROCESSING_RETRY_DELAY 120

# Enable caching
python3 tools/config_cli.py set CACHE_ENABLED true
python3 tools/config_cli.py set CACHE_TTL 600
```

### System Optimization

```bash
# Configure system limits
sudo tee /etc/security/limits.d/atlas.conf > /dev/null << EOF
atlas soft nofile 65536
atlas hard nofile 65536
atlas soft nproc 4096
atlas hard nproc 4096
EOF

# Configure sysctl settings
sudo tee /etc/sysctl.d/99-atlas.conf > /dev/null << EOF
# Network optimization
net.core.rmem_max = 16777216
net.core.wmem_max = 16777216
net.ipv4.tcp_rmem = 4096 65536 16777216
net.ipv4.tcp_wmem = 4096 65536 16777216

# File system optimization
fs.file-max = 100000
vm.swappiness = 10
EOF

sudo sysctl -p
```

---

*This guide is part of the Atlas documentation. For additional information, see other files in the `docs/` directory.*