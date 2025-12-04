# Atlas Setup Guide

**Last Updated**: 2025-12-04
**Status**: 🔄 Active Development

## Prerequisites

- Python 3.8+
- Git
- 2GB+ free disk space
- Ubuntu 24.04 LTS or macOS

## Quick Start

```bash
# 1. Clone and enter directory
git clone <repository-url>
cd atlas

# 2. Create virtual environment and install dependencies
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 3. Configure environment
cp .env.template .env
# Edit .env with your configuration

# 4. Check status
./atlas_status.sh

# 5. Start processing (if needed)
python3 processors/atlas_manager.py
```

## Data Directory Structure

### Version-Controlled (IN git)
- `config/` - Configuration YAML/JSON
- `processors/`, `modules/`, `src/` - Code
- `README.md`, `docs/` - Documentation

### Runtime Data (NOT in git)
Generated during operation, excluded via `.gitignore`:

```
html/                    # Generated HTML content  
markdown/                # Generated markdown
metadata/                # Generated JSON metadata
data for atlas/          # Imported data
atlas_content/           # Processing artifacts
*.db                     # SQLite databases
content_tracker.json     # Content tracking
```

**Why excluded?**
- Large size (100s of MB+)
- Generated/derived data
- User-specific content
- Binary formats

## Environment Configuration

Copy `.env.template` to `.env`:

```bash
# Required paths
QUEUE_ROOT=data/queue
DATABASE_PATH=data/atlas_vos.db

# Optional API keys
GMAIL_USERNAME=your-email@gmail.com
ATLAS_API_KEY=your-key-here
```

## Troubleshooting

### Database locked
```bash
# Kill running processes
pkill -f atlas_manager
# Restart
./scripts/start/start_atlas.sh
```

### Module not found
```bash
source venv/bin/activate
pip install -r requirements.txt
```

### Permission denied
```bash
chmod +x atlas_status.sh
chmod +x scripts/start/start_atlas.sh
```

## Current Architecture

**Tier**: SQLite + File-based processing
**Upgrade Trigger**: > 500K episodes OR multi-instance needed
**Next Tier**: PostgreSQL + connection pooling

---

See `docs/CURRENT_ARCHITECTURE.md` for details (TODO)
