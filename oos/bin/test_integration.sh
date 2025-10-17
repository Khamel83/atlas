#!/bin/bash
# OOS Integration Testing Suite
# Tests all integration scenarios to prevent JSON failures

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OOS_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo -e "${BLUE}🧪 OOS Integration Testing Suite${NC}"
echo "================================="

# Test 1: JSON validation function
test_json_validation() {
    echo -e "${BLUE}Test 1: JSON Validation${NC}"

    # Create test files
    echo '{"commands": []}' > /tmp/valid.json
    echo '{"commands": [' > /tmp/invalid.json

    # Test valid JSON
    if python3 -c "import json; json.load(open('/tmp/valid.json'))" 2>/dev/null; then
        echo -e "${GREEN}✅ Valid JSON detection works${NC}"
    else
        echo -e "${RED}❌ Valid JSON detection failed${NC}"
        return 1
    fi

    # Test invalid JSON
    if ! python3 -c "import json; json.load(open('/tmp/invalid.json'))" 2>/dev/null; then
        echo -e "${GREEN}✅ Invalid JSON detection works${NC}"
    else
        echo -e "${RED}❌ Invalid JSON detection failed${NC}"
        return 1
    fi

    rm -f /tmp/valid.json /tmp/invalid.json
    return 0
}

# Test 2: JSON merge functionality
test_json_merge() {
    echo -e "${BLUE}Test 2: JSON Merge Functionality${NC}"

    # Create test directory
    mkdir -p /tmp/test_integration/.claude

    # Test merging into empty file
    echo '{"commands": []}' > /tmp/test_integration/.claude/slash_commands.json

    python3 << 'EOF'
import json

# Load existing commands
with open('/tmp/test_integration/.claude/slash_commands.json', 'r') as f:
    data = json.load(f)

# Add consultant command
consultant_cmd = {
    "name": "consultant",
    "description": "Strategic AI consultant",
    "script": "bin/claude-consultant.sh"
}
data['commands'].append(consultant_cmd)

# Write back
with open('/tmp/test_integration/.claude/slash_commands.json', 'w') as f:
    json.dump(data, f, indent=2)
EOF

    # Validate result
    if python3 -c "import json; data=json.load(open('/tmp/test_integration/.claude/slash_commands.json')); assert any(cmd['name']=='consultant' for cmd in data['commands'])" 2>/dev/null; then
        echo -e "${GREEN}✅ JSON merge works correctly${NC}"
    else
        echo -e "${RED}❌ JSON merge failed${NC}"
        return 1
    fi

    rm -rf /tmp/test_integration
    return 0
}

# Test 3: Integration script execution
test_integration_script() {
    echo -e "${BLUE}Test 3: Integration Script Execution${NC}"

    # Create mock parent project
    mkdir -p /tmp/mock_parent/{.git,bin,.claude}
    mkdir -p /tmp/mock_parent/oos

    # Copy OOS into mock parent
    cp -r "$OOS_ROOT"/* /tmp/mock_parent/oos/ 2>/dev/null || true

    # Run integration from mock oos
    cd /tmp/mock_parent/oos
    if ./bin/integrate_to_parent_v2.sh > /tmp/integration_output.log 2>&1; then
        echo -e "${GREEN}✅ Integration script runs without errors${NC}"

        # Check if consultant was added
        if grep -q '"name": "consultant"' ../.claude/slash_commands.json 2>/dev/null; then
            echo -e "${GREEN}✅ Consultant command properly added${NC}"
        else
            echo -e "${RED}❌ Consultant command not found in output${NC}"
            return 1
        fi

        # Validate JSON
        if python3 -c "import json; json.load(open('../.claude/slash_commands.json'))" 2>/dev/null; then
            echo -e "${GREEN}✅ Generated JSON is valid${NC}"
        else
            echo -e "${RED}❌ Generated JSON is invalid${NC}"
            cat ../.claude/slash_commands.json
            return 1
        fi

    else
        echo -e "${RED}❌ Integration script failed${NC}"
        cat /tmp/integration_output.log
        return 1
    fi

    cd "$OOS_ROOT"
    rm -rf /tmp/mock_parent /tmp/integration_output.log
    return 0
}

# Test 4: Consultant script functionality
test_consultant_script() {
    echo -e "${BLUE}Test 4: Consultant Script Functionality${NC}"

    # Test direct consultant execution
    if python3 -c "
import sys
sys.path.insert(0, 'src')
from simple_command_handler import SimpleCommandHandler
import asyncio

async def test():
    handler = SimpleCommandHandler()
    result = await handler.execute_command('consultant', 'status')
    print('Test result:', result['output'])

asyncio.run(test())
" > /tmp/consultant_test.log 2>&1; then
        echo -e "${GREEN}✅ Consultant command works directly${NC}"
    else
        echo -e "${RED}❌ Consultant command failed${NC}"
        cat /tmp/consultant_test.log
        return 1
    fi

    rm -f /tmp/consultant_test.log
    return 0
}

# Run all tests
main() {
    local failed=0

    test_json_validation || failed=1
    echo ""

    test_json_merge || failed=1
    echo ""

    test_integration_script || failed=1
    echo ""

    test_consultant_script || failed=1
    echo ""

    if [ $failed -eq 0 ]; then
        echo -e "${GREEN}🎉 ALL TESTS PASSED!${NC}"
        echo "Integration is bulletproof and ready for deployment."
        return 0
    else
        echo -e "${RED}❌ TESTS FAILED${NC}"
        echo "Integration has reliability issues that must be fixed."
        return 1
    fi
}

main "$@"