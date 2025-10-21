# Atlas Production Reliability Closeout Task Plan

## Overview

Transform Atlas from a development prototype into a reliable, production-ready "ingest engine + API + web UI" that runs 24/7 on an OCI VM with proper monitoring, logging, and operational excellence.

### Current State Assessment

✅ **Working Components**
- FastAPI + SQLite content management system
- Google Search API integration with circuit breakers
- Stage-based content processing (0-599)
- Basic web interface and mobile integration
- 14/15 tests passing across Python 3.9-3.11

❌ **Production Gaps**
- No systemd services for 24/7 operation
- No structured logging or observability
- No configuration management
- No reliability patterns (retries, backpressure, graceful degradation)
- CI only covers basic functionality

## Deliverables

### 1. Systemd Services for 24/7 Operation

**Goal**: Idempotent services that survive reboots and failures

**Implementation Plan**:
```bash
# Create service files
sudo nano /etc/systemd/system/atlas-api.service
sudo nano /etc/systemd/system/atlas-worker.service
sudo nano /etc/systemd/system/atlas-scheduler.timer
sudo nano /etc/systemd/system/atlas-scheduler.service
sudo nano /etc/systemd/system/atlas-backup.timer
sudo nano /etc/systemd/system/atlas-backup.service

# Enable and start services
sudo systemctl daemon-reload
sudo systemctl enable atlas-api.service atlas-worker.service
sudo systemctl enable atlas-scheduler.timer atlas-backup.timer
sudo systemctl start atlas-api.service
```

**Service Configuration**:
- `atlas-api.service`: FastAPI server on port 7444
- `atlas-worker.service`: Background content processing
- `atlas-scheduler.timer`: Every 5 minutes for RSS/feed processing
- `atlas-backup.timer`: Daily database backups

**Acceptance Criteria**:
- [ ] Services auto-start on boot
- [ ] Services restart on failure (Restart=always)
- [ ] Health checks pass within 30 seconds of startup
- [ ] Services survive network interruptions
- [ ] Clean shutdown on systemctl stop

**Verification Commands**:
```bash
# Check service status
sudo systemctl status atlas-api.service atlas-worker.service
sudo systemctl is-enabled atlas-api.service
sudo systemctl list-timers atlas-*

# Test health endpoints
curl -f http://localhost:7444/health
curl -f http://localhost:7444/ready

# Check logs
journalctl -u atlas-api -n 50 --no-pager
journalctl -f -u atlas-worker
```

### 2. Ingestion Reliability

**Goal**: Durable, idempotent content processing with backpressure

**Implementation Plan**:
```python
# Configure SQLite for concurrency
conn.execute("PRAGMA journal_mode=WAL")
conn.execute("PRAGMA busy_timeout=5000")
conn.execute("PRAGMA synchronous=NORMAL")

# Add content deduplication
def get_content_hash(url, content):
    return hashlib.sha256(f"{url}:{content}".encode()).hexdigest()

# Implement queue with backpressure
class ProcessingQueue:
    def __init__(self, max_size=1000):
        self.max_size = max_size
        self.queue = asyncio.Queue(maxsize=max_size)

    async def put_with_backpressure(self, item):
        try:
            await asyncio.wait_for(self.queue.put(item), timeout=30.0)
        except asyncio.TimeoutError:
            raise QueueFullException("Processing queue full, backing off")

# Add circuit breakers for external services
google_breaker = CircuitBreaker(
    failure_threshold=5,
    recovery_timeout=60,
    expected_exception=Exception
)
```

**Acceptance Criteria**:
- [ ] SQLite WAL mode enabled for concurrent access
- [ ] Content deduplication using SHA256 hashes
- [ ] Queue backpressure when >1000 items pending
- [ ] Circuit breakers for external API calls
- [ ] Graceful degradation when services unavailable
- [ ] Atomic database updates to prevent partial states

**Verification Commands**:
```bash
# Check SQLite configuration
sqlite3 data/atlas.db "PRAGMA journal_mode;"

# Test deduplication
python3 -c "
from core.database import get_database
db = get_database()
hash1 = db.get_content_hash('http://test.com', 'content')
hash2 = db.get_content_hash('http://test.com', 'content')
print('Deduplication working:', hash1 == hash2)
"

# Test queue backpressure
python3 tests/test_queue_backpressure.py -v
```

### 3. Observability

**Goal**: Structured logging, metrics, and health monitoring

