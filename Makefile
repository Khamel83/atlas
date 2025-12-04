# Atlas Makefile
# Common tasks for Atlas podcast transcript discovery system

.PHONY: help setup test run status clean deploy

# Default target
help:
	@echo "Atlas - Podcast Transcript Discovery System"
	@echo ""
	@echo "Available targets:"
	@echo "  make setup    - Create venv and install dependencies"
	@echo "  make test     - Run test suite"
	@echo "  make run      - Start Atlas processor"
	@echo "  make status   - Check system status"
	@echo "  make api      - Start REST API server"
	@echo "  make clean    - Remove generated files and caches"
	@echo "  make deploy   - Deploy systemd service"
	@echo ""
	@echo "Development:"
	@echo "  make lint     - Run code linting"
	@echo "  make format   - Format code with black"
	@echo ""

# Setup: Create virtual environment and install dependencies
setup:
	@echo "🔧 Setting up Atlas..."
	python3 -m venv venv
	./venv/bin/pip install --upgrade pip
	./venv/bin/pip install -r requirements.txt
	@if [ -f ".env.template" ] && [ ! -f ".env" ]; then \
		cp .env.template .env; \
		echo "✅ Created .env from template - please edit with your configuration"; \
	fi
	@echo "✅ Setup complete!"
	@echo ""
	@echo "Next steps:"
	@echo "  1. Edit .env with your configuration"
	@echo "  2. Run 'make status' to check system"
	@echo "  3. Run 'make run' to start processing"

# Run tests
test:
	@echo "🧪 Running tests..."
	@if [ -f "run_tests.sh" ]; then \
		./run_tests.sh; \
	elif [ -d "venv" ]; then \
		./venv/bin/pytest; \
	else \
		pytest; \
	fi

# Start main Atlas processor
run:
	@echo "🚀 Starting Atlas processor..."
	@if [ -f "scripts/start/start_atlas.sh" ]; then \
		./scripts/start/start_atlas.sh; \
	else \
		python3 processors/atlas_manager.py; \
	fi

# Check system status
status:
	@if [ -f "atlas_status.sh" ]; then \
		./atlas_status.sh; \
	else \
		@echo "⚠️  atlas_status.sh not found"; \
		@echo "Checking basic status..."; \
		@if [ -f "podcast_processing.db" ]; then \
			echo "✅ Database exists"; \
		else \
			echo "❌ Database not found"; \
		fi; \
		@if pgrep -f "atlas_manager.py" > /dev/null; then \
			echo "✅ Atlas manager running (PID: $$(pgrep -f atlas_manager.py))"; \
		else \
			echo "❌ Atlas manager not running"; \
		fi; \
	fi

# Start REST API server
api:
	@echo "🌐 Starting Atlas REST API..."
	@if [ -d "venv" ]; then \
		./venv/bin/python -m uvicorn api.main:app --host 0.0.0.0 --port 7444; \
	else \
		python3 -m uvicorn api.main:app --host 0.0.0.0 --port 7444; \
	fi

# Clean generated files
clean:
	@echo "🧹 Cleaning generated files..."
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	rm -f .coverage
	@echo "✅ Cleanup complete"

# Deploy as systemd service
deploy:
	@echo "📦 Deploying Atlas as systemd service..."
	@if [ ! -f "systemd/atlas-manager.service" ]; then \
		echo "❌ systemd/atlas-manager.service not found"; \
		exit 1; \
	fi
	@echo "Current working directory will be: $$(pwd)"
	@echo ""
	@read -p "Install systemd service? [y/N] " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		sudo cp systemd/atlas-manager.service /etc/systemd/system/; \
		sudo systemctl daemon-reload; \
		sudo systemctl enable atlas-manager; \
		echo "✅ Service installed"; \
		echo ""; \
		echo "To start: sudo systemctl start atlas-manager"; \
		echo "To check: sudo systemctl status atlas-manager"; \
	fi

# Development: Lint code
lint:
	@echo "🔍 Linting code..."
	@if [ -d "venv" ]; then \
		./venv/bin/ruff check . || echo "Install ruff: pip install ruff"; \
	else \
		ruff check . || echo "Install ruff: pip install ruff"; \
	fi

# Development: Format code
format:
	@echo "✨ Formatting code..."
	@if [ -d "venv" ]; then \
		./venv/bin/black . || echo "Install black: pip install black"; \
	else \
		black . || echo "Install black: pip install black"; \
	fi

# Stop Atlas processor
stop:
	@echo "🛑 Stopping Atlas processor..."
	@if pgrep -f "atlas_manager.py" > /dev/null; then \
		pkill -f "atlas_manager.py"; \
		echo "✅ Atlas manager stopped"; \
	else \
		echo "⚠️  Atlas manager not running"; \
	fi
