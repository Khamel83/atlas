#!/bin/bash
# Clarification workflow - refine vague requests
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Colors
BLUE='\033[0;34m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${BLUE}🤔 Starting clarification workflow...${NC}"

# Check if clarification system exists
if [[ ! -f "$PROJECT_ROOT/src/clarification_workflow.py" ]]; then
    echo -e "${YELLOW}Clarification system not found. Using basic clarification...${NC}"

    echo -e "\n${GREEN}Let's clarify your request:${NC}"
    echo "1. What exactly are you trying to accomplish?"
    echo "2. What context or constraints should I know about?"
    echo "3. What would success look like?"
    echo "4. Are there any specific technologies or approaches you prefer?"
    echo "5. What's your timeline or priority level?"
    echo ""
    echo "Please provide more details based on these questions."
    exit 0
fi

# Run the full clarification workflow
source "$PROJECT_ROOT/venv/bin/activate"
cd "$PROJECT_ROOT"

python3 -c "
import sys
sys.path.insert(0, 'src')

from clarification_workflow import get_clarification_workflow
import asyncio

async def run_clarification():
    if len(sys.argv) < 2:
        print('Usage: /clarify \"your vague request\"')
        return

    user_input = ' '.join(sys.argv[1:])
    workflow = get_clarification_workflow()
    session = await workflow.start_workflow(user_input)

    print(f'Intent detected: {session.cleaned_input.extracted_intent}')
    print(f'Confidence: {session.cleaned_input.confidence:.1%}')
    print()

    if session.questions:
        print('Clarification questions:')
        for i, question in enumerate(session.questions, 1):
            print(f'{i}. {question.text}')
            if question.options:
                for j, option in enumerate(question.options, 1):
                    print(f'   {j}) {option}')
            print()
    else:
        print('Your request is clear! Ready to proceed.')

asyncio.run(run_clarification())
" "$@"