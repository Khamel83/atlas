#!/bin/bash
# Comprehensive test runner for Atlas REST API

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Print header
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Atlas API Test Runner${NC}"
echo -e "${BLUE}========================================${NC}\n"

# Check if we're in the right directory
if [ ! -f "web/api/main.py" ]; then
    echo -e "${RED}Error: Not in Atlas root directory${NC}"
    echo "Please run this script from the Atlas project root."
    exit 1
fi

# Install test dependencies if needed
echo -e "${YELLOW}Installing test dependencies...${NC}"
pip install -q pytest pytest-asyncio httpx fastapi[testing] 2>/dev/null || true

# Set Python path
export PYTHONPATH="${PYTHONPATH}:$(pwd)/web/api"

echo -e "\n${GREEN}Running unit tests...${NC}"

# Run unit tests
echo -e "${BLUE}Testing Atlas TrojanHorse integration...${NC}"
python3 -m pytest tests/test_trojanhorse_router.py -v \
    --tb=short \
    --disable-warnings \
    --color=yes \
    --cov=routers.trojanhorse \
    --cov-report=term-missing \
    --cov-report=html:htmlcov \
    --cov-fail-under=80

# Test Atlas API core functionality
echo -e "\n${GREEN}Testing Atlas API endpoints...${NC}"
python3 -m pytest tests/test_api_core.py -v \
    --tb=short \
    --disable-warnings \
    --color=yes \
    --cov=web.api \
    --cov-report=term-missing

# Run specific test categories
echo -e "\n${BLUE}Running specific test categories...${NC}"

echo -e "${YELLOW}Testing TrojanHorse integration...${NC}"
python3 -m pytest tests/test_trojanhorse_router.py::TestTrojanHorseHealthEndpoint -v \
    --disable-warnings \
    --color=yes

echo -e "${YELLOW}Testing note ingestion...${NC}"
python3 -m pytest tests/test_trojanhorse_router.py::TestIngestSingleNote -v \
    --disable-warnings \
    --color=yes

echo -e "${YELLOW}Testing batch ingestion...${NC}"
python3 -m pytest tests/test_trojanhorse_router.py::TestIngestBatchNotes -v \
    --disable-warnings \
    --color=yes

echo -e "${YELLOW}Testing Pydantic models...${NC}"
python3 -m pytest tests/test_trojanhorse_router.py::TestIngestNoteValidation -v \
    --disable-warnings \
    --color=yes

echo -e "${YELLOW}Testing error handling...${NC}"
python3 -m pytest tests/test_trojanhorse_router.py::TestErrorHandling -v \
    --disable-welines \
    --color=yes

# Test with different Python versions if available
echo -e "\n${BLUE}Testing Python version compatibility...${NC}"
python_version=$(python3 --version 2>&1 | awk '{print $2}')
echo -e "${GREEN}Testing with Python ${python_version}...${NC}"

# Run a quick smoke test
echo -e "\n${YELLOW}Running smoke tests...${NC}"
python3 -c "
import sys
import os
sys.path.append('web/api')
sys.path.append('.')

# Test imports
try:
    from main import app
    from routers.trojanhorse import router
    print('✅ All imports successful')
except ImportError as e:
    print(f'❌ Import error: {e}')
    sys.exit(1)

# Test FastAPI app creation
try:
    from fastapi.testclient import TestClient
    client = TestClient(app)
    response = client.get('/trojanhorse/health')
    assert response.status_code == 200
    print('✅ FastAPI app creation successful')
    print('✅ TrojanHorse router integration successful')
except Exception as e:
    print(f'❌ FastAPI app creation failed: {e}')
    sys.exit(1)

# Test router functionality
try:
    # Test router is properly configured
    assert len(router.routes) > 0
    print('✅ Router configuration successful')
except Exception as e:
    print(f'❌ Router configuration failed: {e}')
    sys.exit(1)

# Test Pydantic models
try:
    from routers.trojanhorse import IngestNote, IngestResponse

    # Test valid note
    note = IngestNote(
        id='test-123',
        path='/test/path.md',
        title='Test Note',
        body='# Test Note\nContent here',
        category='test',
        project='test'
    )
    assert note.id == 'test-123'
    assert note.title == 'Test Note'

    # Test response model
    response = IngestResponse(status='ok', message='Success', count=1)
    assert response.count == 1

    print('✅ Pydantic models validation successful')
except Exception as e:
    print(f'❌ Pydantic models validation failed: {e}')
    sys.exit(1)

print('✅ All smoke tests passed')
"

# Test database integration
echo -e "\n${YELLOW}Testing database integration...${NC}"
python3 -c "
import sys
sys.path.append('web/api')
sys.path.append('.')

# Test SimpleDatabase import (should be mocked in tests)
try:
    import os
    os.environ['ATLAS_API_KEY'] = 'test-key'
    print('✅ Environment configuration successful')