**Implementation Plan**:
```python
# Structured logging
import structlog
logger = structlog.get_logger()

# Add request correlation IDs
@app.middleware("http")
async def add_correlation_id(request: Request, call_next):
    correlation_id = str(uuid.uuid4())
    request.state.correlation_id = correlation_id
    logger.info("Request started", correlation_id=correlation_id)

    response = await call_next(request)

    logger.info("Request completed",
                correlation_id=correlation_id,
                status_code=response.status_code)
    return response

# Metrics endpoint
from prometheus_client import Counter, Histogram, Gauge, generate_latest

REQUEST_COUNT = Counter('atlas_requests_total', 'Total requests', ['method', 'endpoint'])
PROCESSING_TIME = Histogram('atlas_processing_seconds', 'Processing time')

@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type="text/plain")

# Health checks
@app.get("/health")
async def health_check():
    db_healthy = await check_database()
    processor_healthy = await check_processor()

    return {
        "status": "healthy" if all([db_healthy, processor_healthy]) else "unhealthy",
        "database": "healthy" if db_healthy else "unhealthy",
        "processor": "healthy" if processor_healthy else "unhealthy",
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/ready")
async def readiness_check():
    queue_size = get_queue_size()
    return {
        "ready": queue_size < 1000,
        "queue_size": queue_size,
        "max_queue_size": 1000
    }
```

**Acceptance Criteria**:
- [ ] Structured JSON logging with correlation IDs
- [ ] `/metrics` endpoint with Prometheus-style metrics
- [ ] `/health` endpoint for service health
- [ ] `/ready` endpoint for readiness probes
- [ ] Log rotation with retention (30 days)
- [ ] Error tracking with unique error IDs

**Verification Commands**:
```bash
# Test metrics endpoint
curl -s http://localhost:7444/metrics | grep 'atlas_'

# Test health endpoints
curl -s http://localhost:7444/health | jq .
curl -s http://localhost:7444/ready | jq .

# Check structured logging
tail -f logs/atlas.log | jq -c 'select(.level=="error")'

# Test log rotation
logrotate -f /etc/logrotate.d/atlas
```

### 4. CI Enhancement

**Goal**: Test across Python 3.9-3.12 with fast smoke tests

**Implementation Plan**:
```yaml
# .github/workflows/ci.yml
name: Atlas CI

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  smoke-test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ['3.9', '3.10', '3.11', '3.12']
    timeout-minutes: 5

    steps:
    - uses: actions/checkout@v4
    - name: Set up Python ${{ matrix.python-version }}
      uses: actions/setup-python@v4
      with:
        python-version: ${{ matrix.python-version }}

    - name: Fast smoke test
      run: |
        pip install -r requirements.txt
        python3 -c "
        import api
        import core
        import helpers
        print('✅ All modules import successfully')
        "

    - name: Run core tests
      run: |
        python3 -m pytest tests/test_google_search_fallback.py -v --tb=short
        python3 -m pytest tests/test_reliability/ -v --tb=short

  full-test:
    needs: smoke-test
    runs-on: ubuntu-latest
    timeout-minutes: 30

    steps:
    - uses: actions/checkout@v4
    - name: Set up Python 3.11
      uses: actions/setup-python@v4
      with:
        python-version: 3.11

    - name: Run full test suite
      run: |
        pip install -r requirements.txt
        python3 -m pytest tests/ -v --cov=. --cov-report=xml

    - name: Upload coverage
      uses: codecov/codecov-action@v3
```

**Acceptance Criteria**:
- [ ] CI runs on Python 3.9, 3.10, 3.11, and 3.12
- [ ] Smoke tests complete in under 30 seconds
- [ ] All existing tests pass across all versions
- [ ] Coverage reporting enabled
- [ ] Security scanning for dependencies
- [ ] Performance benchmarks included

**Verification Commands**:
```bash
# Test all Python versions
for version in 3.9 3.10 3.11 3.12; do
  python${version} -m pytest tests/test_google_search_fallback.py -v
done

# Run smoke test
time python3 -c "import api, core, helpers; print('Smoke test passed')"

# Run full test suite
pytest tests/ --cov=. --cov-report=html
```

### 5. Configuration Management

**Goal**: Single source of truth with .env file and validation

