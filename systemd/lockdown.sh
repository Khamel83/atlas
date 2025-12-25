#!/bin/bash
# Atlas Lockdown Script
# Ensures ONLY the daemon runs - kills rogue processes, enforces resource policy
#
# Usage: ./systemd/lockdown.sh

set -e

echo "=== Atlas Lockdown ==="
echo ""

# Kill any atlas Python processes NOT managed by systemd
echo "Checking for rogue atlas processes..."
ROGUE_PIDS=$(pgrep -f "atlas.*\.py" 2>/dev/null | while read pid; do
    # Check if this PID is managed by systemd
    if ! systemctl --user status atlas-daemon.service 2>/dev/null | grep -q "Main PID: $pid"; then
        # Also check if it's the API (allowed)
        CMDLINE=$(ps -p $pid -o args= 2>/dev/null || echo "")
        if [[ ! "$CMDLINE" =~ "uvicorn" ]]; then
            echo $pid
        fi
    fi
done)

if [ -n "$ROGUE_PIDS" ]; then
    echo "Found rogue processes:"
    for pid in $ROGUE_PIDS; do
        ps -p $pid -o pid,etime,rss,args 2>/dev/null || true
    done
    echo ""
    echo "Killing rogue processes..."
    for pid in $ROGUE_PIDS; do
        kill $pid 2>/dev/null && echo "  Killed PID $pid" || true
    done
else
    echo "  No rogue processes found"
fi

echo ""
echo "=== Systemd Service Status ==="

# Check daemon status
if systemctl --user is-active atlas-daemon.service >/dev/null 2>&1; then
    echo "atlas-daemon.service: RUNNING"
    systemctl --user show atlas-daemon.service --property=MemoryCurrent,MemoryMax,CPUQuotaPerSecUSec 2>/dev/null | head -5
else
    echo "atlas-daemon.service: NOT RUNNING"
    echo "  Starting daemon..."
    systemctl --user start atlas-daemon.service
    sleep 2
    if systemctl --user is-active atlas-daemon.service >/dev/null 2>&1; then
        echo "  Started successfully"
    else
        echo "  FAILED TO START - check: journalctl --user -u atlas-daemon.service"
    fi
fi

echo ""
echo "=== Current Atlas Processes ==="
pgrep -af "atlas" 2>/dev/null | grep -v "lockdown" || echo "  None running"

echo ""
echo "=== Memory Usage ==="
free -h | head -2

echo ""
echo "Lockdown complete."
