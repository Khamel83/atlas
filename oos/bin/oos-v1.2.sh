#!/bin/bash
# OOS v1.2 Main Entry Point - Bulletproof task execution
set -e

OOS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TASK_RUNNER="$OOS_DIR/bin/task_runner.sh"
TASKS_FILE="$OOS_DIR/.oos/tasks.json"

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

show_help() {
    echo -e "${BLUE}OOS v1.2 - Open Operating System${NC}"
    echo ""
    echo "🚀 New in v1.2: Bulletproof task runner that never gives up"
    echo ""
    echo "Usage:"
    echo "  $0 run            Run all tasks until complete"
    echo "  $0 status         Show execution status"
    echo "  $0 reset          Reset execution state"
    echo "  $0 list-tasks     List available tasks"
    echo "  $0 add-task       Add a new task"
    echo "  $0 search         Search for information"
    echo "  $0 help           Show this help"
    echo ""
    echo "Examples:"
    echo "  $0 run                    # Execute all tasks"
    echo "  $0 status                 # Check progress"
    echo "  $0 search 'python docs'   # Search the web"
    echo ""
    echo "Task runner ensures ALL tasks complete or explicit failure."
}

list_tasks() {
    echo -e "${BLUE}Available OOS Tasks:${NC}"
    echo "═════════════════════════════════════════════════"

    if [ ! -f "$TASKS_FILE" ]; then
        echo "❌ No tasks file found"
        return 1
    fi

    jq -r '.[] | "• \(.id): \(.description)"' "$TASKS_FILE" | while read -r line; do
        echo "$line"
    done
}

add_task() {
    echo -e "${BLUE}Add New Task${NC}"
    echo "═════════════════════════════════════════════════"

    read -p "Task ID: " task_id
    read -p "Action (command): " action
    read -p "Description: " description
    read -p "Retries (default 3): " retries
    read -p "Timeout in seconds (default 300): " timeout

    # Set defaults
    retries=${retries:-3}
    timeout=${timeout:-300}

    # Create new task JSON
    local new_task=$(jq -n \
        --arg id "$task_id" \
        --arg action "$action" \
        --arg description "$description" \
        --argjson retries "$retries" \
        --argjson timeout "$timeout" \
        '{
            id: $id,
            action: $action,
            description: $description,
            retries: $retries,
            timeout: $timeout
        }')

    # Add to tasks file
    if [ -f "$TASKS_FILE" ]; then
        jq ". += [$new_task]" "$TASKS_FILE" > "${TASKS_FILE}.tmp" && mv "${TASKS_FILE}.tmp" "$TASKS_FILE"
    else
        echo "[$new_task]" > "$TASKS_FILE"
    fi

    echo -e "${GREEN}✅ Task added successfully${NC}"
    echo "Run '$0 run' to execute all tasks"
}

search_web() {
    local query="$1"
    if [ -z "$query" ]; then
        echo "❌ Please provide a search query"
        echo "Usage: $0 search 'your query here'"
        exit 1
    fi

    echo -e "${BLUE}🔍 Searching: $query${NC}"
    echo "═════════════════════════════════════════════════"

    # Try multiple search engines
    if command -v curl >/dev/null 2>&1; then
        # DuckDuckGo (no API key needed)
        echo "🦆 DuckDuckGo results:"
        curl -s "https://api.duckduckgo.com/?q=$(echo "$query" | sed 's/ /+/g')&format=json" | jq -r '.Abstract // .RelatedTopics[].Text' 2>/dev/null | head -5 || echo "No results from DuckDuckGo"

        echo ""

        # Free Wikipedia API
        echo "📚 Wikipedia results:"
        curl -s "https://en.wikipedia.org/api/rest_v1/page/summary/$(echo "$query" | sed 's/ /_/g')" | jq -r '.extract' 2>/dev/null | head -3 || echo "No Wikipedia summary found"
    else
        echo "❌ curl not available for web search"
    fi
}

# Main command handling
case "${1:-help}" in
    "run")
        echo -e "${GREEN}🚀 Starting OOS v1.2 Task Runner${NC}"
        echo "This will run ALL tasks until complete. Press Ctrl+C to pause."
        echo ""
        "$TASK_RUNNER" run
        ;;
    "status")
        "$TASK_RUNNER" status
        ;;
    "reset")
        "$TASK_RUNNER" reset
        ;;
    "list-tasks")
        list_tasks
        ;;
    "add-task")
        add_task
        ;;
    "search")
        search_web "$2"
        ;;
    "help"|"-h"|"--help")
        show_help
        ;;
    *)
        echo "Unknown command: $1"
        echo ""
        show_help
        exit 1
        ;;
esac