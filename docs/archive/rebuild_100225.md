# ATLAS PROJECT COMPREHENSIVE AUDIT & REBUILD ANALYSIS
**Date**: October 2, 2025
**Status**: SYSTEM BROKEN - Multiple Competing Processes
**Database**: 25,831 content records (15,977 substantial)
**New Content Processing**: **ZERO** (broken)

## EXECUTIVE SUMMARY

### What's Working ✅
- **Database**: `/home/ubuntu/dev/atlas/data/atlas.db` contains 25,831 content records with 15,977 substantial pieces
- **Core Content**: System has successfully extracted real content in the past
- **RSS Discovery**: Can discover podcast episodes from feeds
- **User-Agent Fix**: Applied to prevent HTTP 403 errors

### What's Broken 🚨
- **Zero New Content**: No content processed since October 2, 2025 14:00
- **Process Death Spiral**: Atlas processes get SIGTERM signals every 30 seconds
- **Multiple Competing Systems**: atlas_manager.py, atlas_v2, systemd services all interfering
- **Auto-Restart Hell**: SystemD services automatically restart killed processes
- **No Content Extraction**: Despite RSS discovery working, no actual content is being stored

### Critical Issues
1. **Processes keep dying**: Receiving SIGTERM (signal 15) every 30 seconds
2. **SystemD interference**: Multiple services auto-restarting processes
3. **Atlas v2 chaos**: Created more problems than solutions, now disabled
4. **Success rate: 0.0%**: No episodes processed successfully
5. **Database confusion**: Multiple schemas and conflicting data paths

---

## DETAILED SYSTEM INVENTORY

### Core System Files

#### **Working Atlas v1 System**
- **`atlas_manager.py`** - Main entry point, log-stream architecture
- **`atlas_log_processor.py`** - Core processing logic
- **`universal_url_processor.py`** - Content extraction (User-Agent fixed)
- **`data/atlas.db`** - Main database with 25,831 records

#### **Broken Atlas v2 System** (Now Disabled)
- **`atlas_v2_DISABLED_20251002_134357/`** - Renamed and disabled
- Created competing database schemas
- Added complexity without functional benefit
- Multiple modules with conflicting configurations

#### **SystemD Services** (The Problem)
```bash
atlas-api.service                 - auto-restart (DISABLED)
atlas-guardian.service           - auto-restart (DISABLED)
atlas-health-monitor.service     - auto-restart (DISABLED)
atlas-manager.service            - running (DISABLED)
atlas-monitor.service            - running (DISABLED)
atlas-watchdog.service           - auto-restart (DISABLED)
atlas_metrics_exporter.service  - auto-restart (DISABLED)
```

#### **Monitoring & Support**
- **`monitoring_service.py`** - Dashboard service (port 7445)
- **`atlas_health.sh`** - Health check script
- **`enhanced_monitor_atlas_fixed.sh`** - Auto-restart monitor

### Database Analysis

#### **Main Database**: `data/atlas.db`
```sql
-- WORKING DATA
content: 25,831 records
├── completed: 9,566 records
├── pending: 16,265 records
└── substantial content: 15,977 records (>100 chars)

-- ATLAS V2 TABLES (Broken)
content_metadata: 5 records
processing_queue: 5 records
processed_content: 0 records (EMPTY!)
```

#### **Key Schema**
```sql
content (
  id INTEGER PRIMARY KEY,
  title TEXT,
  url TEXT,
  content TEXT,           -- THE ACTUAL CONTENT
  content_type TEXT,
  created_at TEXT,
  processing_status TEXT  -- 'completed' | 'pending'
)
```

### Process Conflicts

#### **What's Running**
```bash
PID     COMMAND                          STATUS
1941756 python3 atlas_manager.py        DYING (gets SIGTERM)
1916445 python3 monitoring_service.py   RUNNING
```

#### **Auto-Restart Mechanisms**
1. **SystemD Services**: Automatically restart on failure
2. **Guardian Scripts**: Monitor and restart processes
3. **Health Monitors**: Restart if unhealthy
4. **Cron Jobs**: Scheduled restarts (disabled)

---

## ROOT CAUSE ANALYSIS

### Why Processes Keep Dying
1. **Signal 15 (SIGTERM)** sent every 30 seconds
2. **Source Unknown** - Could be systemd, guardian, or monitoring
3. **Competing Services** trying to manage same process
4. **Port Conflicts** multiple services on same ports

### Why No Content Processing
1. **Death Spiral**: Process restarts before completing work
2. **Configuration Conflicts**: Multiple database paths
3. **Missing Dependencies**: Components broken during v2 migration
4. **Resource Contention**: Competing processes interfering

### User-Agent Issue (FIXED)
- **Before**: `'Atlas/1.0; +https://github.com/atlas'` (suspicious, blocked)
- **After**: Chrome browser headers (realistic, works)

---

## THREE REBUILD OPTIONS

### Option A: MINIMAL FIX (Recommended)
**Goal**: Get existing system working with minimal changes

