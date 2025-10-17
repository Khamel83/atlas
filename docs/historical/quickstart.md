# Atlas Quickstart Guide

This guide provides a quick overview of how to get started with Atlas.

## 1. Setup

Atlas requires Python 3.12 and a virtual environment. Ensure you have `git` installed.

```bash
# Clone the repository
git clone https://github.com/your-repo/atlas.git
cd atlas

# Create and activate a virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies (minimal for now)
pip install -r requirements.txt

# Run the diagnostic script to check your environment
./venv/bin/python scripts/diagnose_environment.py
```

## 2. Running Atlas Services

Atlas runs as a set of background services managed by `atlas_service_manager.py`.

```bash
# Start all Atlas services
./venv/bin/python atlas_service_manager.py start

# Check service status
./venv/bin/python atlas_service_manager.py status

# Stop all Atlas services
./venv/bin/python atlas_service_manager.py stop
```

## 3. Basic Usage (Current Functionality)

Currently, Atlas focuses on content ingestion and processing. More user-friendly interfaces are under development.

### Ingesting Articles (Example)

To ingest articles, you can place URLs in `inputs/articles.txt`.

1. Create the `inputs` directory if it doesn't exist:
   ```bash
   mkdir -p inputs
   ```
2. Add URLs to `inputs/articles.txt`, one URL per line:
   ```
   https://example.com/article1
   https://example.com/article2
   ```
3. The background services will automatically pick up and process these articles.

### Checking Processed Content

Processed articles and their metadata will be stored in the `output/articles/` directory.

## 4. Troubleshooting

If you encounter issues, refer to the `TROUBLESHOOTING.md` guide for common problems and solutions.

```bash
# Run system health check
./venv/bin/python helpers/resource_monitor.py

# View detailed service status
./venv/bin/python atlas_status.py --detailed
```

## 5. Future Development

Atlas is actively being developed. Future phases will focus on:
- Enhanced user interfaces (web dashboard, mobile apps)
- Advanced content analysis and cognitive features
- Improved Apple product integration for seamless data transfer
- Comprehensive user-facing documentation and tutorials
- Streamlined file organization

Stay tuned for updates!
