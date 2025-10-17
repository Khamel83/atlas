# Atlas Development Workflow

## Daily Startup
```bash
./start_work.sh                 # One-command startup
python atlas_status.py          # Quick status check
python atlas_status.py --dev    # Development mode
```

## Development Process

### 1. Check Existing Components
Always check `ATLAS_COMPONENT_INDEX.md` before building new functionality to avoid duplication.

### 2. Environment Setup
- Load environment variables from `.env`
- Activate background services if needed
- Verify database connectivity

### 3. Code Changes
- Follow type hints and docstring conventions
- Use pathlib for all path operations
- Implement comprehensive error handling
- Add tests for new functionality

### 4. Testing
```bash
pytest tests/                    # Run test suite
python atlas_system_test.py     # Full system test
```

### 5. Quality Checks
```bash
python -m ruff check .          # Linting
python -m mypy .               # Type checking
pytest --cov=. tests/          # Coverage report
```

### 6. Deployment
```bash
git add .
git commit -m "feat: descriptive commit message"
git push origin main
```

## Service Management
```bash
./scripts/start_atlas_service.sh start    # Start background service
./scripts/start_atlas_service.sh status   # Check status
./scripts/start_atlas_service.sh logs     # Monitor logs
```

## Common Tasks

### Adding New Content Source
1. Create processor in `helpers/`
2. Add configuration to `config/`
3. Update background service scheduler
4. Add tests and documentation

### Debugging Issues
1. Check logs: `tail -f logs/atlas_service.log`
2. Run system test: `python atlas_system_test.py`
3. Check database: `sqlite3 data/atlas.db`
4. Verify API: `curl http://localhost:8000/api/v1/health`

### Performance Optimization
1. Profile with `cProfile`
2. Check database query performance
3. Monitor memory usage with `psutil`
4. Optimize background processing batch sizes