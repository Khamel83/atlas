# Atlas Portability Guide

## Environment Variables for Path Configuration

Atlas now supports configurable paths through environment variables for better portability:

### Core Paths
- `ATLAS_ROOT`: Main Atlas directory (default: `/home/ubuntu/dev/atlas`)
- `ATLAS_BACKUP_DIR`: Backup storage directory (default: `${ATLAS_ROOT}/backups`)
- `ATLAS_BACKUP_KEY_PATH`: Encryption key location (default: `${ATLAS_BACKUP_DIR}/.backup_key`)
- `ATLAS_TEMP_DIR`: Temporary files directory (default: `/tmp`)
- `ATLAS_SSH_DIR`: SSH configuration directory (default: `~/.ssh`)

### Usage for Different Environments

#### Development Environment
```bash
export ATLAS_ROOT="/Users/username/atlas"
export ATLAS_BACKUP_DIR="/Users/username/atlas-backups"
```

#### Production Environment
```bash
export ATLAS_ROOT="/opt/atlas"
export ATLAS_BACKUP_DIR="/var/backups/atlas"
export ATLAS_TEMP_DIR="/var/tmp/atlas"
```

#### Docker Environment
```bash
export ATLAS_ROOT="/app/atlas"
export ATLAS_BACKUP_DIR="/data/backups"
export ATLAS_TEMP_DIR="/tmp/atlas"
```

## Files Modified for Portability

The following files have been updated to use environment variables:
- `backup/restore_system.py` - Backup and restore paths
- `BLOCK_14_PROGRESS.py` - Progress tracking paths
- `tests/final_verification_block14.py` - Test file paths
- `backup/database_backup.py` - Temporary file paths
- `backup/local_sync_backup.py` - SSH and temporary paths
- `backup/oci_storage_backup.py` - Temporary file paths

## Benefits

- ✅ **Portable**: Works in any directory structure
- ✅ **Configurable**: Easy to adapt for different environments
- ✅ **Secure**: SSH and key paths can be customized
- ✅ **Docker-friendly**: No hardcoded host paths
- ✅ **Multi-user**: Each user can configure their own paths