**Steps**:
1. **Kill Everything**: `sudo systemctl stop atlas-*` (DONE)
2. **Disable SystemD**: `sudo systemctl disable atlas-*` (DONE)
3. **Run Single Process**: `python3 atlas_manager.py` (clean start)
4. **Monitor for SIGTERM**: Find what's killing processes
5. **Fix Signal Source**: Remove whatever sends SIGTERM

**Pros**: Preserves all 25,831 content records, minimal risk
**Cons**: May still have underlying architectural issues
**Time**: 1-2 hours
**Success Probability**: 70%

### Option B: CLEAN SLATE REBUILD
**Goal**: Start fresh with lessons learned

**Steps**:
1. **Backup Database**: `cp data/atlas.db data/atlas_backup_$(date).db`
2. **Delete All Code**: Keep only essential files
3. **Simple Script**: Single file that processes content
4. **Import Database**: Use existing content records
5. **No Monitoring**: Just basic processing

**Keep**:
- `data/atlas.db` (the precious content)
- Basic RSS feed configs
- Content extraction logic from `universal_url_processor.py`

**Delete**:
- All Atlas v2 files
- SystemD services
- Monitoring infrastructure
- Guardian processes

**Pros**: Clean, simple, no conflicts
**Cons**: Lose monitoring, lose advanced features
**Time**: 4-6 hours
**Success Probability**: 90%

### Option C: HYBRID SALVAGE
**Goal**: Keep database and core logic, rebuild infrastructure

**Steps**:
1. **Preserve**: Database + working content extraction
2. **Rebuild**: Process management without systemd
3. **Simplify**: Remove complex monitoring
4. **Test**: Verify end-to-end processing

**Architecture**:
```
atlas_simple.py              # Single entry point
├── content_extractor.py     # From universal_url_processor.py
├── rss_discovery.py         # RSS feed parsing
├── database.py              # Simple SQLite operations
└── config.json              # Basic configuration
```

**Pros**: Best of both worlds, maintains features
**Cons**: More complex than Option B
**Time**: 6-8 hours
**Success Probability**: 80%

---

## RECOMMENDED PATH FORWARD

### **RECOMMENDATION: Option A (Minimal Fix)**

**Reasoning**:
1. **Low Risk**: Preserves all existing work
2. **Quick**: Can be working in 1-2 hours
3. **Proven**: The system worked before, can work again
4. **Debuggable**: Can identify exact issue causing SIGTERM

**Immediate Actions**:
```bash
# 1. Ensure everything is stopped
sudo systemctl stop atlas-* && sudo pkill -f atlas

# 2. Start clean single process
python3 atlas_manager.py

# 3. Monitor for signals
strace -p $(pgrep atlas_manager) -e signal

# 4. Identify signal source
sudo fuser -v $(pgrep atlas_manager)
```

**Success Criteria**:
- Process runs >10 minutes without SIGTERM
- Content count increases: `SELECT COUNT(*) FROM content WHERE created_at > NOW()`
- Processing status shows activity

### **Fallback Plan**:
If Option A fails after 2 hours → Switch to Option B (Clean Slate)

---

## CRITICAL QUESTIONS ANSWERED

### Can I salvage the existing 15,977 content records?
**YES** - Database is intact and accessible. All content preserved.

### What's the simplest working configuration?
**Single Process**: `python3 atlas_manager.py` with no systemd, no monitors, no guardians.

### Which Python file is the actual entry point?
**`atlas_manager.py`** - This created the 25,831 content records.

### Do I need monitoring/guardian services?
**NO** - They're causing more problems than solving. Start simple.

### Is this salvageable?
**YES** - The core system works. It's the process management that's broken.

---

## FILES TO KEEP vs DELETE

### **KEEP** (Essential)
```
atlas_manager.py              # Main entry point
atlas_log_processor.py        # Core processing
universal_url_processor.py    # Content extraction (User-Agent fixed)
data/atlas.db                 # THE PRECIOUS DATABASE
config/podcast_*.csv          # RSS feed configs
logs/                         # For debugging
```

### **DELETE** (Problematic)
```
atlas_v2_DISABLED_*/          # Already renamed
/etc/systemd/system/atlas-*   # SystemD services
enhanced_monitor_*            # Auto-restart scripts
monitoring_service.py         # Complex monitoring
atlas_guardian.sh             # Process supervisor
```

### **INVESTIGATE** (Unknown)
```
atlas_health.sh               # May be useful for status
start_monitoring.sh           # Could be causing restarts
maintenance/                  # Cron job scripts
```

---

## NEXT STEPS

1. **Execute Option A** (Minimal Fix)
2. **Monitor for 1 hour** - Check content processing
3. **Document results** in this file
4. **If successful**: Add basic monitoring back gradually
5. **If failed**: Switch to Option B (Clean Slate)

**THIS IS SALVAGEABLE.** The system worked before and can work again. The issue is process management conflicts, not fundamental architecture problems.

---

*This audit confirms Atlas has a solid foundation with real, substantial content. The current chaos is fixable with focused debugging of the process death spiral.*