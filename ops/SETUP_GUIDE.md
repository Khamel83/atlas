# 🚀 OOS Agent-OS Setup Guide

Complete setup guide for deploying OOS with Agent-OS integration on OCI free tier.

## Quick Start (3 Commands)

```bash
# 1. Bootstrap the system
make -C ops bootstrap

# 2. Configure environment
cp ops/.env.template ops/.env && $EDITOR ops/.env

# 3. Initialize and check health
sqlite3 /opt/oos/data/oos.db < ops/schema.sql && make -C ops start
```

## Prerequisites

### System Requirements
- Ubuntu 20.04+ or similar Linux distribution
- 1GB RAM minimum (OCI free tier: VM.Standard.E2.1.Micro)
- 10GB storage minimum (OCI free tier: 200GB block volume)
- SSH access with key-based authentication

### Required Tools
```bash
# Install on Ubuntu/Debian
sudo apt-get update
sudo apt-get install -y sqlite3 python3-pip curl jq

# Install Python tools
pip3 install --user datasette sqlite-web

# Install security tools
make -C ops install-sops
```

## Step-by-Step Setup

### 1. Initial System Setup

```bash
# Create OOS user (recommended)
sudo useradd -m -s /bin/bash oos
sudo usermod -aG sudo oos

# Create directory structure
sudo mkdir -p /opt/oos/{data,backups,config}
sudo chown -R oos:oos /opt/oos

# Clone OOS repository
sudo -u oos git clone https://github.com/Khamel83/oos.git /opt/oos/repo
cd /opt/oos/repo
```

### 2. Environment Configuration

```bash
# Copy and edit environment template
cp ops/.env.template ops/.env

# Essential configuration variables:
cat >> ops/.env << 'EOF'
# Paths
OOS_DB=/opt/oos/data/oos.db
OOS_DATA_ROOT=/opt/oos/data
OOS_BACKUP_DIR=/opt/oos/backups

# Security
SOPS_AGE_KEY_FILE=/opt/oos/config/age-key.txt

# Google Sheets (optional but recommended)
GOOGLE_SERVICE_ACCOUNT_JSON=/opt/oos/config/service-account.json
GOOGLE_SPREADSHEET_ID=your_spreadsheet_id_here

# Monitoring (optional)
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_CHAT_ID=your_chat_id_here
EOF
```

### 3. Database Initialization

```bash
# Initialize SQLite database
mkdir -p /opt/oos/data
sqlite3 /opt/oos/data/oos.db < ops/schema.sql

# Verify initialization
sqlite3 /opt/oos/data/oos.db "SELECT name FROM sqlite_master WHERE type='table';"
```

### 4. Security Setup

```bash
# Generate age key for secrets encryption
age-keygen -o /opt/oos/config/age-key.txt
chmod 600 /opt/oos/config/age-key.txt

# Set up Google Sheets service account (if using)
# 1. Create service account in Google Cloud Console
# 2. Download JSON key file
# 3. Place at /opt/oos/config/service-account.json
# 4. Share your Google Sheet with the service account email
```

### 5. systemd Services Setup

```bash
# Copy systemd files
sudo cp ops/systemd/*.service ops/systemd/*.timer /etc/systemd/system/

# Create system environment file
sudo mkdir -p /etc/oos
sudo cp ops/.env /etc/oos/oos.env

# Enable and start timers
sudo systemctl daemon-reload
make -C ops enable-timers

# Verify services
sudo systemctl status backup-sqlite.timer
sudo systemctl status export-to-sheets.timer
sudo systemctl status writeback-from-sheets.timer
```

### 6. Verify Installation

```bash
# Run comprehensive health check
ops/scripts/health_check.sh

# Run preflight checks
make -C ops preflight

# Test backup system
make -C ops backup

# Test database access
make -C ops readui
# Access via SSH tunnel: ssh -L 9090:127.0.0.1:9090 user@host
```

## Daily Operations

### Starting a Development Session

```bash
# Run this at the start of each development session
make -C ops start

# Copy the output and paste into Claude Code as your first message
```

### Monitoring System Health

```bash
# Quick health check
ops/scripts/health_check.sh

# Detailed system status
make -C ops preflight

# View recent activity
sqlite3 /opt/oos/data/oos.db "SELECT * FROM events_log ORDER BY timestamp DESC LIMIT 10;"
```

### Data Access

```bash
# Read-only data browsing (safe)
make -C ops readui
# Then: ssh -L 9090:127.0.0.1:9090 user@host
# Browse: http://localhost:9090

# Direct database editing (rare, requires care)
make -C ops editui
# Then: ssh -L 8080:127.0.0.1:8080 user@host
# Browse: http://localhost:8080
```

### Backup and Restore

```bash
# Manual backup
make -C ops backup

# Test restore procedure
ops/scripts/restore_test.sh

# List available backups
ls -la /opt/oos/backups/
```

