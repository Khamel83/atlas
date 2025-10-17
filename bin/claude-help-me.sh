#!/bin/bash
# Claude Help Me - Automated Meta-AI Prompt Enhancement Workflow
# This script automates the process of enhancing prompts for better Claude responses

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
ENHANCER="$SCRIPT_DIR/meta-ai-enhancer.py"
CONFIG_DIR="$PROJECT_ROOT/config"
TEMP_DIR="$HOME/.oos/temp"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Ensure temp directory exists
mkdir -p "$TEMP_DIR"

print_header() {
    echo -e "${BLUE}======================================${NC}"
    echo -e "${BLUE}  Claude Help Me - Prompt Enhancer${NC}"
    echo -e "${BLUE}======================================${NC}"
}

print_usage() {
    cat << EOF
Usage: $0 [OPTIONS] "your brief request"

This tool helps you generate better prompts for Claude by:
1. Taking your brief request
2. Creating an enhanced prompt template
3. Providing instructions for meta-AI enhancement
4. Optionally integrating with your preferred meta-AI

OPTIONS:
    -h, --help          Show this help message
    -i, --interactive   Interactive mode - prompts for details
    -o, --output FILE   Save enhanced prompt to file
    -t, --type TYPE     Specify request type (code|analysis|docs|general)
    -q, --quick         Quick mode - just show the enhanced prompt
    --history           Show recent prompt history
    --template          Show available templates

EXAMPLES:
    $0 "fix the auth bug"
    $0 -t code "implement user login"
    $0 -i "analyze the performance"
    $0 --history

WORKFLOW:
    1. Run this script with your brief request
    2. Copy the generated enhanced prompt
    3. Send it to your meta-AI (ChatGPT, etc.)
    4. Use the meta-AI's structured response with Claude
EOF
}

show_history() {
    local history_file="$HOME/.oos/prompt_history.json"
    if [[ -f "$history_file" ]]; then
        echo -e "${GREEN}Recent prompt enhancements:${NC}"
        python3 -c "
import json
import sys
from datetime import datetime

try:
    with open('$history_file', 'r') as f:
        history = json.load(f)

    for i, entry in enumerate(history[-10:], 1):
        print(f'{i:2d}. {entry[\"original_request\"][:50]}...')
        print(f'    Type: {entry[\"request_type\"]}')
        print()
except Exception as e:
    print('No history available yet')
"
    else
        echo -e "${YELLOW}No prompt history found yet.${NC}"
    fi
}

main() {
    local request=""
    local output_file=""
    local request_type=""
    local quick=false

    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                print_usage
                exit 0
                ;;
            -o|--output)
                output_file="$2"
                shift 2
                ;;
            -t|--type)
                request_type="$2"
                shift 2
                ;;
            -q|--quick)
                quick=true
                shift
                ;;
            --history)
                show_history
                exit 0
                ;;
            -*)
                echo -e "${RED}Unknown option: $1${NC}" >&2
                print_usage
                exit 1
                ;;
            *)
                request="$1"
                shift
                ;;
        esac
    done

    print_header

    # Check if enhancer exists
    if [[ ! -f "$ENHANCER" ]]; then
        echo -e "${RED}Error: Meta-AI enhancer not found at $ENHANCER${NC}" >&2
        exit 1
    fi

    # Require request
    if [[ -z "$request" ]]; then
        echo -e "${RED}Error: Please provide a request${NC}" >&2
        print_usage
        exit 1
    fi

    # Generate enhanced prompt
    echo -e "${YELLOW}Processing your request...${NC}"

    local cmd_args=("$request")
    if [[ -n "$output_file" ]]; then
        cmd_args+=(--output "$output_file")
    fi

    python3 "$ENHANCER" "${cmd_args[@]}"

    if [[ "$quick" != true ]]; then
        echo
        echo -e "${GREEN}Next steps:${NC}"
        echo "1. Copy the enhanced prompt above"
        echo "2. Send it to your meta-AI (ChatGPT, Claude-3, etc.)"
        echo "3. Use the meta-AI's structured response as your prompt to Claude"
    fi
}

main "$@"