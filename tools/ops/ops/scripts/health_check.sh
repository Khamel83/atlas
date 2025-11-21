#!/usr/bin/env bash
set -euo pipefail

DB="${OOS_DB:-/opt/oos/data/oos.db}"
BACKUP_DIR="${OOS_BACKUP_DIR:-/opt/oos/backups}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Status counters
CHECKS_PASSED=0
CHECKS_WARNING=0
CHECKS_FAILED=0

check_status() {
    local level="$1"
    local message="$2"
    local details="${3:-}"

    case "$level" in
        "PASS")
            echo -e "${GREEN}✅ PASS${NC} $message"
            ((CHECKS_PASSED++))
            ;;
        "WARN")
            echo -e "${YELLOW}⚠️  WARN${NC} $message"
            if [[ -n "$details" ]]; then
                echo -e "   ${YELLOW}└─${NC} $details"
            fi
            ((CHECKS_WARNING++))
            ;;
        "FAIL")
            echo -e "${RED}❌ FAIL${NC} $message"
            if [[ -n "$details" ]]; then
                echo -e "   ${RED}└─${NC} $details"
            fi
            ((CHECKS_FAILED++))
            ;;
    esac
}

echo -e "${BLUE}🏥 OOS Health Check${NC}"
echo "=================="

# Database Health
echo -e "\n${BLUE}📊 Database Health${NC}"
if [[ -f "$DB" ]]; then
    check_status "PASS" "Database file exists: $DB"

    # Check WAL mode
    wal_mode=$(sqlite3 "$DB" "PRAGMA journal_mode;" 2>/dev/null || echo "unknown")
    if [[ "$wal_mode" == "wal" ]]; then
        check_status "PASS" "WAL mode enabled"
    else
        check_status "WARN" "WAL mode not enabled" "Current mode: $wal_mode"
    fi

    # Check integrity
    if sqlite3 "$DB" "PRAGMA integrity_check;" 2>/dev/null | grep -q "ok"; then
        check_status "PASS" "Database integrity check passed"
    else
        check_status "FAIL" "Database integrity check failed"
    fi

    # Check database size and growth
    db_size=$(stat -c%s "$DB" 2>/dev/null || echo "0")
    db_size_mb=$((db_size / 1024 / 1024))
    if [[ $db_size_mb -lt 100 ]]; then
        check_status "PASS" "Database size reasonable: ${db_size_mb}MB"
    elif [[ $db_size_mb -lt 500 ]]; then
        check_status "WARN" "Database size growing: ${db_size_mb}MB"
    else
        check_status "WARN" "Database size large: ${db_size_mb}MB" "Consider archiving old data"
    fi

    # Check recent activity
    recent_events=$(sqlite3 "$DB" "SELECT COUNT(*) FROM events_log WHERE timestamp > datetime('now', '-24 hours');" 2>/dev/null || echo "0")
    if [[ $recent_events -gt 0 ]]; then
        check_status "PASS" "Recent activity detected: $recent_events events in 24h"
    else
        check_status "WARN" "No recent activity detected" "May indicate system not running"
    fi
else
    check_status "FAIL" "Database file not found: $DB"
fi

# Backup Health
echo -e "\n${BLUE}💾 Backup Health${NC}"
if [[ -d "$BACKUP_DIR" ]]; then
    backup_count=$(find "$BACKUP_DIR" -name "oos_*.db" -type f | wc -l)
    if [[ $backup_count -gt 0 ]]; then
        check_status "PASS" "Backup directory exists with $backup_count backups"

        # Check latest backup age
        latest_backup=$(find "$BACKUP_DIR" -name "oos_*.db" -type f -printf '%T@ %p\n' 2>/dev/null | sort -n | tail -1 | cut -d' ' -f2-)
        if [[ -n "$latest_backup" ]]; then
            backup_age=$(( $(date +%s) - $(stat -c %Y "$latest_backup") ))
            backup_hours=$((backup_age / 3600))

            if [[ $backup_hours -lt 25 ]]; then
                check_status "PASS" "Latest backup is recent: ${backup_hours}h old"
            elif [[ $backup_hours -lt 48 ]]; then
                check_status "WARN" "Latest backup is ${backup_hours}h old"
            else
                check_status "FAIL" "Latest backup is ${backup_hours}h old" "Backup schedule may be broken"
            fi

            # Check backup integrity
            if sqlite3 "$latest_backup" "PRAGMA integrity_check;" 2>/dev/null | grep -q "ok"; then
                check_status "PASS" "Latest backup integrity verified"
            else
                check_status "FAIL" "Latest backup integrity check failed"
            fi
        fi
    else
        check_status "WARN" "No backup files found" "Run: make -C ops backup"
    fi
else
    check_status "WARN" "Backup directory not found: $BACKUP_DIR"
fi

# System Resources
echo -e "\n${BLUE}💻 System Resources${NC}"

