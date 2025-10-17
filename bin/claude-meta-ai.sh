#!/bin/bash
# Generate prompt for external AI assistance
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Colors
BLUE='\033[0;34m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${BLUE}🤖 Generating meta-AI prompt...${NC}"

# Use the existing meta-AI enhancer
if [[ $# -eq 0 ]]; then
    echo -e "${YELLOW}Please provide the question or context you need help with:${NC}"
    echo "Usage: /meta-ai \"Claude's confusing question or your unclear situation\""
    echo ""
    echo "Example: /meta-ai \"Claude asked about database schema requirements but I'm not sure what details to provide\""
    exit 0
fi

# Call the meta-AI enhancer with the request
"$SCRIPT_DIR/meta-ai-enhancer.py" "$*"

echo ""
echo -e "${GREEN}💡 Pro tip:${NC} Copy the enhanced prompt above and send it to ChatGPT, Claude-3, or another AI"
echo -e "${GREEN}💡 Then use their structured response back here for much better results!${NC}"