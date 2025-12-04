# Atlas Testing Guide

**Last Updated**: 2025-12-04
**Status**: 🔄 Test Infrastructure Available

## Running Tests

### Quick Start
```bash
# Run all tests
make test

# Or directly
./run_tests.sh

# Or with pytest
pytest
```

### With Coverage
```bash
pytest --cov=. --cov-report=html
# View report: open htmlcov/index.html
```

## Test Structure

```
tests/
├── test_*.py           # Unit tests
├── integration/        # Integration tests
├── conftest.py         # Pytest configuration
└── test_data/          # Test fixtures
```

## CI/CD

Tests run automatically on:
- Push to `main` or `develop` branches
- Pull requests

**GitHub Actions**: `.github/workflows/test.yml`

### CI Pipeline
1. **Linting** - Code style checks (continue on error)
2. **Tests** - Unit and integration tests
3. **Coverage** - Test coverage report (continue on error)
4. **Build Check** - Syntax validation

## Writing Tests

### Unit Test Example
```python
# tests/test_processor.py
import pytest
from processors.atlas_manager import AtlasManager

def test_atlas_manager_initialization():
    """Test Atlas manager can be initialized."""
    manager = AtlasManager()
    assert manager is not None
    assert manager.running is True
```

### Integration Test Example
```python
# tests/integration/test_api.py
import pytest
import requests

def test_api_health_endpoint():
    """Test API health endpoint."""
    response = requests.get("http://localhost:7444/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
```

## Test Configuration

**pytest.ini** or **pyproject.toml**:
```ini
[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
addopts = "-v --tb=short"
```

## Mocking External Services

```python
from unittest.mock import patch, MagicMock

@patch('requests.get')
def test_fetch_transcript(mock_get):
    """Test transcript fetching with mocked HTTP."""
    mock_get.return_value.status_code = 200
    mock_get.return_value.text = "Mock transcript"
    
    # Your test code here
    result = fetch_transcript("http://example.com")
    assert result == "Mock transcript"
```

## Current Test Status

⚠️ **Note**: Test infrastructure exists but pytest is not installed by default.

To run tests:
```bash
# Install test dependencies
pip install -r config/requirements-dev.txt

# Run tests
make test
```

## Test Coverage Goals

**Current Coverage**: Unknown (TODO: measure)
**Target Coverage**: 60%+ for core processors

### Priority Areas
1. ✅ Core processor initialization
2. ⏳ Transcript discovery logic
3. ⏳ API endpoints
4. ⏳ Database operations
5. ⏳ Content parsing

## Continuous Integration

### GitHub Actions
- **Trigger**: Push, PR
- **Python Version**: 3.11
- **OS**: Ubuntu 24.04
- **Cache**: pip dependencies

### Local Pre-commit (Optional)
```bash
# Install pre-commit hooks
pip install pre-commit
pre-commit install

# Run manually
pre-commit run --all-files
```

## Troubleshooting

### "pytest not found"
```bash
pip install -r config/requirements-dev.txt
```

### "Module not found in tests"
```bash
# Add project root to PYTHONPATH
export PYTHONPATH=$PWD
pytest
```

### "Tests fail locally but pass in CI"
```bash
# Check Python version matches CI
python --version

# Clean cache
make clean
```

## Future Improvements

- [ ] Measure and track test coverage
- [ ] Add integration tests for all API endpoints
- [ ] Add performance/load tests
- [ ] Set up test database fixtures
- [ ] Add smoke tests for deployment validation

---

See `run_tests.sh` for current test execution logic.