## Google Sheets Integration

### Setup Process

1. **Create Google Sheet** with these tabs:
   - `Pending_Approvals`
   - `Runs`
   - `Errors_Hotlist`
   - `KPIs`

2. **Configure Service Account**:
   ```bash
   # 1. Go to Google Cloud Console
   # 2. Create new project or select existing
   # 3. Enable Google Sheets API
   # 4. Create service account
   # 5. Download JSON key
   # 6. Share sheet with service account email
   ```

3. **Test Integration**:
   ```bash
   # Export data to sheets (currently stub)
   ops/scripts/export_to_sheets.sh

   # Import approved changes (currently stub)
   ops/scripts/writeback_from_sheets.sh
   ```

### Sheet Structure

See `ops/docs/MIRROR_CONTRACT.md` for detailed column specifications.

## Security Hardening

### Network Security
- All services bind to `127.0.0.1` only
- Access via SSH tunnels: `ssh -L local_port:127.0.0.1:remote_port user@host`
- No public web interfaces

### Authentication
- SSH key authentication only
- No passwords in URLs or configs
- Service accounts for API access

### Secrets Management
```bash
# Encrypt sensitive files with sops
sops --encrypt --age $(cat /opt/oos/config/age-key.txt | grep public | cut -d: -f2) ops/.env.secret > ops/.env.secret.enc

# Decrypt when needed
sops --decrypt ops/.env.secret.enc > ops/.env.secret
```

### File Permissions
```bash
# Set secure permissions
chmod 600 /opt/oos/data/oos.db
chmod 600 /opt/oos/config/age-key.txt
chmod 600 /opt/oos/config/service-account.json
```

## Monitoring and Alerting

### Health Monitoring
```bash
# Manual health check
ops/scripts/health_check.sh

# Daily heartbeat (automated)
ops/scripts/heartbeat.sh
```

### Log Management
```bash
# View systemd logs
journalctl -u backup-sqlite.service -n 50
journalctl -u export-to-sheets.service -n 50

# View application events
sqlite3 /opt/oos/data/oos.db "SELECT * FROM events_log WHERE event_type = 'error' ORDER BY timestamp DESC LIMIT 10;"
```

### Telegram Notifications
```bash
# Configure in ops/.env
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id

# Test notification
ops/scripts/heartbeat.sh
```

## Troubleshooting

### Common Issues

**Database locked errors**:
```bash
# Check for hanging processes
ps aux | grep sqlite

# Check WAL mode
sqlite3 /opt/oos/data/oos.db "PRAGMA journal_mode;"

# Re-enable WAL if needed
sqlite3 /opt/oos/data/oos.db "PRAGMA journal_mode=WAL;"
```

**Service not starting**:
```bash
# Check service status
sudo systemctl status service-name.service

# View logs
journalctl -u service-name.service -n 50

# Check environment
sudo systemctl edit service-name.service
```

**Backup failures**:
```bash
# Check disk space
df -h /opt/oos

# Check permissions
ls -la /opt/oos/backups/

# Manual backup test
ops/scripts/backup_sqlite.sh
```

### Emergency Procedures

**Database corruption**:
```bash
# 1. Stop all services
sudo systemctl stop backup-sqlite.timer export-to-sheets.timer writeback-from-sheets.timer

# 2. Check integrity
sqlite3 /opt/oos/data/oos.db "PRAGMA integrity_check;"

# 3. Restore from backup if needed
cp /opt/oos/backups/oos_YYYYMMDD.db /opt/oos/data/oos.db

# 4. Restart services
sudo systemctl start backup-sqlite.timer export-to-sheets.timer writeback-from-sheets.timer
```

**Disk space emergency**:
```bash
# Clean old backups
find /opt/oos/backups -name "oos_*.db" -mtime +7 -delete

# Clean system logs
sudo journalctl --vacuum-time=1d

# Check for large files
du -sh /opt/oos/* | sort -hr
```

## Maintenance Schedule

### Daily (Automated)
- Database backups (02:00)
- Google Sheets sync (hourly)
- Health monitoring

### Weekly (Manual)
- Review health check reports
- Check disk usage trends
- Update system packages

### Monthly (Manual)
- Test backup restore procedure
- Review security configurations
- Update documentation

### Quarterly (Manual)
- Full disaster recovery drill
- Security audit
- Performance review

## Advanced Configuration

### Custom Monitoring
Add custom health checks to `ops/scripts/health_check.sh`

### Extended Backup Retention
Modify `BACKUP_RETENTION_DAYS` in `ops/.env`

### Additional Security
- Enable full disk encryption
- Configure fail2ban
- Set up intrusion detection

### Performance Tuning
- Adjust SQLite PRAGMA settings
- Configure logrotate for application logs
- Monitor and optimize queries

---

This setup provides a production-ready OOS deployment with Agent-OS integration, following security best practices while remaining cost-effective on OCI free tier.