# Atlas Operations Runbook

**Last Updated**: 2025-12-04
**Audience**: Operators, DevOps, Future You

## Quick Reference

| Task | Command |
|------|---------|
| Check status | `make status` or `./atlas_status.sh` |
| Start system | `make run` |
| Stop system | `make stop` |
| View logs | `tail -f logs/atlas_manager.log` |
| Run tests | `make test` |
| Deploy service | `make deploy` |

## Starting Atlas

### Development (Local)
```bash
# Option 1: Makefile
make run

# Option 2: Direct script
./scripts/start/start_atlas.sh

# Option 3: Direct Python
python3 processors/atlas_manager.py
```

### Production (Systemd)
```bash
# Start
sudo systemctl start atlas-manager

# Enable auto-start on boot
sudo systemctl enable atlas-manager

# Check status
sudo systemctl status atlas-manager

# View logs
sudo journalctl -u atlas-manager -f
```

## Stopping Atlas

### Development
```bash
# Option 1: Makefile
make stop

# Option 2: Manual
pkill -f atlas_manager.py
```

### Production
```bash
sudo systemctl stop atlas-manager
```

## Checking Status

```bash
# Quick status
make status

# Detailed status
./atlas_status.sh

# API health check
curl http://localhost:7444/health

# Database stats
sqlite3 podcast_processing.db "SELECT COUNT(*) FROM episodes WHERE transcript_found = 1"

# Check processes
ps aux | grep atlas
```

## Common Operations

### View Logs
```bash
# Manager logs
tail -f logs/atlas_manager.log

# Systemd logs
sudo journalctl -u atlas-manager -n 100 --no-pager

# API logs
sudo journalctl -u atlas-api -f
```

### Restart After Config Change
```bash
# Development
make stop
# Edit config/feeds.yaml or .env
make run

# Production
sudo systemctl restart atlas-manager
```

### Database Operations
```bash
# Backup database
cp podcast_processing.db podcast_processing.db.backup.$(date +%Y%m%d)

# Check database size
du -h podcast_processing.db

# Run integrity check
sqlite3 podcast_processing.db "PRAGMA integrity_check;"

# Query episode count
sqlite3 podcast_processing.db "SELECT COUNT(*) FROM episodes"

# Query transcript success rate
sqlite3 podcast_processing.db "SELECT 
  COUNT(*) as total,
  SUM(CASE WHEN transcript_found = 1 THEN 1 ELSE 0 END) as found,
  ROUND(100.0 * SUM(CASE WHEN transcript_found = 1 THEN 1 ELSE 0 END) / COUNT(*), 2) as percentage
FROM episodes"
```

## Troubleshooting

### Process Won't Start
```bash
# Check for existing process
ps aux | grep atlas_manager

# Kill if stuck
pkill -9 -f atlas_manager.py

# Check port conflicts (API)
lsof -i :7444

# Check logs for errors
tail -50 logs/atlas_manager.log
```

### Database Locked
```bash
# Check for multiple processes
ps aux | grep atlas

# Kill all Atlas processes
pkill -f atlas

# Wait a few seconds
sleep 5

# Restart
make run
```

### High CPU/Memory Usage
```bash
# Check resource usage
top -p $(pgrep -f atlas_manager.py)

# Check database size
du -sh data/

# Check log size
du -sh logs/

# Consider cleanup
make clean
```

### API Not Responding
```bash
# Check API process
curl http://localhost:7444/health

# Check API logs
sudo journalctl -u atlas-api -n 50

# Restart API service
sudo systemctl restart atlas-api
```

## Deployment Procedures

### Deploy New Version
```bash
# 1. Backup database
cp podcast_processing.db podcast_processing.db.backup.$(date +%Y%m%d_%H%M%S)

# 2. Stop service
sudo systemctl stop atlas-manager

# 3. Pull latest code
git pull origin main

# 4. Update dependencies
source venv/bin/activate
pip install -r requirements.txt --upgrade

# 5. Run tests (optional)
make test

# 6. Restart service
sudo systemctl start atlas-manager

# 7. Verify
make status
curl http://localhost:7444/health
```

### Rollback Procedure
```bash
# 1. Stop service
sudo systemctl stop atlas-manager

# 2. Restore previous version
git checkout <previous-commit>

# 3. Restore database if needed
cp podcast_processing.db.backup.<timestamp> podcast_processing.db

# 4. Restart
sudo systemctl start atlas-manager

# 5. Verify
make status
```

## Maintenance

### Daily Checks
- [ ] Check system status: `make status`
- [ ] Review logs for errors: `tail logs/atlas_manager.log`
- [ ] Verify API health: `curl http://localhost:7444/health`

### Weekly Tasks
- [ ] Backup database: `cp podcast_processing.db backups/`
- [ ] Check disk space: `df -h`
- [ ] Review processing stats: `./atlas_status.sh`

### Monthly Tasks
- [ ] Clean old logs: `find logs/ -name "*.log" -mtime +30 -delete`
- [ ] Update dependencies: `pip install -r requirements.txt --upgrade`
- [ ] Review and archive migration docs

## Migration History

See `docs/migrations/` for detailed migration reports:
- `MIGRATION_REPORT.md` - Ubuntu → Homelab migration (Nov 2025)
- `ATLAS_CONTENT_PROCESSING_STATUS.md` - Content processing status
- `MAC_ARCHIVE_TRANSFER_PLAN.md` - Mac archive migration plan

## Emergency Contacts

**For system issues**:
- Check `docs/TROUBLESHOOTING.md` (TODO)
- Review logs in `logs/`
- Check GitHub issues

**For deployment issues**:
- Review `docs/SETUP.md`
- Check systemd service status
- Verify environment configuration

---

**Remember**: Always backup the database before major operations!
