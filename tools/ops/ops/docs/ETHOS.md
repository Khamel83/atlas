# 🎯 OOS Development Ethos

## Core Principles

**Reliable, Consistent, Free, Fast, Open-Source**

We prioritize **reliability and consistency** over raw performance and throughput. Our philosophy: if it doesn't work the first time, it MUST work the second time.

### 1. **Free-Tier First** 💰
- Everything runs on free tiers (OCI Always Free, Google Sheets, Telegram)
- Zero ongoing operational costs
- No paid services required for core functionality
- Optional paid upgrades only when free limits are genuinely exceeded

### 2. **Reliability Over Performance** 🛡️
- Prefer simple, proven solutions over complex optimizations
- Build for consistency: same inputs → same outputs
- Graceful degradation when services are unavailable
- Comprehensive error handling and recovery procedures

### 3. **Rate Limit Discipline** ⏱️
- Stay WAY below documented rate limits
- If docs say 100 requests/hour, we use 20 requests/hour
- Build in backoff and retry with exponential delays
- Monitor usage and alert before approaching limits

### 4. **Relative Paths Everywhere** 📁
- All configurations use relative paths by default
- Hardening happens at deployment time, not development time
- Easy to move between environments (dev → staging → prod)
- No hardcoded absolute paths in source code

### 5. **Self-Documenting Operations** 📖
- Every operation logs what it's doing and why
- Clear error messages with specific fix instructions
- Audit trails for all changes
- Runbooks that anyone can follow

## Free Tier Resource Management

### Google Sheets API
```bash
# Limits: 100 requests per 100 seconds per user
# Our usage: Max 1 request per 30 seconds (120 requests/hour)
# Implementation: 30-second delays between API calls
```

### OCI Always Free
```bash
# VM: 2x VM.Standard.E2.1.Micro (1/8 OCPU, 1GB RAM each)
# Storage: 200GB block volume + 10GB object storage
# Network: 10TB outbound per month
# Our usage: 1 VM, <50GB storage, minimal network
```

### Telegram Bot API
```bash
# Limits: 30 messages per second
# Our usage: 1 message per day (heartbeat) + rare alerts
# Implementation: No rate limiting needed at our scale
```

## Relative Path Strategy

### Development (Relative Paths)
```bash
# All paths in source code are relative
OOS_DB=./data/oos.db
OOS_BACKUP_DIR=./backups
GOOGLE_SERVICE_ACCOUNT_JSON=./config/service-account.json

# Scripts use relative paths
./ops/scripts/backup_sqlite.sh
make -C ops preflight
```

### Deployment (Hardened Paths)
```bash
# ops/.env gets hardened during deployment
OOS_DB=/opt/oos/data/oos.db
OOS_BACKUP_DIR=/opt/oos/backups
GOOGLE_SERVICE_ACCOUNT_JSON=/opt/oos/config/service-account.json

# systemd services use absolute paths
ExecStart=/opt/oos/ops/scripts/backup_sqlite.sh
WorkingDirectory=/opt/oos
```

### Path Resolution Logic
```python
# Pattern used throughout OOS
import os
from pathlib import Path

def resolve_path(path_str, base_dir=None):
    """Convert relative paths to absolute, relative to base_dir or cwd."""
    path = Path(path_str)
    if path.is_absolute():
        return path

    base = Path(base_dir) if base_dir else Path.cwd()
    return (base / path).resolve()

# Usage examples
db_path = resolve_path(os.environ.get("OOS_DB", "./data/oos.db"))
backup_dir = resolve_path(os.environ.get("OOS_BACKUP_DIR", "./backups"))
```

## Consistency Patterns

### Idempotent Operations
```bash
# All operations can be run multiple times safely
make -C ops bootstrap     # Safe to run repeatedly
make -C ops preflight     # Always checks current state
ops/scripts/backup_sqlite.sh  # Creates timestamped backups
```

### Predictable Behavior
```bash
# Same inputs always produce same outputs
# Same environment variables → same behavior
# Same file structure → same results
# Same commands → same outcomes
```

### Error Recovery
```bash
# Every error includes specific fix instructions
ERROR: Database not found: /opt/oos/data/oos.db
FIX: mkdir -p /opt/oos/data && sqlite3 /opt/oos/data/oos.db < ops/schema.sql

ERROR: WAL mode not enabled
FIX: sqlite3 /opt/oos/data/oos.db "PRAGMA journal_mode=WAL;"
```

## Quality Assurance

### Before Any Change
1. **Document the problem** - what exactly isn't working?
2. **Test the fix** - does it solve the problem completely?
3. **Check for side effects** - what else might break?
4. **Update documentation** - how do others avoid this issue?
5. **Add monitoring** - how will we detect this in the future?

### Testing Philosophy
```bash
# Test the happy path
./test-normal-operation.sh

# Test the error cases
./test-database-missing.sh
./test-network-failure.sh
./test-disk-full.sh

# Test the edge cases
./test-concurrent-access.sh
./test-power-failure-recovery.sh
```

### Code Review Checklist
- [ ] Uses relative paths in development
- [ ] Includes error handling with specific fixes
- [ ] Logs operations for audit trail
- [ ] Respects rate limits with generous margins
- [ ] Can be run multiple times safely
- [ ] Works on free tier resources only
- [ ] Documentation updated

## Deployment Strategy

### Development Environment
```bash
# Everything relative, local, fast iteration
cd my-project
./ops/scripts/health_check.sh
make -C ops preflight
```

### Production Environment
```bash
# Absolute paths, service accounts, monitoring
/opt/oos/ops/scripts/health_check.sh
systemctl status backup-sqlite.timer
journalctl -u export-to-sheets.service
```

### Migration Between Environments
```bash
# 1. Code stays the same (relative paths)
# 2. Environment files get updated (hardened paths)
# 3. systemd services use absolute paths
# 4. Monitoring adapts to environment
```

## Success Metrics

### Reliability Targets
- **99.9% uptime** for core functionality
- **<5 second recovery** from transient failures
- **100% data integrity** (never lose user data)
- **Zero manual intervention** for routine operations

### Consistency Targets
- **100% reproducible builds** across environments
- **Same behavior** for same inputs every time
- **Predictable performance** within expected ranges
- **Clear failure modes** with documented recovery

### Cost Targets
- **$0/month** for standard usage
- **<$5/month** if exceeding free tiers
- **No surprise charges** ever
- **Clear cost monitoring** and alerts

---

*This ethos guides every decision in OOS development. When in doubt, choose the more reliable, more consistent, more predictable option - even if it's slower or less elegant.*