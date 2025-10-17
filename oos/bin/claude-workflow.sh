#!/bin/bash
# Start structured workflow for complex tasks
set -e

# Colors
BLUE='\033[0;34m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${BLUE}🚀 Starting structured workflow...${NC}"

if [[ $# -eq 0 ]]; then
    echo -e "${YELLOW}Please describe your complex task:${NC}"
    echo "Usage: /workflow \"implement user authentication with OAuth\""
    echo ""
    echo "The workflow will help you break down complex tasks into manageable steps."
    exit 0
fi

TASK="$*"
echo -e "${GREEN}Task: $TASK${NC}"
echo ""

# Simple workflow breakdown
echo -e "${BLUE}📋 Workflow Planning:${NC}"
echo ""

echo "1. 🎯 Define Requirements"
echo "   • What specific features are needed?"
echo "   • What are the constraints and requirements?"
echo "   • Who is the target user/audience?"
echo ""

echo "2. 🏗️ Architecture Planning"
echo "   • What components need to be built?"
echo "   • How do they interact?"
echo "   • What technologies/frameworks to use?"
echo ""

echo "3. 📋 Task Breakdown"
echo "   • Break into smaller, manageable tasks"
echo "   • Identify dependencies between tasks"
echo "   • Estimate time and complexity"
echo ""

echo "4. 🔄 Implementation Phase"
echo "   • Start with core functionality"
echo "   • Build incrementally and test frequently"
echo "   • Handle edge cases and error conditions"
echo ""

echo "5. ✅ Testing & Validation"
echo "   • Unit tests for individual components"
echo "   • Integration tests for workflows"
echo "   • User acceptance testing"
echo ""

echo "6. 📚 Documentation & Deployment"
echo "   • Update documentation"
echo "   • Create deployment guides"
echo "   • Monitor and maintain"
echo ""

echo -e "${GREEN}💡 Next Steps:${NC}"
echo "1. Use /clarify to refine requirements for: $TASK"
echo "2. Use /meta-ai if you need help planning any phase"
echo "3. Break down Phase 1 (Requirements) into specific questions"
echo "4. Use /smart-commit as you complete each phase"

echo ""
echo -e "${BLUE}🛠️ Recommended Tools:${NC}"
echo "  • /clarify - Refine vague requirements"
echo "  • /meta-ai - Get external AI help for planning"
echo "  • /optimize - Keep context focused"
echo "  • /doc-check - Ensure documentation completeness"
echo "  • /smart-commit - Track progress with good commits"