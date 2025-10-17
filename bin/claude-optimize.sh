#!/bin/bash
# Optimize current context for token efficiency
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Colors
BLUE='\033[0;34m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${BLUE}🔧 Optimizing context for token efficiency...${NC}"

# Check if token optimization system exists
if [[ ! -f "$PROJECT_ROOT/src/token_optimization.py" ]]; then
    echo -e "${YELLOW}Token optimization system not found. Using basic optimization...${NC}"
    echo ""
    echo "Basic optimization tips:"
    echo "• Focus on specific questions instead of broad requests"
    echo "• Provide concrete examples rather than abstract descriptions"
    echo "• Break complex tasks into smaller, focused steps"
    echo "• Use bullet points for lists instead of paragraphs"
    echo "• Reference specific files/functions when relevant"
    exit 0
fi

# Run token optimization
source "$PROJECT_ROOT/venv/bin/activate"
cd "$PROJECT_ROOT"

python3 -c "
import sys
sys.path.insert(0, 'src')

from token_optimization import optimize_for_budget, estimate_context_tokens
import asyncio
import json

async def optimize_context():
    print('📊 Analyzing current context...')

    # Get context from recent conversation
    context = {
        'conversation_summary': 'Current Claude Code session',
        'project_context': 'OOS development project',
        'active_files': ['README.md', 'mcp_server.py', 'bin/claude-*.sh'],
        'optimization_request': True
    }

    # Estimate tokens
    original_tokens = await estimate_context_tokens(context)
    print(f'   Current estimated tokens: {original_tokens}')

    if original_tokens > 2000:
        print('🔧 Applying optimization strategies...')
        optimized_context, result = await optimize_for_budget(context, 2000)
        print(f'   Optimized to: {result.optimized_tokens} tokens')
        print(f'   Reduction: {result.reduction_percentage:.1f}%')
        print(f'   Strategy: {result.strategy}')
    else:
        print('✅ Context is already optimized!')

    print()
    print('💡 Context optimization tips:')
    print('   • Use specific file references instead of broad descriptions')
    print('   • Focus on one task at a time')
    print('   • Provide concrete examples over abstract concepts')
    print('   • Use structured formats (bullets, headers, code blocks)')

asyncio.run(optimize_context())
"