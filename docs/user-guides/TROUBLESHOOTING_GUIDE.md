# Atlas Troubleshooting Guide

This guide helps you diagnose and fix common issues with Atlas. Follow the diagnostic steps to identify problems quickly and apply the appropriate solutions.

## Table of Contents

1. [System Diagnostics](#system-diagnostics)
2. [Common Issues](#common-issues)
3. [Component-Specific Issues](#component-specific-issues)
4. [Performance Issues](#performance-issues)
5. [Recovery Procedures](#recovery-procedures)
6. [Getting Help](#getting-help)

## System Diagnostics

### Quick Health Check

Start with these commands to get an overview of system health:

```bash
# Comprehensive system status
python3 atlas_status.py --detailed

# Check service status
python3 unified_service_manager.py status

# Verify database connectivity
python3 -c "
from helpers.database_config import get_database_connection
try:
    conn = get_database_connection()
    print('✅ Database: Connected')
    conn.close()
except Exception as e:
    print(f'❌ Database: Failed - {e}')
"

# Test AI API connection
python3 -c "
from helpers.ai_interface import get_ai_response
try:
    response = get_ai_response('test')
    print('✅ AI API: Connected')
except Exception as e:
    print(f'❌ AI API: Failed - {e}')
"
```

### Detailed System Diagnostics

```bash
# Comprehensive environment diagnosis
python3 scripts/diagnose_environment.py

# Check all dependencies
python3 scripts/validate_dependencies.py --test-all

# Resource monitoring
python3 helpers/resource_monitor.py --summary

# Log analysis
python3 scripts/log_analyzer.py --recent --errors-only
```

### Service-Specific Health Checks

```bash
# YouTube processing status
python3 -c "
from integrations.youtube_api_client import YouTubeAPIClient
client = YouTubeAPIClient()
print('YouTube API:', client.test_connection())
"

# Mac Mini connectivity
python3 -c "
from helpers.mac_mini_client import MacMiniClient
client = MacMiniClient()
print('Mac Mini:', client.test_connection())
"

# PODEMOS system status
python3 podemos_monitor.py --health-check
```

## Common Issues

### 1. Atlas Won't Start

**Symptoms**: Service fails to start, immediate exit, or connection refused

**Diagnosis**:
```bash
# Check for port conflicts
lsof -i :7444

# Verify Python environment
which python3
python3 --version

# Check virtual environment
source venv/bin/activate || echo "Virtual environment not activated"

# Verify dependencies
pip list | grep -E "(fastapi|sqlite|requests)"
```

**Solutions**:

**A. Port Already in Use**:
```bash
# Find process using port
lsof -i :7444
kill -9 <PID>

# Or change port in .env
echo "API_PORT=8000" >> .env
```

**B. Missing Dependencies**:
```bash
# Reinstall requirements
pip install -r requirements.txt

# Or use setup script
python3 scripts/setup_wizard.py --fix-dependencies
```

**C. Database Issues**:
```bash
# Verify database file exists and is writable
ls -la data/atlas.db
chmod 664 data/atlas.db

# Initialize database if corrupted
python3 scripts/init_atlas_db.py --force
```

### 2. OpenRouter API Errors

**Symptoms**: "API key invalid", "Quota exceeded", or AI features not working

**Diagnosis**:
```bash
# Check API key format
grep OPENROUTER_API_KEY .env
# Should start with "sk-or-v1-"

# Test API connection
curl -H "Authorization: Bearer $OPENROUTER_API_KEY" \
     -H "Content-Type: application/json" \
     https://openrouter.ai/api/v1/models
```

**Solutions**:

**A. Invalid API Key**:
```bash
# Regenerate key at openrouter.ai
# Update .env file
sed -i 's/OPENROUTER_API_KEY=.*/OPENROUTER_API_KEY=sk-or-v1-NEW-KEY/' .env
```

**B. Quota Exceeded**:
- Check usage at OpenRouter dashboard
- Upgrade plan if needed
- Wait for quota reset (monthly)

**C. Network Issues**:
```bash
# Test internet connectivity
curl -I https://openrouter.ai

# Check DNS resolution
nslookup openrouter.ai
```

### 3. Content Processing Failures

**Symptoms**: "Processing failed", content stuck in queue, or timeout errors

**Diagnosis**:
```bash
# Check processing queue status
python3 -c "
from universal_processing_queue import UniversalQueue
queue = UniversalQueue()
print('Queue size:', queue.size())
print('Failed jobs:', len(queue.get_failed_jobs()))
"

# Check recent processing logs
tail -n 50 logs/processing.log | grep -E "(ERROR|FAILED)"
```

**Solutions**:

**A. Queue Stuck**:
```bash
# Clear processing queue
python3 -c "
from universal_processing_queue import UniversalQueue
queue = UniversalQueue()
queue.clear_failed_jobs()
print('Queue cleared')
"

# Restart processing services
python3 unified_service_manager.py restart --processing-only
```

**B. Memory Issues**:
```bash
# Check available memory
free -h

# Reduce concurrent processing
echo "MAX_CONCURRENT_PROCESSING=2" >> .env
```

**C. Network Timeouts**:
```bash
# Increase timeout settings
echo "PROCESSING_TIMEOUT=600" >> .env
echo "DOWNLOAD_TIMEOUT=300" >> .env
```

### 4. Search Not Working

**Symptoms**: No search results, slow searches, or indexing failures

**Diagnosis**:
```bash
# Check search index status
python3 scripts/search_manager.py status

# Test search functionality
python3 -c "
from helpers.semantic_search_ranker import SemanticSearchRanker
ranker = SemanticSearchRanker()
results = ranker.search('test query', limit=5)
print(f'Search results: {len(results)}')
"
```

**Solutions**:

**A. Rebuild Search Index**:
```bash
# Clear and rebuild index
python3 scripts/search_manager.py rebuild

# Or incremental update
python3 scripts/search_manager.py update
```

**B. Database Corruption**:
```bash
# Check database integrity
sqlite3 data/atlas.db "PRAGMA integrity_check;"

# Backup and repair if needed
cp data/atlas.db data/atlas.db.backup
sqlite3 data/atlas.db ".recover" | sqlite3 data/atlas_recovered.db
mv data/atlas_recovered.db data/atlas.db
```

## Component-Specific Issues

### YouTube Processing Issues

**Problem**: "YouTube API quota exceeded"
**Solution**:
```bash
# Check current quota usage
python3 -c "
from integrations.youtube_api_client import YouTubeAPIClient
client = YouTubeAPIClient()
print('Quota usage:', client.get_quota_usage())
"

# Reduce processing frequency
echo "YOUTUBE_PROCESSING_INTERVAL=720" >> .env  # 12 hours instead of 5
```

**Problem**: "No captions available for video"
**Solution**:
```bash
# Enable Mac Mini audio processing for videos without captions
echo "YOUTUBE_USE_MAC_MINI_FALLBACK=true" >> .env

# Or skip videos without captions
echo "YOUTUBE_REQUIRE_CAPTIONS=true" >> .env
```

### PODEMOS Podcast Issues

**Problem**: "PODEMOS processing taking too long"
**Solution**:
```bash
# Check PODEMOS queue status
python3 podemos_monitor.py --queue-status

# Restart PODEMOS services
python3 unified_service_manager.py restart --podemos

# Reduce concurrent processing
echo "PODEMOS_MAX_CONCURRENT=1" >> .env
```

**Problem**: "Oracle OCI upload failing"
**Solution**:
```bash
# Test OCI connectivity
python3 -c "
import boto3
from botocore.exceptions import ClientError
try:
    # Test OCI connection
    session = boto3.Session(
        aws_access_key_id=os.environ['OCI_ACCESS_KEY'],
        aws_secret_access_key=os.environ['OCI_SECRET_KEY']
    )
    s3 = session.client('s3', endpoint_url=os.environ['OCI_ENDPOINT'])
    s3.list_objects_v2(Bucket=os.environ['OCI_BUCKET_NAME'], MaxKeys=1)
    print('✅ OCI: Connected')
except Exception as e:
    print(f'❌ OCI: Failed - {e}')
"

# Check OCI credentials
grep -E "OCI_.*=" .env
```

### Mac Mini Integration Issues

**Problem**: "Mac Mini connection failed"
**Solution**:
```bash
# Test SSH connectivity manually
ssh macmini "echo 'SSH connection successful'"

# Check SSH key configuration
ls -la ~/.ssh/id_rsa*
ssh-add -l

# Regenerate SSH connection if needed
./scripts/setup_mac_mini_ssh.sh --force
```

**Problem**: "Mac Mini worker not responding"
**Solution**:
```bash
# Check worker status on Mac Mini
ssh macmini "ps aux | grep atlas_worker"

# Restart worker on Mac Mini
ssh macmini "pkill -f atlas_worker && nohup python3 ~/atlas_worker/scripts/mac_mini_worker.py > ~/atlas_worker/logs/worker.log 2>&1 &"

# Check worker logs
ssh macmini "tail -n 20 ~/atlas_worker/logs/worker.log"
```

## Performance Issues

### Slow Processing

**Symptoms**: Long processing times, system responsiveness issues

**Diagnosis**:
```bash
# Monitor system resources
top -bn1 | head -20

# Check disk I/O
iotop -ao

# Database query performance
python3 scripts/db_performance_analyzer.py
```

**Solutions**:

**A. Reduce Concurrent Processing**:
```bash
# Limit concurrent tasks
echo "MAX_CONCURRENT_ARTICLES=3" >> .env
echo "MAX_CONCURRENT_PODCASTS=1" >> .env
echo "MAX_CONCURRENT_YOUTUBE=2" >> .env
```

**B. Optimize Database**:
```bash
# Vacuum database
sqlite3 data/atlas.db "VACUUM;"

# Analyze and optimize
sqlite3 data/atlas.db "ANALYZE;"

# Add indexes if missing
python3 scripts/optimize_database.py
```

**C. Clear Old Data**:
```bash
# Clean old processed items
python3 scripts/cleanup_old_data.py --older-than-days=90

# Clear logs
find logs/ -name "*.log" -mtime +30 -delete
```

### Memory Issues

**Symptoms**: Out of memory errors, system slowdown

**Diagnosis**:
```bash
# Check memory usage
free -h
ps aux --sort=-%mem | head -10

# Monitor memory over time
python3 helpers/resource_monitor.py --memory --duration=300
```

**Solutions**:

**A. Reduce Memory Usage**:
```bash
# Limit cache sizes
echo "SEARCH_INDEX_CACHE_SIZE=100" >> .env
echo "CONTENT_CACHE_SIZE=50" >> .env

# Reduce concurrent processing
echo "MAX_CONCURRENT_TOTAL=3" >> .env
```

**B. Enable Swap**:
```bash
# Check current swap
free -h

# Add swap file if needed (Ubuntu)
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

### Disk Space Issues

**Symptoms**: "No space left on device", processing failures

**Diagnosis**:
```bash
# Check disk usage
df -h
du -sh data/ logs/ output/

# Find large files
find . -type f -size +100M -exec ls -lh {} \;
```

**Solutions**:

**A. Clean Up Data**:
```bash
# Remove old audio files
find data/audio/ -name "*.mp3" -mtime +7 -delete

# Clear temporary files
rm -rf temp/* tmp/*

# Compress old logs
gzip logs/*.log.1 logs/*.log.2
```

**B. Archive Old Content**:
```bash
# Export old content
python3 scripts/export_old_content.py --older-than-months=6 --output=archive/

# Remove exported content from database
python3 scripts/cleanup_archived_content.py --confirm
```

## Recovery Procedures

### Database Recovery

**When to use**: Database corruption, data inconsistency

```bash
# 1. Stop all Atlas services
python3 unified_service_manager.py stop

# 2. Backup current database
cp data/atlas.db data/atlas.db.corrupted.$(date +%Y%m%d-%H%M%S)

# 3. Check database integrity
sqlite3 data/atlas.db "PRAGMA integrity_check;"

# 4. If corrupted, attempt repair
sqlite3 data/atlas.db ".recover" > atlas_recovered.sql
rm data/atlas.db
sqlite3 data/atlas.db < atlas_recovered.sql

# 5. If repair fails, restore from backup
ls -la backups/
cp backups/atlas_backup_YYYYMMDD.db data/atlas.db

# 6. Restart services
python3 unified_service_manager.py start
```

### Configuration Recovery

**When to use**: Configuration corruption, service conflicts

```bash
# 1. Backup current configuration
cp .env .env.backup.$(date +%Y%m%d-%H%M%S)

# 2. Reset to template
cp .env.template .env

# 3. Restore essential settings
echo "OPENROUTER_API_KEY=your-key-here" >> .env
echo "API_PORT=7444" >> .env

# 4. Test configuration
python3 scripts/validate_config.py

# 5. Restart services
python3 unified_service_manager.py restart
```

### Complete System Recovery

**When to use**: Multiple system failures, unknown issues

```bash
# 1. Create recovery backup
mkdir -p recovery/$(date +%Y%m%d-%H%M%S)
cp data/atlas.db recovery/$(date +%Y%m%d-%H%M%S)/
cp .env recovery/$(date +%Y%m%d-%H%M%S)/

# 2. Stop all services
python3 unified_service_manager.py stop
pkill -f atlas

# 3. Clean temporary data
rm -rf temp/* tmp/* logs/*.log

# 4. Reinstall dependencies
pip install -r requirements.txt --force-reinstall

# 5. Rebuild search index
python3 scripts/search_manager.py rebuild

# 6. Restart system
python3 unified_service_manager.py start

# 7. Verify functionality
python3 scripts/system_health_check.py --comprehensive
```

## Log Analysis

### Important Log Files

```bash
# Service logs
tail -f logs/atlas_service.log          # Main service log
tail -f logs/processing.log            # Content processing
tail -f logs/youtube_processing.log    # YouTube specific
tail -f logs/podemos_processing.log    # PODEMOS specific
tail -f logs/api_requests.log          # API access log

# Error logs
grep -E "(ERROR|CRITICAL)" logs/*.log | tail -20

# Performance logs
grep -E "(SLOW|TIMEOUT)" logs/*.log | tail -10
```

### Log Analysis Commands

```bash
# Find recent errors
find logs/ -name "*.log" -mtime -1 -exec grep -l "ERROR" {} \; | xargs tail -n 5

# Count error types
grep "ERROR" logs/*.log | cut -d: -f2 | sort | uniq -c | sort -nr

# Performance analysis
grep "PROCESSING_TIME" logs/processing.log | awk '{print $NF}' | sort -n | tail -10
```

## Getting Help

### Self-Diagnosis Checklist

Before seeking help, run through this checklist:

- [ ] System health check passed
- [ ] All required services are running
- [ ] API keys are valid and not expired
- [ ] Sufficient disk space and memory available
- [ ] Network connectivity to external services
- [ ] Recent logs reviewed for specific errors
- [ ] Configuration validated

### Information to Gather

When reporting issues, include:

```bash
# System information
python3 atlas_status.py --detailed > system_status.txt

# Configuration (sanitized)
grep -v -E "(API_KEY|SECRET|PASSWORD)" .env > config_sanitized.txt

# Recent logs
tail -n 100 logs/atlas_service.log > recent_logs.txt

# Error summary
grep -E "(ERROR|CRITICAL)" logs/*.log | tail -50 > error_summary.txt
```

### Community Support

- **GitHub Issues**: https://github.com/your-username/atlas/issues
- **Documentation**: All guides in `docs/user-guides/`
- **Status Dashboard**: `python3 atlas_status.py --web` for live monitoring

### Emergency Contacts

For critical production issues:
- System down: Run recovery procedures above
- Data corruption: Stop system immediately and create backups
- Security concerns: Review API access logs and rotate keys

---

**💡 Pro Tip**: Set up automated monitoring with `python3 helpers/resource_monitor.py --daemon` to catch issues before they become critical.