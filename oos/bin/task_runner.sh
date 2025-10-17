#!/bin/bash
# OOS Task Runner v1.2 - Never stops until all tasks complete
# Bulletproof execution that refuses to give up
set -e

TASKS_FILE=".oos/tasks.json"
STATE_FILE=".oos/execution_state.json"
LOG_FILE=".oos/task_runner.log"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Ensure .oos directory exists
mkdir -p .oos

log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "$LOG_FILE"
}

show_banner() {
    echo -e "${BLUE}"
    echo "🔥 OOS Task Runner v1.2 - Never Stops Until Complete"
    echo "═════════════════════════════════════════════════"
    echo -e "${NC}"
}

load_tasks() {
    if [ ! -f "$TASKS_FILE" ]; then
        log "❌ No tasks file found at $TASKS_FILE"
        return 1
    fi
    cat "$TASKS_FILE"
}

load_state() {
    if [ -f "$STATE_FILE" ]; then
        cat "$STATE_FILE"
    else
        echo '{"completed_tasks": [], "failed_tasks": [], "current_task": "", "total_tasks": 0, "start_time": "", "last_update": ""}'
    fi
}

save_state() {
    echo "$1" > "$STATE_FILE"
    log "State updated: $(echo "$1" | jq -r '.current_task // "none"')"
}

get_task_retries() {
    local task_id="$1"
    load_tasks | jq -r ".[] | select(.id == \"$task_id\") | .retries // 3"
}

execute_task() {
    local task="$1"
    local action=$(load_tasks | jq -r ".[] | select(.id == \"$task\") | .action")
    local timeout=$(load_tasks | jq -r ".[] | select(.id == \"$task\") | .timeout // 300")

    log "🎯 Executing task: $task"
    log "📝 Action: $action"

    # Set timeout for the task
    timeout "$timeout" bash -c "$action" 2>/dev/null
    local exit_code=$?

    if [ $exit_code -eq 0 ]; then
        log "✅ Task $task completed successfully"
        return 0
    elif [ $exit_code -eq 124 ]; then
        log "⏰ Task $task timed out after ${timeout}s"
        return 1
    else
        log "❌ Task $task failed with exit code $exit_code"
        return 1
    fi
}

try_alternative_approaches() {
    local task="$1"
    log "🔄 Trying alternative approaches for $task"

    case "$task" in
        "check_python")
            python3 --version 2>/dev/null || python --version 2>/dev/null || python2 --version 2>/dev/null || {
                log "❌ No python found, trying installation"
                apt update && apt install -y python3 python3-pip 2>/dev/null || {
                    log "❌ Cannot install python automatically"
                    return 1
                }
            }
            ;;
        "copy_integration")
            # Try different copy methods
            cp .claude/slash_commands.json ../.claude/ 2>/dev/null || \
            scp .claude/slash_commands.json ../.claude/ 2>/dev/null || \
            rsync -av .claude/slash_commands.json ../.claude/ 2>/dev/null || {
                log "❌ All copy methods failed"
                return 1
            }
            ;;
        "network_check")
            # Try different connectivity checks
            ping -c 1 8.8.8.8 2>/dev/null || \
            curl -s --connect-timeout 5 https://www.google.com >/dev/null 2>/dev/null || \
            wget --timeout=5 --tries=1 -q -O /dev/null https://www.google.com 2>/dev/null || {
                log "❌ No network connectivity"
                return 1
            }
            ;;
        *)
            log "⚠️ No alternative approaches defined for $task"
            return 1
            ;;
    esac

    log "✅ Alternative approach worked for $task"
    return 0
}

execute_with_retry() {
    local task="$1"
    local max_retries=$(get_task_retries "$task")

    for ((i=1; i<=max_retries; i++)); do
        log "🎯 Attempt $i/$max_retries for task $task"

        if execute_task "$task"; then
            return 0
        fi

        if [ $i -lt $max_retries ]; then
            local wait_time=$((i * 5))
            log "⏳ Waiting ${wait_time}s before retry..."
            sleep $wait_time
        fi
    done

    log "🔄 All retries failed, trying alternative approaches"
    if try_alternative_approaches "$task"; then
        return 0
    fi

    log "❌ Task $task failed after all attempts"
    return 1
}

get_next_task() {
    local state=$(load_state)

    # Find first task not in completed or failed
    load_tasks | jq -r --argjson completed "$(echo "$state" | jq '.completed_tasks // []')" --argjson failed "$(echo "$state" | jq '.failed_tasks // []')" '.[] | select(.id as $id | $completed | index($id) | not and ($failed | index($id) | not) ) | .id' | head -1
}