**Implementation Plan**:
```python
# config.py
from pydantic import BaseSettings, Field
from typing import Optional
import os

class AtlasSettings(BaseSettings):
    # Database
    database_path: str = Field(default="data/atlas.db", env="ATLAS_DATABASE_PATH")
    database_pool_size: int = Field(default=5, env="ATLAS_DB_POOL_SIZE")

    # API
    api_host: str = Field(default="0.0.0.0", env="ATLAS_API_HOST")
    api_port: int = Field(default=7444, env="ATLAS_API_PORT")

    # Processing
    max_queue_size: int = Field(default=1000, env="ATLAS_MAX_QUEUE_SIZE")
    worker_concurrency: int = Field(default=4, env="ATLAS_WORKER_CONCURRENCY")

    # External APIs
    google_search_api_key: Optional[str] = Field(default=None, env="GOOGLE_SEARCH_API_KEY")
    google_search_engine_id: Optional[str] = Field(default=None, env="GOOGLE_SEARCH_ENGINE_ID")

    # Logging
    log_level: str = Field(default="INFO", env="ATLAS_LOG_LEVEL")
    log_file: str = Field(default="logs/atlas.log", env="ATLAS_LOG_FILE")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

def get_settings() -> AtlasSettings:
    return AtlasSettings()

def validate_config():
    """Validate configuration at startup"""
    settings = get_settings()

    # Create necessary directories
    os.makedirs(os.path.dirname(settings.database_path), exist_ok=True)
    os.makedirs(os.path.dirname(settings.log_file), exist_ok=True)

    # Validate database path is writable
    if not os.access(os.path.dirname(settings.database_path) or '.', os.W_OK):
        raise ValueError(f"Database directory not writable: {settings.database_path}")

    return settings
```

**Sample .env file**:
```env
# Atlas Configuration
ATLAS_DATABASE_PATH=data/atlas.db
ATLAS_API_HOST=0.0.0.0
ATLAS_API_PORT=7444
ATLAS_MAX_QUEUE_SIZE=1000
ATLAS_WORKER_CONCURRENCY=4
ATLAS_LOG_LEVEL=INFO
ATLAS_LOG_FILE=logs/atlas.log

# External APIs (set these in production)
GOOGLE_SEARCH_API_KEY=your_api_key_here
GOOGLE_SEARCH_ENGINE_ID=your_engine_id_here
```

**Acceptance Criteria**:
- [ ] Single .env file for all configuration
- [ ] Environment variable validation with defaults
- [ ] Secrets not committed to git
- [ ] Configuration validation at startup
- [ ] Environment-specific overrides supported
- [ ] Required directories created automatically

**Verification Commands**:
```bash
# Test configuration loading
python3 -c "
from core.config import validate_config
settings = validate_config()
print('Config valid:', bool(settings))
print('Database path:', settings.database_path)
print('API port:', settings.api_port)
"

# Test environment overrides
ATLAS_API_PORT=9999 python3 -c "
from core.config import get_settings
print('Port overridden:', get_settings().api_port)
"

# Check .env file exists and is readable
ls -la .env
cat .env
```

### 6. Operational Tooling

**Goal**: Make deployment and operations trivial

**Implementation Plan**:
```makefile
# Makefile
.PHONY: help install start stop restart status logs clean backup restore deploy

help:
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Install dependencies and setup
	python3 -m pip install -r requirements.txt
	python3 -c "from core.config import validate_config; validate_config()"
	mkdir -p data logs
	chmod +x scripts/*.sh

start: ## Start all services
	sudo systemctl start atlas-api.service atlas-worker.service
	sudo systemctl enable atlas-scheduler.timer atlas-backup.timer

stop: ## Stop all services
	sudo systemctl stop atlas-api.service atlas-worker.service
	sudo systemctl disable atlas-scheduler.timer atlas-backup.timer

restart: ## Restart all services
	sudo systemctl restart atlas-api.service atlas-worker.service

status: ## Show service status
	sudo systemctl status atlas-api.service atlas-worker.service
	sudo systemctl list-timers atlas-*

logs: ## Show service logs
	journalctl -f -u atlas-api -u atlas-worker

clean: ## Clean up temporary files
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	rm -rf logs/*.log.1

backup: ## Create database backup
	./scripts/backup.sh

restore: ## Restore database from backup
	./scripts/restore.sh

deploy: ## Deploy/update the system
	./scripts/deploy.sh

health: ## Check system health
	./scripts/health_check.sh
```

**Shell Scripts**:
```bash
#!/bin/bash
# scripts/deploy.sh
set -euo pipefail

echo "🚀 Deploying Atlas..."

# Pull latest code
git pull origin main

# Install dependencies
make install

# Restart services
sudo systemctl restart atlas-api.service atlas-worker.service

# Wait for health check
echo "⏳ Waiting for services to start..."
sleep 10

if curl -f http://localhost:7444/health; then
    echo "✅ Deployment successful"
else
    echo "❌ Health check failed"
    exit 1
fi
```