# Disk space
if command -v df >/dev/null; then
    usage=$(df "$(dirname "$DB")" | awk 'NR==2 {print $5}' | sed 's/%//')
    if [[ $usage -lt 70 ]]; then
        check_status "PASS" "Disk usage normal: ${usage}%"
    elif [[ $usage -lt 85 ]]; then
        check_status "WARN" "Disk usage elevated: ${usage}%"
    else
        check_status "FAIL" "Disk usage critical: ${usage}%" "Clean up space immediately"
    fi
fi

# Memory usage (if available)
if command -v free >/dev/null; then
    mem_usage=$(free | awk 'NR==2{printf "%.1f", $3*100/$2}')
    mem_usage_int=${mem_usage%.*}
    if [[ $mem_usage_int -lt 80 ]]; then
        check_status "PASS" "Memory usage normal: ${mem_usage}%"
    elif [[ $mem_usage_int -lt 90 ]]; then
        check_status "WARN" "Memory usage elevated: ${mem_usage}%"
    else
        check_status "WARN" "Memory usage high: ${mem_usage}%"
    fi
fi

# Load average (if available)
if command -v uptime >/dev/null; then
    load_avg=$(uptime | awk -F'load average:' '{print $2}' | awk '{print $1}' | sed 's/,//')
    load_avg_int=${load_avg%.*}
    cpu_count=$(nproc 2>/dev/null || echo "1")
    if [[ $load_avg_int -lt $cpu_count ]]; then
        check_status "PASS" "Load average normal: $load_avg"
    elif [[ $load_avg_int -lt $((cpu_count * 2)) ]]; then
        check_status "WARN" "Load average elevated: $load_avg"
    else
        check_status "WARN" "Load average high: $load_avg"
    fi
fi

# Services Health
echo -e "\n${BLUE}⚙️  Services Health${NC}"

# Check systemd timers
timers=("backup-sqlite.timer" "export-to-sheets.timer" "writeback-from-sheets.timer")
for timer in "${timers[@]}"; do
    if systemctl is-active --quiet "$timer" 2>/dev/null; then
        check_status "PASS" "Timer active: $timer"
    else
        check_status "WARN" "Timer inactive: $timer" "Run: sudo systemctl start $timer"
    fi
done

# Tools Health
echo -e "\n${BLUE}🛠️  Tools Health${NC}"

tools=("sqlite3" "datasette" "sqlite_web" "sops" "age")
for tool in "${tools[@]}"; do
    if command -v "$tool" >/dev/null; then
        check_status "PASS" "Tool available: $tool"
    else
        case "$tool" in
            "datasette"|"sqlite_web")
                check_status "WARN" "Tool missing: $tool" "Install: pip install $tool"
                ;;
            "sops"|"age")
                check_status "WARN" "Tool missing: $tool" "Install: make -C ops install-sops"
                ;;
            *)
                check_status "WARN" "Tool missing: $tool"
                ;;
        esac
    fi
done

# Configuration Health
echo -e "\n${BLUE}⚙️  Configuration Health${NC}"

if [[ -f "ops/.env" ]]; then
    check_status "PASS" "Environment file exists: ops/.env"

    # Check critical variables
    source ops/.env 2>/dev/null || true
    if [[ -n "${OOS_DB:-}" ]]; then
        check_status "PASS" "OOS_DB configured"
    else
        check_status "WARN" "OOS_DB not configured"
    fi

    if [[ -n "${GOOGLE_SPREADSHEET_ID:-}" ]]; then
        check_status "PASS" "Google Sheets configured"
    else
        check_status "WARN" "Google Sheets not configured" "Mirrors will be disabled"
    fi
else
    check_status "WARN" "Environment file missing" "Copy ops/.env.template to ops/.env"
fi

# Security Health
echo -e "\n${BLUE}🔒 Security Health${NC}"

# Check file permissions
if [[ -f "$DB" ]]; then
    db_perms=$(stat -c %a "$DB" 2>/dev/null || echo "000")
    if [[ "$db_perms" == "600" || "$db_perms" == "640" ]]; then
        check_status "PASS" "Database permissions secure: $db_perms"
    else
        check_status "WARN" "Database permissions may be too open: $db_perms"
    fi
fi

# Summary
echo -e "\n${BLUE}📋 Health Check Summary${NC}"
echo "======================"
echo -e "${GREEN}Passed:${NC} $CHECKS_PASSED"
echo -e "${YELLOW}Warnings:${NC} $CHECKS_WARNING"
echo -e "${RED}Failed:${NC} $CHECKS_FAILED"

total_checks=$((CHECKS_PASSED + CHECKS_WARNING + CHECKS_FAILED))
if [[ $CHECKS_FAILED -eq 0 && $CHECKS_WARNING -eq 0 ]]; then
    echo -e "\n${GREEN}🎉 System is healthy!${NC}"
    exit 0
elif [[ $CHECKS_FAILED -eq 0 ]]; then
    echo -e "\n${YELLOW}⚠️  System has warnings but is operational${NC}"
    exit 0
else
    echo -e "\n${RED}❌ System has critical issues that need attention${NC}"
    exit 1
fi