# Atlas Reliability Runbook

## 🚨 Emergency Response Guide

### If Transcript Processing Stalls

**Symptoms:**
- `make status` shows 0 transcriptions or old timestamps
- Episodes > 0 but no new transcripts in 30+ minutes

**Immediate Actions:**
```bash
# 1. Check status
make status

# 2. Restart services
make restart

# 3. Monitor logs
make logs

# 4. Run smoke test
make smoke
```

**If Still Failing:**
```bash
# Check database connectivity
python3 scripts/db_introspect.py

# Test worker manually
python3 scripts/fixed_transcript_worker.py --limit 1

# Check disk space
df -h

# Check memory
free -h
```

### Service Recovery Commands

**Atlas Main Service:**
```bash
sudo systemctl restart atlas.service
sudo systemctl status atlas.service
journalctl -u atlas.service -f
```

**Watchdog Service:**
```bash
sudo systemctl restart atlas-watchdog.timer
sudo systemctl status atlas-watchdog.timer
journalctl -u atlas-watchdog -f
```

**Transcript Discovery:**
```bash
sudo systemctl restart atlas-discovery.timer
sudo systemctl status atlas-discovery.timer
journalctl -u atlas-discovery -f
```

## 📊 Health Check Commands

### Quick Status Check
```bash
make status
```

### Detailed Diagnostics
```bash
# Database health
python3 scripts/db_introspect.py

# Processing stats with details
python3 atlas_status.py --detailed

# Recent logs
make logs

# System resources
htop
df -h
```

### Manual Testing
```bash
# Test transcript worker
python3 scripts/fixed_transcript_worker.py --limit 2

# Test watchdog
python3 maintenance/enhanced_progress_watchdog.py

# Test notifications (requires Telegram setup)
python3 scripts/notify.py --test
```

## 🔧 Common Issues & Solutions

### "No transcriptions found"
**Cause:** Worker saving to wrong table or not running
**Solution:**
```bash
# Use fixed worker (saves to transcriptions table)
python3 scripts/fixed_transcript_worker.py --limit 5

# Check if old content exists
sqlite3 data/atlas.db "SELECT COUNT(*) FROM content WHERE content_type='podcast_transcript'"
```

### "Database path errors"
**Cause:** Inconsistent database paths
**Solution:**
```bash
# Check resolved path
bash scripts/db_path.sh

# Verify ATLAS_DB_PATH in .env
grep ATLAS_DB_PATH .env

# Update all scripts to use centralized config
python3 -c "from helpers.database_config import get_database_path; print(get_database_path())"
```

### "Services not starting"
**Cause:** Missing dependencies or permissions
**Solution:**
```bash
# Install services
make install

# Check service files
sudo systemctl daemon-reload

# Check permissions
ls -la systemd/
sudo chown root:root /etc/systemd/system/atlas-*

# Enable services
sudo systemctl enable --now atlas-watchdog.timer
```

### "Memory leaks"
**Cause:** Long-running processes accumulating memory
**Solution:**
```bash
# Check memory usage
ps aux | grep atlas | sort -k4 -nr

# Restart services (automatic via systemd)
make restart

# Check memory limits
systemctl show atlas.service | grep Memory
```

## ⚙️ Preventive Maintenance

### Daily Checks
```bash
# Run via cron: 0 9 * * * cd /home/ubuntu/dev/atlas && make status
make status > /tmp/atlas_daily_status.log
```

### Weekly Tasks
```bash
# Clean old logs (systemd handles rotation)
find logs/ -name "*.log.*" -mtime +7 -delete

# Backup database
cp data/atlas.db backups/atlas_$(date +%Y%m%d).db

# Update status
make status
```

### Monitoring Setup
```bash
# Install watchdog service
make install
sudo systemctl enable --now atlas-watchdog.timer

# Configure Telegram alerts in .env:
# TELEGRAM_BOT_TOKEN=your_token
# TELEGRAM_CHAT_ID=your_chat_id
```

## 📱 Alert Channels

### Telegram Setup
1. Create bot: https://t.me/BotFather
2. Get bot token
3. Get chat ID: send message to bot, visit https://api.telegram.org/botTOKEN/getUpdates
4. Add to `.env`:
```bash
TELEGRAM_BOT_TOKEN=your_token_here
TELEGRAM_CHAT_ID=your_chat_id_here
```

### Test Alerts
```bash
# Test notification system
python3 scripts/notify.py --test

# Test watchdog alert
python3 scripts/notify.py --msg "Test alert" --title "Manual Test"
```

## 🎯 Expected Behavior

### Healthy System
- Transcriptions count increases regularly
- Latest transcription timestamp within last 30 minutes
- Services show "active (running)" status
- No errors in recent logs
- Disk space > 5GB free

### Auto-Recovery
- Watchdog detects stalls within 5 minutes
- Services restart automatically via systemd
- Telegram alerts sent on issues and recovery
- System resumes processing within 2 minutes

## 📞 Escalation

If automated recovery fails:
1. Check this runbook for manual steps
2. Review system logs: `journalctl -xe`
3. Check disk space and memory
4. Consider reboot if system-wide issues
5. File issue in GitHub repo with logs

**Critical Files to Preserve:**
- `data/atlas.db` (main database)
- `logs/` directory (debugging info)
- `.env` (configuration)