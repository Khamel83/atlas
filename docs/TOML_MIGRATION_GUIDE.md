# TOML Migration Guide for Atlas

## Overview

This guide documents the migration from JSON to TOML configuration format for the Atlas podcast transcript discovery system. The migration is designed to be reversible with comprehensive fallback mechanisms.

## Migration Date

**Completed:** November 12, 2025

## Files Changed

### Configuration Files
- **BEFORE:** `atlas_relayq_config.json` (JSON format)
- **AFTER:** `atlas_config.toml` (TOML format)
- **ADDED:** `pyproject.toml` (Python project configuration)

### Code Files
- **MODIFIED:** `relayq_service_setup.py` (added TOML support)
- **ADDED:** `config_manager.py` (configuration management with fallback)

## What Was Migrated

### 1. Main Configuration (`atlas_config.toml`)

```toml
# Service metadata
[service]
name = "Atlas RelayQ Integration"
version = "1.0.0"

# Atlas-specific settings
[atlas]
database_path = "/home/ubuntu/dev/atlas/podcast_processing.db"
podcasts_count = 73
episodes_count = 2373

# RelayQ integration
[relayq]
repository = "Khamel83/relayq"
workflow_file = "atlas_podcast_processing.yml"
job_labels = ["atlas-podcast", "transcript-discovery"]
auto_schedule = "0 */4 * * *"

# Processing parameters
[processing]
batch_size = 10
retry_attempts = 3
priority_levels = 5
supported_tasks = [
    "transcript-discovery",
    "episode-backlog",
    "podcast-monitoring",
    "batch-processing"
]

# API endpoints
[endpoints]
github_api = "https://api.github.com"
relayq_repo = "https://github.com/Khamel83/relayq"
atlas_status = "sqlite:///home/ubuntu/dev/atlas/podcast_processing.db"
```

### 2. Project Configuration (`pyproject.toml`)

- **Project metadata**: name, version, description, authors
- **Dependencies**: requests, feedparser, tomli (for Python <3.11)
- **Development tools**: pytest, black, mypy, flake8
- **Atlas-specific configuration**: default values, module settings
- **Tool configurations**: black, mypy, pytest

## Benefits of TOML

1. **Human-Readable**: Cleaner syntax with comments support
2. **Better for Configuration**: Designed specifically for config files
3. **Comments**: Can document configuration choices inline
4. **Industry Standard**: Aligns with modern Python packaging (PEP 518)
5. **Less Verbose**: No curly braces or quotes for simple values

## Rollback Procedure

### Quick Rollback (JSON Restoration)

1. **Restore JSON configuration:**
   ```bash
   cp config_backup/atlas_relayq_config.json ./
   ```

2. **Remove TOML files:**
   ```bash
   rm -f atlas_config.toml pyproject.toml
   ```

3. **Revert Python code:**
   ```bash
   # Remove TOML-specific imports in relayq_service_setup.py
   # Remove config_manager.py
   rm config_manager.py
   ```

### Complete Rollback

If you need to completely revert the migration:

```bash
# 1. Restore original JSON config
cp config_backup/atlas_relayq_config.json ./

# 2. Remove TOML files
rm -f atlas_config.toml pyproject.toml

# 3. Remove config manager
rm config_manager.py

# 4. Revert relayq_service_setup.py
git checkout HEAD~1 -- relayq_service_setup.py
```

## Testing the Migration

### 1. Verify TOML Loading
```bash
python3 -c "
from config_manager import AtlasConfig
config = AtlasConfig()
data = config.load_config()
print('✅ TOML loaded successfully')
print(f'Format: {config.get_source_format()}')
print(f'Atlas database: {data[\"atlas\"][\"database_path\"]}')
"
```

### 2. Test Fallback Mechanism
```bash
# Temporarily rename TOML to test JSON fallback
mv atlas_config.toml atlas_config.toml.bak

python3 -c "
from config_manager import AtlasConfig
config = AtlasConfig()
data = config.load_config(prefer_toml=False)
print(f'✅ Fallback works: {config.get_source_format()}')
"

# Restore TOML
mv atlas_config.toml.bak atlas_config.toml
```

### 3. Run Existing Scripts
```bash
# Test that existing functionality still works
python3 relayq_service_setup.py
```

## Dependencies

### Required for TOML Support
- **Python 3.11+**: Built-in `tomllib` module
- **Python <3.11**: `pip install tomli` (already in pyproject.toml)

### Optional Development Dependencies
- `pytest` - for testing
- `black` - for code formatting
- `mypy` - for type checking

## Migration Script

If you need to redo the migration, use the built-in functionality:

```python
from config_manager import AtlasConfig

# Initialize config manager
config = AtlasConfig()

# Migrate JSON to TOML (with backup)
success = config.migrate_to_toml(backup=True)
if success:
    print("✅ Migration completed")
else:
    print("❌ Migration failed")
```

## Validation

The `config_manager.py` includes validation:

```python
from config_manager import AtlasConfig

config = AtlasConfig()
data = config.load_config()
is_valid = config.validate_config(data)
```

**Validates:**
- Required sections exist (`atlas`, `relayq`, `processing`, `endpoints`)
- Database path is specified
- Database file accessibility (warning if not found)

## Troubleshooting

### TOML Library Not Found
```bash
# For Python <3.11
pip install tomli
```

### Configuration Loading Issues
```bash
# Check current format
python3 -c "
from config_manager import AtlasConfig
config = AtlasConfig()
print(f'Current format: {config.get_source_format()}')
"
```

### Syntax Errors in TOML
- Check for proper quoting of string values
- Ensure arrays use proper bracket syntax
- Use double quotes for strings with special characters

## Future Maintenance

### Adding New Configuration

1. **TOML format:**
   ```toml
   [new_section]
   setting = "value"
   number = 42
   list = ["item1", "item2"]
   ```

2. **Access in code:**
   ```python
   config = AtlasConfig()
   data = config.load_config()
   new_setting = data["new_section"]["setting"]
   ```

### Updating Dependencies

Edit `pyproject.toml` and reinstall:
```bash
pip install -e .
```

## Success Metrics

✅ **Migration Complete:**
- [x] JSON config backed up to `config_backup/`
- [x] TOML configuration created and validated
- [x] Python code updated with TOML support
- [x] Fallback mechanism implemented
- [x] Project configuration modernized with `pyproject.toml`
- [x] Documentation and rollback procedures created

## Contact and Support

For issues with the TOML migration:
1. Check this guide first
2. Use the `config_manager.py` validation tools
3. Rollback to JSON if needed (procedures above)
4. Test thoroughly before production deployment

---

*Migration completed November 12, 2025*