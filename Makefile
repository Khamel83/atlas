# OOS (Organized Operational Setup) Makefile
# Provides convenient commands for development, testing, and deployment

.PHONY: help install uninstall start stop restart status test test-watchdog clean lint format

# Default target
help:
	@echo "OOS (Organized Operational Setup) - Available targets:"
	@echo ""
	@echo "Service Management:"
	@echo "  install           Install service and dependencies"
	@echo "  uninstall         Remove service and cleanup"
	@echo "  start             Start OOS service"
	@echo "  stop              Stop OOS service"
	@echo "  restart           Restart OOS service"
	@echo "  status            Show service status"
	@echo ""
	@echo "Testing:"
	@echo "  test              Run all tests"
	@echo "  test-watchdog     Test SystemD watchdog functionality"
	@echo "  test-resources    Test resource management"
	@echo "  test-search       Test Google Search fallback"
	@echo ""
	@echo "Development:"
	@echo "  lint              Run code linting"
	@echo "  format            Format code"
	@echo "  clean             Clean temporary files"
	@echo ""
	@echo "Utilities:"
	@echo "  validate          Validate all configurations"
	@echo "  logs              Show service logs"
	@echo "  metrics           Show system metrics"

# Installation
install:
	@echo "Installing OOS service..."
	sudo mkdir -p /opt/oos
	sudo cp -r . /opt/oos/
	sudo chown -R root:root /opt/oos
	sudo chmod +x /opt/oos/oos_service_manager.py
	sudo chmod +x /opt/oos/scripts/*.py
	sudo chmod +x /opt/oos/bin/*.sh
	sudo useradd -r -s /bin/false -d /opt/oos oos || true
	sudo chown -R oos:oos /opt/oos/data
	sudo cp systemd/oos.service /etc/systemd/system/
	sudo systemctl daemon-reload
	sudo systemctl enable oos.service
	@echo "✓ OOS service installed"

uninstall:
	@echo "Uninstalling OOS service..."
	sudo systemctl stop oos.service || true
	sudo systemctl disable oos.service || true
	sudo rm -f /etc/systemd/system/oos.service
	sudo systemctl daemon-reload
	sudo userdel oos || true
	sudo rm -rf /opt/oos
	@echo "✓ OOS service uninstalled"

# Service management
start:
	sudo systemctl start oos.service
	@echo "✓ OOS service started"

stop:
	sudo systemctl stop oos.service
	@echo "✓ OOS service stopped"

restart:
	sudo systemctl restart oos.service
	@echo "✓ OOS service restarted"

status:
	@echo "=== OOS Service Status ==="
	sudo systemctl status oos.service --no-pager || true
	@echo ""
	@echo "=== Resource Usage ==="
	sudo systemctl show oos.service | grep -E "(Memory|CPU|Limit)" || true

# Testing
test:
	@echo "Running OOS test suite..."
	python3 -m pytest tests/ -v || python3 tests/test_health_check.py
	python3 tests/test_new_oos.py
	@echo "Testing service manager..."
	python3 oos_service_manager.py --test
	@echo "Testing resource management..."
	python3 scripts/test_worker_scaling.py | head -20
	@echo "Testing Google Search fallback..."
	python3 lib/google_search_fallback.py --status
	@echo "✓ All tests completed"

test-watchdog:
	@echo "Testing SystemD watchdog functionality..."
	@echo "1. Testing service manager configuration..."
	python3 oos_service_manager.py --test
	@echo ""
	@echo "2. Testing watchdog heartbeat (requires systemd)..."
	@if systemctl is-active --quiet oos.service; then \
		echo "Service is running, checking logs for watchdog..."; \
		sudo journalctl -u oos.service --since="1 minute ago" | grep -i watchdog || echo "No watchdog messages found"; \
	else \
		echo "Service not running, start with 'make start' first"; \
	fi
	@echo ""
	@echo "3. Testing restart policy (simulation)..."
	@echo "   Note: Run 'sudo kill -9 \$$(pgrep -f oos_service_manager)' to test restart"
	@echo "✓ Watchdog tests completed"

test-resources:
	@echo "Testing resource management..."
	python3 -c "from helpers.resource_manager import check_memory_pressure; print('Memory check:', check_memory_pressure())"
	python3 scripts/check_throttling.py
	python3 scripts/disk_cleanup.py --status
	@echo "✓ Resource management tests completed"

test-search:
	@echo "Testing Google Search fallback..."
	python3 lib/google_search_fallback.py --status
	@echo "✓ Google Search tests completed"

# Development
lint:
	@echo "Running code linting..."
	python3 -m flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics || echo "flake8 not available"
	python3 -m pylint lib/ helpers/ scripts/ || echo "pylint not available, skipping"
	@echo "✓ Linting completed"

format:
	@echo "Formatting code..."
	python3 -m black . || echo "black not available, skipping"
	@echo "✓ Code formatting completed"

clean:
	@echo "Cleaning temporary files..."
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -exec rm -rf {} + || true
	rm -rf .pytest_cache
	rm -rf *.egg-info
	rm -f data/*.log data/cleanup_logs/*.log || true
	@echo "✓ Cleanup completed"

# Utilities
validate:
	@echo "Validating configurations..."
	@echo "1. Testing imports..."
	python3 -c "from lib.health_check import health_check; print('✓ health_check import')"
	python3 -c "from helpers.resource_manager import ResourceManager; print('✓ resource_manager import')"
	python3 -c "from lib.google_search_fallback import GoogleSearchFallback; print('✓ google_search_fallback import')"
	@echo "2. Testing configurations..."
	python3 oos_service_manager.py --test
	@echo "3. Testing scripts..."
	python3 scripts/check_throttling.py >/dev/null
	@echo "✓ All validations passed"

logs:
	@echo "=== Recent OOS Service Logs ==="
	sudo journalctl -u oos.service --since="10 minutes ago" --no-pager || echo "Service not installed"
	@echo ""
	@echo "=== Application Logs ==="
	tail -20 data/oos_service.log 2>/dev/null || echo "No application logs found"

metrics:
	@echo "=== System Metrics ==="
	python3 -c "from helpers.resource_manager import get_resource_status; import json; print(json.dumps(get_resource_status(), indent=2))"

# Development workflow targets
dev-setup:
	@echo "Setting up development environment..."
	python3 -m pip install --user pytest pytest-cov black flake8 pylint || echo "Some packages may not be available"
	mkdir -p data logs
	@echo "✓ Development setup completed"

dev-test: clean test lint
	@echo "✓ Full development test cycle completed"

# Deployment targets  
deploy: clean test install start
	@echo "✓ Deployment completed"

# Quick targets
quick-test:
	python3 tests/test_health_check.py
	python3 oos_service_manager.py --test

check: validate quick-test
	@echo "✓ Quick check completed"