update_state_for_task() {
    local task="$1"
    local status="$2"
    local state=$(load_state)

    # Update timestamps
    local current_time=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
    local start_time=$(echo "$state" | jq -r '.start_time // empty')
    [ -z "$start_time" ] && start_time="$current_time"

    # Update state
    if [ "$status" == "completed" ]; then
        state=$(echo "$state" | jq --arg task "$task" --arg time "$current_time" --arg start "$start_time" '
            .completed_tasks += [$task] |
            .current_task = "" |
            .last_update = $time |
            .start_time = $start
        ')
    elif [ "$status" == "failed" ]; then
        state=$(echo "$state" | jq --arg task "$task" --arg time "$current_time" --arg start "$start_time" '
            .failed_tasks += [$task] |
            .current_task = "" |
            .last_update = $time |
            .start_time = $start
        ')
    elif [ "$status" == "started" ]; then
        state=$(echo "$state" | jq --arg task "$task" --arg time "$current_time" --arg start "$start_time" '
            .current_task = $task |
            .last_update = $time |
            .start_time = $start
        ')
    fi

    # Set total tasks count
    local total_tasks=$(load_tasks | jq '. | length')
    state=$(echo "$state" | jq --argjson total "$total_tasks" '.total_tasks = $total')

    save_state "$state"
}

run_all_tasks() {
    show_banner

    local total_tasks=$(load_tasks | jq '. | length')
    log "🚀 Starting execution of $total_tasks tasks"

    while true; do
        local next_task=$(get_next_task)

        if [ -z "$next_task" ]; then
            local state=$(load_state)
            local completed=$(echo "$state" | jq -r '.completed_tasks | length')
            local failed=$(echo "$state" | jq -r '.failed_tasks | length')

            echo -e "${GREEN}"
            echo "🎉 TASK EXECUTION COMPLETE!"
            echo "═════════════════════════════════════════════════"
            echo "✅ Completed: $completed/$total_tasks"
            echo "❌ Failed: $failed/$total_tasks"
            echo "📊 Success Rate: $(( (completed * 100) / total_tasks ))%"
            echo -e "${NC}"

            if [ $failed -gt 0 ]; then
                echo -e "${YELLOW}⚠️  Some tasks failed. Check $LOG_FILE for details.${NC}"
                echo "Failed tasks: $(echo "$state" | jq -r '.failed_tasks[]' | tr '\n' ' ')"
            fi

            log "🏁 Task runner completed with $completed successes, $failed failures"
            break
        fi

        echo -e "${BLUE}"
        echo "🎯 Current Task: $next_task"
        echo "═════════════════════════════════════════════════"
        echo -e "${NC}"

        update_state_for_task "$next_task" "started"

        if execute_with_retry "$next_task"; then
            update_state_for_task "$next_task" "completed"
            echo -e "${GREEN}✅ Task completed: $next_task${NC}"
        else
            update_state_for_task "$next_task" "failed"
            echo -e "${RED}❌ Task failed: $next_task${NC}"
        fi

        echo ""
    done
}

show_status() {
    echo -e "${BLUE}OOS Task Runner Status${NC}"
    echo "═════════════════════════════════════════════════"

    if [ ! -f "$STATE_FILE" ]; then
        echo "📊 No execution state found"
        return
    fi

    local state=$(load_state)
    local completed=$(echo "$state" | jq -r '.completed_tasks | length')
    local failed=$(echo "$state" | jq -r '.failed_tasks | length')
    local total=$(echo "$state" | jq -r '.total_tasks')
    local current=$(echo "$state" | jq -r '.current_task // "none"')
    local start_time=$(echo "$state" | jq -r '.start_time // "never"')
    local last_update=$(echo "$state" | jq -r '.last_update // "never"')

    echo "📊 Total Tasks: $total"
    echo "✅ Completed: $completed"
    echo "❌ Failed: $failed"
    echo "🔄 Current: $current"
    echo "⏰ Started: $start_time"
    echo "🕐 Last Update: $last_update"

    if [ $completed -gt 0 ]; then
        echo ""
        echo "✅ Completed Tasks:"
        echo "$state" | jq -r '.completed_tasks[]' | sed 's/^/  • /'
    fi

    if [ $failed -gt 0 ]; then
        echo ""
        echo "❌ Failed Tasks:"
        echo "$state" | jq -r '.failed_tasks[]' | sed 's/^/  • /'
    fi
}

reset_state() {
    rm -f "$STATE_FILE"
    rm -f "$LOG_FILE"
    echo "🔄 Task runner state reset"
    log "Task runner state reset by user"
}

# Main command handling
case "${1:-run}" in
    "run")
        run_all_tasks
        ;;
    "status")
        show_status
        ;;
    "reset")
        reset_state
        ;;
    "help"|"-h"|"--help")
        echo "OOS Task Runner v1.2"
        echo ""
        echo "Usage:"
        echo "  $0 run          Run all tasks until complete"
        echo "  $0 status       Show execution status"
        echo "  $0 reset        Reset execution state"
        echo "  $0 help         Show this help"
        echo ""
        echo "Tasks are defined in $TASKS_FILE"
        echo "State is tracked in $STATE_FILE"
        echo "Logs are written to $LOG_FILE"
        ;;
    *)
        echo "Unknown command: $1"
        echo "Use '$0 help' for usage information"
        exit 1
        ;;
esac