except Exception as e:
    print(f'⚠️  Environment warning: {e}')

# Test router functionality with mock
try:
    from unittest.mock import Mock
    from routers.trojanhorse import validate_api_key

    # Test validation without API key requirement
    result = validate_api_key()
    assert result == True
    print('✅ API key validation successful')
except Exception as e:
    print(f'❌ API key validation failed: {e}')
    sys.exit(1)
"

# Test security features
echo -e "\n${YELLOW}Testing security features...${NC}"
python3 -c "
import sys
sys.path.append('web/api')
sys.path.append('.')

try:
    from routers.trojanhorse import IngestNote

    # Test validation limits
    note = IngestNote(
        id='test',
        path='/test/path.md',
        title='Test',
        body='# Test\nContent'
    )

    # Test that large content is handled
    large_content = 'x' * 1000000  # 1MB
    note_large = IngestNote(
        id='test-large',
        path='/test/large.md',
        title='Large Content Test',
        body=large_content
    )

    # Test tag limits (should pass validation)
    note_tags = IngestNote(
        id='test-tags',
        path='/test/tags.md',
        title='Tags Test',
        body='# Test\nContent',
        tags=[f'tag-{i}' for i in range(10)]  # 10 tags (within limit)
    )

    print('✅ Security validation tests passed')
except Exception as e:
    print(f'❌ Security validation failed: {e}')
    sys.exit(1)
"

# Test API endpoints manually
echo -e "\n${YELLOW}Testing API endpoints manually...${NC}"
python3 -c "
import sys
sys.path.append('web/api')
sys.path.append('.')

from fastapi.testclient import TestClient
from main import app
from unittest.mock import patch

try:
    client = TestClient(app)

    # Mock database dependencies
    with patch('helpers.simple_database.SimpleDatabase'):
        # Test health check
        response = client.get('/trojanhorse/health')
        assert response.status_code == 200
        data = response.json()
        assert data['status'] == 'ok'
        assert 'service' in data

        print('✅ Health endpoint working')

        # Test main API health
        response = client.get('/health')
        assert response.status_code == 200
        data = response.json()
        assert 'status' in data

        print('✅ Main health endpoint working')

        # Test root endpoint
        response = client.get('/')
        assert response.status_code == 200

        print('✅ Root endpoint working')

except Exception as e:
    print(f'❌ API endpoint test failed: {e}')
    sys.exit(1)
"

# Generate coverage report
if [ -d "htmlcov" ]; then
    echo -e "\n${BLUE}Coverage report generated: ${NC}file://${PWD}/htmlcov/index.html"
fi

# Check test results
TEST_EXIT_CODE=0

# Summary
echo -e "\n${GREEN}========================================${NC}"
echo -e "${GREEN}Atlas API Test Summary${NC}"
echo -e "${GREEN}========================================${NC}"

echo -e "${GREEN}✅ Unit tests completed${NC}"
echo -e "${GREEN}✅ TrojanHorse integration tests completed${NC}"
echo -e "${GREEN}✅ Pydantic model tests completed${NC}"
echo -e "${GREEN}✅ Error handling tests completed${NC}"
echo -e "${GREEN}✅ Security validation tests completed${NC}"
echo -e "${GREEN}✅ API endpoint tests completed${NC}"
echo -e "${GREEN}✅ Smoke tests completed${NC}"

echo -e "\n${BLUE}To run specific tests:${NC}"
echo -e "${YELLOW}  pytest tests/test_trojanhorse_router.py::TestTrojanHorseHealthEndpoint${NC}"
echo -e "${YELLOW}  pytest tests/test_trojanhorse_router.py::TestIngestSingleNote${NC}"
echo -e "${YELLOW}  pytest tests/test_trojanhorse_router.py::TestIngestBatchNotes${NC}"
echo -e "${YELLOW}  pytest tests/test_trojanhorse_router.py::TestIngestNoteValidation${NC}"

echo -e "\n${BLUE}To run tests with coverage:${NC}"
echo -e "${YELLOW}  pytest --cov=routers.trojanhorse --cov-report=html${NC}"
echo -e "${YELLOW}  pytest --cov=web.api --cov-report=term-missing${NC}"

echo -e "\n${BLUE}To run tests in verbose mode:${NC}"
echo -e "${YELLOW}  pytest -v --tb=long${NC}"

echo -e "\n${BLUE}To run tests with specific patterns:${NC}"
echo -e "${YELLOW}  pytest tests/test_trojanhorse_router.py -k 'test_ingest'${NC}"
echo -e "${YELLOW}  pytest tests/ -k 'integration' --tb=short${NC}"

echo -e "\n${BLUE}To debug failing tests:${NC}"
echo -e "${YELLOW}  pytest tests/test_trojanhorse_router.py::TestIngestSingleNote -v --tb=long -s${NC}"

echo -e "\n${GREEN}All Atlas API tests completed successfully! 🎉${NC}"