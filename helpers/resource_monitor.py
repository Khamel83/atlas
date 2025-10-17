#!/usr/bin/env python3
import psutil
import sys
from pathlib import Path

def check_system_health():
    """Pre-flight system health check"""
    issues = []

    # Disk space
    disk = psutil.disk_usage('/')
    free_gb = disk.free / (1024**3)
    if free_gb < 5.0:
        issues.append(f"Low disk space: {free_gb:.1f}GB (need 5GB+)")

    # Memory
    memory = psutil.virtual_memory()
    if memory.percent > 90:
        issues.append(f"High memory usage: {memory.percent}%")

    # Log files
    log_dir = Path("logs")
    if log_dir.exists():
        for log_file in log_dir.glob("*.log"):
            size_mb = log_file.stat().st_size / (1024**2)
            if size_mb > 100:
                issues.append(f"Large log file: {log_file} ({size_mb:.1f}MB)")

    if issues:
        print("🚨 SYSTEM HEALTH ISSUES:")
        for issue in issues:
            print(f"   ❌ {issue}")
        return False

    print("✅ System health check passed")
    return True

if __name__ == "__main__":
    success = check_system_health()
    sys.exit(0 if success else 1)
