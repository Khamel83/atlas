# Atlas API

The Atlas API provides programmatic access to all cognitive amplification features of the Atlas platform.

## Features

- Content management (list, retrieve, submit, delete)
- Full-text search with indexing
- Cognitive amplification features:
  - Proactive content surfacing
  - Temporal relationship detection
  - Socratic question generation
  - Spaced repetition scheduling
  - Pattern detection

## Quick Start

1. Install dependencies:
   ```bash
   pip install -r api/requirements.txt
   ```

2. Start the API server:
   ```bash
   ./start_api.sh
   ```

3. The API will be available at `http://localhost:8000`

## Documentation

See [API Documentation](docs/api.md) for detailed information about endpoints and usage.

## Testing

Run the test suite:
```bash
pytest tests/test_api.py
```