**Acceptance Criteria**:
- [ ] Makefile with all operational targets
- [ ] Idempotent deployment script
- [ ] Health check script for monitoring
- [ ] Backup and restore procedures
- [ ] One-command setup and teardown
- [ ] All commands work with appropriate permissions

**Verification Commands**:
```bash
# Test all make targets
make help
make install
make status
make logs
make health

# Test deployment script
./scripts/deploy.sh

# Test health monitoring
./scripts/health_check.sh
```

### 7. Documentation

**Goal**: Comprehensive operational documentation

**Implementation Plan**:
1. **Update QUICKSTART.md** with systemd setup
2. **Create OPERATIONS.md** with troubleshooting
3. **Create RELIABILITY_CHECKLIST.md** for production validation

**Verification Commands**:
```bash
# Check documentation exists and is readable
ls -la QUICKSTART.md OPERATIONS.md RELIABILITY_CHECKLIST.md

# Test documentation links
markdownlint *.md 2>/dev/null || echo "markdownlint not available, skipping"

# Check quickstart includes systemd
grep -c systemd QUICKSTART.md

# Check operations guide has troubleshooting sections
grep -c "troubleshooting\|debug\|error" OPERATIONS.md
```

### 8. Reliability Tests

**Goal**: Test failure scenarios and long-running reliability

**Implementation Plan**:
```python
# tests/test_reliability/test_systemd_services.py
import pytest
import subprocess
import time

def test_api_service_restart():
    """Test API service restarts properly"""
    subprocess.run(["sudo", "systemctl", "restart", "atlas-api.service"], check=True)
    time.sleep(5)

    # Check health endpoint
    result = subprocess.run(["curl", "-f", "http://localhost:7444/health"], capture_output=True)
    assert result.returncode == 0

def test_worker_backpressure():
    """Test worker handles queue backpressure"""
    # Fill queue beyond capacity
    for i in range(1500):
        add_test_item_to_queue()

    # Check that new items are rejected or queued
    stats = get_queue_stats()
    assert stats['rejected'] > 0 or stats['queue_size'] >= 1000

# tests/test_reliability/test_database_reliability.py
def test_database_concurrent_access():
    """Test SQLite WAL mode handles concurrent access"""
    import threading
    import sqlite3

    def concurrent_access():
        conn = sqlite3.connect('data/atlas.db')
        conn.execute("INSERT INTO content (title, url) VALUES (?, ?)",
                   (f"Test {threading.current_thread().ident}", "http://test.com"))
        conn.commit()
        conn.close()

    threads = []
    for _ in range(10):
        t = threading.Thread(target=concurrent_access)
        threads.append(t)
        t.start()

    for t in threads:
        t.join()

    # Verify all inserts succeeded
    conn = sqlite3.connect('data/atlas.db')
    count = conn.execute("SELECT COUNT(*) FROM content WHERE title LIKE 'Test %'").fetchone()[0]
    conn.close()
    assert count == 10
```

**Verification Commands**:
```bash
# Run reliability tests
python3 -m pytest tests/test_reliability/ -v

# Run performance tests
python3 -m pytest tests/test_performance/ -v

# Run integration tests
python3 -m pytest tests/test_integration/ -v

# Test with high load
python3 tests/test_load.py --iterations=1000 --concurrent=50
```

## Implementation Sequence

1. **Week 1**: Foundation (Tasks 1, 2, 5)
   - Systemd services
   - Ingestion reliability
   - Configuration management

2. **Week 2**: Observability (Tasks 3, 6)
   - Logging and metrics
   - Operational tooling

3. **Week 3**: CI and Testing (Tasks 4, 8)
   - CI enhancement
   - Reliability tests

4. **Week 4**: Documentation and Handoff (Task 7)
   - Documentation updates
   - End-to-end validation

## Success Criteria

- ✅ **Reliability**: 99.9% uptime with automatic recovery
- ✅ **Observability**: All components monitored with metrics and logs
- ✅ **Maintainability**: One-command deployment and operations
- ✅ **Test Coverage**: 95%+ test coverage with reliability scenarios
- ✅ **Documentation**: Complete operational guides
- ✅ **Performance**: Handles 1000+ concurrent operations gracefully

## Risk Mitigation

1. **Data Loss**: Daily backups + WAL mode + atomic operations
2. **Service Outages**: Systemd auto-restart + health checks
3. **Performance Issues**: Backpressure + queue limits + monitoring
4. **Configuration Errors**: Validation at startup + documentation
5. **Deployment Failures**: Idempotent scripts + rollback procedures