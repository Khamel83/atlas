#!/bin/bash
"""
Atlas Health Check - Single KPI Metric
Provides instant status without searching through logs

Returns:
- Health score (0-100)
- Status category
- Brief explanation
- Auto-fix status
"""

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ATLAS_DIR="$SCRIPT_DIR/atlas_v2"

# Colors for output
RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Health check function
check_atlas_health() {
    local health_score=0
    local status="UNKNOWN"
    local message=""
    local auto_fix_status="disabled"

    # Check if Atlas is running
    if pgrep -f "python.*main.py" > /dev/null; then
        health_score=$((health_score + 30))
        status_running="✅"
    else
        status_running="❌"
    fi

    # Check API health
    if curl -s http://localhost:8001/health > /dev/null 2>&1; then
        health_score=$((health_score + 40))
        status_api="✅"
    else
        status_api="❌"
    fi

    # Check recent activity (logs from last 10 minutes)
    if [ -f "$ATLAS_DIR/logs/atlas_output.log" ]; then
        recent_activity=$(find "$ATLAS_DIR/logs" -name "*.log" -mmin -10 | wc -l)
        if [ "$recent_activity" -gt 0 ]; then
            health_score=$((health_score + 20))
            status_activity="✅"
        else
            status_activity="⚠️"
        fi
    else
        status_activity="❓"
    fi

    # Check if auto-fix is enabled
    if [ -n "$OPENROUTER_API_KEY" ]; then
        auto_fix_status="enabled"
        health_score=$((health_score + 10))  # Bonus for having auto-fix
    fi

    # Determine status category
    if [ "$health_score" -ge 80 ]; then
        status="${GREEN}ACTIVE${NC}"
        emoji="🟢"
    elif [ "$health_score" -ge 60 ]; then
        status="${YELLOW}RUNNING${NC}"
        emoji="🟡"
    elif [ "$health_score" -ge 40 ]; then
        status="${YELLOW}IDLE${NC}"
        emoji="🟠"
    elif [ "$health_score" -ge 20 ]; then
        status="${RED}DEGRADED${NC}"
        emoji="🔴"
    else
        status="${RED}STOPPED${NC}"
        emoji="⚫"
    fi

    # Generate status message
    message="Running: $status_running, API: $status_api, Activity: $status_activity, Auto-Fix: $auto_fix_status"

    # Output the result
    echo "$emoji Atlas Health Score: $health_score/100 ($status)"
    echo "📊 $message"

    # Return just the score for programmatic use
    return $health_score
}

# Main execution
if [ "$1" = "--score" ]; then
    check_atlas_health > /dev/null
    echo $?
else
    check_atlas_health
fi